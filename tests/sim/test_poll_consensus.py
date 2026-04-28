"""Unit tests for src.sim.poll_consensus."""
from __future__ import annotations

import pytest

from src.sim.poll_consensus import (
    aggregate_poll_response,
    bandwagon_underdog,
    consensus,
    default_house_effect,
    default_mode_effect,
)


def _poll(
    pollster: str = "한국갤럽",
    mode: str = "phone",
    n: int = 1000,
    day: int = 0,
    shares: dict[str, float] | None = None,
    quality: float = 1.0,
) -> dict:
    return {
        "pollster": pollster,
        "mode": mode,
        "n": n,
        "day": day,
        "quality": quality,
        "shares": shares or {"a": 0.5, "b": 0.4, "c": 0.1},
    }


def test_consensus_empty_input() -> None:
    out = consensus([])
    assert out == {}


def test_consensus_single_poll_recovers_shares_when_priors_disabled() -> None:
    poll = _poll(shares={"a": 0.55, "b": 0.45})
    out = consensus([poll], house_effect={}, mode_effect={})
    assert out["a"]["p_hat"] == pytest.approx(0.55, abs=1e-9)
    assert out["b"]["p_hat"] == pytest.approx(0.45, abs=1e-9)
    assert out["a"]["var"] == pytest.approx(0.0, abs=1e-9)


def test_consensus_multiple_polls_weighted_average() -> None:
    polls = [
        _poll(n=1000, day=0, shares={"a": 0.6, "b": 0.4}),
        _poll(n=1000, day=0, shares={"a": 0.5, "b": 0.5}),
    ]
    out = consensus(polls, house_effect={}, mode_effect={})
    # equal weights → mean
    assert out["a"]["p_hat"] == pytest.approx(0.55, abs=1e-9)
    assert out["b"]["p_hat"] == pytest.approx(0.45, abs=1e-9)


def test_consensus_house_effect_subtracts() -> None:
    poll = _poll(pollster="biased_house", shares={"a": 0.55, "b": 0.45})
    out = consensus(
        [poll],
        house_effect={"biased_house": 0.05},
        mode_effect={},
    )
    assert out["a"]["p_hat"] == pytest.approx(0.50, abs=1e-9)
    assert out["b"]["p_hat"] == pytest.approx(0.40, abs=1e-9)


def test_consensus_default_priors_load_korean_pollsters() -> None:
    # When no explicit dict passed, Korean pollster priors should kick in.
    house = default_house_effect()
    mode = default_mode_effect()
    assert isinstance(house, dict) and isinstance(mode, dict)
    # Must contain at least Gallup + RealMeter + a phone/ARS mode key.
    assert "한국갤럽" in house or "갤럽" in house
    assert "리얼미터" in house
    assert "phone" in mode and "ARS" in mode
    # Bounded conservatively (±0.02).
    for v in list(house.values()) + list(mode.values()):
        assert -0.02 - 1e-9 <= float(v) <= 0.02 + 1e-9


def test_consensus_uses_default_priors_when_none() -> None:
    poll = _poll(pollster="리얼미터", mode="ARS", shares={"a": 0.55, "b": 0.45})
    out_default = consensus([poll])  # no explicit dicts → should auto-load
    out_zero = consensus([poll], house_effect={}, mode_effect={})
    # Default priors subtract some bias; values should differ.
    assert out_default["a"]["p_hat"] != out_zero["a"]["p_hat"]


def test_bandwagon_underdog_leader_zero() -> None:
    p_hat = {"a": 0.6, "b": 0.3, "c": 0.1}
    # Leader: margin == 0 → bandwagon adds 0; underdog requires margin < -0.1.
    assert bandwagon_underdog(p_hat, "a") == pytest.approx(0.0, abs=1e-9)


def test_bandwagon_underdog_trailing_negative_delta() -> None:
    p_hat = {"a": 0.6, "b": 0.3}
    # bandwagon penalizes trailers (negative)
    delta = bandwagon_underdog(p_hat, "b", enable_underdog=False)
    assert delta < 0


def test_aggregate_poll_response_basic_tally() -> None:
    candidates = [{"id": "a"}, {"id": "b"}]
    responses = [
        {"vote": "a", "turnout": True},
        {"vote": "a", "turnout": True},
        {"vote": "b", "turnout": False},
        {"vote": "abstain", "turnout": True},
    ]
    out = aggregate_poll_response(responses, candidates)
    # 3 decided votes (1 abstain), a:2/3, b:1/3
    assert out["support_by_candidate"]["a"] == pytest.approx(2 / 3, abs=1e-9)
    assert out["support_by_candidate"]["b"] == pytest.approx(1 / 3, abs=1e-9)
    assert out["n_responses"] == 4
    assert out["n_abstain"] == 1
    assert out["turnout_intent"] == pytest.approx(0.75, abs=1e-9)
