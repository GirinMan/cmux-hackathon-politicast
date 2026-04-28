"""Phase 4 (#77 / #80) — networkx → Neo4j mirror smoke (driver-less).

Uses ``InMemoryNeo4jSession`` so we can assert on the exact UNWIND payloads
emitted by :func:`src.kg.builder.apply_graph_to_neo4j` for the real 5-region
build. Drives the migrator end-to-end without a Neo4j container."""
from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path


def _load_neo4j_session_module():
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "backend" / "app" / "db" / "neo4j_session.py"
    spec = importlib.util.spec_from_file_location(
        "_kg_neo4j_session_under_test_2", path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    # Critical: the builder will `from backend.app.db.neo4j_session import ...`
    # so we register the same module under the canonical dotted path too,
    # and stub the parent package to bypass its SQLAlchemy import.
    sys.modules.setdefault("backend", _make_pkg_stub("backend"))
    sys.modules.setdefault("backend.app", _make_pkg_stub("backend.app"))
    sys.modules.setdefault("backend.app.db", _make_pkg_stub("backend.app.db"))
    sys.modules["backend.app.db.neo4j_session"] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_pkg_stub(name: str):
    import types
    pkg = types.ModuleType(name)
    pkg.__path__ = []  # type: ignore[attr-defined]
    return pkg


def test_apply_graph_to_neo4j_mirrors_all_nodes_and_edges():
    neo4j_mod = _load_neo4j_session_module()
    from src.kg.builder import apply_graph_to_neo4j, build_kg_from_scenarios
    from src.kg.cypher import group_edges_by_rel, group_nodes_by_label

    G, _index = build_kg_from_scenarios()
    expected_nodes = sum(
        len(v) for v in group_nodes_by_label(G).values()
    )
    expected_edges = sum(
        len(v) for v in group_edges_by_rel(G).values()
    )

    session = neo4j_mod.InMemoryNeo4jSession()

    async def _run():
        return await apply_graph_to_neo4j(G, session)

    counters = asyncio.run(_run())

    assert counters["nodes_merged"] == expected_nodes
    assert counters["edges_merged"] == expected_edges
    assert counters["ddl_applied"] > 0

    # Every emitted query is either a CREATE CONSTRAINT/INDEX (DDL) or a
    # MERGE — no stray writes.
    for q in session.queries:
        assert "CREATE" in q.query or "MERGE" in q.query


def test_5_region_smoke_preserves_220_374_counts():
    """Phase 3 invariant — staging-on graph still 220 nodes / 374 edges."""
    import os
    os.environ.setdefault("POLITIKAST_KG_USE_STAGING", "1")
    from src.kg.builder import build_with_staging

    G, idx = build_with_staging()
    assert G.number_of_nodes() == 220
    assert G.number_of_edges() == 374
    assert sorted(idx.by_region) == [
        "busan_buk_gap", "daegu_dalseo_gap", "daegu_mayor",
        "gwangju_mayor", "seoul_mayor",
    ]
