"""Generic V8t finalizer for triple-fire / cutoff_ts=2026-04-26 results.

Usage:
    python scripts/v8t_post_finalize.py <region_id> [<UTC_ts>]

Effect:
- Reads RESULTS_DIR/<region_id>__<region_id>_2026.json (auto-written by run_scenario).
- Renames to <region_id>__rolling_v2_<UTC_ts>.json, also updates mirror.
- Updates results_index.json (is_mock=False, policy_version=v2.0_validation_first).
- Prints headline JSON for SendMessage broadcasts.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO / "_workspace" / "snapshots" / "results"
INDEX = REPO / "_workspace" / "snapshots" / "results_index.json"


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: v8t_post_finalize.py <region_id> [<UTC_ts>]", file=sys.stderr)
        return 2
    region_id = sys.argv[1]
    if len(sys.argv) >= 3:
        ts = sys.argv[2]
    else:
        ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    src = RESULTS_DIR / f"{region_id}__{region_id}_2026.json"
    if not src.exists():
        print(f"FAIL: {src} not found", file=sys.stderr)
        return 2

    new_scenario_id = f"rolling_v2_{ts}"
    dest = RESULTS_DIR / f"{region_id}__{new_scenario_id}.json"
    mirror = REPO / "_workspace" / "snapshots" / f"{region_id}_result.json"

    with src.open("r", encoding="utf-8") as f:
        result = json.load(f)
    old_scenario_id = result.get("scenario_id")
    result["scenario_id"] = new_scenario_id
    meta = result.setdefault("meta", {})
    meta.setdefault("policy_version", "v2.0_validation_first")
    meta["original_scenario_id"] = old_scenario_id
    meta["finalized_at"] = dt.datetime.now(dt.timezone.utc).isoformat()

    with dest.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with mirror.open("w", encoding="utf-8") as f:
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
    # Keep the previous rolling_v2 entries — the dashboard treats them as
    # historical rolling-origin points.
    idx.append(
        {
            "path": str(dest.relative_to(REPO)),
            "mirror_path": f"_workspace/snapshots/{region_id}_result.json",
            "scenario_id": new_scenario_id,
            "region_id": region_id,
            "persona_n": result.get("persona_n"),
            "timestep_count": result.get("timestep_count"),
            "winner": (result.get("final_outcome") or {}).get("winner"),
            "is_mock": False,
            "policy_version": "v2.0_validation_first",
            "wrote_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
    )
    INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        src.unlink()
    except OSError:
        pass

    val = (meta.get("official_poll_validation") or {})
    metrics = val.get("metrics") or {}
    voter_stats = (meta.get("voter_stats") or {})
    print(json.dumps({
        "region_id": region_id,
        "result_path": str(dest.relative_to(REPO)),
        "mirror_path": f"_workspace/snapshots/{region_id}_result.json",
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
