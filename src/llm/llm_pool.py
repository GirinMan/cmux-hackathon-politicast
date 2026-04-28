"""LiteLLM 기반 멀티 프로바이더 LLM 풀 — 키 회전 + RPM 한계 + sqlite 캐시.

지원 공급자: openai, gemini, vertex_ai, anthropic, azure, bedrock, groq, openrouter,
그리고 LiteLLM이 지원하는 모든 모델. 모델 prefix로 자동 라우팅.

환경변수
--------
- ``LITELLM_MODEL``       모델 식별자 (default: ``gemini/gemini-3-flash-preview``)
                          예: ``gpt-4o-mini``, ``claude-haiku-4-5-20251001``,
                          ``azure/<deployment>``, ``vertex_ai/gemini-3-flash``,
                          ``bedrock/anthropic.claude-haiku-4-5-20251001-v1:0``
- ``LLM_API_KEYS``        공급자 무관 키 리스트 (comma-separated). 모든 provider에 동일 적용.
- ``GEMINI_API_KEYS``     Gemini 전용 (legacy 호환)
- ``OPENAI_API_KEYS``     OpenAI 전용
- ``ANTHROPIC_API_KEYS``  Anthropic 전용
- ``AZURE_API_KEYS``      Azure 전용. ``AZURE_API_BASE`` + ``AZURE_API_VERSION`` 함께 필요.
- ``GROQ_API_KEYS``       Groq 전용
- ``OPENROUTER_API_KEYS`` OpenRouter 전용
- ``LITELLM_API_BASE``    Custom endpoint (proxy/self-hosted)
- ``LLM_PER_KEY_RPM``     키당 1분 RPM 한계 (default 10)

Vertex AI / Bedrock은 IAM 기반 (``GOOGLE_APPLICATION_CREDENTIALS`` /
``AWS_*``)이므로 키 회전 없이 단일 client로 동작합니다.
"""
from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import orjson
from dotenv import load_dotenv
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_PATH = REPO_ROOT / "_workspace" / "db" / "llm_cache.sqlite"

# .env 를 모듈 import 시점에 로드 — DEFAULT_MODEL / DEV_OVERRIDE_MODEL 등
# module-level 상수가 평가되기 전에 LITELLM_* 환경변수가 채워져야 한다.
# override=False 라 shell export 가 우선되며, 누락된 키만 .env 에서 보충.
load_dotenv(REPO_ROOT / ".env", override=False)

DEFAULT_MODEL = os.environ.get(
    "LITELLM_MODEL",
    os.environ.get("GEMINI_MODEL", "gemini/gemini-3.1-flash-lite-preview"),
)
DEFAULT_PER_KEY_RPM = int(
    os.environ.get("LLM_PER_KEY_RPM", os.environ.get("GEMINI_PER_KEY_RPM", "500"))
)

# Dev mode 강제 라우팅 — POLITIKAST_ENV=dev면 모든 호출이 Gemini Flash(무료)로
DEV_OVERRIDE_MODEL = os.environ.get(
    "DEV_OVERRIDE_MODEL", "gemini/gemini-3.1-flash-lite-preview"
)


def _is_dev_mode() -> bool:
    return os.environ.get("POLITIKAST_ENV", "prod").lower() == "dev"


def _disable_thinking_kwargs(provider: str, model: str) -> dict[str, Any]:
    """Provider별 thinking 비활성화 인자.

    - OpenAI gpt-5.x / o-series : ``reasoning_effort="none"``
    - Anthropic claude         : ``thinking={"type":"disabled"}`` (default도 동일)
    - Gemini 3.x               : ``thinkingConfig.thinkingBudget=0`` (lite는 default 0)
    """
    m = model.lower()
    if provider == "openai" and (
        m.startswith(("gpt-5", "o1", "o3", "o4")) or "/gpt-5" in m or "/o1" in m
    ):
        return {"reasoning_effort": "none"}
    if provider == "anthropic":
        return {"thinking": {"type": "disabled"}}
    if provider in ("gemini", "vertex_ai"):
        # LiteLLM은 generationConfig를 model-specific하게 패스스루
        return {
            "thinking_config": {"thinking_budget": 0},
            "generationConfig": {"thinkingConfig": {"thinkingBudget": 0}},
        }
    return {}


