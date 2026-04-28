"""Task #8 — firewall self-test reinforcement.

Loads each of the 5 real scenarios from ``_workspace/data/scenarios/`` and
applies a fixed cutoff of ``2026-04-26 23:59:59`` (the hackathon date). For
every region:

1. Every ``EVENT_NODE_TYPES`` node returned by
   :py:meth:`KGRetriever._events_visible_at` must have ``ts <= cutoff``.
2. The retriever's ``subgraph_at(persona, t=0, ...)`` must not leak any
   future event into ``context_text``.
3. Any KG node whose ``ts`` is strictly greater than the cutoff must NOT
   appear in the visible set for any region.

The test is skipped (rather than failed) when the scenario directory is
missing — keeps `pytest tests/kg/ -q` green on a clean checkout.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from src.kg.builder import DEFAULT_SCENARIO_DIR, build_kg_from_scenarios
from src.kg.firewall import assert_no_future_leakage
from src.kg.ontology import EVENT_NODE_TYPES
from src.kg.retriever import KGRetriever


CUTOFF = datetime(2026, 4, 26, 23, 59, 59)
EXPECTED_REGIONS = {
    "seoul_mayor",
    "busan_buk_gap",
    "daegu_mayor",
    "gwangju_mayor",
    "daegu_dalseo_gap",
}


@pytest.fixture(scope="module")
def real_kg():
    if not Path(DEFAULT_SCENARIO_DIR).exists():
        pytest.skip("scenario dir missing")
    G, index = build_kg_from_scenarios()
    if not G.number_of_nodes():
        pytest.skip("KG empty")
    retriever = KGRetriever(G, index)
    return G, index, retriever


def test_all_5_regions_present(real_kg):
    _G, index, _r = real_kg
    have = set(index.by_region.keys())
    missing = EXPECTED_REGIONS - have
    assert not missing, f"missing scenario regions: {missing} (have {have})"


def test_visible_events_respect_cutoff(real_kg):
    _G, index, retriever = real_kg
    for region_id in index.by_region.keys():
        visible = retriever._events_visible_at(region_id, CUTOFF)
        for n, attrs in visible:
            ts = attrs.get("ts")
            assert isinstance(ts, datetime), (
                f"region={region_id} node={n} has non-datetime ts={ts!r}"
            )
            assert ts <= CUTOFF, (
                f"region={region_id} node={n} ts={ts} exceeds cutoff={CUTOFF}"
            )


def test_no_future_event_leaks_into_any_region(real_kg):
    G, index, retriever = real_kg
    future_ids: set[str] = set()
    for n, attrs in G.nodes(data=True):
        if attrs.get("type") not in EVENT_NODE_TYPES:
            continue
        ts = attrs.get("ts")
        if isinstance(ts, datetime) and ts > CUTOFF:
            future_ids.add(n)
    if not future_ids:
        pytest.skip("no future-dated events present in current KG snapshot")

    for region_id in index.by_region.keys():
        visible_ids = {n for n, _ in retriever._events_visible_at(region_id, CUTOFF)}
        leak = visible_ids & future_ids
        assert not leak, (
            f"region={region_id} leaks future events: {leak}"
        )


def test_subgraph_at_t0_no_leakage(real_kg):
    """`assert_no_future_leakage` round-trip on a generic persona at t=0."""
    _G, index, retriever = real_kg
    persona = {
        "district": "서울특별시",
        "age": 40,
        "occupation": "사무직",
        "professional_persona": "정치 관심 시민",
    }
    for region_id in index.by_region.keys():
        # cutoff at t=0 == t_start for the region; firewall must hold.
        result = assert_no_future_leakage(
            retriever, persona, t=0, region_id=region_id, k=10
        )
        # additional sanity: every emitted event timestep equals 0.
        for ev in result.events_used:
            assert ev["timestep"] == 0
