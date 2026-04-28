"""ScenarioTree + ScenarioEvent ORM (#12) + Alembic 0003 (#11) 회귀.

PG 미연결 환경에서도 ORM 메타데이터 import / Alembic migration 모듈 import 까지는
검증 가능. 실 DDL apply / IntegrityError 검증은 PG 띄운 환경에서 추가 게이트로.
"""
from __future__ import annotations

import importlib
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
def test_scenario_models_registered() -> None:
    if not _has_sqlalchemy():
        pytest.skip("sqlalchemy 미설치 — 컨테이너에서만 검증")
    from backend.app.db.models import ALL_MODELS, ScenarioEvent, ScenarioTree

    names = {m.__tablename__ for m in ALL_MODELS}
    assert {"scenario_tree", "scenario_event"} <= names
    assert ScenarioTree.__tablename__ == "scenario_tree"
    assert ScenarioEvent.__tablename__ == "scenario_event"


def test_phase5_models_still_registered() -> None:
    """Phase 5 community 모델 회귀 보호."""
    if not _has_sqlalchemy():
        pytest.skip("sqlalchemy 미설치")
    from backend.app.db.models import ALL_MODELS

    expected = {"app_user", "board_topic", "comment", "comment_report"}
    have = {m.__tablename__ for m in ALL_MODELS}
    missing = expected - have
    assert not missing, f"Phase 5 모델 회귀: {missing}"


def test_scenario_tree_unique_constraint_declared() -> None:
    if not _has_sqlalchemy():
        pytest.skip("sqlalchemy 미설치")
    from backend.app.db.models import ScenarioTree

    uq_names = {
        c.name
        for c in ScenarioTree.__table__.constraints
        if c.__class__.__name__ == "UniqueConstraint"
    }
    assert "uq_scenario_tree_region_contest_as_of" in uq_names

    ck_names = {
        c.name
        for c in ScenarioTree.__table__.constraints
        if c.__class__.__name__ == "CheckConstraint"
    }
    assert "ck_scenario_tree_status" in ck_names


def test_scenario_event_check_constraints_declared() -> None:
    if not _has_sqlalchemy():
        pytest.skip("sqlalchemy 미설치")
    from backend.app.db.models import ScenarioEvent

    ck_names = {
        c.name
        for c in ScenarioEvent.__table__.constraints
        if c.__class__.__name__ == "CheckConstraint"
    }
    assert "ck_scenario_event_source" in ck_names
    assert "ck_scenario_event_prior_p" in ck_names

    # 'metadata' 컬럼은 DB-side 이름 — Python attr 은 'event_metadata'.
    cols = {c.name for c in ScenarioEvent.__table__.columns}
    assert "metadata" in cols
    assert "candidate_patches" in cols
    assert "event_patches" in cols


# ---------------------------------------------------------------------------
# Alembic migration import
# ---------------------------------------------------------------------------
def test_alembic_0003_module_imports() -> None:
    if not _has_sqlalchemy():
        pytest.skip("sqlalchemy 미설치")
    mod = importlib.import_module("alembic.versions.0003_scenario_tree")
    assert mod.revision == "0003_scenario_tree"
    assert mod.down_revision == "0002_community"
    assert callable(mod.upgrade)
    assert callable(mod.downgrade)


# ---------------------------------------------------------------------------
# CRUD smoke / IntegrityError — PG 가 떠 있을 때만
# ---------------------------------------------------------------------------
def _pg_session_available() -> bool:
    if not _has_sqlalchemy():
        return False
    try:
        from backend.app.db.session import SessionLocal  # type: ignore
        s = SessionLocal()
        s.execute  # touch
        s.close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _pg_session_available(), reason="Postgres 세션 미가용")
def test_scenario_tree_unique_violation_raises() -> None:  # pragma: no cover
    import datetime as dt
    from sqlalchemy.exc import IntegrityError
    from backend.app.db.models import ScenarioTree
    from backend.app.db.session import SessionLocal

    s = SessionLocal()
    try:
        a = ScenarioTree(
            region_id="seoul_mayor",
            contest_id="seoul_mayor_2026",
            as_of=dt.date(2026, 4, 28),
            election_date=dt.date(2026, 6, 3),
            beam_width=3,
            beam_depth=4,
            config={},
            artifact_path="_workspace/snapshots/scenario_trees/test_a.json",
            status="building",
        )
        b = ScenarioTree(
            region_id="seoul_mayor",
            contest_id="seoul_mayor_2026",
            as_of=dt.date(2026, 4, 28),
            election_date=dt.date(2026, 6, 3),
            beam_width=5,
            beam_depth=4,
            config={},
            artifact_path="_workspace/snapshots/scenario_trees/test_b.json",
            status="building",
        )
        s.add(a)
        s.flush()
        s.add(b)
        with pytest.raises(IntegrityError):
            s.flush()
    finally:
        s.rollback()
        s.close()


@pytest.mark.skipif(not _pg_session_available(), reason="Postgres 세션 미가용")
def test_scenario_event_check_violation_raises() -> None:  # pragma: no cover
    import datetime as dt
    from sqlalchemy.exc import IntegrityError
    from backend.app.db.models import ScenarioEvent
    from backend.app.db.session import SessionLocal

    s = SessionLocal()
    try:
        # prior_p 범위 위반
        bad = ScenarioEvent(
            region_id="seoul_mayor",
            source="custom",
            occurs_at=dt.datetime(2026, 5, 1, tzinfo=dt.timezone.utc),
            description="bad prior",
            prior_p=1.5,
        )
        s.add(bad)
        with pytest.raises(IntegrityError):
            s.flush()
    finally:
        s.rollback()
        s.close()