# ---------------------------------------------------------------------------
# Provider derivation
# ---------------------------------------------------------------------------
# SoT: `_workspace/contracts/llm_strategy.json` 의 supported_providers 리스트.
# 컨트랙트 로드에 실패하면 보수적인 fallback 으로 빌드 진행을 허용한다 (해커톤
# 운영 안정성 우선 — JSON 스키마 검증은 scripts/export_jsonschema.py 에서 따로 수행).
_FALLBACK_PROVIDER_KEY_ENV: dict[str, str] = {
    "openai": "OPENAI_API_KEYS",
    "gemini": "GEMINI_API_KEYS",
    "anthropic": "ANTHROPIC_API_KEYS",
    "azure": "AZURE_API_KEYS",
    "groq": "GROQ_API_KEYS",
    "openrouter": "OPENROUTER_API_KEYS",
    # vertex_ai, bedrock: IAM 기반 — 별도 env 불필요
}


def _load_provider_key_env() -> dict[str, str]:
    try:
        from src.schemas.llm_strategy import provider_key_env_map  # type: ignore

        mapping = provider_key_env_map()
        if mapping:
            return mapping
    except Exception as e:  # pragma: no cover — contract 부재 시 fallback
        logger.warning(
            "llm_strategy contract 로드 실패 — fallback PROVIDER_KEY_ENV 사용: %s", e
        )
    return dict(_FALLBACK_PROVIDER_KEY_ENV)


PROVIDER_KEY_ENV: dict[str, str] = _load_provider_key_env()


def _derive_provider(model: str) -> str:
    """LiteLLM 모델 문자열에서 provider 추론."""
    m = model.lower()
    if m.startswith("vertex_ai/") or m.startswith("vertex/"):
        return "vertex_ai"
    if m.startswith(("gemini/", "google/")):
        return "gemini"
    if m.startswith("anthropic/") or m.startswith("claude"):
        return "anthropic"
    if m.startswith("azure/"):
        return "azure"
    if m.startswith("bedrock/"):
        return "bedrock"
    if m.startswith("groq/"):
        return "groq"
    if m.startswith("openrouter/"):
        return "openrouter"
    if m.startswith(("openai/", "gpt-", "gpt", "o1", "o3", "o4", "text-", "chatgpt")):
        return "openai"
    return "openai"


def _provider_uses_keys(provider: str) -> bool:
    """Vertex/Bedrock은 IAM 기반이라 키 회전 의미 없음."""
    return provider in PROVIDER_KEY_ENV


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class LLMPoolError(RuntimeError):
    """LLMPool 일반 예외."""


class RateLimitError(LLMPoolError):
    """429 / RESOURCE_EXHAUSTED."""


class NetworkError(LLMPoolError):
    """transient network/connection 오류."""


class LLMCostThresholdError(LLMPoolError):
    """누적 비용이 provider별 threshold를 초과 — 즉시 abort (retry 대상 아님).

    prod fire 직후 비용 폭주 방지용 핵심 가드.
    """


