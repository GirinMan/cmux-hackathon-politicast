"""VoterAgent — async persona-conditioned vote sampler.

Backend strategy (per `_workspace/contracts/llm_strategy.json`):
  * Plan A (default): LiteLLM-based `src.llm.llm_pool.LLMPool` — 모든 공급자
    (openai/gemini/anthropic/azure/vertex_ai/bedrock/groq/openrouter/...)
    지원, `LITELLM_MODEL` 환경변수로 즉시 스왑. 키 회전 + RPM + sqlite 캐시.
  * Plan B (선택): CAMEL `ChatAgent` with `ModelType.GEMINI_3_FLASH`,
    `response_format={"type": "json_object"}`. CAMEL framework의 ChatAgent
    상태/도구 호출이 필요할 때 `POLITIKAST_LLM_BACKEND=camel` 명시.

Both backends produce a parsed dict matching `voter_response_schema`:
    {"vote": str|None, "turnout": bool, "confidence": float,
     "reason": str, "key_factors": [str, ...]}
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Iterable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Persona-conditional model routing
# ---------------------------------------------------------------------------
# 사용자 결정 (12:11): D 옵션 + 학력 cutoff = bachelor.
# 라우팅 정책은 src.sim.routing 의 RoutingStrategy 로 분리되어 있다.
# 본 모듈의 정상 경로는 ``DEFAULT_ROUTING.model_for(persona)`` 호출이며,
# legacy import 호환을 위해 thin shim 도 노출한다.
from src.sim.routing import (  # noqa: E402
    DEFAULT_BACHELOR_KEYWORDS as EDU_BACHELOR_KEYWORDS,  # legacy alias
    DEFAULT_ROUTING,
    RoutingStrategy,
)


def _is_educated(persona: dict[str, Any]) -> bool:
    """학사 이상 여부 (legacy shim — RoutingStrategy 로 위임)."""
    return DEFAULT_ROUTING.is_educated(persona)  # type: ignore[attr-defined]


def _model_for_persona(persona: dict[str, Any]) -> str:
    """Persona 학력에 따라 LiteLLM 모델 식별자 반환 (RoutingStrategy 위임)."""
    return DEFAULT_ROUTING.model_for(persona)


# ---------------------------------------------------------------------------
# Response shape + abstain fallback
# ---------------------------------------------------------------------------
ABSTAIN_RESPONSE: dict[str, Any] = {
    "vote": None,
    "turnout": False,
    "confidence": 0.0,
    "reason": "LLM 응답 파싱 실패 — 기권 처리",
    "key_factors": ["llm_error"],
}


def _parse_voter_json(text: str, valid_candidate_ids: Iterable[str]) -> dict[str, Any]:
    """Extract JSON object from raw text and validate vote field."""
    if not text:
        raise ValueError("empty LLM text")
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Salvage first {...} block
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise
        data = json.loads(m.group(0))

    valid = set(valid_candidate_ids)
    vote = data.get("vote")
    if vote in ("기권", "abstain", "미정", "undecided", "", "null"):
        vote = None
    elif vote not in valid:
        # Try fuzzy match against candidate names provided by upstream caller —
        # but we only know IDs here. Fall through; downstream tally counts as
        # abstain.
        vote = None

    return {
        "vote": vote,
        "turnout": bool(data.get("turnout", vote is not None)),
        "confidence": float(data.get("confidence", 0.5) or 0.5),
        "reason": str(data.get("reason", "") or "")[:300],
        "key_factors": [str(x) for x in (data.get("key_factors") or [])][:3],
    }


# ---------------------------------------------------------------------------
# Backend abstraction
# ---------------------------------------------------------------------------
LLMBackend = Callable[[str, str, dict[str, Any]], Awaitable[str]]
"""Signature: (system_prompt, user_prompt, extras) -> raw text response."""


def make_pool_backend(pool: Any) -> LLMBackend:
    """Wrap the synchronous ``LLMPool.chat`` (or compatible) in an async callable.

    ``pool`` is duck-typed — anything exposing ``.chat(messages, ...) -> str`` works
    (``LLMPool``, legacy ``GeminiPool`` alias, custom mock).
    """

    async def _backend(system_prompt: str, user_prompt: str, extras: dict[str, Any]) -> str:
        def _call() -> str:
            kw: dict[str, Any] = dict(
                # Gemini 3 needs temp ≥ 1.0 (LiteLLM warns at <1.0) AND a generous
                # max_output_tokens because thinking tokens are counted against the
                # output budget — 512 leaves only ~10 chars after thinking on long
                # persona prompts, causing "Unterminated string" parse failures.
                temperature=extras.get("temperature", 1.0),
                max_output_tokens=extras.get("max_output_tokens", 2048),
                json_mode=True,
                cache=extras.get("cache", True),
            )
            # Per-call cross-provider override (persona-conditional voter model,
            # interview Claude, etc.). dev 모드에서는 LLMPool이 DEV_OVERRIDE_MODEL로
            # 강제 라우팅하므로 이 인자는 prod에서만 의미 있음.
            if extras.get("model"):
                kw["model"] = extras["model"]
            return pool.chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                **kw,
            )

        return await asyncio.to_thread(_call)

    return _backend


# Backward-compat alias (older code/tests may still import this name)
make_gemini_pool_backend = make_pool_backend


_MOCK_CANDIDATE_PATTERN = re.compile(
    r"^- (?:\[출마 포기\] )?([a-z][a-z0-9_]+) \|", re.MULTILINE
)


def _build_mock_backend() -> LLMBackend:
    """Deterministic offline backend — used when no LLM provider is reachable.

    Why: Phase 6 build-tree smoke and reproducible tests need a backend that
    works without API keys (CI, offline dev, expired keys). Picks a candidate
    via SHA-1(user_prompt) so the same persona+context always returns the same
    vote, while different prompts spread votes across the roster.
    """
    import hashlib

    async def _backend(
        system_prompt: str, user_prompt: str, extras: dict[str, Any]
    ) -> str:
        ids = _MOCK_CANDIDATE_PATTERN.findall(user_prompt)
        if not ids:
            return json.dumps(
                {
                    "vote": None,
                    "turnout": False,
                    "confidence": 0.5,
                    "reason": "mock backend: no candidates parsed from prompt",
                    "key_factors": ["mock_backend", "no_candidates"],
                },
                ensure_ascii=False,
            )
        h = int(hashlib.sha1(user_prompt.encode("utf-8")).hexdigest(), 16)
        choice = ids[h % len(ids)]
        confidence = 0.50 + ((h >> 8) % 50) / 100.0
        return json.dumps(
            {
                "vote": choice,
                "turnout": True,
                "confidence": round(confidence, 2),
                "reason": "mock backend: deterministic SHA-1(prompt) routing",
                "key_factors": ["mock_backend", "deterministic"],
            },
            ensure_ascii=False,
        )

    return _backend


def try_make_camel_backend() -> LLMBackend | None:
    """Plan A — CAMEL native. Returns None if camel-ai not importable."""
    try:
        from camel.agents import ChatAgent  # type: ignore
        from camel.configs import GeminiConfig  # type: ignore
        from camel.messages import BaseMessage  # type: ignore
        from camel.models import ModelFactory  # type: ignore
        from camel.types import ModelPlatformType, ModelType  # type: ignore
    except Exception:  # pragma: no cover
        logger.warning("camel-ai not importable; Plan A unavailable.")
        return None

    keys = [k.strip() for k in os.environ.get("GEMINI_API_KEYS", "").split(",") if k.strip()]
    if not keys:
        return None

    # One model per key (round-robin)
    models = [
        ModelFactory.create(
            model_platform=ModelPlatformType.GEMINI,
            model_type=ModelType.GEMINI_3_FLASH,
            api_key=k,
            model_config_dict=GeminiConfig(
                temperature=1.0,  # Gemini 3 requires ≥1.0 for stable JSON output
                max_tokens=512,
                response_format={"type": "json_object"},
            ).as_dict(),
            timeout=30.0,
            max_retries=1,
        )
        for k in keys
    ]
    rr_idx = {"i": 0}
    rr_lock = asyncio.Lock()

    async def _backend(system_prompt: str, user_prompt: str, extras: dict[str, Any]) -> str:
        async with rr_lock:
            idx = rr_idx["i"] % len(models)
            rr_idx["i"] += 1
        model = models[idx]
        sys_msg = BaseMessage.make_assistant_message(role_name="KoreanVoter", content=system_prompt)
        agent = ChatAgent(system_message=sys_msg, model=model)
        user_msg = BaseMessage.make_user_message(role_name="Pollster", content=user_prompt)
        try:
            resp = await agent.astep(user_msg)
        except AttributeError:
            # older CAMEL: synchronous step
            resp = await asyncio.to_thread(agent.step, user_msg)
        return resp.msgs[0].content if resp and getattr(resp, "msgs", None) else ""

    return _backend


# ---------------------------------------------------------------------------
# VoterAgent
# ---------------------------------------------------------------------------
@dataclass
class VoterAgent:
    persona: dict[str, Any]
    persona_text: dict[str, Any]
    backend: LLMBackend
    region_label: str = ""
    contest_id: str = ""
    max_attempts: int = 3
    stats: dict[str, Any] = field(
        default_factory=lambda: {
            "calls": 0,
            "parse_fail": 0,
            "abstain": 0,
            "latency_ms_sum": 0.0,  # divide by `calls` for mean
            # Per-model breakdown — populated when extras["model"] is set.
            # Bucket key normalized to short label (nano/mini/sonnet/...) so
            # policy-engineer's voter_model_split report stays compact.
            "calls_by_model": {},
        }
    )

    @property
    def persona_id(self) -> str:
        return str(self.persona.get("uuid") or self.persona.get("id") or id(self))

    # --- Prompt construction -------------------------------------------------
    def system_prompt(self) -> str:
        p = self.persona
        t = self.persona_text or {}
        province = p.get("province") or p.get("region") or "한국"
        district = p.get("district") or p.get("city") or ""
        return (
            "당신은 한국 유권자입니다. 아래 페르소나를 1인칭으로 체화하여 답하세요.\n"
            f"- 거주: {province} {district}\n"
            f"- 연령: {p.get('age', '미상')}, 성별: {p.get('sex', '미상')}\n"
            f"- 직업: {p.get('occupation', '미상')}, 학력: {p.get('education_level', '미상')}\n"
            f"- 가족: {p.get('marital_status', '미상')}\n"
            "\n=== 서사 ===\n"
            f"{t.get('persona', '')}\n"
            f"{t.get('professional_persona', '')}\n"
            f"{t.get('family_persona', '')}\n"
            f"{t.get('cultural_background', '')}\n"
            "\n=== 규칙 ===\n"
            "1. 제공된 컨텍스트(이슈·이벤트·공개 정보) 외 정보를 사용하지 마세요. "
            "공식 여론조사 target은 보정/검증 label이며 기본적으로 당신에게 제공되지 않습니다.\n"
            "2. 출마를 포기한 후보는 선택할 수 없습니다.\n"
            "3. 미래 결과를 안다고 가정하지 마세요. 페르소나의 가치관·관심사로만 추론하세요.\n"
            "4. 반드시 단일 JSON 객체로만 응답합니다 (코드펜스 금지). 스키마:\n"
            '   {"vote": "<candidate_id|null>", "turnout": true|false, '
            '"confidence": 0.0~1.0, "reason": "<짧은 한 줄>", '
            '"key_factors": ["<핵심 요인 최대 3개>"]}'
        )

    def user_prompt(
        self,
        candidates: list[dict[str, Any]],
        context_block: str,
        timestep: int,
        mode: str,
    ) -> str:
        cand_lines = []
        for c in candidates:
            tag = "[출마 포기] " if c.get("withdrawn") else ""
            party_label = c.get("party_name") or c.get("party") or "무소속"
            head = f"- {tag}{c['id']} | {c.get('name', c['id'])} ({party_label})"
            cand_lines.append(head)
            # Candidate background + key_pledges are high-salience content
            # signals and remain visible even when official poll targets are
            # hidden from the voter prompt.
            bg = (c.get("background") or "").strip()
            if bg:
                if len(bg) > 160:
                    bg = bg[:160] + "…"
                cand_lines.append(f"    배경: {bg}")
            pledges = c.get("key_pledges") or []
            if pledges:
                cand_lines.append(
                    f"    핵심공약: {' · '.join(str(p) for p in pledges[:5])}"
                )
            slogan = (c.get("slogan") or "").strip()
            if slogan:
                cand_lines.append(f"    슬로건: {slogan}")
        mode_block = {
            "secret_ballot": (
                "지금은 투표소 안입니다. 비공개 투표용지에 단 한 명을 기표하세요. "
                "reason은 한 줄로 짧게."
            ),
            "poll_response": (
                "여론조사원이 전화로 묻습니다. 솔직하게 답하되, 마음을 정하지 못했으면 "
                "vote=null로 응답하세요."
            ),
            "virtual_interview": (
                "심층 인터뷰입니다. reason과 key_factors를 충실히 작성하세요."
            ),
        }.get(mode, "선택해 주세요.")
        return (
            f"=== {self.region_label} (timestep t={timestep}) ===\n"
            f"[모드] {mode}\n{mode_block}\n\n"
            "[후보]\n" + "\n".join(cand_lines) + "\n\n"
            f"[컨텍스트 (t≤{timestep})]\n"
            f"{context_block.strip() or '(추가 정보 없음)'}\n"
        )

    # --- Public async API ----------------------------------------------------
    async def vote(
        self,
        candidates: list[dict[str, Any]],
        context_block: str,
        timestep: int,
        *,
        mode: str = "poll_response",
        extras: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        valid_ids = [c["id"] for c in candidates if not c.get("withdrawn")]
        sys_p = self.system_prompt()
        user_p = self.user_prompt(candidates, context_block, timestep, mode)
        ex = dict(extras or {})
        # Persona-conditional voter model. Caller (e.g. ElectionEnv interview wave)
        # may override by passing extras={"model": "<id>"} explicitly — only
        # default if absent.
        if not ex.get("model") and mode in ("poll_response", "secret_ballot"):
            ex["model"] = _model_for_persona(self.persona)
        # virtual_interview wants longer reason → bump tokens further
        if mode == "virtual_interview":
            ex.setdefault("max_output_tokens", 3072)
            ex.setdefault("temperature", 1.0)  # Gemini 3 requires ≥1.0
        # Bucket short label for the per-model counter (nano / mini / sonnet
        # / haiku / gemini / other). Keeps the voter_model_split report human-
        # readable without bloating with full model identifiers.
        model_id = (ex.get("model") or "default").lower()
        if "nano" in model_id:
            bucket = "nano"
        elif "mini" in model_id:
            bucket = "mini"
        elif "sonnet" in model_id:
            bucket = "sonnet"
        elif "haiku" in model_id:
            bucket = "haiku"
        elif "gemini" in model_id or "flash" in model_id:
            bucket = "gemini"
        else:
            bucket = model_id[:24] if model_id != "default" else "default"
        last_err: Exception | None = None
        for attempt in range(self.max_attempts):
            self.stats["calls"] += 1
            cbm = self.stats["calls_by_model"]
            cbm[bucket] = cbm.get(bucket, 0) + 1
            t0 = time.monotonic()
            try:
                raw = await self.backend(sys_p, user_p, ex)
                self.stats["latency_ms_sum"] += (time.monotonic() - t0) * 1000.0
                parsed = _parse_voter_json(raw, valid_ids)
                parsed["_persona_id"] = self.persona_id
                parsed["_timestep"] = timestep
                parsed["_mode"] = mode
                if parsed["vote"] is None:
                    self.stats["abstain"] += 1
                return parsed
            except (json.JSONDecodeError, ValueError) as e:
                self.stats["parse_fail"] += 1
                last_err = e
                # small jitter before retry — gives pool a moment
                await asyncio.sleep(0.2 + random.random() * 0.3)
            except Exception as e:  # pragma: no cover — pool should retry
                last_err = e
                await asyncio.sleep(0.5 + random.random() * 0.5)
        logger.warning(
            "VoterAgent %s: %d attempts failed (%s); abstaining.",
            self.persona_id,
            self.max_attempts,
            last_err,
        )
        out = dict(ABSTAIN_RESPONSE)
        out["_persona_id"] = self.persona_id
        out["_timestep"] = timestep
        out["_mode"] = mode
        self.stats["abstain"] += 1
        return out


# ---------------------------------------------------------------------------
# Backend factory respecting POLITIKAST_LLM_BACKEND env
# ---------------------------------------------------------------------------
def build_default_backend(pool: Any | None = None) -> LLMBackend:
    """Return a backend respecting POLITIKAST_LLM_BACKEND={litellm,camel,auto}.

    Plan A (default) — LiteLLM 기반 ``LLMPool``: 모든 공급자(openai/gemini/
    anthropic/azure/vertex/bedrock/...) 지원, ``LITELLM_MODEL`` 한 줄 변경으로 스왑.
    Plan B (선택) — CAMEL native: ``ChatAgent`` framework의 메모리·툴 콜 등
    필요 시 ``POLITIKAST_LLM_BACKEND=camel`` 명시.

    ``auto`` (default): LiteLLM 풀을 우선 시도, 미설치/키 부재면 CAMEL fallback.
    ``pool``/``litellm``/``llm_pool``: LiteLLM 풀 강제.
    ``camel``/``plan_b``: CAMEL 강제.
    """
    pref = os.environ.get("POLITIKAST_LLM_BACKEND", "auto").lower()

    if pref == "mock":
        logger.info("VoterAgent backend: mock (deterministic, offline).")
        return _build_mock_backend()

    def _build_litellm() -> LLMBackend | None:
        try:
            from src.llm.llm_pool import LLMPool  # type: ignore
        except Exception as e:
            logger.warning("LLMPool import 실패: %s", e)
            return None
        try:
            p = pool if pool is not None else LLMPool()
        except Exception as e:
            logger.warning("LLMPool 인스턴스화 실패: %s", e)
            return None
        return make_pool_backend(p)

    if pref in ("pool", "litellm", "llm_pool", "plan_a", "auto"):
        backend = _build_litellm()
        if backend is not None:
            logger.info("VoterAgent backend: LiteLLM LLMPool (Plan A).")
            return backend
        if pref in ("pool", "litellm", "llm_pool", "plan_a"):
            raise RuntimeError(
                "POLITIKAST_LLM_BACKEND=litellm 명시되었으나 LLMPool 사용 불가."
            )

    if pref in ("camel", "plan_b", "auto"):
        camel = try_make_camel_backend()
        if camel is not None:
            logger.info("VoterAgent backend: CAMEL native (Plan B).")
            return camel
        if pref in ("camel", "plan_b"):
            raise RuntimeError("POLITIKAST_LLM_BACKEND=camel but camel-ai unavailable.")

    raise RuntimeError(
        "어떤 LLM backend도 사용 불가. .env에 LLM_API_KEYS / GEMINI_API_KEYS / "
        "OPENAI_API_KEYS 중 하나를 채우거나 POLITIKAST_LLM_BACKEND=mock 설정."
    )
