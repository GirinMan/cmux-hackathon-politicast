"""ORM mirror of `src/schemas/*` + ingestion staging tables.

설계 원칙
---------
- Pydantic 모델은 read-side / 어댑터 인터페이스 SoT.
- ORM 은 DB 측 SoT. 두 모델 간 매핑은 ``to_orm()`` / ``to_pydantic()`` 헬퍼로.
- nullable 정책은 DuckDB 시절 DDL 을 유지 (NOT NULL 컬럼은 동일하게 유지).
- VARCHAR 길이는 Postgres 의 ``TEXT`` 동등으로 ``String`` (length 미지정).
- Time 컬럼은 ISO 8601 문자열로 들어오므로 그대로 ``String`` — 상위 layer (Pydantic)
  가 파싱. 추후 하드 cutover 시 ``TIMESTAMPTZ`` 로 마이그.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .session import Base


# ---------------------------------------------------------------------------
# Persona — Nemotron-Personas-Korea 인제션 결과 미러
# ---------------------------------------------------------------------------
class PersonaCore(Base):
    __tablename__ = "persona_core"

    uuid: Mapped[str] = mapped_column(String, primary_key=True)
    sex: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    province: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    education_level: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    occupation: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    persona: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cultural_background: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PersonaText(Base):
    __tablename__ = "persona_text"

    uuid: Mapped[str] = mapped_column(
        String,
        ForeignKey("persona_core.uuid", ondelete="CASCADE"),
        primary_key=True,
    )
    professional_persona: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    family_persona: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Polls — raw_poll / raw_poll_result + poll_consensus_daily
# ---------------------------------------------------------------------------
class RawPoll(Base):
    __tablename__ = "raw_poll"

    poll_id: Mapped[str] = mapped_column(String, primary_key=True)
    contest_id: Mapped[str] = mapped_column(String, nullable=False)
    region_id: Mapped[str] = mapped_column(String, nullable=False)
    field_start: Mapped[Optional[Any]] = mapped_column(Date, nullable=True)
    field_end: Mapped[Optional[Any]] = mapped_column(Date, nullable=True)
    publish_ts: Mapped[Optional[Any]] = mapped_column(DateTime(timezone=True), nullable=True)
    pollster: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sponsor: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mode: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sample_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    population: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    margin_error: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quality: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"))
    ingested_at: Mapped[Optional[Any]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nesdc_reg_no: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class RawPollResult(Base):
    __tablename__ = "raw_poll_result"
    __table_args__ = (PrimaryKeyConstraint("poll_id", "candidate_id"),)

    poll_id: Mapped[str] = mapped_column(String, nullable=False)
    candidate_id: Mapped[str] = mapped_column(String, nullable=False)
    share: Mapped[float] = mapped_column(Float, nullable=False)
    undecided_share: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class PollConsensusDaily(Base):
    __tablename__ = "poll_consensus_daily"
    __table_args__ = (
        PrimaryKeyConstraint("contest_id", "region_id", "as_of_date", "candidate_id"),
    )

    contest_id: Mapped[str] = mapped_column(String, nullable=False)
    region_id: Mapped[str] = mapped_column(String, nullable=False)
    as_of_date: Mapped[Any] = mapped_column(Date, nullable=False)
    candidate_id: Mapped[str] = mapped_column(String, nullable=False)
    p_hat: Mapped[float] = mapped_column(Float, nullable=False)
    variance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    n_polls: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    method_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_poll_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Election result — 선관위 공식 개표 (선거일 후)
# ---------------------------------------------------------------------------
class ElectionResult(Base):
    __tablename__ = "election_result"
    __table_args__ = (
        PrimaryKeyConstraint("region_id", "contest_id", "candidate_id"),
    )

    region_id: Mapped[str] = mapped_column(String, nullable=False)
    contest_id: Mapped[str] = mapped_column(String, nullable=False)
    election_date: Mapped[Any] = mapped_column(Date, nullable=False)
    candidate_id: Mapped[str] = mapped_column(String, nullable=False)
    vote_share: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    turnout: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_winner: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"))
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ingested_at: Mapped[Optional[Any]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ---------------------------------------------------------------------------
# Ingest staging — DuckDB 시절 stg_* 미러 (PK 동일)
# ---------------------------------------------------------------------------
class IngestRun(Base):
    __tablename__ = "ingest_run"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[str] = mapped_column(String, nullable=False)
    finished_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    n_fetched: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    n_loaded: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    n_unresolved: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    status: Mapped[str] = mapped_column(String, server_default=text("'pending'"))
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"))


class StgRawPoll(Base):
    __tablename__ = "stg_raw_poll"
    __table_args__ = (PrimaryKeyConstraint("run_id", "poll_id"),)

    run_id: Mapped[str] = mapped_column(String, nullable=False)
    poll_id: Mapped[str] = mapped_column(String, nullable=False)
    region_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    contest_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    pollster: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    mode: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    n: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fieldwork_start: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    fieldwork_end: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    quality: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class StgRawPollResult(Base):
    __tablename__ = "stg_raw_poll_result"
    __table_args__ = (PrimaryKeyConstraint("run_id", "poll_id", "cand_id"),)

    run_id: Mapped[str] = mapped_column(String, nullable=False)
    poll_id: Mapped[str] = mapped_column(String, nullable=False)
    cand_id: Mapped[str] = mapped_column(String, nullable=False)
    share: Mapped[float] = mapped_column(Float, nullable=False)
    raw_label: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class StgKgTriple(Base):
    __tablename__ = "stg_kg_triple"
    __table_args__ = (PrimaryKeyConstraint("run_id", "src_doc_id", "triple_idx"),)

    run_id: Mapped[str] = mapped_column(String, nullable=False)
    src_doc_id: Mapped[str] = mapped_column(String, nullable=False)
    triple_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    subj: Mapped[str] = mapped_column(String, nullable=False)
    pred: Mapped[str] = mapped_column(String, nullable=False)
    obj: Mapped[str] = mapped_column(Text, nullable=False)
    subj_kind: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    obj_kind: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ts: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    region_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class EntityAlias(Base):
    __tablename__ = "entity_alias"
    __table_args__ = (PrimaryKeyConstraint("alias", "kind"),)

    alias: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    canonical_id: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, server_default=text("1.0"))
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class UnresolvedEntity(Base):
    __tablename__ = "unresolved_entity"
    __table_args__ = (PrimaryKeyConstraint("run_id", "alias", "kind"),)

    run_id: Mapped[str] = mapped_column(String, nullable=False)
    alias: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, server_default=text("'pending'"))


# ---------------------------------------------------------------------------
# Phase 5 — Community (anonymous user / comment / board / report)
# ---------------------------------------------------------------------------
# server_default 의 ``gen_random_uuid()`` 는 pgcrypto extension 필요 (Alembic
# 0002 가 박는다). ORM 인스턴스화 시 id 미지정이면 PG 측에서 자동 생성.

import uuid as _uuid


class AppUser(Base):
    """익명 사용자 — anon_token 기반 cookie identity."""

    __tablename__ = "app_user"

    id: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    anon_token: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    nickname: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_banned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    ban_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # relationship — primaryjoin/foreign_keys 명시 (FK 가 여러 개)
    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="author",
        foreign_keys="Comment.author_id",
        lazy="selectin",
    )
    topics: Mapped[list["BoardTopic"]] = relationship(
        "BoardTopic",
        back_populates="author",
        foreign_keys="BoardTopic.author_id",
        lazy="selectin",
    )
    reports_filed: Mapped[list["CommentReport"]] = relationship(
        "CommentReport",
        foreign_keys="CommentReport.reporter_id",
        back_populates="reporter",
        lazy="selectin",
    )


class BoardTopic(Base):
    """게시판 주제글 — region/scenario 컨텍스트와 옵션 연결."""

    __tablename__ = "board_topic"

    id: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    author_id: Mapped[Optional[_uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    region_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    scenario_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_pinned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    deleted_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    author: Mapped[Optional["AppUser"]] = relationship(
        "AppUser",
        back_populates="topics",
        foreign_keys=[author_id],
        lazy="joined",
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="board_topic",
        cascade="all, delete-orphan",
        foreign_keys="Comment.board_topic_id",
        lazy="selectin",
    )


class Comment(Base):
    """댓글 / 대댓글 (parent_id self-ref)."""

    __tablename__ = "comment"

    id: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    author_id: Mapped[Optional[_uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_id: Mapped[Optional[_uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("comment.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    board_topic_id: Mapped[Optional[_uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("board_topic.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    region_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    scenario_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    deleted_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # relationships
    author: Mapped[Optional["AppUser"]] = relationship(
        "AppUser",
        back_populates="comments",
        foreign_keys=[author_id],
        lazy="joined",
    )
    parent: Mapped[Optional["Comment"]] = relationship(
        "Comment",
        remote_side="Comment.id",
        back_populates="children",
        lazy="joined",
    )
    children: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    board_topic: Mapped[Optional["BoardTopic"]] = relationship(
        "BoardTopic",
        back_populates="comments",
        foreign_keys=[board_topic_id],
        lazy="joined",
    )


class CommentReport(Base):
    """모더레이션 신고 — comment 또는 board_topic 둘 중 정확히 하나 대상."""

    __tablename__ = "comment_report"
    __table_args__ = (
        CheckConstraint(
            "(target_comment_id IS NOT NULL)::int + "
            "(target_topic_id IS NOT NULL)::int = 1",
            name="ck_comment_report_one_target",
        ),
        CheckConstraint(
            "status IN ('pending','resolved','dismissed')",
            name="ck_comment_report_status",
        ),
    )

    id: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    reporter_id: Mapped[Optional[_uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_comment_id: Mapped[Optional[_uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("comment.id", ondelete="CASCADE"),
        nullable=True,
    )
    target_topic_id: Mapped[Optional[_uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("board_topic.id", ondelete="CASCADE"),
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'pending'"), index=True
    )
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    resolved_at: Mapped[Optional[Any]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[Optional[_uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # relationships
    reporter: Mapped[Optional["AppUser"]] = relationship(
        "AppUser",
        back_populates="reports_filed",
        foreign_keys=[reporter_id],
        lazy="joined",
    )
    target_comment: Mapped[Optional["Comment"]] = relationship(
        "Comment", foreign_keys=[target_comment_id], lazy="joined"
    )
    target_topic: Mapped[Optional["BoardTopic"]] = relationship(
        "BoardTopic", foreign_keys=[target_topic_id], lazy="joined"
    )
    resolver: Mapped[Optional["AppUser"]] = relationship(
        "AppUser", foreign_keys=[resolved_by], lazy="joined"
    )


# ---------------------------------------------------------------------------
# Pydantic ↔ ORM 변환 헬퍼
# ---------------------------------------------------------------------------
def to_dict(orm_obj: Any) -> dict[str, Any]:
    """ORM 인스턴스 → kwargs dict (Pydantic 모델로 fed-in)."""
    if orm_obj is None:
        return {}
    cols = orm_obj.__table__.columns.keys()
    return {c: getattr(orm_obj, c) for c in cols}


def from_dict(model_cls: type, payload: dict[str, Any]) -> Any:
    """payload dict → ORM 인스턴스. table column 만 발췌해서 instantiation."""
    cols = set(model_cls.__table__.columns.keys())
    safe = {k: v for k, v in payload.items() if k in cols}
    return model_cls(**safe)


# ---------------------------------------------------------------------------
# Aggregate exports — Alembic / migration tool 이 사용
# ---------------------------------------------------------------------------
ALL_MODELS = (
    PersonaCore,
    PersonaText,
    RawPoll,
    RawPollResult,
    PollConsensusDaily,
    ElectionResult,
    IngestRun,
    StgRawPoll,
    StgRawPollResult,
    StgKgTriple,
    EntityAlias,
    UnresolvedEntity,
    # Phase 5 community
    AppUser,
    BoardTopic,
    Comment,
    CommentReport,
)


# `official_poll` 은 raw_poll JOIN raw_poll_result 위의 view — Postgres 측에서
# Alembic migration 으로 별도 정의 (raw SQL). Pydantic OfficialPollSnapshot 와
# 동일 shape 를 돌려준다.
OFFICIAL_POLL_VIEW_SQL = """
CREATE OR REPLACE VIEW official_poll AS
SELECT
    rp.region_id        AS region_id,
    rp.contest_id       AS contest_id,
    CAST(rp.field_end AS VARCHAR) AS as_of_date,
    rp.pollster         AS pollster,
    COALESCE(rp.mode, 'phone')    AS mode,
    COALESCE(rp.sample_size, 0)   AS n,
    rpr.candidate_id    AS candidate_id,
    rpr.share           AS share,
    rp.source_url       AS source_url,
    CAST(rp.ingested_at AS VARCHAR) AS ingested_at
