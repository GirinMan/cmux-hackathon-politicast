"""실측 snapshot 회귀 테스트.

각 snapshot 의 `meta.official_poll_validation.by_candidate` 의 (simulated, official)
값으로부터 4종 metric 을 재계산해 같은 snapshot 의 stored `metrics` 값과 일치하는지
확인. 해커톤 결과를 바이트 단위로 재현하므로 향후 리팩터의 정확성 게이트 역할.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.eval import compute_validation_metrics

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "_workspace" / "snapshots" / "results"


def _gather_cases() -> list[tuple[str, dict, dict]]:
    cases: list[tuple[str, dict, dict]] = []
    for f in sorted(RESULTS_DIR.glob("*.json")):
        data = json.loads(f.read_text())
        opv = (data.get("meta") or {}).get("official_poll_validation") or {}
        bc = opv.get("by_candidate") or {}
        m = opv.get("metrics") or {}
        if not bc or m.get("mae") is None:
            continue
        sim = {cid: row["simulated_share"] for cid, row in bc.items()}
        off = {cid: row["official_consensus"] for cid, row in bc.items()}
        cases.append((f.name, m, {"sim": sim, "off": off}))
    return cases


CASES = _gather_cases()


@pytest.mark.parametrize("name,stored,inputs", CASES, ids=[c[0] for c in CASES])
def test_metric_regression(name: str, stored: dict, inputs: dict) -> None:
    """저장된 by_candidate 로 재계산한 metric 이 stored metric 과 일치."""
    sim = {k: float(v) for k, v in inputs["sim"].items()}
    off = {k: float(v) for k, v in inputs["off"].items()}

    out = compute_validation_metrics(sim, off)

    # 4-decimal rounding 으로 산출되므로 ±2e-4 tolerance 로 비교
    assert out.mae == pytest.approx(stored["mae"], abs=2e-4), name
    assert out.rmse == pytest.approx(stored["rmse"], abs=2e-4), name
    assert out.margin_error == pytest.approx(stored["margin_error"], abs=2e-4), name
    assert out.leader_match == stored["leader_match"], name


def test_overlap_empty_returns_none_metrics() -> None:
    """sim 과 official 이 후보 교집합이 없으면 4종 모두 None."""
    out = compute_validation_metrics({"a": 1.0}, {"b": 1.0})
    assert out.mae is None
    assert out.rmse is None
    assert out.margin_error is None
    assert out.leader_match is None


def test_perfect_match_zero_error() -> None:
    sim = {"a": 0.6, "b": 0.4}
    off = {"a": 0.6, "b": 0.4}
    out = compute_validation_metrics(sim, off)
    assert out.mae == 0.0
    assert out.rmse == 0.0
    assert out.margin_error == 0.0
    assert out.leader_match is True


def test_renormalization_to_overlap() -> None:
    """sim 에만 있는 후보는 overlap 정규화에서 빠진다."""
    sim = {"a": 0.5, "b": 0.3, "extra": 0.2}
    off = {"a": 0.6, "b": 0.4}
    out = compute_validation_metrics(sim, off)
    # overlap={a,b} → sim 정규화: a=5/8=0.625, b=3/8=0.375
    # off 정규화: a=0.6, b=0.4
    # err: 0.025, 0.025 → mae 0.025
    assert out.mae == pytest.approx(0.025, abs=1e-4)
    assert out.leader_match is True
