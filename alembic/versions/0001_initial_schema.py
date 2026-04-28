"""initial schema — DuckDB → Postgres cutover (Phase 4).

본 마이그레이션은 ``backend/app/db/models.py`` 의 ORM 미러를 그대로 박는다:
  persona_core / persona_text — Nemotron 인제션 결과
  raw_poll / raw_poll_result / poll_consensus_daily — 여론조사
  election_result — 선관위 공식 개표
  ingest_run / stg_raw_poll / stg_raw_poll_result / stg_kg_triple
  entity_alias / unresolved_entity — ingestion staging

추가로 ``official_poll`` VIEW 를 raw SQL 로 정의 (raw_poll JOIN raw_poll_result).

Revision ID: 0001_initial
Revises: -
Create Date: 2026-04-28T00:00:00+09:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------
def upgrade() -> None:
    # persona_core
    op.create_table(
        "persona_core",
        sa.Column("uuid", sa.String(), primary_key=True),
        sa.Column("sex", sa.String()),
        sa.Column("age", sa.Integer()),
        sa.Column("province", sa.String()),
        sa.Column("district", sa.String()),
        sa.Column("education_level", sa.String()),
        sa.Column("occupation", sa.String()),
        sa.Column("persona", sa.Text()),
        sa.Column("cultural_background", sa.Text()),
    )

    # persona_text
    op.create_table(
        "persona_text",
        sa.Column(
            "uuid",
            sa.String(),
            sa.ForeignKey("persona_core.uuid", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("professional_persona", sa.Text()),
        sa.Column("family_persona", sa.Text()),
    )

    # raw_poll
    op.create_table(
        "raw_poll",
        sa.Column("poll_id", sa.String(), primary_key=True),
        sa.Column("contest_id", sa.String(), nullable=False),
        sa.Column("region_id", sa.String(), nullable=False),
        sa.Column("field_start", sa.Date()),
        sa.Column("field_end", sa.Date()),
        sa.Column("publish_ts", sa.DateTime(timezone=True)),
        sa.Column("pollster", sa.String()),
        sa.Column("sponsor", sa.String()),
        sa.Column("source_url", sa.Text()),
        sa.Column("mode", sa.String()),
        sa.Column("sample_size", sa.Integer()),
        sa.Column("population", sa.Text()),
        sa.Column("margin_error", sa.Float()),
        sa.Column("quality", sa.Float()),
        sa.Column("is_placeholder", sa.Boolean(), server_default=sa.text("FALSE")),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("title", sa.Text()),
        sa.Column("nesdc_reg_no", sa.String()),
    )

    # raw_poll_result
    op.create_table(
        "raw_poll_result",
        sa.Column("poll_id", sa.String(), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("share", sa.Float(), nullable=False),
        sa.Column("undecided_share", sa.Float()),
        sa.PrimaryKeyConstraint("poll_id", "candidate_id"),
    )

    # poll_consensus_daily
    op.create_table(
        "poll_consensus_daily",
        sa.Column("contest_id", sa.String(), nullable=False),
        sa.Column("region_id", sa.String(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("p_hat", sa.Float(), nullable=False),
        sa.Column("variance", sa.Float()),
        sa.Column("n_polls", sa.Integer()),
        sa.Column("method_version", sa.String()),
        sa.Column("source_poll_ids", sa.Text()),
        sa.PrimaryKeyConstraint(
            "contest_id", "region_id", "as_of_date", "candidate_id"
        ),
    )

    # election_result
    op.create_table(
        "election_result",
        sa.Column("region_id", sa.String(), nullable=False),
        sa.Column("contest_id", sa.String(), nullable=False),
        sa.Column("election_date", sa.Date(), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("vote_share", sa.Float(), nullable=False),
        sa.Column("votes", sa.Integer()),
        sa.Column("turnout", sa.Float()),
        sa.Column("is_winner", sa.Boolean(), server_default=sa.text("FALSE")),
        sa.Column("source_url", sa.Text()),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("region_id", "contest_id", "candidate_id"),
    )

    # ingest_run
    op.create_table(
        "ingest_run",
        sa.Column("run_id", sa.String(), primary_key=True),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("started_at", sa.String(), nullable=False),
        sa.Column("finished_at", sa.String()),
        sa.Column("n_fetched", sa.Integer(), server_default=sa.text("0")),
        sa.Column("n_loaded", sa.Integer(), server_default=sa.text("0")),
        sa.Column("n_unresolved", sa.Integer(), server_default=sa.text("0")),
        sa.Column("status", sa.String(), server_default=sa.text("'pending'")),
        sa.Column("error", sa.Text()),
        sa.Column("config_hash", sa.String()),
        sa.Column("dry_run", sa.Boolean(), server_default=sa.text("FALSE")),
    )

    # stg_raw_poll
    op.create_table(
        "stg_raw_poll",
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("poll_id", sa.String(), nullable=False),
        sa.Column("region_id", sa.String()),
        sa.Column("contest_id", sa.String()),
        sa.Column("pollster", sa.String()),
        sa.Column("mode", sa.String()),
        sa.Column("n", sa.Integer()),
        sa.Column("fieldwork_start", sa.String()),
        sa.Column("fieldwork_end", sa.String()),
        sa.Column("quality", sa.Float()),
        sa.Column("source_url", sa.Text()),
        sa.Column("raw_json", sa.Text()),
        sa.Column("fetched_at", sa.String()),
        sa.PrimaryKeyConstraint("run_id", "poll_id"),
    )

    # stg_raw_poll_result
    op.create_table(
        "stg_raw_poll_result",
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("poll_id", sa.String(), nullable=False),
        sa.Column("cand_id", sa.String(), nullable=False),
        sa.Column("share", sa.Float(), nullable=False),
        sa.Column("raw_label", sa.String()),
        sa.PrimaryKeyConstraint("run_id", "poll_id", "cand_id"),
    )

    # stg_kg_triple
    op.create_table(
        "stg_kg_triple",
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("src_doc_id", sa.String(), nullable=False),
        sa.Column("triple_idx", sa.Integer(), nullable=False),
        sa.Column("subj", sa.String(), nullable=False),
        sa.Column("pred", sa.String(), nullable=False),
        sa.Column("obj", sa.Text(), nullable=False),
        sa.Column("subj_kind", sa.String()),
        sa.Column("obj_kind", sa.String()),
        sa.Column("ts", sa.String()),
        sa.Column("region_id", sa.String()),
        sa.Column("confidence", sa.Float()),
        sa.Column("source_url", sa.Text()),
        sa.Column("raw_text", sa.Text()),
        sa.PrimaryKeyConstraint("run_id", "src_doc_id", "triple_idx"),
    )

    # entity_alias
    op.create_table(
        "entity_alias",
        sa.Column("alias", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("canonical_id", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default=sa.text("1.0")),
        sa.Column("source", sa.String()),
        sa.Column("created_at", sa.String()),
        sa.PrimaryKeyConstraint("alias", "kind"),
    )

    # unresolved_entity
    op.create_table(
        "unresolved_entity",
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("alias", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("context", sa.Text()),
        sa.Column("suggested_id", sa.String()),
        sa.Column("status", sa.String(), server_default=sa.text("'pending'")),
        sa.PrimaryKeyConstraint("run_id", "alias", "kind"),
    )

    # official_poll VIEW (raw_poll JOIN raw_poll_result)
    op.execute(
        """
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
    )


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------
def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS official_poll")
    op.drop_table("unresolved_entity")
    op.drop_table("entity_alias")
    op.drop_table("stg_kg_triple")
    op.drop_table("stg_raw_poll_result")
    op.drop_table("stg_raw_poll")
    op.drop_table("ingest_run")
    op.drop_table("election_result")
    op.drop_table("poll_consensus_daily")
    op.drop_table("raw_poll_result")
    op.drop_table("raw_poll")
    op.drop_table("persona_text")
    op.drop_table("persona_core")