FROM raw_poll rp
JOIN raw_poll_result rpr USING (poll_id)
WHERE rp.is_placeholder = FALSE OR rp.is_placeholder IS NULL
"""


__all__ = [
    "ALL_MODELS",
    "AppUser",
    "Base",
    "BoardTopic",
    "Comment",
    "CommentReport",
    "ElectionResult",
    "EntityAlias",
    "IngestRun",
    "OFFICIAL_POLL_VIEW_SQL",
    "PersonaCore",
    "PersonaText",
    "PollConsensusDaily",
    "RawPoll",
    "RawPollResult",
    "ScenarioEvent",
    "ScenarioTree",
    "StgKgTriple",
    "StgRawPoll",
    "StgRawPollResult",
    "UnresolvedEntity",
    "from_dict",
    "to_dict",
]


# ---------------------------------------------------------------------------
# Phase 6 — ScenarioTree + ScenarioEvent (beam-search 산출 트리 + KG/LLM/custom
# 통합 이벤트 레지스트리). Alembic 0003 가 박는 테이블의 ORM 미러.
# ---------------------------------------------------------------------------
from sqlalchemy import UniqueConstraint as _UniqueConstraint  # noqa: E402
from sqlalchemy.dialects.postgresql import JSONB as _PG_JSONB  # noqa: E402


class ScenarioTree(Base):
    """Beam-search 산출 시나리오 트리 메타데이터.

    Node-level 데이터(수 천 개 가능)는 ``artifact_path`` 가 가리키는
    ``_workspace/snapshots/scenario_trees/{tree_id}.json`` 에 별도 저장 — DB
    비대화 방지. ``UNIQUE(region_id, contest_id, as_of)`` — 같은 region/cutoff
    당 1개. 재빌드 시 replace.
    """

    __tablename__ = "scenario_tree"
    __table_args__ = (
        CheckConstraint(
            "status IN ('building','complete','failed')",
            name="ck_scenario_tree_status",
        ),
        # alembic 0003 가 박은 이름과 동일하게 맞춘다.
        _UniqueConstraint(
            "region_id",
            "contest_id",
            "as_of",
            name="uq_scenario_tree_region_contest_as_of",
        ),
    )

    id: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    region_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    contest_id: Mapped[str] = mapped_column(String, nullable=False)
    as_of: Mapped[Any] = mapped_column(Date, nullable=False)
    election_date: Mapped[Any] = mapped_column(Date, nullable=False)
    beam_width: Mapped[int] = mapped_column(Integer, nullable=False)
    beam_depth: Mapped[int] = mapped_column(Integer, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(
        _PG_JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    artifact_path: Mapped[str] = mapped_column(String, nullable=False)
    mlflow_run_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    built_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    built_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)


class ScenarioEvent(Base):
    """KG / LLM / custom 통합 이벤트 레지스트리.

    EventProposer 의 source 인터페이스와 정합. ``candidate_patches`` /
    ``event_patches`` 는 ``run_counterfactual.py`` 의 patch 형식 재사용.
    """

    __tablename__ = "scenario_event"
    __table_args__ = (
        CheckConstraint(
            "source IN ('kg_confirmed','llm_hypothetical','custom')",
            name="ck_scenario_event_source",
        ),
        CheckConstraint(
            "prior_p >= 0 AND prior_p <= 1",
            name="ck_scenario_event_prior_p",
        ),
    )

    id: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    region_id: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, index=True)
    occurs_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_patches: Mapped[list[Any]] = mapped_column(
        _PG_JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    event_patches: Mapped[list[Any]] = mapped_column(
        _PG_JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    prior_p: Mapped[float] = mapped_column(Float, nullable=False)
    # SQLAlchemy 2.x 에서 Python attr name 은 'metadata_' 로 두는 경우가 많지만
    # DeclarativeBase 의 reserved attribute 'metadata' 와 충돌하므로 컬럼명만
    # DB 측에 'metadata' 로 두고 Python attr 은 'event_metadata' 로 매핑.
    event_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", _PG_JSONB, nullable=True
    )
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("TRUE")
    )


# ALL_MODELS 확장 (Alembic / migration tool 검증용).
ALL_MODELS = ALL_MODELS + (ScenarioTree, ScenarioEvent)
