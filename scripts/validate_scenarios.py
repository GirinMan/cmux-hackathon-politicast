#!/usr/bin/env python
"""5 region 시나리오 sanity validator + 누락 필드 자동 보완.

처리 흐름:
  1. `_workspace/data/scenarios/<region>.json` 5개 로드.
  2. 각 시나리오에서 `region_id` → ElectionCalendar 조회.
  3. 누락된 `election_date` (top-level) 는 calendar.election_date 로 채움.
     누락된 `timezone` 은 calendar.timezone (= "Asia/Seoul") 로 채움.
  4. `--apply` 모드일 때만 디스크에 저장. 기본은 dry-run.
  5. `--strict` 모드에서는 누락 필드가 있으면 exit 1.

Usage:
    make validate-scenarios            # dry-run, 요약만 출력
    python scripts/validate_scenarios.py --apply
    python scripts/validate_scenarios.py --strict   # CI 게이트
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = REPO_ROOT / "_workspace" / "data" / "scenarios"

# 5 region 시드 — hill_climbing_*, historical_outcomes 는 검사 대상 아님.
RATED_REGIONS = [
    "seoul_mayor",
    "busan_buk_gap",
    "daegu_mayor",
    "gwangju_mayor",
    "daegu_dalseo_gap",
]

# Top-level 필드 중 ElectionCalendar 로 자동 보완 가능한 키.
AUTO_FILLABLE = ("election_date", "timezone")


def _ensure_repo_on_path() -> None:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))


_ensure_repo_on_path()
from src.schemas.calendar import load_election_calendar  # noqa: E402


def _missing_fields(scenario: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for k in AUTO_FILLABLE:
        if scenario.get(k) in (None, "", [], {}):
            missing.append(k)
    if not scenario.get("region_id"):
        missing.insert(0, "region_id")
    return missing


def _autofill(scenario: dict[str, Any], region_id: str) -> tuple[dict[str, Any], list[str]]:
    """Return (patched_scenario, list_of_filled_field_names)."""
    cal = load_election_calendar()
    try:
        win = cal.get(region_id)
    except KeyError:
        return scenario, []
    filled: list[str] = []
    out = dict(scenario)
    if not out.get("election_date"):
        out["election_date"] = win.election_date.isoformat()
        filled.append("election_date")
    if not out.get("timezone"):
        out["timezone"] = win.timezone
        filled.append("timezone")
    return out, filled


def validate_one(path: Path, *, apply: bool, strict: bool) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    region_id = raw.get("region_id") or path.stem
    missing = _missing_fields(raw)
    patched, filled = _autofill(raw, region_id)
    still_missing = _missing_fields(patched)

    status = "ok"
    if filled:
        status = "patched" if apply else "needs_patch"
    if still_missing:
        status = "fail"

    if apply and filled and not still_missing:
        path.write_text(
            json.dumps(patched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    return {
        "file": str(path.relative_to(REPO_ROOT)),
        "region_id": region_id,
        "missing": missing,
        "filled": filled,
        "still_missing": still_missing,
        "status": status,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true",
        help="누락 필드를 디스크에 기록 (기본은 dry-run).",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="누락 필드가 하나라도 있으면 exit 1.",
    )
    parser.add_argument(
        "--scenario-dir", type=Path, default=SCENARIO_DIR,
    )
    args = parser.parse_args()

    files: list[Path] = []
    for region in RATED_REGIONS:
        p = args.scenario_dir / f"{region}.json"
        if p.exists():
            files.append(p)
        else:
            print(f"  [missing] {p.relative_to(REPO_ROOT)}")

    reports = [validate_one(p, apply=args.apply, strict=args.strict) for p in files]

    print(f"[validate-scenarios] dir={args.scenario_dir} "
          f"mode={'apply' if args.apply else 'dry-run'} "
          f"checked={len(reports)} / expected={len(RATED_REGIONS)}")
    for r in reports:
        flag = {
            "ok": "✓",
            "patched": "✎",
            "needs_patch": "·",
            "fail": "✗",
        }.get(r["status"], "?")
        msg = f"  {flag} {r['region_id']:<20} {r['status']}"
        if r["filled"]:
            msg += f"  filled={r['filled']}"
        if r["still_missing"]:
            msg += f"  STILL_MISSING={r['still_missing']}"
        print(msg)

    failures = [r for r in reports if r["status"] == "fail"]
    needs = [r for r in reports if r["status"] == "needs_patch"]

    if failures:
        return 1
    if args.strict and (needs or len(reports) < len(RATED_REGIONS)):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
