"""Neo4j async session wrapper (Phase 4 #75).

Wraps :mod:`neo4j` (the official async driver) into a small surface tailored
to PolitiKAST's KG layer:

* :func:`get_driver` — singleton driver, configured from
  :class:`backend.app.settings.Settings` (``neo4j_uri``, ``neo4j_user``,
  ``neo4j_password``).
* :func:`get_session` — FastAPI ``yield`` dependency (``Depends(get_neo4j_session)``)
  that scopes one async session per request.
* :func:`run_read` / :func:`run_write` — helpers that execute a Cypher query
  with parameters and return rows as ``list[dict]``. Used by
  :mod:`backend.app.services.kg_service` and the migration script.
* :func:`apply_schema` — runs ``src.kg.cypher.schema_ddl()`` once on startup.
* :class:`InMemoryNeo4jSession` — pure-Python stub that records every Cypher
  query invocation. Used by tests so the suite stays driver-independent.

When the ``neo4j`` driver is not installed, :func:`get_driver` returns
``None`` and dependents must short-circuit (``kg_service`` falls back to the
networkx in-process retriever).
"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Optional

from src.kg.cypher import schema_ddl

logger = logging.getLogger("backend.db.neo4j")

try:
    from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession  # type: ignore
    _DRIVER_AVAILABLE = True
except Exception:  # ImportError on dev machines without the package
    AsyncDriver = Any  # type: ignore[assignment, misc]
    AsyncSession = Any  # type: ignore[assignment, misc]
    AsyncGraphDatabase = None  # type: ignore[assignment]
    _DRIVER_AVAILABLE = False


_DRIVER_SINGLETON: Optional[Any] = None
_DRIVER_LOCK = asyncio.Lock()


def driver_available() -> bool:
    """True when the ``neo4j`` package is importable in this interpreter."""
    return _DRIVER_AVAILABLE


# ---------------------------------------------------------------------------
# Driver lifecycle
# ---------------------------------------------------------------------------
async def get_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
) -> Optional[Any]:
    """Return the singleton :class:`neo4j.AsyncDriver`, creating it on first
    call. ``None`` when the driver package is unavailable or no URI is set."""
    global _DRIVER_SINGLETON
    if not _DRIVER_AVAILABLE:
        return None
    uri = uri or os.environ.get("NEO4J_URI") or _settings_attr("neo4j_uri")
    if not uri:
        return None
    user = user or os.environ.get("NEO4J_USER") or _settings_attr("neo4j_user") or "neo4j"
    password = (
        password
        or os.environ.get("NEO4J_PASSWORD")
        or _settings_attr("neo4j_password")
        or "password"
    )
    async with _DRIVER_LOCK:
        if _DRIVER_SINGLETON is None:
            logger.info("[kg/neo4j] connecting driver to %s", uri)
            _DRIVER_SINGLETON = AsyncGraphDatabase.driver(  # type: ignore[union-attr]
                uri, auth=(user, password)
            )
    return _DRIVER_SINGLETON


def _settings_attr(name: str) -> Optional[str]:
    """Fish a value out of :class:`backend.app.settings.Settings` without
    forcing the import at module load (so this file works inside the
    ``src/`` execution path used by tests)."""
    try:
        from backend.app.settings import get_settings
    except Exception:
        return None
    try:
        s = get_settings()
    except Exception:
        return None
    return getattr(s, name, None)


async def close_driver() -> None:
    global _DRIVER_SINGLETON
    if _DRIVER_SINGLETON is None:
        return
    try:
        await _DRIVER_SINGLETON.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[kg/neo4j] driver close failed: %s", exc)
    _DRIVER_SINGLETON = None


# ---------------------------------------------------------------------------
# Session dependency
# ---------------------------------------------------------------------------
async def get_session() -> AsyncIterator[Any]:
    """FastAPI dependency — one session per request. Yields ``None`` when the
    driver is unavailable so routes can degrade gracefully."""
    drv = await get_driver()
    if drv is None:
        yield None
        return
    session = drv.session()
    try:
        yield session
    finally:
        await session.close()


@asynccontextmanager
async def session_ctx() -> AsyncIterator[Any]:
    """Standalone (non-FastAPI) helper for scripts."""
    drv = await get_driver()
    if drv is None:
        raise RuntimeError("Neo4j driver unavailable — set NEO4J_URI / install driver")
    session = drv.session()
    try:
        yield session
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Read / write helpers
# ---------------------------------------------------------------------------
async def run_read(
    session: Any, query: str, params: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Execute ``query`` in a read transaction and return rows as dicts."""
    async def _runner(tx):
        result = await tx.run(query, **(params or {}))
        rows = []
        async for record in result:
            rows.append(dict(record))
        return rows

    return await session.execute_read(_runner)


async def run_write(
    session: Any, query: str, params: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    async def _runner(tx):
        result = await tx.run(query, **(params or {}))
        rows = []
        async for record in result:
            rows.append(dict(record))
        return rows

    return await session.execute_write(_runner)


async def apply_schema(session: Any) -> int:
    """Run every DDL statement from :func:`src.kg.cypher.schema_ddl`. Returns
    the count of statements executed (idempotent)."""
    n = 0
    for stmt in schema_ddl():
        await run_write(session, stmt)
        n += 1
    return n


# ---------------------------------------------------------------------------
# In-memory test stub
# ---------------------------------------------------------------------------
@dataclass
class _RecordedQuery:
    query: str
    params: dict[str, Any] = field(default_factory=dict)


class InMemoryNeo4jSession:
    """Driver-less stub used by tests.

    Records every ``execute_read`` / ``execute_write`` invocation so tests
    can assert on the Cypher emitted. ``run_read`` / ``run_write`` return
    whatever the optional ``responder`` callback yields.
    """

    def __init__(self, responder: Optional[Callable[[_RecordedQuery], list[dict[str, Any]]]] = None):
        self.queries: list[_RecordedQuery] = []
        self._responder = responder or (lambda _q: [])

    # ``execute_read`` / ``execute_write`` mirror neo4j-driver's session API
    # by accepting a unit-of-work callable; we feed it a fake transaction.
    async def execute_read(self, fn):
        return await fn(_FakeTx(self))

    async def execute_write(self, fn):
        return await fn(_FakeTx(self))

    async def close(self) -> None:  # parity with the real session
        return None


class _FakeTx:
    def __init__(self, session: "InMemoryNeo4jSession"):
        self._session = session

    async def run(self, query: str, **params):
        rec = _RecordedQuery(query=query, params=params)
        self._session.queries.append(rec)
        rows = self._session._responder(rec)
        return _FakeResult(rows)


class _FakeResult:
    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = rows

    def __aiter__(self):
        async def _gen():
            for r in self._rows:
                yield _FakeRecord(r)
        return _gen()


class _FakeRecord(dict):
    pass


__all__ = [
    "driver_available",
    "get_driver",
    "close_driver",
    "get_session",
    "session_ctx",
    "run_read",
    "run_write",
    "apply_schema",
    "InMemoryNeo4jSession",
]
