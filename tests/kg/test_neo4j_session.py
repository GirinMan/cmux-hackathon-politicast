"""Phase 4 (#75) — driver-less coverage of ``neo4j_session.py``.

Loads the module via :mod:`importlib` so the test stays insulated from the
``backend.app.db`` package init (which pulls in SQLAlchemy from the
db-postgres stream and would otherwise force a hard dependency)."""
from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest


def _load_neo4j_session_module():
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "backend" / "app" / "db" / "neo4j_session.py"
    spec = importlib.util.spec_from_file_location(
        "_kg_neo4j_session_under_test", path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def neo4j_mod():
    return _load_neo4j_session_module()


def test_driver_unavailable_returns_none(neo4j_mod, monkeypatch):
    monkeypatch.delenv("NEO4J_URI", raising=False)
    drv = asyncio.run(neo4j_mod.get_driver())
    # On dev machines neo4j-python isn't installed → None. When the package
    # IS installed, the env var is missing so it still returns None. Either
    # way the contract holds.
    assert drv is None


def test_in_memory_session_records_queries(neo4j_mod):
    session = neo4j_mod.InMemoryNeo4jSession(
        responder=lambda q: [{"echo": q.query}]
    )

    async def _run():
        rows = await neo4j_mod.run_read(session, "RETURN 1", {"x": 7})
        return rows

    rows = asyncio.run(_run())
    assert len(session.queries) == 1
    assert session.queries[0].query == "RETURN 1"
    assert session.queries[0].params == {"x": 7}
    assert rows == [{"echo": "RETURN 1"}]


def test_apply_schema_runs_every_ddl(neo4j_mod):
    from src.kg.cypher import schema_ddl

    session = neo4j_mod.InMemoryNeo4jSession()

    async def _run():
        return await neo4j_mod.apply_schema(session)

    n = asyncio.run(_run())
    expected = len(schema_ddl())
    assert n == expected
    assert len(session.queries) == expected
    # First statement is a constraint create — sanity check.
    assert "CREATE CONSTRAINT" in session.queries[0].query
