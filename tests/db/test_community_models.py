"""Community ORM (#90) + Alembic 0002 (#89) 회귀.

PG 미연결 환경에서도 ORM 메타데이터 / Alembic migration 모듈 import 까지는
검증 가능하다. 실 DDL apply 는 PG 띄운 환경에서 추가 게이트로 검증.
"""
from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def _has_sqlalchemy() -> bool:
    try:
        import sqlalchemy  # noqa: F401

        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# ORM metadata
# ---------------------------------------------------------------------------
def test_community_models_registered() -> None:
    if not _has_sqlalchemy():
        pytest.skip("sqlalchemy 미설치 — 컨테이너에서만 검증")
    from backend.app.db.models import (
        ALL_MODELS,
        AppUser,
        BoardTopic,
        Comment,
        CommentReport,
    )

    names = {m.__tablename__ for m in ALL_MODELS}
    assert {"app_user", "board_topic", "comment", "comment_report"} <= names


def test_phase4_models_still_registered() -> None:
    """Phase 4 12 모델 모두 유지 (회귀 보호)."""
    if not _has_sqlalchemy():
        pytest.skip("sqlalchemy 미설치")
    from backend.app.db.models import ALL_MODELS

    expected = {
        "persona_core", "persona_text",
        "raw_poll", "raw_poll_result", "poll_consensus_daily",
        "election_result",
        "ingest_run", "stg_raw_poll", "stg_raw_poll_result",
        "stg_kg_triple", "entity_alias", "unresolved_entity",
    }
    have = {m.__tablename__ for m in ALL_MODELS}
    missing = expected - have
    assert not missing, f"Phase 4 모델 회귀: {missing}"


def test_comment_self_reference() -> None:
    if not _has_sqlalchemy():
        pytest.skip("sqlalchemy 미설치")
    from backend.app.db.models import Comment

    cols = Comment.__table__.columns
    assert "parent_id" in cols
    parent_fks = list(cols["parent_id"].foreign_keys)
    assert any("comment.id" in str(fk) for fk in parent_fks), (
        "parent_id self-reference 누락"
    )


def test_comment_relationships_present() -> None:
    if not _has_sqlalchemy():
        pytest.skip("sqlalchemy 미설치")
    from backend.app.db.models import Comment

    rels = {r.key for r in Comment.__mapper__.relationships}
    assert {"author", "parent", "children", "board_topic"} <= rels


def test_comment_report_check_constraints_present() -> None:
    if not _has_sqlalchemy():
        pytest.skip("sqlalchemy 미설치")
    from backend.app.db.models import CommentReport

    constraint_names = {
        c.name for c in CommentReport.__table__.constraints if c.name
    }
    assert "ck_comment_report_one_target" in constraint_names
    assert "ck_comment_report_status" in constraint_names


def test_app_user_has_unique_anon_token() -> None:
    if not _has_sqlalchemy():
        pytest.skip("sqlalchemy 미설치")
    from backend.app.db.models import AppUser

    col = AppUser.__table__.columns["anon_token"]
    assert col.unique is True
    assert col.nullable is False


def test_uuid_columns_use_pg_dialect() -> None:
    if not _has_sqlalchemy():
        pytest.skip("sqlalchemy 미설치")
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID

    from backend.app.db.models import AppUser, BoardTopic, Comment, CommentReport

    for model in (AppUser, BoardTopic, Comment, CommentReport):
        col = model.__table__.columns["id"]
        assert isinstance(col.type, PG_UUID), (
            f"{model.__tablename__}.id is {type(col.type).__name__}, expected UUID"
        )


# ---------------------------------------------------------------------------
# Alembic 0002 migration module
# ---------------------------------------------------------------------------
def test_alembic_0002_module_imports() -> None:
    """0002 모듈이 import 가능하고 down_revision 이 0001 을 가리킨다."""
    if not _has_sqlalchemy():
        pytest.skip("sqlalchemy 미설치")
    # alembic 도 필요 — fallback skip.
    try:
        import alembic  # noqa: F401
    except Exception:
        pytest.skip("alembic 미설치")

    spec_path = REPO_ROOT / "alembic" / "versions" / "0002_community_tables.py"
    assert spec_path.exists()
    # parse 만 (Alembic context 없이 직접 exec 는 op.* 가 fail).
    src = spec_path.read_text()
    assert 'down_revision: Union[str, None] = "0001_initial"' in src
    assert 'revision: str = "0002_community"' in src
    assert "CREATE EXTENSION IF NOT EXISTS pgcrypto" in src
    assert "gen_random_uuid()" in src


def test_phase4_alembic_0001_unchanged() -> None:
    """0001 이 여전히 community 테이블을 박지 않아야 한다 (Phase 4 보존)."""
    src = (
        REPO_ROOT / "alembic" / "versions" / "0001_initial_schema.py"
    ).read_text()
    for forbidden in ("app_user", "board_topic", "comment_report"):
        assert forbidden not in src, (
            f"{forbidden!r} 가 0001 에 누출 — Phase 4 / Phase 5 분리 위반"
        )


def test_metadata_includes_community_tables() -> None:
    """Base.metadata 에 community 4 테이블 + Phase 4 12 테이블 모두 등록."""
    if not _has_sqlalchemy():
        pytest.skip("sqlalchemy 미설치")
    from backend.app.db.models import Base

    table_names = set(Base.metadata.tables.keys())
    assert {
        "app_user", "board_topic", "comment", "comment_report",
        "persona_core", "raw_poll", "stg_kg_triple",
    } <= table_names
