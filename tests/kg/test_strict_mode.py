"""Task #10 — ``POLITIKAST_KG_STRICT=1`` builds the KG with Pydantic-mirror
validation enforced. Real scenarios must round-trip through it.

Also exercises the negative path: building a synthetic event node with a
missing ``ts`` raises ``KGSchemaError`` regardless of strict mode (task #6).
"""
from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest


@pytest.fixture
def strict_builder(monkeypatch):
    """Reload ``src.kg.builder`` with POLITIKAST_KG_STRICT=1 set so the
    module-level ``_STRICT_KG`` flag picks it up."""
    monkeypatch.setenv("POLITIKAST_KG_STRICT", "1")
    import src.kg.builder as _builder
    return importlib.reload(_builder)


def test_real_scenarios_round_trip_strict(strict_builder):
    builder = strict_builder
    if not Path(builder.DEFAULT_SCENARIO_DIR).exists():
        pytest.skip("scenario dir missing")
    G, index = builder.build_kg_from_scenarios()
    if not G.number_of_nodes():
        pytest.skip("KG empty")
    # If strict mode found a malformed node it would already have raised
    # KGSchemaError. Sanity-assert all 5 regions registered.
    expected = {
        "seoul_mayor", "busan_buk_gap", "daegu_mayor",
        "gwangju_mayor", "daegu_dalseo_gap",
    }
    missing = expected - set(index.by_region.keys())
    assert not missing, f"missing regions in strict build: {missing}"


def test_event_without_ts_rejected(monkeypatch):
    """Task #6 — event nodes must carry a datetime ``ts``."""
    monkeypatch.delenv("POLITIKAST_KG_STRICT", raising=False)
    import src.kg.builder as _builder
    builder = importlib.reload(_builder)
    import networkx as nx
    G = nx.MultiDiGraph()
    with pytest.raises(builder.KGSchemaError):
        builder._add_node(
            G,
            "MediaEvent:bogus",
            type="MediaEvent",
            event_id="bogus",
            title="missing ts",
        )


def test_non_event_node_without_ts_ok():
    """Reference / actor nodes don't need ``ts`` — only event-typed do."""
    import src.kg.builder as _builder
    builder = importlib.reload(_builder)
    import networkx as nx
    G = nx.MultiDiGraph()
    builder._add_node(
        G, "Party:p_test", type="Party", party_id="p_test", name="테스트당",
    )
    assert "Party:p_test" in G.nodes
