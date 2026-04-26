"""LLMPool cost guard 단위 검증 — 도커 안에서 실행.

시나리오
--------
1. ``LLMCostThresholdError`` import 가능
2. ``LLM_COST_THRESHOLD_OPENAI_USD=0.001`` (낮게) + dev 모드 OFF + mock LiteLLM:
   - 첫 호출: 비용 $0.005 누적 (임계 $0.001 초과 상태로 기록됨)
   - 두 번째 호출: ``_enforce_cost_threshold``가 throw
3. 정상 시나리오 — 임계 무한대면 호출 N번 모두 통과
4. dev 모드 (``POLITIKAST_ENV=dev``) — 비용 추적 skip, throw 없음
5. ``stats()``에 ``cost_usd`` / ``cost_thresholds`` 키 포함 확인

실행
----
docker compose exec app python scripts/verify_llmpool_cost_guard.py
또는 host에서: PYTHONPATH=. python3 scripts/verify_llmpool_cost_guard.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# 캐시 충돌 회피용 — 임시 캐시 사용
_TMP_CACHE = Path(tempfile.mkdtemp()) / "llm_cache.sqlite"

# 테스트용 env 강제 설정 (LLMPool import 이전에)
os.environ["LLM_COST_THRESHOLD_OPENAI_USD"] = "0.001"
os.environ["LLM_COST_THRESHOLD_ANTHROPIC_USD"] = "0.001"
os.environ["LLM_COST_THRESHOLD_GEMINI_USD"] = "0.001"
os.environ["POLITIKAST_ENV"] = "prod"  # prod 모드 강제 (cost 추적 ON, .env override)
os.environ["OPENAI_API_KEYS"] = "fake-key-1,fake-key-2"
os.environ["LITELLM_MODEL"] = "gpt-5.4-nano"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.llm import llm_pool as lp  # noqa: E402


# --------------------------------------------------------------------------
# Mock litellm
# --------------------------------------------------------------------------
class _MockResp(dict):
    def __init__(self, text: str = '{"ok": true}'):
        super().__init__()
        self["choices"] = [{"message": {"content": text}}]
        # litellm.completion_cost는 실제 모델 매핑을 보지만 — fallback test도 동시에 검증
        self["usage"] = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        self["model"] = "gpt-5.4-nano"


class _MockExceptions:
    class APIConnectionError(Exception):
        pass

    class APIError(Exception):
        pass

    class BadRequestError(Exception):
        pass

    class RateLimitError(Exception):
        pass

    class ServiceUnavailableError(Exception):
        pass

    class Timeout(Exception):
        pass


class _MockLiteLLM:
    """litellm.completion + litellm.completion_cost 모킹."""

    exceptions = _MockExceptions

    def __init__(self, fixed_cost: float | None = 0.005, raise_on_cost: bool = False):
        self.fixed_cost = fixed_cost
        self.raise_on_cost = raise_on_cost
        self.call_count = 0

    def completion(self, **kwargs):
        self.call_count += 1
        return _MockResp()

    def completion_cost(self, completion_response=None, **_):
        if self.raise_on_cost:
            raise RuntimeError("model not in price map")
        return self.fixed_cost


def _install_mock(mock: _MockLiteLLM) -> None:
    """litellm 모듈 + litellm.exceptions 강제 주입."""
    sys.modules["litellm"] = mock  # type: ignore
    # _call_with_retry 안의 ``from litellm.exceptions import ...`` 도 이걸 보게
    sys.modules["litellm.exceptions"] = _MockExceptions  # type: ignore


# --------------------------------------------------------------------------
# 시나리오 1: low-threshold throw
# --------------------------------------------------------------------------
def test_low_threshold_throws() -> None:
    print("[1] low-threshold throw 테스트…")
    mock = _MockLiteLLM(fixed_cost=0.005)
    _install_mock(mock)

    pool = lp.LLMPool(
        api_keys=["fake1"],
        model="gpt-5.4-nano",
        cache_path=_TMP_CACHE,
    )
    # 첫 호출: 비용 $0.005 누적 (임계 $0.001 즉시 초과)
    text = pool.chat([{"role": "user", "content": "hello"}], cache=False)
    assert text, "first call must succeed"
    cost = pool._provider_cost_usd["openai"]
    assert cost >= 0.005, f"expected accumulated cost >= 0.005, got {cost}"
    print(f"   첫 호출 OK — 누적 ${cost:.4f}")

    # 두 번째 호출: 임계 초과 → throw
    try:
        pool.chat([{"role": "user", "content": "hello-2"}], cache=False)
    except lp.LLMCostThresholdError as e:
        print(f"   두 번째 호출 throw OK — {e}")
        return
    except Exception as e:  # noqa: BLE001
        raise AssertionError(f"expected LLMCostThresholdError, got {type(e).__name__}: {e}")
    raise AssertionError("expected LLMCostThresholdError on 2nd call but no exception raised")


# --------------------------------------------------------------------------
# 시나리오 2: 정상 — 임계 무한
# --------------------------------------------------------------------------
def test_normal_within_threshold() -> None:
    print("[2] 정상 시나리오 (임계 무한대) 테스트…")
    os.environ.pop("LLM_COST_THRESHOLD_OPENAI_USD", None)
    os.environ.pop("LLM_COST_THRESHOLD_ANTHROPIC_USD", None)
    os.environ.pop("LLM_COST_THRESHOLD_GEMINI_USD", None)
    mock = _MockLiteLLM(fixed_cost=0.0001)
    _install_mock(mock)
    pool = lp.LLMPool(
        api_keys=["fakeX"],
        model="gpt-5.4-nano",
        cache_path=_TMP_CACHE,
    )
    for i in range(5):
        pool.chat([{"role": "user", "content": f"q{i}"}], cache=False)
    assert mock.call_count == 5
    cost = pool._provider_cost_usd["openai"]
    print(f"   5회 호출 모두 OK — 누적 ${cost:.6f}")
    # threshold 복구
    os.environ["LLM_COST_THRESHOLD_OPENAI_USD"] = "0.001"
    os.environ["LLM_COST_THRESHOLD_ANTHROPIC_USD"] = "0.001"
    os.environ["LLM_COST_THRESHOLD_GEMINI_USD"] = "0.001"


# --------------------------------------------------------------------------
# 시나리오 3: dev 모드 — 추적 skip
# --------------------------------------------------------------------------
def test_dev_mode_skips_tracking() -> None:
    print("[3] dev 모드 cost 추적 skip 테스트…")
    os.environ["POLITIKAST_ENV"] = "dev"
    os.environ["GEMINI_API_KEYS"] = "fake-gem-1"
    # dev override 라우팅 우회를 위해 model 인자에 OpenAI 사용 안 함 — 라우터가 dev면 강제 Gemini로 바꿈
    mock = _MockLiteLLM(fixed_cost=99.99)  # 비싸지만 dev면 무시
    _install_mock(mock)
    pool = lp.LLMPool(
        api_keys=["fakeY"],
        model="gpt-5.4-nano",
        cache_path=_TMP_CACHE,
    )
    for i in range(3):
        pool.chat([{"role": "user", "content": f"dev-{i}"}], cache=False)
    # dev이므로 누적 0
    cost = pool._provider_cost_usd.get("openai", 0.0)
    assert cost == 0.0, f"dev mode must not accumulate cost, got {cost}"
    stats = pool.stats()
    assert stats["cost_tracking_enabled"] is False, stats
    print("   dev 모드 누적 0 OK + cost_tracking_enabled=False")
    os.environ["POLITIKAST_ENV"] = "prod"  # 다른 테스트와 격리


# --------------------------------------------------------------------------
# 시나리오 4: completion_cost() 인식 실패 → 0 fallback
# --------------------------------------------------------------------------
def test_completion_cost_fallback() -> None:
    print("[4] completion_cost() raise 시 0 fallback 테스트…")
    mock = _MockLiteLLM(fixed_cost=None, raise_on_cost=True)
    _install_mock(mock)
    pool = lp.LLMPool(
        api_keys=["fakeZ"],
        model="gpt-5.4-nano",
        cache_path=_TMP_CACHE,
    )
    pool.chat([{"role": "user", "content": "fallback"}], cache=False)
    cost = pool._provider_cost_usd["openai"]
    assert cost == 0.0, f"fallback must be 0, got {cost}"
    print("   completion_cost() 실패 → 0 누적 OK")


# --------------------------------------------------------------------------
# 시나리오 5: stats() 스키마
# --------------------------------------------------------------------------
def test_stats_schema() -> None:
    print("[5] stats() 스키마 테스트…")
    mock = _MockLiteLLM(fixed_cost=0.0001)
    _install_mock(mock)
    pool = lp.LLMPool(api_keys=["fS"], model="gpt-5.4-nano", cache_path=_TMP_CACHE)
    pool.chat([{"role": "user", "content": "s"}], cache=False)
    s = pool.stats()
    for key in ("cost_usd", "cost_thresholds", "cost_tracking_enabled"):
        assert key in s, f"missing key {key} in stats(): {list(s.keys())}"
    assert isinstance(s["cost_usd"], dict)
    assert isinstance(s["cost_thresholds"], dict)
    print(f"   stats() OK — cost_usd={s['cost_usd']}, thresholds={s['cost_thresholds']}")


# --------------------------------------------------------------------------
# 시나리오 6: 실제 litellm.completion_cost() — gpt-5.4-nano 인식 여부
# --------------------------------------------------------------------------
def test_real_completion_cost_recognition() -> None:
    print("[6] 실제 litellm.completion_cost() — gpt-5.4-nano 인식 여부…")
    # 모킹 해제 — 실제 litellm import
    sys.modules.pop("litellm", None)
    sys.modules.pop("litellm.exceptions", None)
    try:
        import litellm  # type: ignore
    except Exception as e:
        print(f"   litellm import 실패 — skip: {e}")
        return

    fake_resp = {
        "choices": [{"message": {"content": '{"ok":true}'}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        "model": "gpt-5.4-nano",
    }
    for model in ("gpt-5.4-nano", "gpt-5.4-mini", "gpt-4o-mini"):
        fake_resp["model"] = model
        try:
            c = litellm.completion_cost(completion_response=fake_resp, model=model)
            print(f"   {model}: ${c:.6f} 인식 OK")
        except Exception as e:
            print(f"   {model}: 인식 실패 → 0 fallback (in pool). detail={e}")


def main() -> int:
    failures: list[str] = []
    for fn in (
        test_low_threshold_throws,
        test_normal_within_threshold,
        test_dev_mode_skips_tracking,
        test_completion_cost_fallback,
        test_stats_schema,
        test_real_completion_cost_recognition,
    ):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            import traceback

            traceback.print_exc()
            failures.append(f"{fn.__name__}: {e}")
    if failures:
        print("\nFAILED:")
        for f in failures:
            print(" -", f)
        return 1
    print("\nALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
