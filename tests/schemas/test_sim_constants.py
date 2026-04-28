"""sim_constants.json + 모델 — 기본값이 election_env/poll_consensus 의 매직 값과 일치."""
from __future__ import annotations

import pytest

from src.schemas.sim_constants import (
    DEFAULT_CONTRACT_PATH,
    BandwagonParams,
    ConsensusParams,
    EnvDefaults,
    SimConstants,
    load_sim_constants,
)


def test_defaults_match_legacy_magic_values() -> None:
    """ConsensusParams/BandwagonParams 기본값 = legacy 인라인 값."""
    c = ConsensusParams()
    assert c.alpha == 0.5
    assert c.lam == 0.05
    assert c.ref_day == 0
    assert c.fieldwork_window_days == 30

    b = BandwagonParams()
    assert b.bandwagon_w == 0.3
    assert b.underdog_w == 0.1
    assert b.trigger_threshold == 0.1
    assert b.enable_bandwagon is True
    assert b.enable_underdog is True

    e = EnvDefaults()
    assert e.timesteps == 4
    assert e.n_interviews == 30
    assert e.concurrency == 8


def test_load_from_json_matches_defaults() -> None:
    """현재 JSON 시드는 legacy 기본값과 동일해야 회귀 보장."""
    s = load_sim_constants()
    ref = SimConstants()
    assert s.consensus.alpha == ref.consensus.alpha
    assert s.consensus.lam == ref.consensus.lam
    assert s.consensus.fieldwork_window_days == ref.consensus.fieldwork_window_days
    assert s.bandwagon.bandwagon_w == ref.bandwagon.bandwagon_w
    assert s.bandwagon.underdog_w == ref.bandwagon.underdog_w
    assert s.env.timesteps == ref.env.timesteps


def test_extra_fields_forbidden() -> None:
    with pytest.raises(Exception):
        ConsensusParams(unknown=1)  # type: ignore[call-arg]


def test_default_contract_path_exists() -> None:
    assert DEFAULT_CONTRACT_PATH.exists(), DEFAULT_CONTRACT_PATH