# ---------------------------------------------------------------------------
# Cost thresholds (env에서 읽기, 기본값은 보수적)
# ---------------------------------------------------------------------------
def _load_cost_thresholds() -> dict[str, float]:
    """Provider별 누적 비용 임계 (USD). env 미설정 시 inf (가드 비활성)."""

    def _read(name: str, default: float = float("inf")) -> float:
        raw = os.environ.get(name, "").strip()
        if not raw:
            return default
        try:
            return float(raw)
        except ValueError:
            logger.warning("Invalid cost threshold %s=%r — fallback inf", name, raw)
            return default

    return {
        "openai": _read("LLM_COST_THRESHOLD_OPENAI_USD"),
        "anthropic": _read("LLM_COST_THRESHOLD_ANTHROPIC_USD"),
        "gemini": _read("LLM_COST_THRESHOLD_GEMINI_USD"),
        "vertex_ai": _read("LLM_COST_THRESHOLD_GEMINI_USD"),
        "azure": _read("LLM_COST_THRESHOLD_OPENAI_USD"),
        "bedrock": _read("LLM_COST_THRESHOLD_ANTHROPIC_USD"),
        "groq": _read("LLM_COST_THRESHOLD_OPENAI_USD"),
        "openrouter": _read("LLM_COST_THRESHOLD_OPENAI_USD"),
    }


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
class _SqliteCache:
    """messages_hash + model 키를 영구 보관하는 sqlite K/V 캐시."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_cache (
                    cache_key TEXT PRIMARY KEY,
                    model TEXT NOT NULL,
                    response TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            self._conn.commit()

    @staticmethod
    def make_key(messages: list[dict[str, Any]], model: str, extra: dict[str, Any]) -> str:
        payload = orjson.dumps(
            {"m": messages, "model": model, "extra": extra},
            option=orjson.OPT_SORT_KEYS,
        )
        return hashlib.sha256(payload).hexdigest()

    def get(self, key: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT response FROM llm_cache WHERE cache_key = ?", (key,)
            ).fetchone()
        return row[0] if row else None

    def put(self, key: str, model: str, response: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO llm_cache (cache_key, model, response, created_at) "
                "VALUES (?, ?, ?, ?)",
                (key, model, response, time.time()),
            )
            self._conn.commit()


# ---------------------------------------------------------------------------
# Per-key state
# ---------------------------------------------------------------------------
@dataclass
class _KeyState:
    api_key: str | None  # None for IAM-based providers (vertex/bedrock)
    rpm_window: deque[float] = field(default_factory=deque)
    total_calls: int = 0
    total_429: int = 0


# ---------------------------------------------------------------------------
# Pool
# ---------------------------------------------------------------------------
class LLMPool:
    """멀티 프로바이더 LLM 풀 — round-robin 키 회전 + RPM rate-limit + sqlite 캐시.

    사용 예::

        pool = LLMPool()                                   # env에서 모델/키 자동 로드
        pool = LLMPool(model="claude-haiku-4-5-20251001")  # provider 자동 추론
        pool = LLMPool(api_keys=["k1", "k2"], model="gemini/gemini-3-flash-preview")
        text = pool.chat([{"role": "user", "content": "ping"}])
    """

    def __init__(
        self,
        api_keys: list[str] | None = None,
        model: str = DEFAULT_MODEL,
        per_key_rpm: int = DEFAULT_PER_KEY_RPM,
        cache_path: Path = DEFAULT_CACHE_PATH,
        env_path: Path | None = None,
        api_base: str | None = None,
    ) -> None:
        # 1) .env 로드
        if env_path is None:
            env_path = REPO_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False)

        self.model = model
        self.provider = _derive_provider(model)
        self.per_key_rpm = per_key_rpm
        self.api_base = api_base or os.environ.get("LITELLM_API_BASE")

        # 2) 키 수집
        if api_keys is None:
            api_keys = self._collect_keys(self.provider)

        # 3) IAM 기반 provider면 키 없이 단일 state
        if not api_keys:
            if _provider_uses_keys(self.provider):
                raise LLMPoolError(
                    f"No API keys found for provider '{self.provider}'. "
                    f"Set {PROVIDER_KEY_ENV.get(self.provider, 'LLM_API_KEYS')}=k1,k2,... in .env"
                )
            # vertex_ai / bedrock: IAM 기반 단일 클라이언트
            self._states = [_KeyState(api_key=None)]
            logger.info(
                "LLMPool: provider=%s in IAM mode (no key rotation).", self.provider
            )
        else:
            self._states = [_KeyState(api_key=k) for k in api_keys]
            logger.info(
                "LLMPool: provider=%s, model=%s, keys=%d, per_key_rpm=%d",
                self.provider,
                self.model,
                len(self._states),
                self.per_key_rpm,
            )

        self._rr_idx = 0
        self._lock = threading.Lock()

        self._cache = _SqliteCache(cache_path)
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_calls = 0

        # 비용 누적 — provider별 USD. dev 모드는 무료 가정으로 계산 자체 skip.
        self._cost_thresholds: dict[str, float] = _load_cost_thresholds()
        self._provider_cost_usd: dict[str, float] = {
            p: 0.0 for p in self._cost_thresholds
        }

    # ------------------------------------------------------------------
    # Key collection
    # ------------------------------------------------------------------
    @staticmethod
    def _collect_keys(provider: str) -> list[str]:
        """공급자별 env → 일반 ``LLM_API_KEYS`` 순서로 키 수집."""
        # 1) provider-specific
        env_var = PROVIDER_KEY_ENV.get(provider)
        if env_var:
            raw = os.environ.get(env_var, "")
            keys = [k.strip() for k in raw.split(",") if k.strip()]
            if keys:
                return keys
        # 2) 일반 LLM_API_KEYS
        raw = os.environ.get("LLM_API_KEYS", "")
        keys = [k.strip() for k in raw.split(",") if k.strip()]
        return keys

    # ------------------------------------------------------------------
    # Key selection / rate limiting
    # ------------------------------------------------------------------
    def _prune_window(self, state: _KeyState, now: float) -> None:
        cutoff = now - 60.0
        while state.rpm_window and state.rpm_window[0] < cutoff:
            state.rpm_window.popleft()

    def _key_available(self, state: _KeyState, now: float) -> bool:
        self._prune_window(state, now)
        return len(state.rpm_window) < self.per_key_rpm

    def _next_key(self) -> _KeyState:
        n = len(self._states)
        while True:
            with self._lock:
                now = time.time()
                for i in range(n):
                    idx = (self._rr_idx + i) % n
                    state = self._states[idx]
                    if self._key_available(state, now):
                        self._rr_idx = (idx + 1) % n
                        state.rpm_window.append(now)
                        return state
                soonest = min(
                    (s.rpm_window[0] for s in self._states if s.rpm_window),
                    default=now,
                )
                wait = max(0.05, (soonest + 60.0) - now)
            time.sleep(min(wait, 5.0))

    def _release_slot(self, state: _KeyState) -> None:
        with self._lock:
            if state.rpm_window:
                state.rpm_window.pop()

    # ------------------------------------------------------------------
    # Cost tracking
    # ------------------------------------------------------------------
    def _enforce_cost_threshold(self, provider: str) -> None:
        """Provider 누적 비용이 threshold 초과면 LLMCostThresholdError raise.

        dev 모드(POLITIKAST_ENV=dev)에서는 비용 추적 자체를 skip하므로 항상 통과.
        """
        if _is_dev_mode():
            return
        threshold = self._cost_thresholds.get(provider, float("inf"))
        used = self._provider_cost_usd.get(provider, 0.0)
        if used >= threshold:
            raise LLMCostThresholdError(
                f"Cost threshold exceeded for provider '{provider}': "
                f"used=${used:.4f} >= threshold=${threshold:.4f}. "
                "실행 중단 — prod fire 방지 가드."
            )

    def _record_cost(self, provider: str, resp: Any) -> float:
        """LiteLLM 응답에서 비용 추출 후 누적. 인식 실패 시 0 fallback + warn.

        dev 모드는 추적 skip ($0 가정).
        반환: 이번 호출의 비용 (USD).
        """
        if _is_dev_mode():
            return 0.0
        try:
            import litellm  # type: ignore

            call_cost = float(litellm.completion_cost(completion_response=resp))
        except Exception as e:
            logger.warning(
                "completion_cost() 실패 (provider=%s): %s — 0 fallback", provider, e
            )
            call_cost = 0.0
        if call_cost < 0:
            call_cost = 0.0
        with self._lock:
            self._provider_cost_usd[provider] = (
                self._provider_cost_usd.get(provider, 0.0) + call_cost
            )
        return call_cost

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.7,
        max_output_tokens: int = 512,
        json_mode: bool = True,
        system_instruction: str | None = None,
        cache: bool = True,
        model: str | None = None,
        source_id: str | None = None,
        prompt_version: str | None = None,
        **extra: Any,
    ) -> str:
        """OpenAI-스타일 messages → 응답 텍스트.

        ``messages = [{"role": "system"|"user"|"assistant", "content": "..."}]``
        ``system_instruction`` 명시 시 system 메시지 앞에 prepend.
        ``model`` per-call override (persona-conditional voter, separate interview model 등).
        명시 없으면 ``self.model`` 사용. dev 모드면 어쨌든 DEV_OVERRIDE_MODEL로 덮어씀.

        ``source_id`` / ``prompt_version`` 은 sqlite cache key 에 포함되어
        adapter 별 cache 격리를 보장한다 (news_article / perplexity / resolver
        동일 prompt 라도 source_id 가 다르면 별도 entry).
        """
        # source_id / prompt_version 을 extra 로 병합 — cache_extra 에서 사용.
        if source_id is not None:
            extra.setdefault("source_id", source_id)
        if prompt_version is not None:
            extra.setdefault("prompt_version", prompt_version)
        # 1) system_instruction 병합
        chat_msgs: list[dict[str, Any]] = []
        if system_instruction:
            chat_msgs.append({"role": "system", "content": str(system_instruction)})
        for m in messages:
            role = m.get("role", "user")
            chat_msgs.append({"role": role, "content": str(m.get("content", ""))})

        # 2) per-call model override → dev mode override 순으로 적용
        effective_model = model or self.model
        effective_provider = _derive_provider(effective_model)
        if _is_dev_mode():
            effective_model = DEV_OVERRIDE_MODEL
            effective_provider = _derive_provider(effective_model)

        # 3) 비용 사전 체크 — 직전 호출에서 임계 도달했으면 즉시 abort.
        #    cache hit/miss 모두 동일하게 막아야 함 (cache hit는 비용 0이지만,
        #    이미 임계를 넘은 상태면 후속 시도를 차단해 안전 동작).
        self._enforce_cost_threshold(effective_provider)

        # 4) 캐시 키
        cache_extra = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "json_mode": json_mode,
            "provider": effective_provider,
            **{k: v for k, v in extra.items() if isinstance(v, (str, int, float, bool))},
        }
        cache_key = _SqliteCache.make_key(chat_msgs, effective_model, cache_extra)

        # 5) 캐시 hit
        if cache:
            hit = self._cache.get(cache_key)
            if hit is not None:
                with self._lock:
                    self._cache_hits += 1
                return hit

        with self._lock:
            self._cache_misses += 1
            self._total_calls += 1

        # 5) 키 선점 + 호출
        state = self._next_key()
        try:
            text = self._call_with_retry(
                state=state,
                messages=chat_msgs,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
                extra=extra,
                model=effective_model,
                provider=effective_provider,
            )
        except Exception:
            raise
        else:
            state.total_calls += 1
            if cache:
                self._cache.put(cache_key, effective_model, text)
            return text

    @retry(
        reraise=True,
        retry=retry_if_exception_type((RateLimitError, NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1.0, min=1.0, max=10.0),
    )
    def _call_with_retry(
        self,
        *,
        state: _KeyState,
        messages: list[dict[str, Any]],
        temperature: float,
        max_output_tokens: int,
        json_mode: bool,
        extra: dict[str, Any],
        model: str | None = None,
        provider: str | None = None,
    ) -> str:
        # litellm import는 lazy — 호스트(컨테이너 외부)에서 모듈 import 시 실패 회피
        try:
            import litellm  # type: ignore
            from litellm.exceptions import (  # type: ignore
                APIConnectionError,
                APIError,
                BadRequestError,
                RateLimitError as _LiteRateLimitError,
                ServiceUnavailableError,
                Timeout,
            )
        except Exception as e:  # pragma: no cover
            raise LLMPoolError(f"litellm not installed: {e}") from e

        eff_model = model or self.model
        eff_provider = provider or self.provider

        kwargs: dict[str, Any] = {
            "model": eff_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        # API 키 라우팅 — eff_provider가 self.provider와 다르면(per-call cross-provider
        # override, dev mode → Gemini 등) `state.api_key`는 잘못된 provider의 키이므로
        # eff_provider의 env에서 직접 fetch한다. 같은 provider면 state 그대로.
        if eff_provider == self.provider and state.api_key:
            kwargs["api_key"] = state.api_key
        elif _provider_uses_keys(eff_provider):
            override_keys = self._collect_keys(eff_provider)
            if not override_keys:
                env_var = PROVIDER_KEY_ENV.get(eff_provider, "?")
                if _is_dev_mode():
                    raise LLMPoolError(
                        f"POLITIKAST_ENV=dev이지만 {env_var} 미설정. "
                        "사용자에게 보고 필요 — Gemini 키 갱신 또는 prod 모드 전환."
                    )
                raise LLMPoolError(
                    f"Per-call provider override를 '{eff_provider}'로 시도했으나 "
                    f"{env_var}에 키가 없음. .env 갱신 필요."
                )
            kwargs["api_key"] = override_keys[0]  # 단순 round-robin (state는 init provider 기준)
        # IAM 기반 (vertex_ai/bedrock)은 키 인자 없이 동작
        if self.api_base:
            kwargs["api_base"] = self.api_base
        # Azure 추가 인자
        if eff_provider == "azure":
            api_version = os.environ.get("AZURE_API_VERSION")
            if api_version:
                kwargs["api_version"] = api_version
            api_base = os.environ.get("AZURE_API_BASE")
            if api_base and not self.api_base:
                kwargs["api_base"] = api_base
        # Thinking 비활성화 — 사용자 결정 ("모든 모델 thinking 강제 off")
        kwargs.update(_disable_thinking_kwargs(eff_provider, eff_model))
        # extras 중 LiteLLM이 인식하는 일부 패스스루
        for k in ("top_p", "frequency_penalty", "presence_penalty", "stop", "seed"):
            if k in extra:
                kwargs[k] = extra[k]

        try:
            resp = litellm.completion(**kwargs)
        except _LiteRateLimitError as e:
            state.total_429 += 1
            raise RateLimitError(str(e)) from e
        except (APIConnectionError, ServiceUnavailableError, Timeout) as e:
            raise NetworkError(str(e)) from e
        except (BadRequestError, APIError) as e:
            msg = str(e).lower()
            if any(s in msg for s in ("429", "quota", "rate", "resource_exhausted")):
                state.total_429 += 1
                raise RateLimitError(str(e)) from e
            raise

        # 비용 누적 (dev 모드는 skip). prod에서 임계 초과 시 다음 호출에서 throw.
        self._record_cost(eff_provider, resp)

        try:
            text = resp["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            text = getattr(
                getattr(resp.choices[0], "message", None), "content", None
            )
        if not text:
            raise LLMPoolError("Empty response from LLM.")
        return str(text)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        now = time.time()
        per_key = []
        with self._lock:
            for i, s in enumerate(self._states):
                self._prune_window(s, now)
                per_key.append(
                    {
                        "key_index": i,
                        "current_rpm": len(s.rpm_window),
                        "limit_rpm": self.per_key_rpm,
                        "total_calls": s.total_calls,
                        "total_429": s.total_429,
                    }
                )
            cost_usd = dict(self._provider_cost_usd)
            cost_thresholds = dict(self._cost_thresholds)
            return {
                "provider": self.provider,
                "model": self.model,
                "per_key": per_key,
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "total_calls": self._total_calls,
                "n_keys": len(self._states),
                "iam_mode": self._states[0].api_key is None if self._states else False,
                "cost_usd": cost_usd,
                "cost_thresholds": cost_thresholds,
                "cost_tracking_enabled": not _is_dev_mode(),
            }


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    pool = LLMPool()
    out = pool.chat(
        [
            {
                "role": "system",
                "content": "Reply with strict JSON only: {\"ok\": true}.",
            },
            {"role": "user", "content": "ping"},
        ],
        max_output_tokens=64,
    )
    print("[smoke] response:", out[:200])
    print("[smoke] stats:", pool.stats())
