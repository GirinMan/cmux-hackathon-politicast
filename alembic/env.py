"""Alembic environment — async-friendly + ORM autogenerate.

Sync engine for migrations (psycopg2). DSN 결정:
  1. ``DATABASE_URL`` env / ``POLITIKAST_PG_DSN``
  2. alembic.ini ``sqlalchemy.url``
"""
from __future__ import annotations

import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool, text

# Make repo importable.
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.app.db.models import Base, OFFICIAL_POLL_VIEW_SQL  # noqa: E402
from backend.app.db.session import resolve_dsn  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _override_url() -> str:
    """env DSN 이 있으면 그걸로 alembic.ini 의 url 을 덮어쓴다."""
    return resolve_dsn(async_=False)


def run_migrations_offline() -> None:
    url = _override_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg_section = config.get_section(config.config_ini_section) or {}
    cfg_section["sqlalchemy.url"] = _override_url()
    connectable = engine_from_config(
        cfg_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
