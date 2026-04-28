"""ElectionTypology controlled vocab — 5 region 시나리오 통과 확인."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.schemas.typology import (
    POSITION_TYPE_LABELS,
    is_valid_position_type,
    position_type_values,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_DIR = REPO_ROOT / "_workspace" / "data" / "scenarios"


@pytest.mark.parametrize(
    "fname",
    [
        "seoul_mayor.json",
        "gwangju_mayor.json",
        "daegu_mayor.json",
        "busan_buk_gap.json",
        "daegu_dalseo_gap.json",
    ],
)
def test_scenario_position_type_in_vocab(fname: str) -> None:
    path = SCENARIO_DIR / fname
    if not path.exists():
        pytest.skip(f"scenario {fname} not present")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    contest = data.get("contest") or {}
    pt = contest.get("position_type")
    assert pt is not None, f"{fname} missing contest.position_type"
    assert is_valid_position_type(pt), f"{fname}: {pt!r} not in vocab"


def test_vocab_covers_known_types() -> None:
    vals = position_type_values()
    assert "metropolitan_mayor" in vals
    assert "national_assembly_by_election" in vals
    # 라벨 매핑도 모든 vocab key 를 커버.
    for v in vals:
        assert v in POSITION_TYPE_LABELS


def test_invalid_inputs_rejected() -> None:
    assert not is_valid_position_type("president")  # 오타
    assert not is_valid_position_type(None)
    assert not is_valid_position_type(123)
