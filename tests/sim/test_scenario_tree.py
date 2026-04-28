"""Tests for src.sim.scenario_tree.BeamSearch (Phase 6, pipeline-model task #10).

Uses a deterministic shim sim_runner so the suite never hits an LLM. Verifies:
- determinism (same inputs → same tree)
- cumulative_p product invariant (root=1.0, child = parent × prior_p)
- FirewallViolation when proposer emits an event with occurs_at <= parent_t
- beam_width prune behavior (only top-W kept per depth)

Suite intentionally avoids pytest-asyncio (not in repo deps) — wraps the
async coordinator with `asyncio.run` per test.
"""
from __future__ import annotations

import asyncio
import datetime as dt
from typing import Any

import pytest

from src.kg.firewall import FirewallViolation
from src.schemas.beam_event import BeamEvent
from src.schemas.scenario_tree import BeamConfig, ScenarioTree
from src.sim.scenario_tree import BeamSearch


def _utc(year: int, month: int, day: int) -> dt.datetime:
    return dt.datetime(year, month, day, tzinfo=dt.timezone.utc)


BASE_SCENARIO: dict[str, Any] = {
    "scenario_id": "seoul_mayor_2026",
    "region_id": "seoul_mayor",
    "contest_id": "seoul_mayor_2026",
    "candidates": [
        {"id": "c_a", "candidate_id": "c_a", "name": "A", "party": "p_dem"},
        {"id": "c_b", "candidate_id": "c_b", "name": "B", "party": "p_ppp"},
    ],
    "election": {"date": "2026-06-03"},
}


def _shim_runner_factory():
    async def _runner(scenario, ctx):
        seed_events = scenario.get("seed_events") or []
        leader = "c_a"
        if seed_events:
            last = seed_events[-1].get("event_id", "")
            leader = "c_b" if hash(last) % 2 == 0 else "c_a"
        shares = (
            {"c_a": 0.55, "c_b": 0.45}
            if leader == "c_a"
            else {"c_a": 0.4, "c_b": 0.6}
        )
        return {
            "scenario_id": scenario["scenario_id"],
            "final_outcome": {"winner": leader, "vote_share_by_candidate": shares},
            "meta": {"shim": True},
        }

    return _runner


class _FixedProposer:
    name = "fixed"

    def __init__(self, events_by_depth: list[list[BeamEvent]]):
        self._by_depth = events_by_depth

    def propose(self, region_id, current_t, history, k):
        depth = len(history)
        if depth >= len(self._by_depth):
            return []
        return list(self._by_depth[depth])[:k]


def _make_search(
    *, config: BeamConfig, proposer, tree_id: str
) -> BeamSearch:
    return BeamSearch(
        region_id="seoul_mayor",
        contest_id="seoul_mayor_2026",
        as_of=dt.date(2026, 4, 28),
        election_date=dt.date(2026, 6, 3),
        base_scenario=BASE_SCENARIO,
        config=config,
        proposer=proposer,
        sim_runner=_shim_runner_factory(),
        tree_id=tree_id,
    )


def test_beam_root_only_when_depth_zero():
    proposer = _FixedProposer([])
    config = BeamConfig(beam_width=2, beam_depth=1, k_propose=2)
    search = _make_search(config=config, proposer=proposer, tree_id="t_root_only")
    tree = asyncio.run(search.expand())
    assert len(tree.nodes) == 1
    root = tree.nodes[tree.root_id]
    assert root.cumulative_p == 1.0
    assert root.event is None
    assert root.depth == 0


def test_beam_cumulative_p_is_product_of_priors():
    e1 = BeamEvent(
        event_id="e1",
        source="custom",
        occurs_at=_utc(2026, 5, 5),
        description="e1",
        prior_p=0.6,
    )
    e2 = BeamEvent(
        event_id="e2",
        source="custom",
        occurs_at=_utc(2026, 5, 20),
        description="e2",
        prior_p=0.4,
    )
    proposer = _FixedProposer([[e1], [e2]])
    config = BeamConfig(beam_width=1, beam_depth=2, k_propose=1)
    search = _make_search(config=config, proposer=proposer, tree_id="t_cum_p")
    tree = asyncio.run(search.expand())

    d1 = next(n for n in tree.nodes.values() if n.depth == 1)
    assert d1.cumulative_p == pytest.approx(0.6)
    d2 = next(n for n in tree.nodes.values() if n.depth == 2)
    assert d2.cumulative_p == pytest.approx(0.6 * 0.4)


