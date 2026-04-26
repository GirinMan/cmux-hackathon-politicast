"""Rename V8b busan_buk_gap result to `busan_buk_gap__rolling_v2_<UTC>.json`,
update results_index.json (`is_mock=false, policy_version="v2.0_validation"`),
keep mirror at `busan_buk_gap_result.json`, print headline metrics.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO / "_workspace" / "snapshots" / "results"
INDEX = REPO / "_workspace" / "snapshots" / "results_index.json"
MIRROR = REPO / "_workspace" / "snapshots" / "busan_buk_gap_result.json"
SRC = RESULTS_DIR / "busan_buk_gap__busan_buk_gap_2026.json"


def _ts() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    p = Path("/tmp/politikast_v8b_ts.txt")
    if p.exists():
        return p.read_text().strip()
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> int:
    if not SRC.exists():
        print(f"FAIL: {SRC} not found", file=sys.stderr)
        return 2
    ts = _ts()
    new_scenario_id = f"rolling_v2_{ts}"
    dest = RESULTS_DIR / f"busan_buk_gap__{new_scenario_id}.json"

    with SRC.open("r", encoding="utf-8") as f:
        result = json.load(f)
    old_scenario_id = result.get("scenario_id")
    result["scenario_id"] = new_scenario_id
    meta = result.setdefault("meta", {})
    meta.setdefault("policy_version", "v2.0_validation")
    meta["original_scenario_id"] = old_scenario_id
    meta["finalized_at"] = dt.datetime.now(dt.timezone.utc).isoformat()

    with dest.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with MIRROR.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    idx: list[dict] = []
    if INDEX.exists():
        try:
            idx = json.loads(INDEX.read_text(encoding="utf-8"))
            if not isinstance(idx, list):
                idx = []
        except Exception:
            idx = []
    idx = [e for e in idx if e.get("scenario_id") != old_scenario_id]
    idx = [
        e for e in idx
        if not (
            e.get("region_id") == "busan_buk_gap"
            and isinstance(e.get("scenario_id"), str)
            and e["scenario_id"].startswith("rolling_v2_")
        )
    ]
    idx.append(
        {
            "path": str(dest.relative_to(REPO)),
            "mirror_path": "_workspace/snapshots/busan_buk_gap_result.json",
            "scenario_id": new_scenario_id,
            "region_id": "busan_buk_gap",
            "persona_n": result.get("persona_n"),
            "timestep_count": result.get("timestep_count"),
            "winner": (result.get("final_outcome") or {}).get("winner"),
            "is_mock": False,
            "policy_version": "v2.0_validation",
            "wrote_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
    )
    INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        SRC.unlink()
    except OSError:
        pass

    val = (meta.get("official_poll_validation") or {})
    metrics = val.get("metrics") or {}
    voter_stats = (meta.get("voter_stats") or {})
    print(json.dumps({
        "result_path": str(dest.relative_to(REPO)),
        "mirror_path": "_workspace/snapshots/busan_buk_gap_result.json",
        "scenario_id": new_scenario_id,
        "policy_version": meta.get("policy_version"),
        "wall_seconds": meta.get("wall_seconds"),
        "actual_keys_used": meta.get("actual_keys_used"),
        "effective_model": meta.get("effective_model"),
        "voter_stats": {
            "calls": voter_stats.get("calls"),
            "parse_fail_rate": voter_stats.get("parse_fail_rate"),
            "abstain_rate": voter_stats.get("abstain_rate"),
            "mean_latency_ms": voter_stats.get("mean_latency_ms"),
        },
        "winner": (result.get("final_outcome") or {}).get("winner"),
        "vote_share_by_candidate": (result.get("final_outcome") or {}).get(
            "vote_share_by_candidate"
        ),
        "official_poll_validation": {
            "target_series": val.get("target_series"),
            "method_version": val.get("method_version"),
            "as_of_date": val.get("as_of_date"),
            "cutoff_ts": val.get("cutoff_ts"),
            "metrics": metrics,
            "by_candidate": val.get("by_candidate"),
        },
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
