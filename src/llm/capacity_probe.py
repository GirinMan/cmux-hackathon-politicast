"""LiteLLM 기반 multi-key capacity probe — 60초간 N개 키 동시 호출.

판정: same_project (4 키 합 ≈ 단일 키) vs separate_project (≈ N×) vs inconclusive.
공급자는 ``LITELLM_MODEL`` 또는 ``--model``에서 자동 추론.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.llm.llm_pool import (
    DEFAULT_MODEL,
    PROVIDER_KEY_ENV,
    _derive_provider,
    _provider_uses_keys,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "_workspace" / "checkpoints" / "capacity_probe.json"
DEFAULT_DURATION_SEC = 60
DEFAULT_REPORT_INTERVAL = 5
DEFAULT_PER_KEY_CONCURRENCY = 2
DEFAULT_PROMPT = "Respond with strict JSON only: {\"ok\": true}"


# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
@dataclass
class _KeyCounter:
    api_key_idx: int
    success: int = 0
    rate_limited: int = 0
    other_errors: int = 0
    timestamps: list[float] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------
async def _worker(
    *,
    counter: _KeyCounter,
    api_key: str,
    model: str,
    prompt: str,
    deadline: float,
    sem: asyncio.Semaphore,
) -> None:
    try:
        import litellm  # type: ignore
        from litellm.exceptions import RateLimitError as _LiteRateLimitError  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"litellm not installed: {e}") from e

    messages = [{"role": "user", "content": prompt}]
    base_kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 32,
        "response_format": {"type": "json_object"},
        "api_key": api_key,
    }
    api_base = os.environ.get("LITELLM_API_BASE")
    if api_base:
        base_kwargs["api_base"] = api_base
    if model.lower().startswith("azure/"):
        api_version = os.environ.get("AZURE_API_VERSION")
        if api_version:
            base_kwargs["api_version"] = api_version
        if not api_base:
            azure_base = os.environ.get("AZURE_API_BASE")
            if azure_base:
                base_kwargs["api_base"] = azure_base

    while True:
        now = time.time()
        if now >= deadline:
            return
        async with sem:
            try:
                await asyncio.to_thread(litellm.completion, **base_kwargs)
                counter.success += 1
                counter.timestamps.append(time.time())
            except _LiteRateLimitError:
                counter.rate_limited += 1
                await asyncio.sleep(1.0)
            except Exception as e:
                msg = str(e).lower()
                if any(s in msg for s in ("429", "quota", "rate", "resource_exhausted")):
                    counter.rate_limited += 1
                else:
                    counter.other_errors += 1
                await asyncio.sleep(1.0)


# ---------------------------------------------------------------------------
# Reporter
# ---------------------------------------------------------------------------
async def _periodic_reporter(
    counters: list[_KeyCounter],
    deadline: float,
    interval: int,
) -> None:
    start = time.time()
    while time.time() < deadline:
        await asyncio.sleep(interval)
        elapsed = int(time.time() - start)
        per_key = " | ".join(
            f"k{c.api_key_idx}: {c.success} ok / {c.rate_limited} 429"
            for c in counters
        )
        print(f"[probe t+{elapsed:02d}s] {per_key}")


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------
def _classify(per_key_rpm: list[float], single_key_avg: float) -> str:
    if single_key_avg <= 0:
        return "inconclusive"
    total = sum(per_key_rpm)
    ratio = total / single_key_avg
    if ratio < 1.5:
        return "same_project"
    if ratio > 3.0:
        return "separate_project"
    return "inconclusive"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def run_probe(
    api_keys: list[str],
    model: str,
    prompt: str,
    duration_sec: int,
    report_interval: int,
    per_key_concurrency: int,
    output_path: Path,
) -> dict[str, Any]:
    provider = _derive_provider(model)
    counters = [_KeyCounter(api_key_idx=i) for i in range(len(api_keys))]
    deadline = time.time() + duration_sec
    sems = [asyncio.Semaphore(per_key_concurrency) for _ in api_keys]

    workers = [
        asyncio.create_task(
            _worker(
                counter=counters[i],
                api_key=api_keys[i],
                model=model,
                prompt=prompt,
                deadline=deadline,
                sem=sems[i],
            )
        )
        for i in range(len(api_keys))
    ]
    reporter = asyncio.create_task(
        _periodic_reporter(counters, deadline, report_interval)
    )

    await asyncio.gather(*workers, return_exceptions=True)
    reporter.cancel()
    try:
        await reporter
    except asyncio.CancelledError:
        pass

    norm = 60.0 / max(duration_sec, 1)
    per_key_rpm = [c.success * norm for c in counters]
    total_rpm = sum(per_key_rpm)

    single_key_avg = max(per_key_rpm) if per_key_rpm else 0.0
    verdict = _classify(per_key_rpm, single_key_avg)

    result = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "provider": provider,
        "model": model,
        "duration_sec": duration_sec,
        "n_keys": len(api_keys),
        "per_key_rpm": per_key_rpm,
        "total_rpm": total_rpm,
        "verdict": verdict,
        "raw_counts": {
            f"k{c.api_key_idx}": {
                "success": c.success,
                "rate_limited": c.rate_limited,
                "other_errors": c.other_errors,
            }
            for c in counters
        },
        "heuristic_note": (
            "verdict = same_project if total < 1.5x max_single_key, "
            "separate_project if total > 3.0x, else inconclusive."
        ),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result


def _load_keys(provider: str) -> list[str]:
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)

    if not _provider_uses_keys(provider):
        raise RuntimeError(
            f"Provider '{provider}'은 IAM 기반 — capacity probe는 키 회전이 의미 없음. "
            "단일 client로 시뮬 직접 실행하라."
        )

    # provider-specific env 우선, 없으면 LLM_API_KEYS
    env_var = PROVIDER_KEY_ENV.get(provider)
    if env_var:
        raw = os.environ.get(env_var, "")
        keys = [k.strip() for k in raw.split(",") if k.strip()]
        if keys:
            return keys
    raw = os.environ.get("LLM_API_KEYS", "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        raise RuntimeError(
            f"No API keys for provider '{provider}'. "
            f"Set {env_var or 'LLM_API_KEYS'}=k1,k2,... in .env"
        )
    return keys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="LiteLLM-based multi-key capacity probe (60s)"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION_SEC)
    parser.add_argument("--report-interval", type=int, default=DEFAULT_REPORT_INTERVAL)
    parser.add_argument(
        "--per-key-concurrency", type=int, default=DEFAULT_PER_KEY_CONCURRENCY
    )
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    provider = _derive_provider(args.model)
    api_keys = _load_keys(provider)
    print(
        f"[probe] provider={provider}, model={args.model}, keys={len(api_keys)}, "
        f"duration={args.duration}s, per_key_concurrency={args.per_key_concurrency}"
    )

    result = asyncio.run(
        run_probe(
            api_keys=api_keys,
            model=args.model,
            prompt=args.prompt,
            duration_sec=args.duration,
            report_interval=args.report_interval,
            per_key_concurrency=args.per_key_concurrency,
            output_path=args.output,
        )
    )

    print("\n[probe] === RESULT ===")
    for i, rpm in enumerate(result["per_key_rpm"]):
        print(f"  k{i}: {rpm:6.1f} rpm")
    print(f"  total: {result['total_rpm']:6.1f} rpm")
    print(f"  verdict: {result['verdict']}")
    print(f"  saved: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