def test_beam_width_prunes_to_top_w():
    events = [
        BeamEvent(
            event_id=f"e{i}",
            source="custom",
            occurs_at=_utc(2026, 5, 5 + i),
            description=f"e{i}",
            prior_p=0.1 * (i + 1),  # 0.1, 0.2, 0.3, 0.4
        )
        for i in range(4)
    ]
    proposer = _FixedProposer([events])
    config = BeamConfig(beam_width=2, beam_depth=1, k_propose=4)
    search = _make_search(config=config, proposer=proposer, tree_id="t_prune")
    tree = asyncio.run(search.expand())
    depth1 = [n for n in tree.nodes.values() if n.depth == 1]
    assert len(depth1) == 2
    kept = sorted(n.event.event_id for n in depth1)
    assert kept == ["e2", "e3"]


def test_beam_determinism():
    e = BeamEvent(
        event_id="e1",
        source="custom",
        occurs_at=_utc(2026, 5, 5),
        description="e1",
        prior_p=0.5,
    )
    config = BeamConfig(beam_width=1, beam_depth=1, k_propose=1)

    def _run(tag: str):
        return asyncio.run(
            _make_search(
                config=config, proposer=_FixedProposer([[e]]), tree_id=tag
            ).expand()
        )

    a = _run("t_det_a")
    b = _run("t_det_b")
    assert sorted(n.depth for n in a.nodes.values()) == sorted(
        n.depth for n in b.nodes.values()
    )
    a_d1 = next(n for n in a.nodes.values() if n.depth == 1)
    b_d1 = next(n for n in b.nodes.values() if n.depth == 1)
    assert a_d1.cumulative_p == b_d1.cumulative_p
    assert a_d1.leader_candidate_id == b_d1.leader_candidate_id


def test_beam_declarative_patches_routed_to_modifiers():
    """Declarative shape — pipeline-counterfactual seed JSON form (task #21).

    BeamEvent's declarative `candidate_patches` / `event_patches` must:
    - leave `scenario.candidates` roster unchanged (no op/fields → no apply)
    - land verbatim in `scenario.candidate_modifiers` / `event_modifiers`
    - still surface the BeamEvent itself in `seed_events`
    """
    from src.sim.scenario_tree import _splice_event_into_scenario

    declarative = BeamEvent(
        event_id="seoul_unity_2026",
        source="custom",
        occurs_at=_utc(2026, 5, 15),
        description="주요 야권 단일화 합의",
        candidate_patches=[
            {"candidate_id": "c_a", "boost": 0.06, "reason": "단일화 흡수"},
            {"candidate_id": "c_b", "drop_out": True},
        ],
        event_patches=[
            {"issue": "야권_단일화", "salience": 0.30},
        ],
        prior_p=0.4,
    )
    spliced = _splice_event_into_scenario(BASE_SCENARIO, declarative)
    # Roster is preserved (declarative does NOT mutate candidates).
    roster_ids = sorted(c["id"] for c in spliced["candidates"])
    assert roster_ids == ["c_a", "c_b"]
    # Modifiers are routed verbatim.
    assert spliced["candidate_modifiers"] == [
        {"candidate_id": "c_a", "boost": 0.06, "reason": "단일화 흡수"},
        {"candidate_id": "c_b", "drop_out": True},
    ]
    assert spliced["event_modifiers"] == [
        {"issue": "야권_단일화", "salience": 0.30}
    ]
    # BeamEvent still appears in seed_events for the voter prompt.
    assert any(
        se["event_id"] == "seoul_unity_2026" for se in spliced["seed_events"]
    )


