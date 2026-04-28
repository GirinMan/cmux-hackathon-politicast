"""``stg_kg_triple`` → networkx graft loader.

Phase 3 (#56): the ingest pipeline writes LLM-extracted triples into
``stg_kg_triple`` (DDL: ``src/ingest/staging.py``). This module reads those
rows, normalizes them into :class:`StagingTriple` instances, and merges them
into a builder-produced :class:`networkx.MultiDiGraph`.

Policy — **scenario > staging**: nodes / edges / attributes already present
from the curated scenario JSON win. Staging triples may only:

* Add a new node (with ``type=subj_kind``) when no scenario node exists at
  that id.
* Add a new edge ``(subj, pred, obj)`` when an identical edge does not
  already exist.
* Add an attribute ``key=pred, value=obj`` to the subject node when no
  scenario-set attribute exists for that key.

Firewall invariant carried over from Phase 2: every triple whose subject is
in :data:`src.kg.ontology.EVENT_NODE_TYPES` MUST carry a ``ts`` —
otherwise :class:`src.kg.builder.KGSchemaError` is raised.

The loader silently returns ``[]`` when the database file or the
``stg_kg_triple`` table is absent — adapter-llm may not have populated
anything yet.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import networkx as nx

from src.kg.builder import KGSchemaError, nid, parse_ts
from src.kg.ontology import (
    ACTOR_NODE_TYPES,
    EVENT_NODE_TYPES,
    PRIOR_NODE_TYPES,
)

log = logging.getLogger(__name__)

# Reference node types — anything not in {events, actors, priors, these
# extras} that shows up in ``obj_kind``/``subj_kind`` is treated as a literal
# attribute (logged at DEBUG).
_KNOWN_NODE_TYPES: frozenset[str] = (
    EVENT_NODE_TYPES
    | ACTOR_NODE_TYPES
    | PRIOR_NODE_TYPES
    | frozenset({
        "Election",
        "Contest",
        "District",
        "Party",
        "Candidate",
        "PolicyIssue",
        "NarrativeFrame",
    })
)

_LITERAL_KIND_ALIASES: frozenset[str] = frozenset({
    "literal", "Literal", "LITERAL", "string", "str", "value", "scalar",
})


# ---------------------------------------------------------------------------
# StagingTriple
# ---------------------------------------------------------------------------
@dataclass
class StagingTriple:
    """One row from ``stg_kg_triple`` after type coercion.

    Mirrors the staging DDL exactly so that ``loader → tests`` round-trips
    without translation. Use :func:`row_to_triple` to coerce a raw DuckDB
    row tuple/dict into this shape.
    """

    run_id: str
    src_doc_id: str
    triple_idx: int
    subj: str
    pred: str
    obj: str
    subj_kind: str
    obj_kind: str
    ts: Optional[datetime] = None
    region_id: Optional[str] = None
    confidence: float = 1.0
    source_url: Optional[str] = None
    raw_text: Optional[str] = None
    extras: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    @property
    def subject_node_id(self) -> str:
        return nid(self.subj_kind, self.subj)

    @property
    def is_literal_object(self) -> bool:
        return self.obj_kind in _LITERAL_KIND_ALIASES

    def object_node_id(self) -> Optional[str]:
        if self.is_literal_object:
            return None
        return nid(self.obj_kind, self.obj)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------
_SELECT_COLUMNS = (
    "run_id",
    "src_doc_id",
    "triple_idx",
    "subj",
    "pred",
    "obj",
    "subj_kind",
    "obj_kind",
    "ts",
    "region_id",
    "confidence",
    "source_url",
    "raw_text",
)


def load_kg_triples_from_staging(
    db_path: Optional[str | Path] = None,
    region_id: Optional[str] = None,
    *,
    con: Any = None,
) -> list[StagingTriple]:
    """Read ``stg_kg_triple`` rows for ``region_id`` (or all if None).

    Returns ``[]`` when the DB file or table is missing — adapter-llm may
    not have written anything yet, and downstream callers (builder /
    retriever) should treat that as a no-op.

    Filter: ``region_id IS NULL OR region_id = :region_id`` so cross-region
    triples (e.g. national-narrative events) are emitted into every
    region-scoped graft.
    """
    own_conn = False
    if con is None:
        if db_path is None:
            try:
                from src.ingest.staging import DEFAULT_DB_PATH
                db_path = DEFAULT_DB_PATH
            except Exception:
                return []
        path = Path(db_path)
        if not path.exists():
            log.debug("[kg/staging] db missing: %s — no-op", path)
            return []
        try:
            import duckdb  # type: ignore
            con = duckdb.connect(str(path), read_only=True)
            own_conn = True
        except Exception as exc:  # noqa: BLE001
            log.warning("[kg/staging] duckdb open failed: %s", exc)
            return []

    try:
        return _select_triples(con, region_id)
    finally:
        if own_conn:
            try:
                con.close()
            except Exception:
                pass


def _select_triples(con: Any, region_id: Optional[str]) -> list[StagingTriple]:
    # Explicit information_schema guard (per eval-extender's #43 spec):
    # cleaner than try/except on the actual SELECT and avoids logging noise
    # when adapter-llm has not populated anything yet.
    try:
        present = con.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'stg_kg_triple'"
        ).fetchone()
    except Exception as exc:  # noqa: BLE001
        log.debug("[kg/staging] information_schema probe failed (%s)", exc)
        return []
    if not present:
        return []

    cols = ", ".join(_SELECT_COLUMNS)
    where = ""
    params: tuple[Any, ...] = ()
    if region_id:
        where = " WHERE region_id IS NULL OR region_id = ?"
        params = (region_id,)
    # ORDER BY (run_id, src_doc_id, triple_idx) gives stable graft order so
    # repeat builds are deterministic.
    sql = (
        f"SELECT {cols} FROM stg_kg_triple{where} "
        "ORDER BY run_id, src_doc_id, triple_idx"
    )
    try:
        rows = con.execute(sql, params).fetchall()
    except Exception as exc:  # noqa: BLE001
        log.warning("[kg/staging] SELECT failed (%s) — treat as empty", exc)
        return []
    return [row_to_triple(dict(zip(_SELECT_COLUMNS, r))) for r in rows]


def row_to_triple(row: dict[str, Any]) -> StagingTriple:
    """Coerce a single DuckDB row dict into a :class:`StagingTriple`.

    Defensive parsing: missing ``confidence`` defaults to 1.0; ``triple_idx``
    is coerced to int; ``ts`` is parsed via :func:`src.kg.builder.parse_ts`
    when present (None otherwise — the merger raises on event-typed
    subjects with missing ts).
    """
    ts_raw = row.get("ts")
    ts: Optional[datetime] = None
    if ts_raw not in (None, ""):
        try:
            ts = parse_ts(ts_raw)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "[kg/staging] unparsable ts=%r on triple "
                "(%s, %s, %s) — dropped to None: %s",
                ts_raw, row.get("subj"), row.get("pred"), row.get("obj"), exc,
            )
            ts = None
    try:
        triple_idx = int(row.get("triple_idx") or 0)
    except (TypeError, ValueError):
        triple_idx = 0
    try:
        confidence = float(row.get("confidence") if row.get("confidence") is not None else 1.0)
    except (TypeError, ValueError):
        confidence = 1.0
    return StagingTriple(
        run_id=str(row.get("run_id") or ""),
        src_doc_id=str(row.get("src_doc_id") or ""),
        triple_idx=triple_idx,
        subj=str(row.get("subj") or ""),
        pred=str(row.get("pred") or ""),
        obj=str(row.get("obj") if row.get("obj") is not None else ""),
        subj_kind=str(row.get("subj_kind") or "Literal"),
        obj_kind=str(row.get("obj_kind") or "Literal"),
        ts=ts,
        region_id=row.get("region_id") or None,
        confidence=confidence,
        source_url=row.get("source_url") or None,
        raw_text=row.get("raw_text") or None,
    )


# ---------------------------------------------------------------------------
# Merger — scenario > staging
# ---------------------------------------------------------------------------
def merge_triple_into_graph(
    g: nx.MultiDiGraph,
    triple: StagingTriple,
    *,
    scenario_node_ids: Optional[set[str]] = None,
) -> dict[str, int]:
    """Graft ONE :class:`StagingTriple` onto ``g``.

    Returns a small counters dict (``nodes_added`` / ``edges_added`` /
    ``attrs_added`` / ``skipped_due_to_scenario``) so callers can summarize
    the merge for logging.

    Precedence rules (#57):
      * If ``triple.subject_node_id`` already exists in ``scenario_node_ids``
        — that is, the curated scenario authoritatively owns the node — do
        NOT override its ``type`` or its existing attributes. We may still
        add brand-new attributes/edges, but we never overwrite.
      * If an identical ``(subj, pred, obj)`` edge already exists, skip.
      * Literal-object triples become an attribute on the subject; we never
        overwrite an existing key (scenario wins on attribute keys too).
    """
    counters = {
        "nodes_added": 0, "edges_added": 0,
        "attrs_added": 0, "skipped_due_to_scenario": 0,
    }
    scenario_node_ids = scenario_node_ids or set()

    # ---- Firewall invariant: event-typed subject must carry ts.
    if triple.subj_kind in EVENT_NODE_TYPES and triple.ts is None:
        raise KGSchemaError(
            f"[kg/staging] event-typed triple subject "
            f"{triple.subject_node_id!r} missing ts "
            f"(run_id={triple.run_id}, src_doc_id={triple.src_doc_id}, "
            f"triple_idx={triple.triple_idx})"
        )

    subj_node = triple.subject_node_id

    # ---- Subject node — add iff missing.
    if subj_node not in g.nodes:
        attrs: dict[str, Any] = {
            "type": triple.subj_kind,
            "label": triple.subj,
            "provenance": "staging",
            "source_url": triple.source_url or "",
            "confidence": triple.confidence,
        }
        if triple.subj_kind in EVENT_NODE_TYPES:
            attrs["ts"] = triple.ts
            attrs["event_id"] = triple.subj
            attrs["region_id"] = triple.region_id
            attrs.setdefault("title", triple.raw_text or triple.subj)
            attrs.setdefault("source", "")
            attrs.setdefault("sentiment", 0.0)
        g.add_node(subj_node, **attrs)
        counters["nodes_added"] += 1
    elif subj_node in scenario_node_ids:
        # scenario owns this node — we won't touch its existing attrs.
        pass

    # ---- Object: literal vs. entity.
    if triple.is_literal_object:
        existing = g.nodes[subj_node]
        if triple.pred in existing:
            counters["skipped_due_to_scenario"] += 1
        else:
            existing[triple.pred] = triple.obj
            counters["attrs_added"] += 1
        return counters

    obj_kind = triple.obj_kind
    if obj_kind not in _KNOWN_NODE_TYPES:
        log.debug(
            "[kg/staging] unknown obj_kind=%r on triple (%s,%s,%s) — "
            "treating as literal attribute",
            obj_kind, triple.subj, triple.pred, triple.obj,
        )
        existing = g.nodes[subj_node]
        if triple.pred not in existing:
            existing[triple.pred] = triple.obj
            counters["attrs_added"] += 1
        return counters

    obj_node = triple.object_node_id() or ""
    if obj_node and obj_node not in g.nodes:
        g.add_node(
            obj_node,
            type=obj_kind,
            label=triple.obj,
            provenance="staging",
        )
        counters["nodes_added"] += 1

    # ---- Edge — add iff no existing edge with same key.
    existing_keys = {
        k for _, dst, k in g.out_edges(subj_node, keys=True) if dst == obj_node
    }
    if triple.pred in existing_keys:
        counters["skipped_due_to_scenario"] += 1
        return counters

    g.add_edge(
        subj_node,
        obj_node,
        key=triple.pred,
        rel=triple.pred,
        provenance="staging",
        confidence=triple.confidence,
        run_id=triple.run_id,
    )
    counters["edges_added"] += 1
    return counters


# Single-leading-underscore alias matches the spec: `_merge_triple_into_graph`.
_merge_triple_into_graph = merge_triple_into_graph


def merge_triples_into_graph(
    g: nx.MultiDiGraph,
    triples: list[StagingTriple],
    *,
    scenario_node_ids: Optional[set[str]] = None,
) -> dict[str, int]:
    """Bulk wrapper — accumulates per-triple counters."""
    agg = {"nodes_added": 0, "edges_added": 0,
           "attrs_added": 0, "skipped_due_to_scenario": 0}
    scenario_node_ids = scenario_node_ids or set(g.nodes)
    for t in triples:
        c = merge_triple_into_graph(g, t, scenario_node_ids=scenario_node_ids)
        for k, v in c.items():
            agg[k] = agg.get(k, 0) + v
    return agg


__all__ = [
    "StagingTriple",
    "load_kg_triples_from_staging",
    "row_to_triple",
    "merge_triple_into_graph",
    "merge_triples_into_graph",
    "_merge_triple_into_graph",
]
