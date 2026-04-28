"""community tables — Phase 5.

테이블 추가:
  app_user        — 익명 사용자 (anon_token + 한국어 닉네임).
  comment         — 댓글 / 대댓글 (parent_id self-ref).
  board_topic    — 게시판 주제글 (region/scenario context 옵션).
  comment_report — 모더레이션 신고 큐 (comment 또는 topic 둘 중 하나 대상).

PG-native UUID + ``gen_random_uuid()`` (pgcrypto extension). server_default 로
컬럼 자체에 UUID 생성을 위임 — INSERT 시 id 명시 안 해도 됨.

Revision ID: 0002_community
Revises: 0001_initial
Create Date: 2026-04-28T00:00:00+09:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0002_community"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgcrypto extension — gen_random_uuid().
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ----- app_user -------------------------------------------------------
    op.create_table(
        "app_user",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("anon_token", sa.String(length=64), nullable=False, unique=True),
        sa.Column("nickname", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "is_banned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column("ban_reason", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_app_user_anon_token", "app_user", ["anon_token"], unique=True
    )
    op.create_index("ix_app_user_nickname", "app_user", ["nickname"])

    # ----- board_topic ----------------------------------------------------
    op.create_table(
        "board_topic",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("region_id", sa.String(length=64), nullable=True),
        sa.Column("scenario_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "is_pinned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column("deleted_reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_board_topic_region_id", "board_topic", ["region_id"])
    op.create_index("ix_board_topic_scenario_id", "board_topic", ["scenario_id"])
    op.create_index("ix_board_topic_created_at", "board_topic", ["created_at"])

    # ----- comment --------------------------------------------------------
    op.create_table(
        "comment",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("comment.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "board_topic_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("board_topic.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("region_id", sa.String(length=64), nullable=True),
        sa.Column("scenario_id", sa.String(length=64), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column("deleted_reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_comment_parent_id", "comment", ["parent_id"])
    op.create_index("ix_comment_board_topic_id", "comment", ["board_topic_id"])
    op.create_index("ix_comment_region_id", "comment", ["region_id"])
    op.create_index("ix_comment_scenario_id", "comment", ["scenario_id"])
    op.create_index("ix_comment_created_at", "comment", ["created_at"])

    # ----- comment_report -------------------------------------------------
    op.create_table(
        "comment_report",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "reporter_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "target_comment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("comment.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "target_topic_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("board_topic.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "resolved_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        # 정확히 둘 중 하나만 (target_comment_id XOR target_topic_id) 채워야 한다.
        sa.CheckConstraint(
            "(target_comment_id IS NOT NULL)::int + (target_topic_id IS NOT NULL)::int = 1",
            name="ck_comment_report_one_target",
        ),
        sa.CheckConstraint(
            "status IN ('pending','resolved','dismissed')",
            name="ck_comment_report_status",
        ),
    )
    op.create_index(
        "ix_comment_report_status", "comment_report", ["status"]
    )
    op.create_index(
        "ix_comment_report_created_at", "comment_report", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_comment_report_created_at", table_name="comment_report")
    op.drop_index("ix_comment_report_status", table_name="comment_report")
    op.drop_table("comment_report")

    op.drop_index("ix_comment_created_at", table_name="comment")
    op.drop_index("ix_comment_scenario_id", table_name="comment")
    op.drop_index("ix_comment_region_id", table_name="comment")
    op.drop_index("ix_comment_board_topic_id", table_name="comment")
    op.drop_index("ix_comment_parent_id", table_name="comment")
    op.drop_table("comment")

    op.drop_index("ix_board_topic_created_at", table_name="board_topic")
    op.drop_index("ix_board_topic_scenario_id", table_name="board_topic")
    op.drop_index("ix_board_topic_region_id", table_name="board_topic")
    op.drop_table("board_topic")

    op.drop_index("ix_app_user_nickname", table_name="app_user")
    op.drop_index("ix_app_user_anon_token", table_name="app_user")
    op.drop_table("app_user")
    # pgcrypto extension 은 다른 사용처가 있을 수 있으므로 drop 안 함.
