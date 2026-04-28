"""Rename V8 seoul_mayor result to `seoul_mayor__rolling_v2_<UTC>.json`,
update results_index.json entry (`is_mock=false`, `policy_version="v2.0_validation"`),
keep mirror at `seoul_mayor_result.json`, and print headline metrics.

Usage:
    python scripts/v8_post_finalize.py [<UTC_ts>]

If no UTC_ts is passed, reads /tmp/politikast_v8_ts.txt or generates one.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO / "_workspace" / "snapshots" / "results"
INDEX = REPO / "_workspace" / "snapshots" / "results_index.json"
MIRROR = REPO / "_workspace" / "snapshots" / "seoul_mayor_result.json"
SRC = RESULTS_DIR / "seoul_mayor__seoul_mayor_2026.json"


def _ts() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    p = Path("/tmp/politikast_v8_ts.txt")
    if p.exists():
        return p.read_text().strip()
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> int:
    if not SRC.exists():
        print(f"FAIL: {SRC} not found — V8 run did not produce a result.", file=sys.stderr)
        return 2
    ts = _ts()
    new_scenario_id = f"rolling_v2_{ts}"
    dest = RESULTS_DIR / f"seoul_mayor__{new_scenario_id}.json"

    with SRC.open("r", encoding="utf-8") as f:
        result = json.load(f)
    # Patch scenario_id and meta.policy_version (run_scenario sets it from env,
    # but we pin here for downstream readers to be safe).
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

    # Update results_index.json — drop any earlier seoul_mayor non-mock entry
    # for this run, prepend a fresh one.
    idx: list[dict] = []
    if INDEX.exists():
        try:
            idx = json.loads(INDEX.read_text(encoding="utf-8"))
            if not isinstance(idx, list):
                idx = []
        except Exception:
            idx = []
    # Remove the auto-added entry from run_scenario for the old scenario_id.
    idx = [e for e in idx if e.get("scenario_id") != old_scenario_id]
    # Also drop stale rolling_v2 entries for seoul_mayor (keep one at most).
    idx = [
        e for e in idx
        if not (
            e.get("region_id") == "seoul_mayor"
            and isinstance(e.get("scenario_id"), str)
            and e["scenario_id"].startswith("rolling_v2_")
        )
    ]
    entry = {
        "path": str(dest.relative_to(REPO)),
        "mirror_path": "_workspace/snapshots/seoul_mayor_result.json",
        "scenario_id": new_scenario_id,
        "region_id": "seoul_mayor",
        "persona_n": result.get("persona_n"),
        "timestep_count": result.get("timestep_count"),
        "winner": (result.get("final_outcome") or {}).get("winner"),
        "is_mock": False,
        "policy_version": "v2.0_validation",
        "wrote_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    idx.append(entry)
    INDEX.write_text(
        json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Drop the old un-renamed file so it doesn't clutter the dashboard listing.
    try:
        SRC.unlink()
    except OSError:
        pass

    # Headline metrics for SendMessage
    val = (meta.get("official_poll_validation") or {})
    metrics = val.get("metrics") or {}
    voter_stats = (meta.get("voter_stats") or {})
    print(json.dumps({
        "result_path": str(dest.relative_to(REPO)),
        "mirror_path": "_workspace/snapshots/seoul_mayor_result.json",
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
