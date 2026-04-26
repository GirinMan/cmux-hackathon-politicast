"""Realistic capacity probe — 실 voter prompt(persona context + JSON output)로
RPM/latency 측정. 합성 probe(`src/llm/capacity_probe.py`)는 minimal payload라
실 sim 워크로드 대비 5x 과대평가. 이 스크립트는 voter_agent.system_prompt() /
user_prompt() 형태를 그대로 흉내 낸다.

사용:
    python -m _workspace.research.capacity_probe_realistic \
        --model gemini/gemini-3.1-flash-lite-preview \
        --duration 60 \
        --output _workspace/checkpoints/capacity_probe_v3_realistic.json

또는 latency-only spot 측정 (60s probe 없이 1~2 calls):
    python -m _workspace.research.capacity_probe_realistic \
        --model openai/gpt-5.4-nano --spot 2
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Realistic prompt — clone of VoterAgent.system_prompt() / user_prompt()
# ---------------------------------------------------------------------------
PERSONA_NARRATIVE = (
    "저는 서울특별시 강남구에 거주하는 45세 남성 회계사입니다. 학사 학위를 가지고 있고, 결혼한 지 18년이 되었습니다. "
    "두 자녀(중학생 딸, 초등학생 아들)를 두고 있으며 일과 가정의 균형을 중요하게 생각합니다. "
    "직업적으로는 중견 회계법인에서 시니어 매니저로 근무 중이며 IFRS 도입 후 컨설팅 업무가 늘어났습니다. "
    "세무 정책의 미세한 변화가 클라이언트 자문에 직접 영향을 주기 때문에 정부의 조세 방침을 예의주시하고 있습니다. "
    "가족적으로는 양가 부모님 모두 생존해 계시고 명절마다 본가(부산)에 내려갑니다. 자녀 사교육비 부담이 가계의 가장 큰 고민입니다. "
    "문화적으로는 보수적 가치관과 실용주의가 혼재된 성향입니다. 경제 정책에서는 시장 친화적 태도를 보이지만 교육·돌봄 정책은 "
    "공공이 더 많은 역할을 해야 한다고 봅니다. 평소 종이신문(조선·중앙)을 구독하면서도 유튜브에서 다양한 시사 채널을 챙겨 봅니다. "
    "지역적으로는 강남 8학군 학부모 커뮤니티에서 활발히 활동하며 입시·부동산 관련 이슈에 매우 민감합니다. "
    "최근 관심사는 (1) 자녀 대학 입시, (2) 의료비 지원·실손보험 개편, (3) 부동산 보유세, (4) 세대 간 형평성 이슈입니다. "
    "정치 성향은 중도 보수에 가깝지만 후보 개인의 정책 일관성과 도덕성을 정당보다 우선시한다고 스스로 평가합니다."
)

SYSTEM_PROMPT = (
    "당신은 한국 유권자입니다. 아래 페르소나를 1인칭으로 체화하여 답하세요.\n"
    "- 거주: 서울특별시 강남구\n"
    "- 연령: 45, 성별: 남성\n"
    "- 직업: 회계사, 학력: 학사\n"
    "- 가족: 기혼\n"
    "\n=== 서사 ===\n"
    f"{PERSONA_NARRATIVE}\n"
    "\n=== 규칙 ===\n"
    "1. 제공된 컨텍스트(이슈·여론조사·이벤트) 외 정보를 사용하지 마세요.\n"
    "2. 출마를 포기한 후보는 선택할 수 없습니다.\n"
    "3. 미래 결과를 안다고 가정하지 마세요. 페르소나의 가치관·관심사로만 추론하세요.\n"
    "4. 반드시 단일 JSON 객체로만 응답합니다 (코드펜스 금지). 스키마:\n"
    '   {"vote": "<candidate_id|null>", "turnout": true|false, '
    '"confidence": 0.0~1.0, "reason": "<짧은 한 줄>", '
    '"key_factors": ["<핵심 요인 최대 3개>"]}'
)

USER_PROMPT = (
    "=== 서울시장 보궐선거 (timestep t=2) ===\n"
    "[모드] poll_response\n"
    "여론조사원이 전화로 묻습니다. 솔직하게 답하되, 마음을 정하지 못했으면 vote=null로 응답하세요.\n\n"
    "[후보]\n"
    "- A | 김보수 (국민의힘)\n"
    "- B | 이진보 (더불어민주당)\n"
    "- C | 박중도 (개혁신당)\n\n"
    "[컨텍스트 (t≤2)]\n"
    "- 직전 여론조사: A 35%, B 30%, C 25%, 무응답 10%\n"
    "- 주요 이슈: 부동산 보유세 인하, 사교육비 경감 바우처, 의료비 지원 확대\n"
    "- 최근 이벤트: A 후보의 부동산 정책 토론회 발언이 강남권에서 화제\n"
    "누구에게 투표하시겠습니까?"
)


# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
@dataclass
class _Counter:
    success: int = 0
    rate_limited: int = 0
    other_errors: int = 0
    latencies_ms: list[float] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Worker (single API key, multi-concurrent)
# ---------------------------------------------------------------------------
async def _worker(
    *,
    counter: _Counter,
    api_key: str,
    model: str,
    deadline: float,
    sem: asyncio.Semaphore,
    max_completion_tokens: int,
) -> None:
    import litellm  # type: ignore
    from litellm.exceptions import RateLimitError as _LiteRateLimitError  # type: ignore

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT},
    ]
    base_kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 1.0,
        "max_tokens": max_completion_tokens,
        "response_format": {"type": "json_object"},
        "api_key": api_key,
    }

    while True:
        now = time.time()
        if now >= deadline:
            return
        async with sem:
            t0 = time.monotonic()
            try:
                await asyncio.to_thread(litellm.completion, **base_kwargs)
                counter.success += 1
                counter.latencies_ms.append((time.monotonic() - t0) * 1000.0)
            except _LiteRateLimitError:
                counter.rate_limited += 1
                await asyncio.sleep(1.0)
            except Exception as e:
                msg = str(e).lower()
                if any(s in msg for s in ("429", "quota", "rate", "resource_exhausted")):
                    counter.rate_limited += 1
                else:
                    counter.other_errors += 1
                    if counter.other_errors <= 3:
                        print(f"[probe] error: {type(e).__name__}: {str(e)[:200]}", flush=True)
                await asyncio.sleep(1.0)


async def _periodic_reporter(counter: _Counter, deadline: float, interval: int) -> None:
    start = time.time()
    while time.time() < deadline:
        await asyncio.sleep(interval)
        elapsed = int(time.time() - start)
        n_lat = len(counter.latencies_ms)
        avg_lat = (sum(counter.latencies_ms) / n_lat) if n_lat else 0.0
        print(
            f"[probe t+{elapsed:02d}s] ok={counter.success} 429={counter.rate_limited} "
            f"err={counter.other_errors} avg_latency={avg_lat:.0f}ms",
            flush=True,
        )


# ---------------------------------------------------------------------------
# Spot check — single call(s) latency
# ---------------------------------------------------------------------------
async def _spot_check(model: str, api_key: str, n: int, max_completion_tokens: int) -> dict[str, Any]:
    import litellm  # type: ignore

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT},
    ]
    latencies: list[float] = []
    failures: list[str] = []
    for i in range(n):
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": 1.0,
            "max_tokens": max_completion_tokens,
            "response_format": {"type": "json_object"},
            "api_key": api_key,
        }
        t0 = time.monotonic()
        try:
            await asyncio.to_thread(litellm.completion, **kwargs)
            latencies.append((time.monotonic() - t0) * 1000.0)
        except Exception as e:
            failures.append(f"{type(e).__name__}: {str(e)[:200]}")
    return {
        "model": model,
        "n_calls": n,
        "n_success": len(latencies),
        "latencies_ms": latencies,
        "avg_latency_ms": (statistics.mean(latencies) if latencies else None),
        "failures": failures,
    }


# ---------------------------------------------------------------------------
# Provider + key resolution
# ---------------------------------------------------------------------------
def _provider_of(model: str) -> str:
    m = model.lower()
    if m.startswith("gemini/") or "gemini" in m:
        return "gemini"
    if m.startswith("openai/") or m.startswith("gpt-"):
        return "openai"
    if m.startswith("anthropic/") or m.startswith("claude-"):
        return "anthropic"
    return "unknown"


def _resolve_key(provider: str) -> str:
    env_var = {
        "gemini": "GEMINI_API_KEYS",
        "openai": "OPENAI_API_KEYS",
        "anthropic": "ANTHROPIC_API_KEYS",
    }.get(provider, "")
    if not env_var:
        raise RuntimeError(f"Unknown provider: {provider}")
    raw = os.environ.get(env_var, "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        raise RuntimeError(f"No keys in {env_var}")
    return keys[0]


# ---------------------------------------------------------------------------
# Probe driver
# ---------------------------------------------------------------------------
async def run_probe(
    model: str,
    duration_sec: int,
    concurrency: int,
    max_completion_tokens: int,
    output_path: Path,
) -> dict[str, Any]:
    provider = _provider_of(model)
    api_key = _resolve_key(provider)
    counter = _Counter()
    deadline = time.time() + duration_sec
    sem = asyncio.Semaphore(concurrency)

    workers = [
        asyncio.create_task(
            _worker(
                counter=counter,
                api_key=api_key,
                model=model,
                deadline=deadline,
                sem=sem,
                max_completion_tokens=max_completion_tokens,
            )
        )
        for _ in range(concurrency)
    ]
    reporter = asyncio.create_task(_periodic_reporter(counter, deadline, 5))
    await asyncio.gather(*workers, return_exceptions=True)
    reporter.cancel()
    try:
        await reporter
    except asyncio.CancelledError:
        pass

    norm = 60.0 / max(duration_sec, 1)
    rpm = counter.success * norm
    avg_latency = (
        statistics.mean(counter.latencies_ms) if counter.latencies_ms else None
    )
    p50 = (
        statistics.median(counter.latencies_ms) if counter.latencies_ms else None
    )

    result = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "provider": provider,
        "model": model,
        "duration_sec": duration_sec,
        "concurrency": concurrency,
        "max_completion_tokens": max_completion_tokens,
        "payload": "realistic_voter_prompt",
        "rpm": rpm,
        "avg_latency_ms": avg_latency,
        "p50_latency_ms": p50,
        "raw_counts": {
            "success": counter.success,
            "rate_limited": counter.rate_limited,
            "other_errors": counter.other_errors,
        },
        "system_prompt_chars": len(SYSTEM_PROMPT),
        "user_prompt_chars": len(USER_PROMPT),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--max-completion-tokens", type=int, default=2048)
    parser.add_argument("--spot", type=int, default=0,
                        help="If >0, do N sequential calls and report latency only (no full RPM probe).")
    parser.add_argument("--output", type=Path,
                        default=REPO_ROOT / "_workspace" / "checkpoints" / "capacity_probe_v3_realistic.json")
    args = parser.parse_args(argv)

    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)

    if args.spot > 0:
        provider = _provider_of(args.model)
        api_key = _resolve_key(provider)
        print(f"[spot] model={args.model}, n={args.spot}", flush=True)
        result = asyncio.run(_spot_check(args.model, api_key, args.spot, args.max_completion_tokens))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(
        f"[probe] model={args.model}, duration={args.duration}s, "
        f"concurrency={args.concurrency}, max_tokens={args.max_completion_tokens}",
        flush=True,
    )
    result = asyncio.run(
        run_probe(
            model=args.model,
            duration_sec=args.duration,
            concurrency=args.concurrency,
            max_completion_tokens=args.max_completion_tokens,
            output_path=args.output,
        )
    )
    print("\n[probe] === RESULT ===")
    print(f"  rpm: {result['rpm']:.1f}")
    print(f"  avg_latency: {result['avg_latency_ms']}")
    print(f"  raw: {result['raw_counts']}")
    print(f"  saved: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
