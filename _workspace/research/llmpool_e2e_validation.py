"""LLMPool E2E validation — 3 provider 실호출 + dev mode + cache.

실행:
    docker compose run --rm -e POLITIKAST_ENV=dev  app python _workspace/research/llmpool_e2e_validation.py dev
    docker compose run --rm -e POLITIKAST_ENV=prod app python _workspace/research/llmpool_e2e_validation.py prod

결과는 stdout에 JSON으로 출력 (caller가 파싱해서 markdown 리포트로 박제).
prod fire 직전 critical validation이라 모든 예외를 통째로 캡처해 보고.
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# 🚨 KNOWN BUG WORKAROUND (보고만, src 직접 수정은 사용자 결정)
# llm_pool.py의 chat()에서 cache_extra가 effective_provider/effective_model을
# 참조하는데, 정의는 그 아래에서 일어남 → 모든 호출이 UnboundLocalError로 실패.
# E2E provider 호출 자체를 검증하려면 monkey-patch가 필요.
# 환경변수 LLMPOOL_PATCH=1 일 때만 적용해서, 비패치 baseline도 보고에 남김.
# ---------------------------------------------------------------------------
def _apply_unbound_local_patch():
    """chat() 내부 effective_* 변수 정의를 캐시 키 만들기 전으로 이동.

    원본 함수를 통째로 교체. src/llm/llm_pool.py를 직접 수정하지 않음.
    """
    from src.llm.llm_pool import LLMPool, _SqliteCache, _derive_provider, _is_dev_mode, DEV_OVERRIDE_MODEL  # noqa: WPS433

    def chat(
        self,
        messages,
        *,
        temperature=0.7,
        max_output_tokens=512,
        json_mode=True,
        system_instruction=None,
        cache=True,
        model=None,
        **extra,
    ):
        chat_msgs = []
        if system_instruction:
            chat_msgs.append({"role": "system", "content": str(system_instruction)})
        for m in messages:
            role = m.get("role", "user")
            chat_msgs.append({"role": role, "content": str(m.get("content", ""))})

        # ✅ effective_* 먼저 결정
        effective_model = model or self.model
        effective_provider = _derive_provider(effective_model)
        if _is_dev_mode():
            effective_model = DEV_OVERRIDE_MODEL
            effective_provider = _derive_provider(effective_model)

        cache_extra = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "json_mode": json_mode,
            "provider": effective_provider,
            **{k: v for k, v in extra.items() if isinstance(v, (str, int, float, bool))},
        }
        cache_key = _SqliteCache.make_key(chat_msgs, effective_model, cache_extra)

        if cache:
            hit = self._cache.get(cache_key)
            if hit is not None:
                with self._lock:
                    self._cache_hits += 1
                return hit

        with self._lock:
            self._cache_misses += 1
            self._total_calls += 1

        state = self._next_key()
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
        state.total_calls += 1
        if cache:
            self._cache.put(cache_key, effective_model, text)
        return text

    LLMPool.chat = chat


if os.environ.get("LLMPOOL_PATCH") == "1":
    _apply_unbound_local_patch()


def _safe(label: str, fn):
    t0 = time.time()
    try:
        result = fn()
        return {
            "label": label,
            "ok": True,
            "elapsed_s": round(time.time() - t0, 2),
            "result": result,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "label": label,
            "ok": False,
            "elapsed_s": round(time.time() - t0, 2),
            "error_type": type(e).__name__,
            "error": str(e)[:500],
            "trace": traceback.format_exc()[-1500:],
        }


def _truncate(s, n=60):
    if not isinstance(s, str):
        return s
    s = s.replace("\n", " ")
    return s if len(s) <= n else s[:n] + "..."


def _extract_stats(pool):
    try:
        st = pool.stats()
        # 키 trim — sensitive 정보 없음, 길이만 정리
        return {
            "provider": st.get("provider"),
            "model": st.get("model"),
            "cache_hits": st.get("cache_hits"),
            "cache_misses": st.get("cache_misses"),
            "total_calls": st.get("total_calls"),
            "n_keys": st.get("n_keys"),
        }
    except Exception as e:  # noqa: BLE001
        return {"stats_error": str(e)}


def run_dev():
    from src.llm.llm_pool import LLMPool  # noqa: WPS433

    out = {"mode": "dev", "checks": []}

    # 1) gpt-5.4-nano 명시 → dev override로 Gemini로 라우팅
    def _dev_route():
        pool = LLMPool(model="gpt-5.4-nano")
        text = pool.chat(
            [{"role": "user", "content": '한 단어로만 답: 한국 수도? JSON {"answer":"..."}'}],
            max_output_tokens=64,
            temperature=0.0,
        )
        return {
            "init_model": pool.model,
            "init_provider": pool.provider,
            "output_first30": _truncate(text, 60),
            "output_len": len(text),
            "stats": _extract_stats(pool),
        }

    out["checks"].append(_safe("dev_override_openai_to_gemini", _dev_route))
    return out


def run_prod():
    from src.llm.llm_pool import LLMPool  # noqa: WPS433

    out = {"mode": "prod", "checks": []}

    # === (a) OpenAI gpt-5.4-nano ===
    def _openai_nano():
        pool = LLMPool(model="gpt-5.4-nano")
        text = pool.chat(
            [{"role": "user", "content": '한 단어로 답: 한국 수도? JSON {"answer":"..."}'}],
            max_output_tokens=64,
            temperature=0.0,
        )
        return {
            "model": pool.model,
            "provider": pool.provider,
            "output_first30": _truncate(text, 60),
            "stats": _extract_stats(pool),
            "_pool": id(pool),
        }

    out["checks"].append(_safe("prod_openai_gpt54_nano", _openai_nano))

    # === (b) OpenAI gpt-5.4-mini via per-call override on a Gemini-default pool ===
    def _override_mini():
        pool = LLMPool()  # default gemini
        text = pool.chat(
            [{"role": "user", "content": '한 단어로 답: 일본 수도? JSON {"answer":"..."}'}],
            max_output_tokens=64,
            temperature=0.0,
            model="gpt-5.4-mini",
        )
        return {
            "init_model": pool.model,
            "init_provider": pool.provider,
            "override_model": "gpt-5.4-mini",
            "output_first30": _truncate(text, 60),
            "stats": _extract_stats(pool),
        }

    out["checks"].append(_safe("prod_openai_gpt54_mini_override", _override_mini))

    # === (c) Anthropic claude-sonnet-4-6 ===
    def _claude():
        pool = LLMPool(model="claude-sonnet-4-6")
        text = pool.chat(
            [{"role": "user", "content": '한 단어로 답: 프랑스 수도? JSON {"answer":"..."}'}],
            max_output_tokens=64,
            temperature=0.0,
        )
        return {
            "model": pool.model,
            "provider": pool.provider,
            "output_first30": _truncate(text, 60),
            "stats": _extract_stats(pool),
        }

    out["checks"].append(_safe("prod_anthropic_claude_sonnet_4_6", _claude))

    # === (d) Gemini gemini-3.1-flash-lite-preview ===
    def _gemini():
        pool = LLMPool(model="gemini/gemini-3.1-flash-lite-preview")
        text = pool.chat(
            [{"role": "user", "content": '한 단어로 답: 영국 수도? JSON {"answer":"..."}'}],
            max_output_tokens=64,
            temperature=0.0,
        )
        return {
            "model": pool.model,
            "provider": pool.provider,
            "output_first30": _truncate(text, 60),
            "stats": _extract_stats(pool),
        }

    out["checks"].append(_safe("prod_gemini_3_1_flash_lite", _gemini))

    # === (e) per-call override: same pool, multi-provider ===
    def _multi_override():
        pool = LLMPool(model="gemini/gemini-3.1-flash-lite-preview")
        results = {}
        for label, mdl in [
            ("openai_nano", "gpt-5.4-nano"),
            ("anthropic", "claude-sonnet-4-6"),
        ]:
            t = pool.chat(
                [{"role": "user", "content": f'한 단어로 답: {label} 테스트. JSON {{"k":"v"}}'}],
                max_output_tokens=48,
                temperature=0.0,
                model=mdl,
            )
            results[label] = {"model": mdl, "out_first30": _truncate(t, 60)}
        results["stats"] = _extract_stats(pool)
        return results

    out["checks"].append(_safe("prod_per_call_model_override", _multi_override))

    # === (f) Cache hit: 같은 prompt 2번 호출 ===
    def _cache_check():
        pool = LLMPool(model="gemini/gemini-3.1-flash-lite-preview")
        msg = [{"role": "user", "content": '캐시 테스트 한 단어. JSON {"a":"b"}'}]
        t1 = pool.chat(msg, max_output_tokens=48, temperature=0.0)
        s1 = _extract_stats(pool)
        t2 = pool.chat(msg, max_output_tokens=48, temperature=0.0)
        s2 = _extract_stats(pool)
        return {
            "first_out": _truncate(t1, 60),
            "second_out": _truncate(t2, 60),
            "stats_after_first": s1,
            "stats_after_second": s2,
            "cache_hit_increased": (s2.get("cache_hits", 0) or 0)
            > (s1.get("cache_hits", 0) or 0),
        }

    out["checks"].append(_safe("prod_cache_hit", _cache_check))

    return out


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("POLITIKAST_ENV", "prod")).lower()
    if mode == "dev":
        result = run_dev()
    else:
        result = run_prod()

    # 환경 정보
    result["env"] = {
        "POLITIKAST_ENV": os.environ.get("POLITIKAST_ENV"),
        "has_OPENAI": bool(os.environ.get("OPENAI_API_KEYS")),
        "has_ANTHROPIC": bool(os.environ.get("ANTHROPIC_API_KEYS")),
        "has_GEMINI": bool(os.environ.get("GEMINI_API_KEYS")),
        "python": sys.version.split()[0],
    }
    try:
        import litellm  # noqa: WPS433

        result["env"]["litellm_version"] = getattr(litellm, "__version__", "unknown")
    except Exception as e:  # noqa: BLE001
        result["env"]["litellm_version"] = f"import_error: {e}"

    print("=== VALIDATION_RESULT_JSON_BEGIN ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("=== VALIDATION_RESULT_JSON_END ===")


if __name__ == "__main__":
    main()