def test_beam_imperative_patches_mutate_roster_and_seed_events():
    """Imperative / op-shape (run_counterfactual interop) still works."""
    from src.sim.scenario_tree import _splice_event_into_scenario

    imperative = BeamEvent(
        event_id="cf_choo",
        source="custom",
        occurs_at=_utc(2026, 5, 20),
        description="추경호 단일화",
        candidate_patches=[
            {"op": "withdraw", "candidate_id": "c_b"},
            {
                "op": "upsert",
                "candidate_id": "c_new",
                "candidate": {"id": "c_new", "name": "C", "party": "p_ppp"},
            },
        ],
        event_patches=[
            {
                "op": "add",
                "event": {
                    "event_id": "ev_cf_choo_nom",
                    "timestep": 2,
                    "type": "nomination",
                    "summary": "추경호 후보 확정",
                },
            }
        ],
        prior_p=0.5,
    )
    spliced = _splice_event_into_scenario(BASE_SCENARIO, imperative)
    cand_by_id = {c["id"]: c for c in spliced["candidates"]}
    assert cand_by_id["c_b"]["withdrawn"] is True
    assert "c_new" in cand_by_id
    assert any(
        se["event_id"] == "ev_cf_choo_nom" for se in spliced["seed_events"]
    )
    # No modifiers leaked.
    assert spliced.get("candidate_modifiers", []) == []
    assert spliced.get("event_modifiers", []) == []


def test_beam_mixed_patch_shapes_dispatch_correctly():
    """Mixed declarative + imperative in the same BeamEvent must split cleanly."""
    from src.sim.scenario_tree import _splice_event_into_scenario

    mixed = BeamEvent(
        event_id="mixed_1",
        source="llm_hypothetical",
        occurs_at=_utc(2026, 5, 10),
        description="mixed patches",
        candidate_patches=[
            {"candidate_id": "c_a", "boost": 0.03},  # declarative
            {"op": "withdraw", "candidate_id": "c_b"},  # imperative
        ],
        event_patches=[
            {"issue": "지역_경제", "salience": 0.2},  # declarative
            {
                "op": "add",
                "event": {"event_id": "ev_imp", "timestep": 1, "summary": "imp"},
            },  # imperative
        ],
        prior_p=0.3,
    )
    spliced = _splice_event_into_scenario(BASE_SCENARIO, mixed)
    cand_by_id = {c["id"]: c for c in spliced["candidates"]}
    assert cand_by_id["c_b"]["withdrawn"] is True  # imperative applied
    assert cand_by_id["c_a"].get("boost") is None  # declarative did NOT apply
    assert spliced["candidate_modifiers"] == [{"candidate_id": "c_a", "boost": 0.03}]
    assert spliced["event_modifiers"] == [{"issue": "지역_경제", "salience": 0.2}]
    seed_ids = {se["event_id"] for se in spliced["seed_events"]}
    assert "ev_imp" in seed_ids
    assert "mixed_1" in seed_ids


def test_beam_raises_firewall_violation_on_temporal_leak():
    bad = BeamEvent(
        event_id="leak",
        source="custom",
        occurs_at=_utc(2026, 4, 1),  # before as_of
        description="leak",
        prior_p=0.5,
    )
    config = BeamConfig(beam_width=1, beam_depth=1, k_propose=1, strict_temporal=True)
    search = _make_search(
        config=config, proposer=_FixedProposer([[bad]]), tree_id="t_leak"
    )
    with pytest.raises(FirewallViolation):
        asyncio.run(search.expand())


