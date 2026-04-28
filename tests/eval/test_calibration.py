"""Brier + ECE 단위 테스트 + 1개 snapshot smoke."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.eval.calibration import brier_score, expected_calibration_error

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "_workspace" / "snapshots" / "results"


def test_brier_perfect_zero() -> None:
    assert brier_score([0.6, 0.4], [0.6, 0.4]) == pytest.approx(0.0, abs=1e-12)


def test_brier_max_one_hot() -> None:
    # 완전히 빗나간 1-hot — (1-0)^2 + (0-1)^2 / 2 = 1.0
    assert brier_score([1.0, 0.0], [0.0, 1.0]) == pytest.approx(1.0, abs=1e-12)


def test_brier_dict_intersection() -> None:
    p = {"a": 0.5, "b": 0.5}
    o = {"a": 0.6, "b": 0.4}
    # ((0.5-0.6)^2 + (0.5-0.4)^2)/2 = 0.01
    assert brier_score(p, o) == pytest.approx(0.01, abs=1e-9)


def test_brier_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        brier_score([0.5, 0.5], [0.5])


def test_ece_perfect_zero() -> None:
    assert expected_calibration_error([0.6, 0.4], [0.6, 0.4], n_bins=10) == pytest.approx(0.0)


def test_ece_known_value_two_bins() -> None:
    # 단일 후보, conf=0.9, acc=0.7 → ECE = 0.2
    assert expected_calibration_error([0.9], [0.7], n_bins=10) == pytest.approx(0.2, abs=1e-12)


def test_ece_invalid_bins() -> None:
    with pytest.raises(ValueError):
        expected_calibration_error([0.5], [0.5], n_bins=0)


def test_brier_on_real_snapshot() -> None:
    """실 snapshot 한 건의 by_candidate 로 Brier 계산 — 양수 finite."""
    files = sorted(RESULTS_DIR.glob("*.json"))
    target = None
    for f in files:
        d = json.loads(f.read_text())
        bc = ((d.get("meta") or {}).get("official_poll_validation") or {}).get("by_candidate") or {}
        if bc:
            target = bc
            break
    assert target is not None, "no snapshot with by_candidate"
    sim = {k: float(v["simulated_share"]) for k, v in target.items()}
    off = {k: float(v["official_consensus"]) for k, v in target.items()}
    b = brier_score(sim, off)
    assert b >= 0.0
    assert b < 1.0
    e = expected_calibration_error(sim, off)
    assert 0.0 <= e <= 1.0
