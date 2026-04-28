"""Distribution-collapse 진단 — _workspace/snapshots/results/*.json 일괄 평가.

사용:
    PYTHONPATH=. .venv/bin/python scripts/diagnose_collapse.py
    PYTHONPATH=. .venv/bin/python scripts/diagnose_collapse.py --json   # 기계 판독 출력

각 snapshot 을 evaluate_scenario_result 에 통과시켜 다음 표를 출력:
    snapshot, scenario_id, mae, js, brier, ece, collapse, leader, top_share, top_candidate
collapse_flag=True 인 케이스를 마지막에 별도 강조한다 (Daegu 등 회귀 감시용).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.eval import evaluate_scenario_result  # noqa: E402
from src.schemas.calendar import load_election_calendar  # noqa: E402
from src.schemas.result import ScenarioResult  # noqa: E402

RESULTS_DIR = REPO_ROOT / "_workspace" / "snapshots" / "results"


def _resolve_cutoff(res: ScenarioResult) -> str:
    """ElectionCalendar SoT 우선, 없으면 snapshot 의 cutoff_ts."""
    try:
        cal = load_election_calendar()
        return cal.cutoff_for(res.region_id).isoformat()
    except (FileNotFoundError, KeyError):
        opv = res.meta.official_poll_validation if res.meta else None
        return getattr(opv, "cutoff_ts", "") or ""


def _row(path: Path) -> dict:
    raw = json.loads(path.read_text())
    res = ScenarioResult.model_validate(raw)
    metrics = evaluate_scenario_result(res)

    sim = (res.final_outcome.vote_share_by_candidate if res.final_outcome else {}) or {}
    top_cand, top_share = ("", 0.0)
    if sim:
        top_cand, top_share = max(sim.items(), key=lambda kv: kv[1])

    return {
        "snapshot": path.name,
        "scenario_id": res.scenario_id,
        "cutoff": _resolve_cutoff(res),
        "mae": metrics.mae,
        "rmse": metrics.rmse,
        "js_divergence": metrics.js_divergence,
        "brier": metrics.brier,
        "ece": metrics.ece,
        "collapse_flag": metrics.collapse_flag,
        "leader_match": metrics.leader_match,
        "top_share": round(float(top_share), 4),
        "top_candidate": top_cand,
    }


def _fmt(v: object) -> str:
    if v is None:
        return "  -   "
    if isinstance(v, bool):
        return "Y" if v else "."
    if isinstance(v, float):
        return f"{v:6.4f}"
    return str(v)


def _print_table(rows: list[dict]) -> None:
    cols = ("snapshot", "cutoff", "mae", "js_divergence", "brier", "ece",
            "collapse_flag", "leader_match", "top_share", "top_candidate")
    widths = {c: max(len(c), max((len(_fmt(r[c])) for r in rows), default=0)) for c in cols}
    header = "  ".join(c.ljust(widths[c]) for c in cols)
    print(header)
    print("-" * len(header))
    for r in rows:
        print("  ".join(_fmt(r[c]).ljust(widths[c]) for c in cols))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="JSON array 로 출력")
    ap.add_argument("--results-dir", default=str(RESULTS_DIR))
    args = ap.parse_args()

    files = sorted(Path(args.results_dir).glob("*.json"))
    if not files:
        print(f"no snapshots in {args.results_dir}", file=sys.stderr)
        return 1

    rows: list[dict] = []
    for f in files:
        try:
            rows.append(_row(f))
        except Exception as exc:  # snapshot schema mismatch 는 진단용이므로 계속
            rows.append({"snapshot": f.name, "scenario_id": "ERROR",
                         "cutoff": "",
                         "mae": None, "rmse": None, "js_divergence": None,
                         "brier": None, "ece": None, "collapse_flag": None,
                         "leader_match": None, "top_share": 0.0,
                         "top_candidate": f"err:{exc.__class__.__name__}"})

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    _print_table(rows)
    collapsed = [r for r in rows if r["collapse_flag"] is True]
    print()
    print(f"== collapse_flag=True : {len(collapsed)} / {len(rows)} ==")
    for r in collapsed:
        print(f"  {r['snapshot']:60s}  top={r['top_candidate']} ({r['top_share']:.3f}) "
              f"js={_fmt(r['js_divergence'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
