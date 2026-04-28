"""evaluate_scenario_result 통합 smoke — 실 snapshot 1개로 모든 필드 채워짐 확인."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.eval import evaluate_scenario_result
from src.schemas.result import ScenarioResult, ValidationMetrics

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "_workspace" / "snapshots" / "results"


def _first_validating_snapshot() -> dict:
    for f in sorted(RESULTS_DIR.glob("*.json")):
        d = json.loads(f.read_text())
        opv = (d.get("meta") or {}).get("official_poll_validation") or {}
        m = opv.get("metrics") or {}
        if m.get("mae") is not None and (opv.get("by_candidate") or {}):
            return d
    raise AssertionError("no snapshot with stored metrics found")


def test_evaluate_smoke_real_snapshot() -> None:
    raw = _first_validating_snapshot()
    res = ScenarioResult.model_validate(raw)
    out = evaluate_scenario_result(res)
    assert isinstance(out, ValidationMetrics)
    # base 4
    assert out.mae is not None and out.mae >= 0.0
    assert out.rmse is not None and out.rmse >= 0.0
    assert out.margin_error is not None and out.margin_error >= 0.0
    assert out.leader_match is not None
    # extension 4
    assert out.brier is not None and out.brier >= 0.0
    assert out.ece is not None and out.ece >= 0.0
    assert out.js_divergence is not None and out.js_divergence >= 0.0
    assert out.collapse_flag is not None  # bool


def test_evaluate_with_explicit_official() -> None:
    raw = _first_validating_snapshot()
    res = ScenarioResult.model_validate(raw)
    bc = raw["meta"]["official_poll_validation"]["by_candidate"]
    official = {k: float(v["official_consensus"]) for k, v in bc.items()}
    out = evaluate_scenario_result(res, official=official)
    assert out.mae is not None
    assert out.brier is not None


def test_evaluate_collapse_only_when_no_official() -> None:
    """official 비어있고 sim 만 있을 때, collapse_flag 만 채워지고 나머지는 None."""
    res = ScenarioResult(
        scenario_id="x",
        region_id="x",
        contest_id="x",
        final_outcome={"vote_share_by_candidate": {"a": 1.0, "b": 0.0}},
    )
    out = evaluate_scenario_result(res, official={})
    assert out.mae is None
    assert out.brier is None
    assert out.collapse_flag is True


def test_validation_metrics_extra_forbid_still_enforced() -> None:
    """기존 extra='forbid' 가 새 필드 추가 후에도 유지됨."""
    with pytest.raises(Exception):
        ValidationMetrics(unknown_field=123)  # type: ignore[call-arg]


def test_existing_snapshot_loads_with_none_extension_fields() -> None:
    """기존 19개 snapshot 모두 새 필드 None 으로 잘 로드되는지 확인."""
    for f in sorted(RESULTS_DIR.glob("*.json")):
        raw = json.loads(f.read_text())
        res = ScenarioResult.model_validate(raw)
        opv = res.meta.official_poll_validation
        if opv is not None:
            m = opv.metrics
            assert m.brier is None
            assert m.ece is None
            assert m.js_divergence is None
            assert m.collapse_flag is None
