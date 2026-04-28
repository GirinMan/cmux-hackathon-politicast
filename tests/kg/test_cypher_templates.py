"""Phase 4 (#76) — Cypher template + payload sanity.

Pure-string tests; no Neo4j driver required. Confirms label / relation
vocabulary covers every networkx node ``type`` / edge ``rel`` actually
emitted by the 5-region build, so migration mirrors the in-process KG
losslessly.
"""
from __future__ import annotations

from datetime import datetime

from src.kg import cypher
from src.kg.builder import build_kg_from_scenarios


# ---------------------------------------------------------------------------
# Vocabulary coverage
# ---------------------------------------------------------------------------
def test_node_labels_include_event_actor_prior():
    assert {"MediaEvent", "ScandalEvent", "PollPublication"} <= set(cypher.NODE_LABELS)
    assert {"Person", "Source"} <= set(cypher.NODE_LABELS)
    assert "CohortPrior" in cypher.NODE_LABELS


def test_relationship_types_cover_5_region_build():
    G, _ = build_kg_from_scenarios()
    seen_rels = set()
    for _u, _v, _k, attrs in G.edges(keys=True, data=True):
        seen_rels.add(attrs.get("rel"))
    seen_rels.discard(None)
    # Every edge label that appears in the real 5-region build must be in
    # the cypher vocabulary so unwind_merge_edges_query never emits a
    # backtick-escaped fallback for production data.
    missing = seen_rels - set(cypher.RELATIONSHIP_TYPES)
    assert not missing, f"unmapped edge rels: {missing}"


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
def test_schema_ddl_is_idempotent_shape():
    stmts = cypher.schema_ddl()
    assert stmts, "expected at least one DDL statement"
    assert all("IF NOT EXISTS" in s for s in stmts), (
        "all CREATE statements must be idempotent"
    )


def test_merge_node_query_uses_node_id_param():
    q = cypher.merge_node_query("Candidate")
    assert "MERGE (n:Candidate {node_id: $node_id})" in q
    assert "$props" in q


def test_merge_edge_query_keys_endpoints_then_rel():
    q = cypher.merge_edge_query("about")
    assert "$src_id" in q and "$dst_id" in q
    assert "[r:about]" in q


def test_unknown_relation_label_is_quoted():
    """Tolerate LLM-extracted free-text predicates without crashing."""
    q = cypher.merge_edge_query("hasFreeFormPredicate")
    assert "`hasFreeFormPredicate`" in q


def test_temporal_predicates():
    assert cypher.TS_LE_CUTOFF == "n.ts <= $cutoff"
    assert cypher.TS_GT_CUTOFF == "n.ts > $cutoff"
    assert "$cutoff" in cypher.visible_events_query()


# ---------------------------------------------------------------------------
# Payload serialisation
# ---------------------------------------------------------------------------
def test_serialize_props_handles_datetime_and_dict():
    payload = cypher.serialize_props({
        "ts": datetime(2030, 1, 2, 3, 4, 5),
        "party_lean": {"ppp": 0.3, "dpk": 0.4},
        "tags": ["a", "b"],
        "noisy_none": None,
    })
    assert payload["ts"] == "2030-01-02T03:04:05"
    assert isinstance(payload["party_lean"], str) and "ppp" in payload["party_lean"]
    assert payload["tags"] == ["a", "b"]
    assert "noisy_none" not in payload, "None values must be dropped"


def test_node_payload_injects_node_id():
    p = cypher.node_payload("Candidate:c_kim", {"name": "김민주"})
    assert p["node_id"] == "Candidate:c_kim"
    assert p["props"]["node_id"] == "Candidate:c_kim"
    assert p["props"]["name"] == "김민주"


def test_group_nodes_and_edges_match_5_region_build():
    G, _ = build_kg_from_scenarios()
    nodes_by_label = cypher.group_nodes_by_label(G)
    edges_by_rel = cypher.group_edges_by_rel(G)
    # Every grouped node must have a non-empty label.
    assert all(label in cypher.NODE_LABELS for label in nodes_by_label)
    # Total grouped == total typed nodes.
    typed = sum(
        1 for _, a in G.nodes(data=True) if a.get("type") in cypher.NODE_LABELS
    )
    assert sum(len(v) for v in nodes_by_label.values()) == typed
    # Edges round-trip too.
    assert sum(len(v) for v in edges_by_rel.values()) == G.number_of_edges()
