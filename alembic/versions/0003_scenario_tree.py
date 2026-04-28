"""scenario_tree + scenario_event — Phase 6.

테이블 추가:
  scenario_tree   — beam-search 산출 트리 메타데이터. node-level JSON 은
                    artifact_path 가 가리키는 _workspace/snapshots/scenario_trees/{tree_id}.json
                    에 별도 저장 — DB 비대화 방지.
  scenario_event  — KG / LLM / custom 통합 이벤트 레지스트리. EventProposer
                    의 source 인터페이스와 정합 (CHECK 'kg_confirmed' /
                    'llm_hypothetical' / 'custom').

PG-native UUID + ``gen_random_uuid()`` (pgcrypto extension — 0002 가 이미
설치). JSONB 필드 (config / candidate_patches / event_patches / metadata)
는 sqlalchemy.dialects.postgresql.JSONB.

Revision ID: 0003_scenario_tree
Revises: 0002_community
Create Date: 2026-04-28T00:00:00+09:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0003_scenario_tree"
down_revision: Union[str, None] = "0002_community"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgcrypto extension — gen_random_uuid() (0002 가 설치했지만 멱등 보장).
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ----- scenario_tree --------------------------------------------------
    op.create_table(
        "scenario_tree",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("region_id", sa.String(), nullable=False),
        sa.Column("contest_id", sa.String(), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("election_date", sa.Date(), nullable=False),
        sa.Column("beam_width", sa.Integer(), nullable=False),
        sa.Column("beam_depth", sa.Integer(), nullable=False),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("artifact_path", sa.String(), nullable=False),
        sa.Column("mlflow_run_id", sa.String(), nullable=True),
        sa.Column(
            "built_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("built_by", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.CheckConstraint(
            "status IN ('building','complete','failed')",
            name="ck_scenario_tree_status",
        ),
        sa.UniqueConstraint(
            "region_id",
            "contest_id",
            "as_of",
            name="uq_scenario_tree_region_contest_as_of",
        ),
    )
    op.create_index(
        "ix_scenario_tree_region_id", "scenario_tree", ["region_id"]
    )
    op.create_index(
        "ix_scenario_tree_built_at", "scenario_tree", ["built_at"]
    )

    # ----- scenario_event -------------------------------------------------
    op.create_table(
        "scenario_event",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("region_id", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("occurs_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "candidate_patches",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "event_patches",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("prior_p", sa.Float(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("TRUE"),
        ),
        sa.CheckConstraint(
            "source IN ('kg_confirmed','llm_hypothetical','custom')",
            name="ck_scenario_event_source",
        ),
        sa.CheckConstraint(
            "prior_p >= 0 AND prior_p <= 1",
            name="ck_scenario_event_prior_p",
        ),
    )
    # Partial index — 활성 이벤트만 (region/시간 조회 핫패스).
    op.execute(
        "CREATE INDEX idx_scenario_event_region_t "
        "ON scenario_event(region_id, occurs_at) "
        "WHERE is_active = TRUE"
    )
    op.create_index(
        "ix_scenario_event_source", "scenario_event", ["source"]
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_scenario_event_region_t")
    op.drop_index("ix_scenario_event_source", table_name="scenario_event")
    op.drop_table("scenario_event")

    op.drop_index("ix_scenario_tree_built_at", table_name="scenario_tree")
    op.drop_index("ix_scenario_tree_region_id", table_name="scenario_tree")
    op.drop_table("scenario_tree")
    # pgcrypto 는 다른 사용처가 있으므로 drop 안 함.