def test_cli_artifact_flag_overrides_default_path(tmp_path, monkeypatch):
    """`--artifact <path>` (used by backend scenario_tree_service spawn) must
    override the default `_workspace/snapshots/scenario_trees/{tree_id}.json`.
    """
    import argparse
    from src.sim import scenario_tree as st_mod

    # Stub out everything that would touch the live LLM/KG/persona pipeline.
    async def _fake_runner(scenario, ctx):
        return {
            "scenario_id": scenario.get("scenario_id", "stub"),
            "final_outcome": {
                "winner": "c_a",
                "vote_share_by_candidate": {"c_a": 0.6, "c_b": 0.4},
            },
            "meta": {},
        }

    def _fake_make_runner(*a, **kw):
        return _fake_runner

    def _fake_load_personas(*a, **kw):
        return []

    def _fake_load_scenario(region_id):
        return BASE_SCENARIO

    def _fake_load_contracts():
        return {"regions": [{"id": "seoul_mayor", "label": "Seoul"}]}

    def _fake_load_policy():
        return {}

    def _fake_load_kg():
        return None

    monkeypatch.setattr(st_mod, "make_default_sim_runner", _fake_make_runner)
    monkeypatch.setattr(st_mod, "load_scenario", _fake_load_scenario)
    monkeypatch.setattr(st_mod, "load_contracts", _fake_load_contracts)
    monkeypatch.setattr(st_mod, "load_policy", _fake_load_policy)
    monkeypatch.setattr(st_mod, "_load_kg_retriever", _fake_load_kg)
    monkeypatch.setattr(st_mod, "build_default_backend", lambda: None)

    custom_path = tmp_path / "subdir" / "my_tree.json"
    args = argparse.Namespace(
        region="seoul_mayor",
        as_of="2026-04-26",
        beam_width=1,
        beam_depth=1,
        k_propose=1,
        proposer="custom",
        sample_n=4,
        timesteps=1,
        seed=11,
        tree_id="cli_artifact_test",
        artifact=str(custom_path),
        dry_run=True,
        no_kg=True,
    )
    # Use a no-op proposer so beam doesn't try to expand.
    monkeypatch.setattr(
        st_mod, "build_proposer", lambda *a, **kw: _FixedProposer([])
    )
    out_path = asyncio.run(st_mod._cli_main(args))
    assert out_path == custom_path
    assert custom_path.exists()
    # Default slot should NOT have been written for this tree_id.
    default_slot = (
        st_mod.TREES_DIR / "cli_artifact_test.json"
    )
    assert not default_slot.exists()


def test_cli_artifact_flag_defaults_to_trees_dir(monkeypatch):
    """When --artifact is omitted, output stays in the legacy default slot."""
    import argparse
    from src.sim import scenario_tree as st_mod

    async def _fake_runner(scenario, ctx):
        return {
            "scenario_id": scenario.get("scenario_id", "stub"),
            "final_outcome": {
                "winner": "c_a",
                "vote_share_by_candidate": {"c_a": 0.6, "c_b": 0.4},
            },
            "meta": {},
        }

    monkeypatch.setattr(
        st_mod, "make_default_sim_runner", lambda *a, **kw: _fake_runner
    )
    monkeypatch.setattr(st_mod, "load_scenario", lambda r: BASE_SCENARIO)
    monkeypatch.setattr(
        st_mod,
        "load_contracts",
        lambda: {"regions": [{"id": "seoul_mayor", "label": "Seoul"}]},
    )
    monkeypatch.setattr(st_mod, "load_policy", lambda: {})
    monkeypatch.setattr(st_mod, "_load_kg_retriever", lambda: None)
    monkeypatch.setattr(st_mod, "build_default_backend", lambda: None)
    monkeypatch.setattr(
        st_mod, "build_proposer", lambda *a, **kw: _FixedProposer([])
    )

    args = argparse.Namespace(
        region="seoul_mayor",
        as_of="2026-04-26",
        beam_width=1,
        beam_depth=1,
        k_propose=1,
        proposer="custom",
        sample_n=4,
        timesteps=1,
        seed=11,
        tree_id="cli_default_slot_test",
        artifact=None,
        dry_run=True,
        no_kg=True,
    )
    out_path = asyncio.run(st_mod._cli_main(args))
    assert out_path == st_mod.TREES_DIR / "cli_default_slot_test.json"
    assert out_path.exists()
    out_path.unlink(missing_ok=True)


def test_beam_artifact_round_trips_through_pydantic():
    e = BeamEvent(
        event_id="e1",
        source="custom",
        occurs_at=_utc(2026, 5, 5),
        description="e1",
        prior_p=0.5,
    )
    config = BeamConfig(beam_width=1, beam_depth=1, k_propose=1)
    search = _make_search(
        config=config, proposer=_FixedProposer([[e]]), tree_id="t_roundtrip"
    )
    tree = asyncio.run(search.expand())
    payload = tree.model_dump_json()
    rebuilt = ScenarioTree.model_validate_json(payload)
    assert rebuilt.tree_id == tree.tree_id
    assert rebuilt.root_id in rebuilt.nodes
    # cumulative_p sum across children of root equals d1 cum_p
    root = rebuilt.nodes[rebuilt.root_id]
    child_cum_sum = sum(rebuilt.nodes[c].cumulative_p for c in root.children)
    assert child_cum_sum == pytest.approx(0.5)
