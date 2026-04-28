"""Postgres async DB layer (SQLAlchemy 2.x).

backend/app/db/
  session.py — async engine + session factory + get_session() FastAPI dep
  models.py  — ORM declarative mirror of src/schemas/* + ingest tables
  pg_dialect.py — INSERT … ON CONFLICT helpers shared with src/ingest/staging
  legacy_duckdb.py — fallback connection for existing DuckDB DB during cutover

Cutover policy (Phase 4):
- 정식 backend 는 Postgres 16 (docker-compose 의 `postgres` 서비스, DSN 은
  `POLITIKAST_PG_DSN` env). 기존 DuckDB 파일은 ``tools/migrate_duckdb_to_postgres.py``
  로 이전 후 ``_workspace/db/_archive/`` 로 이동한다.
- `POLITIKAST_DB_BACKEND=duckdb` 로 명시되면 src/data/* 가 DuckDB legacy 경로로
  fallback (tests / 부분 cutover 환경에서 회귀 보전).
"""
from __future__ import annotations

from .session import (  # noqa: F401
    Base,
    DEFAULT_PG_DSN,
    create_async_engine_for,
    get_async_session_factory,
    get_session,
    is_postgres_enabled,
)

__all__ = [
    "Base",
    "DEFAULT_PG_DSN",
    "create_async_engine_for",
    "get_async_session_factory",
    "get_session",
    "is_postgres_enabled",
]
