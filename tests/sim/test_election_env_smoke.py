"""Smoke test for ElectionEnv — instantiation + helpers without LLM calls."""
from __future__ import annotations

import pytest

from src.sim.election_env import (
    ElectionEnv,
    _coerce_retriever,
    _NullRetriever,
    _read_features,
    _read_timesteps,
)


def test_null_retriever_subgraph_at_returns_shim() -> None:
    r = _NullRetriever()
    out = r.subgraph_at(persona=None, t=0, region_id="seoul_mayor")
    # Either string (legacy) or object with context_text attribute
    assert hasattr(out, "context_text") or isinstance(out, str)


def test_coerce_retriever_falls_back_when_none() -> None:
    r = _coerce_retriever(None)
    assert isinstance(r, _NullRetriever)


def test_coerce_retriever_warns_when_missing_method() -> None:
    class Bad:
        pass

    r = _coerce_retriever(Bad())
    assert isinstance(r, _NullRetriever)


def test_election_env_init_minimal() -> None:
    env = ElectionEnv(
        region_id="seoul_mayor",
        contest_id="seoul_mayor_2026",
        candidates=[
            {"id": "c1", "name": "Cand A", "party_id": "p_ppp"},
            {"id": "c2", "name": "Cand B", "party_id": "p_dem"},
        ],
        timesteps=2,
        kg_retriever=None,
        scenario_meta={"parties": [{"party_id": "p_ppp", "name": "국민의힘"}]},
        concurrency=1,
        n_interviews=0,
    )
    assert env.region_id == "seoul_mayor"
    assert env.timesteps == 2
    assert isinstance(env.kg, _NullRetriever)
    assert isinstance(env.features, set)


def test_read_timesteps_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POLITIKAST_TIMESTEPS", raising=False)
    assert _read_timesteps(default=4) == 4


def test_read_timesteps_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLITIKAST_TIMESTEPS", "7")
    assert _read_timesteps(default=4) == 7


def test_read_features_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLITIKAST_FEATURES", "bandwagon, kg_retrieval ")
    feats = _read_features()
    assert feats == {"bandwagon", "kg_retrieval"}


def test_election_env_party_label_lookup() -> None:
    env = ElectionEnv(
        region_id="x",
        contest_id="x_2026",
        candidates=[{"id": "c1", "name": "X", "party_id": "p_ppp"}],
        timesteps=1,
        kg_retriever=None,
        scenario_meta={"parties": [{"party_id": "custom", "name": "Custom Party"}]},
    )
    # Override mapping
    assert env._party_label("p_ppp") == "국민의힘"
    # Scenario fallback
    assert env._party_label("custom") == "Custom Party"
    # Unknown returns None
    assert env._party_label("does_not_exist") is None
