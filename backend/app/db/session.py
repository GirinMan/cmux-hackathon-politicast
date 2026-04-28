"""SQLAlchemy 2.x async engine + session factory.

DSN 결정 순서
-------------
1. ``settings.postgres_dsn`` (POLITIKAST_API_POSTGRES_DSN env)
2. ``POLITIKAST_PG_DSN`` env
3. ``DATABASE_URL`` env (12-factor 표준)
4. fallback: ``postgresql+asyncpg://politikast:politikast@localhost:5433/politikast``

Tests / dev 에서 PG 가 떠있지 않으면 ``is_postgres_enabled()`` 가 False 를
반환해 `src/data/*` 가 DuckDB 경로로 fallback 한다.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import AsyncIterator, Optional

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger("backend.db.session")


DEFAULT_PG_DSN = (
    "postgresql+asyncpg://politikast:politikast@localhost:5433/politikast"
)
DEFAULT_SYNC_PG_DSN = (
    "postgresql+psycopg2://politikast:politikast@localhost:5433/politikast"
)


# ---------------------------------------------------------------------------
# Declarative base + metadata naming convention (Alembic friendly)
# ---------------------------------------------------------------------------
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# ---------------------------------------------------------------------------
# DSN resolution
# ---------------------------------------------------------------------------
def resolve_dsn(*, async_: bool = True) -> str:
    """settings → env → default 순으로 DSN 해석."""
    try:
        from backend.app.settings import get_settings  # local import

        s = get_settings()
        dsn = getattr(s, "postgres_dsn", None)
        if dsn:
            return _ensure_async_driver(dsn) if async_ else _ensure_sync_driver(dsn)
    except Exception:
        pass
    raw = (
        os.environ.get("POLITIKAST_PG_DSN")
        or os.environ.get("DATABASE_URL")
        or (DEFAULT_PG_DSN if async_ else DEFAULT_SYNC_PG_DSN)
    )
    return _ensure_async_driver(raw) if async_ else _ensure_sync_driver(raw)


def _ensure_async_driver(dsn: str) -> str:
    if dsn.startswith("postgresql://"):
        return "postgresql+asyncpg://" + dsn[len("postgresql://"):]
    if dsn.startswith("postgres://"):
        return "postgresql+asyncpg://" + dsn[len("postgres://"):]
    return dsn


def _ensure_sync_driver(dsn: str) -> str:
    if dsn.startswith("postgresql+asyncpg://"):
        return "postgresql+psycopg2://" + dsn[len("postgresql+asyncpg://"):]
    if dsn.startswith("postgres://"):
        return "postgresql+psycopg2://" + dsn[len("postgres://"):]
    if dsn.startswith("postgresql://") and "+" not in dsn.split("://", 1)[1].split("@", 1)[0]:
        # `postgresql://...` 그대로 두면 SQLAlchemy 가 default psycopg2 사용.
        return dsn
    return dsn


def is_postgres_enabled() -> bool:
    """env 에 PG DSN 이 명시됐는지 (없으면 src/data/* 가 DuckDB fallback)."""
    if os.environ.get("POLITIKAST_DB_BACKEND", "").lower() == "duckdb":
        return False
    if os.environ.get("POLITIKAST_PG_DSN") or os.environ.get("DATABASE_URL"):
        return True
    try:
        from backend.app.settings import get_settings

        s = get_settings()
        return bool(getattr(s, "postgres_dsn", None) or getattr(s, "enable_postgres", False))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Engine / sessionmaker — lazily created and cached
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _async_engine() -> AsyncEngine:
    dsn = resolve_dsn(async_=True)
    logger.info("creating async engine for %s", _redact(dsn))
    return create_async_engine(dsn, future=True, pool_pre_ping=True)


def create_async_engine_for(dsn: Optional[str] = None) -> AsyncEngine:
    """Explicit DSN 으로 새 엔진 생성 (tests / migration 도구가 사용)."""
    return create_async_engine(
        dsn or resolve_dsn(async_=True), future=True, pool_pre_ping=True
    )


@lru_cache(maxsize=1)
def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        _async_engine(), expire_on_commit=False, class_=AsyncSession
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency — async session 한 개를 yield."""
    factory = get_async_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """script / migration tool 용 async with 컨텍스트."""
    factory = get_async_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def _redact(dsn: str) -> str:
    if "@" not in dsn:
        return dsn
    head, tail = dsn.rsplit("@", 1)
    if "//" in head:
        scheme, creds = head.split("//", 1)
        if ":" in creds:
            user, _ = creds.split(":", 1)
            return f"{scheme}//{user}:***@{tail}"
    return dsn


__all__ = [
    "Base",
    "DEFAULT_PG_DSN",
    "DEFAULT_SYNC_PG_DSN",
    "create_async_engine_for",
    "get_async_session_factory",
    "get_session",
    "is_postgres_enabled",
    "resolve_dsn",
    "session_scope",
]
