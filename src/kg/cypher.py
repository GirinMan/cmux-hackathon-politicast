"""KG → Cypher mapping (Phase 4 #76).

Single source of truth for:

* **Label mapping** — networkx ``type`` attribute → Neo4j label.
* **Relation mapping** — networkx edge ``rel`` key → Cypher relationship type
  (``RELATIONSHIP_TYPES`` mirrors :data:`src.schemas.kg.EDGE_LABELS` exactly).
* **MERGE templates** — idempotent UPSERT statements for every node label and
  every edge relation; consumers (builder, migrator, kg_service) compose them
  with property dicts. Templates use ``$`` parameters so the
  ``neo4j-driver`` Cypher executor binds them safely.
* **Constraint / index DDL** — created on session startup so node id
  ``MERGE`` is fast and unique.
* **Temporal predicate fragments** — the firewall's
  ``ts <= cutoff`` invariant expressed once so retriever / firewall agree.

This module is **pure strings + dicts** — no driver import, no I/O. It is
exercised both by the migration tool (``tools/migrate_networkx_to_neo4j.py``)
and by the FastAPI ``kg_service`` (``backend/app/services/kg_service.py``).

Phase 2 grep gate (#28): no absolute date literal lives here. The temporal
predicate uses the parameter ``$cutoff`` injected by the caller, which itself
flows from ``src.kg._calendar_adapter``.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Optional

from src.kg.ontology import (
    ACTOR_NODE_TYPES,
    EVENT_NODE_TYPES,
    PRIOR_NODE_TYPES,
)


# ---------------------------------------------------------------------------
# Label / relation vocabulary
# ---------------------------------------------------------------------------
NODE_LABELS: tuple[str, ...] = (
    "Election",
    "Contest",
    "District",
    "Party",
    "Candidate",
    "PolicyIssue",
    "NarrativeFrame",
    "MediaEvent",
    "ScandalEvent",
    "Investigation",
    "Verdict",
    "PressConference",
    "PollPublication",
    "Person",
    "Source",
    "CohortPrior",
)

# Sanity: every event/actor/prior node type referenced by the rest of the KG
# layer must appear in NODE_LABELS — drift here would silently drop nodes
# during migration.
assert EVENT_NODE_TYPES <= set(NODE_LABELS)
assert ACTOR_NODE_TYPES <= set(NODE_LABELS)
assert PRIOR_NODE_TYPES <= set(NODE_LABELS)

RELATIONSHIP_TYPES: tuple[str, ...] = (
    "candidateIn",
    "belongsTo",
    "heldIn",
    "inElection",
    "about",
    "mentions",
    "promotes",
    "framedBy",
    "publishesPoll",
    "attributedTo",
    "speakerIs",
    "appliesToRegion",
    "leansToward",
    "damagesParty",
    "affiliatedTo",
)


# Identity property — every KG node carries ``node_id`` (the canonical
# ``"<Type>:<id>"`` string used by the networkx layer). Plus an entity-typed
# secondary id (e.g. ``candidate_id``) when applicable.
NODE_ID_KEY = "node_id"


# ---------------------------------------------------------------------------
# Constraint / index DDL — run once on session startup
# ---------------------------------------------------------------------------
def schema_ddl() -> list[str]:
    """Return the list of ``CREATE CONSTRAINT`` / ``CREATE INDEX`` statements
    a fresh Neo4j database needs.

    Idempotent — every statement uses ``IF NOT EXISTS``.
    """
    out: list[str] = []
    for label in NODE_LABELS:
        out.append(
            f"CREATE CONSTRAINT {label.lower()}_node_id_unique "
            f"IF NOT EXISTS FOR (n:{label}) "
            f"REQUIRE n.{NODE_ID_KEY} IS UNIQUE"
        )
    # Helpful indexes for common firewall / retriever lookups.
    for label in EVENT_NODE_TYPES:
        out.append(
            f"CREATE INDEX {label.lower()}_ts_idx IF NOT EXISTS "
            f"FOR (n:{label}) ON (n.ts)"
        )
        out.append(
            f"CREATE INDEX {label.lower()}_region_id_idx IF NOT EXISTS "
            f"FOR (n:{label}) ON (n.region_id)"
        )
    out.append(
        "CREATE INDEX district_region_id_idx IF NOT EXISTS "
        "FOR (n:District) ON (n.region_id)"
    )
    out.append(
        "CREATE INDEX cohort_prior_region_idx IF NOT EXISTS "
        "FOR (n:CohortPrior) ON (n.region_id)"
    )
    return out


# ---------------------------------------------------------------------------
# MERGE templates
# ---------------------------------------------------------------------------
def merge_node_query(label: str) -> str:
    """Idempotent node MERGE — keys on ``node_id``, sets every other property
    via ``+= $props`` (caller provides a flat dict)."""
    if label not in NODE_LABELS:
        raise ValueError(f"unknown KG label: {label!r}")
    return (
        f"MERGE (n:{label} {{{NODE_ID_KEY}: $node_id}}) "
        "ON CREATE SET n += $props "
        "ON MATCH SET n += $props "
        "RETURN n"
    )


def merge_edge_query(rel: str) -> str:
    """Idempotent edge MERGE — typed by ``rel``. Keys on (src.node_id,
    dst.node_id, rel), sets edge props via ``+= $edge_props``."""
    if rel not in RELATIONSHIP_TYPES:
        # We tolerate unknown rel labels (e.g. staging-introduced free-text
        # predicates) so that LLM-extracted triples don't crash the migrator.
        # The label is always quoted to stay valid Cypher.
        rel_clause = f"`{rel}`"
    else:
        rel_clause = rel
    return (
        f"MATCH (s {{{NODE_ID_KEY}: $src_id}}), (d {{{NODE_ID_KEY}: $dst_id}}) "
        f"MERGE (s)-[r:{rel_clause}]->(d) "
        "ON CREATE SET r += $edge_props "
        "ON MATCH SET r += $edge_props "
        "RETURN r"
    )


def unwind_merge_nodes_query(label: str) -> str:
    """Bulk variant — accepts ``$rows`` (list of ``{node_id, props}`` dicts).
    Cuts round-trips during migration."""
    if label not in NODE_LABELS:
        raise ValueError(f"unknown KG label: {label!r}")
    return (
        "UNWIND $rows AS row "
        f"MERGE (n:{label} {{{NODE_ID_KEY}: row.node_id}}) "
        "ON CREATE SET n += row.props "
        "ON MATCH SET n += row.props"
    )


def unwind_merge_edges_query(rel: str) -> str:
    """Bulk edge UNWIND. Each row: ``{src_id, dst_id, edge_props}``."""
    rel_clause = rel if rel in RELATIONSHIP_TYPES else f"`{rel}`"
    return (
        "UNWIND $rows AS row "
        f"MATCH (s {{{NODE_ID_KEY}: row.src_id}}), "
        f"(d {{{NODE_ID_KEY}: row.dst_id}}) "
        f"MERGE (s)-[r:{rel_clause}]->(d) "
        "ON CREATE SET r += row.edge_props "
        "ON MATCH SET r += row.edge_props"
    )


# ---------------------------------------------------------------------------
# Temporal predicate (#79) — firewall + retriever agree on this exact fragment
# ---------------------------------------------------------------------------
TS_LE_CUTOFF: str = "n.ts <= $cutoff"
TS_GT_CUTOFF: str = "n.ts > $cutoff"


def visible_events_query(event_label: Optional[str] = None) -> str:
    """Return events for ``$region_id`` whose ``ts <= $cutoff``.

    When ``event_label`` is None, the query unions across all event labels
    (callers supply the list via ``$labels`` or run multiple statements).
    """
    label_clause = f":{event_label}" if event_label else ""
    return (
        f"MATCH (n{label_clause}) "
        "WHERE n.region_id = $region_id "
        f"  AND {TS_LE_CUTOFF} "
        "RETURN n.node_id AS node_id, n.event_id AS event_id, "
        "       n.type AS type, n.ts AS ts, n.title AS title, "
        "       n.sentiment AS sentiment, n.frame_id AS frame_id "
        "ORDER BY n.ts"
    )


def future_events_audit_query() -> str:
    """Auditor — returns event nodes whose ``ts > $cutoff``. Used by
    :func:`src.kg.firewall.assert_no_future_leakage` Cypher path."""
    label_clause = "|".join(sorted(EVENT_NODE_TYPES))
    return (
        f"MATCH (n) WHERE any(l IN labels(n) WHERE l IN [{', '.join(repr(l) for l in EVENT_NODE_TYPES)}]) "
        f"  AND {TS_GT_CUTOFF} "
        "RETURN n.node_id AS node_id, n.ts AS ts, n.title AS title, "
        "       labels(n) AS labels"
    )


# ---------------------------------------------------------------------------
# Property serialisation helper
# ---------------------------------------------------------------------------
def serialize_props(attrs: dict[str, Any]) -> dict[str, Any]:
    """Coerce networkx node/edge attribute dicts into Neo4j-compatible types.

    * ``datetime`` → ISO 8601 string (Neo4j has native ``datetime`` but the
      driver's parameter binding handles strings uniformly across versions).
    * Lists of primitives → kept as-is.
    * Dicts → JSON string (Neo4j cannot store nested objects directly).
    * ``None`` values → dropped (Neo4j treats unset == None semantically).
    """
    import json as _json

    out: dict[str, Any] = {}
    for k, v in attrs.items():
        if v is None:
            continue
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, dict):
            out[k] = _json.dumps(v, ensure_ascii=False, default=str)
        elif isinstance(v, (list, tuple)):
            # If list contains dicts, JSON-encode the whole thing.
            if any(isinstance(x, (dict, list)) for x in v):
                out[k] = _json.dumps(list(v), ensure_ascii=False, default=str)
            else:
                out[k] = list(v)
        else:
            out[k] = v
    return out


def node_payload(node_id: str, attrs: dict[str, Any]) -> dict[str, Any]:
    """Build the ``$node_id``/``$props`` parameter dict for ``merge_node_query``."""
    return {
        "node_id": node_id,
        "props": serialize_props({**attrs, NODE_ID_KEY: node_id}),
    }


def edge_payload(
    src_id: str, dst_id: str, attrs: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return {
        "src_id": src_id,
        "dst_id": dst_id,
        "edge_props": serialize_props(attrs or {}),
    }


# ---------------------------------------------------------------------------
# Iteration helper for bulk migration
# ---------------------------------------------------------------------------
def group_nodes_by_label(
    g: Any,
) -> dict[str, list[dict[str, Any]]]:
    """Group networkx node dicts by their ``type`` label for UNWIND batching."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for node_id, attrs in g.nodes(data=True):
        label = attrs.get("type")
        if label not in NODE_LABELS:
            continue
        grouped.setdefault(label, []).append(node_payload(node_id, attrs))
    return grouped


def group_edges_by_rel(
    g: Any,
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for src_id, dst_id, key, attrs in g.edges(keys=True, data=True):
        rel = attrs.get("rel") or key
        # Skip edges whose endpoints aren't typed (unlikely in practice).
        if not rel:
            continue
        grouped.setdefault(rel, []).append(edge_payload(src_id, dst_id, attrs))
    return grouped


__all__ = [
    "NODE_LABELS",
    "RELATIONSHIP_TYPES",
    "NODE_ID_KEY",
    "schema_ddl",
    "merge_node_query",
    "merge_edge_query",
    "unwind_merge_nodes_query",
    "unwind_merge_edges_query",
    "visible_events_query",
    "future_events_audit_query",
    "TS_LE_CUTOFF",
    "TS_GT_CUTOFF",
    "serialize_props",
    "node_payload",
    "edge_payload",
    "group_nodes_by_label",
    "group_edges_by_rel",
]
