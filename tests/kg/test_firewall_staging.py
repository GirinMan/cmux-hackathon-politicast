"""Phase 3 (#58) — firewall coverage of staging-grafted triples.

The firewall already iterates over all event-typed nodes regardless of
provenance, so a staging event with a future ``ts`` is filtered by the
retriever's ``_events_visible_at`` cutoff just like a scenario event. These
tests pin that contract and add an audit pass via
:func:`assert_staging_triples_well_formed`.
"""
from __future__ import annotations

from datetime import timedelta

import networkx as nx
import pytest

from src.kg._calendar_adapter import get_default_t_start
from src.kg.builder import KGSchemaError, build_kg_from_dicts
from src.kg.firewall import (
    FirewallViolation,
    assert_no_future_leakage,
    assert_staging_triples_well_formed,
)
from src.kg.retriever import KGRetriever
from src.kg.staging_loader import StagingTriple, merge_triple_into_graph
from tests.kg.fixtures import make_synthetic_scenario, SYNTHETIC_REGION_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_kg_with_staging(*, future: bool):
    """Build the synthetic scenario KG, then graft ONE staging MediaEvent.

    ``future=False`` → graft event at base+5d (visible from t=1 onwards).
    ``future=True``  → graft event at base+200d (must NEVER be exposed).
    """
    G, index = build_kg_from_dicts([make_synthetic_scenario()])
    base = get_default_t_start()
    offset = 200 if future else 5
    triple = StagingTriple(
        run_id="run_test",
        src_doc_id="doc_test",
        triple_idx=0,
        subj="ev_staging_01",
        pred="about",
        obj="c_kim",
        subj_kind="MediaEvent",
        obj_kind="Candidate",
        ts=base + timedelta(days=offset),
        region_id=SYNTHETIC_REGION_ID,
        confidence=0.8,
        raw_text="스테이징에서 합성된 미디어 이벤트",
    )
    merge_triple_into_graph(G, triple, scenario_node_ids=set(G.nodes))
    # Ensure the staging node carries region_id so retriever's region filter
    # picks it up via the about-edge (or via region_id attr).
    G.nodes["MediaEvent:ev_staging_01"]["region_id"] = SYNTHETIC_REGION_ID
    return G, index


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_staging_event_visible_after_cutoff():
    G, index = _make_kg_with_staging(future=False)
    retriever = KGRetriever(G, index)
    persona = {"district": "서울특별시", "age": 35, "occupation": "사무직"}
    # t=3 (== T-1 == t_end) — full disclosure.
    result = assert_no_future_leakage(
        retriever, persona, t=3, region_id=SYNTHETIC_REGION_ID, k=20,
    )
    seen = {e["event_id"] for e in result.events_used}
    assert "ev_staging_01" in seen, (
        f"staging event missing from t=T-1 disclosure: {seen}"
    )


def test_future_staging_event_never_leaks():
    G, index = _make_kg_with_staging(future=True)
    retriever = KGRetriever(G, index)
    persona = {"district": "서울특별시", "age": 35, "occupation": "사무직"}
    for t in range(4):
        result = assert_no_future_leakage(
            retriever, persona, t=t, region_id=SYNTHETIC_REGION_ID, k=20,
        )
        seen = {e["event_id"] for e in result.events_used}
        assert "ev_staging_01" not in seen, (
            f"future staging event leaked at t={t}: {seen}"
        )


def test_assert_staging_triples_well_formed_passes_on_valid_graft():
    G, _index = _make_kg_with_staging(future=False)
    inspected = assert_staging_triples_well_formed(G)
    assert inspected >= 1


def test_assert_staging_triples_well_formed_catches_missing_ts():
    """Manually inject a malformed event node with no ts to confirm the
    auditor raises (cannot go through merge_triple_into_graph because that
    would already raise KGSchemaError)."""
    G = nx.MultiDiGraph()
    G.add_node(
        "MediaEvent:bogus",
        type="MediaEvent",
        event_id="bogus",
        provenance="staging",
        # ts intentionally missing
    )
    with pytest.raises(FirewallViolation):
        assert_staging_triples_well_formed(G)


def test_event_typed_staging_triple_without_ts_is_rejected():
    """Phase 2 invariant carries through Phase 3: merge raises on missing
    ts for an event-typed subject."""
    G, _index = build_kg_from_dicts([make_synthetic_scenario()])
    bad = StagingTriple(
        run_id="r", src_doc_id="d", triple_idx=0,
        subj="ev_no_ts", pred="about", obj="c_kim",
        subj_kind="MediaEvent", obj_kind="Candidate",
        ts=None,
    )
    with pytest.raises(KGSchemaError):
        merge_triple_into_graph(G, bad, scenario_node_ids=set(G.nodes))
