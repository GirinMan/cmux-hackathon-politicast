"""Staging DDL + MERGE 헬퍼 — dual backend (DuckDB legacy + Postgres cutover).

PolitiKAST ingestion 파이프라인은 어댑터 출력 → stg_* 테이블 → target 테이블
2-단계 멱등 패턴이다.

테이블 (모두 멱등 CREATE):
  ingest_run           : 실행 메타 (run_id PK)
  stg_raw_poll         : NESDC 등 raw poll 메타
  stg_raw_poll_result  : poll × candidate 결과 (poll_id, cand_id PK)
  stg_kg_triple        : LLM 추출 KG triple (run_id, src_doc_id, triple_idx PK)
  entity_alias         : alias → canonical entity_id (alias, kind PK)
  unresolved_entity    : LLM 후처리 대기 큐 (run_id, alias, kind PK)

방언 (Phase 4 cutover)
----------------------
- Postgres: ``INSERT ... ON CONFLICT DO NOTHING`` (정식 표준).
  멱등 INSERT 는 PG dialect 가 자동 선택. DDL 은 Alembic migration 이 박는
  schema 와 동일 (`backend/app/db/models.py`). ``ensure_stg_tables(con)`` 는
  멱등 보호용 fallback (DuckDB 시절 / fresh test DB) 으로만 동작.
- DuckDB 1.5.x: ``INSERT OR IGNORE INTO``. native MERGE 가 unstable 해서
  target UPSERT 는 DELETE+INSERT.
- 결정: connection 객체의 dialect 가 ``postgres`` 면 PG 분기, 그 외
  (DuckDB / SQLite / unknown) 는 legacy DuckDB 분기.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = REPO_ROOT / "_workspace" / "db" / "politikast.duckdb"

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------
# Composite PK 는 ingest 멱등성을 결정한다. 같은 페이로드 재처리 시
# ON CONFLICT DO NOTHING 으로 INSERT 0.

DDL_INGEST_RUN = """
CREATE TABLE IF NOT EXISTS ingest_run (
    run_id        VARCHAR PRIMARY KEY,
    source_id     VARCHAR NOT NULL,
    started_at    VARCHAR NOT NULL,
    finished_at   VARCHAR,
    n_fetched     INTEGER DEFAULT 0,
    n_loaded      INTEGER DEFAULT 0,
    n_unresolved  INTEGER DEFAULT 0,
    status        VARCHAR DEFAULT 'pending',
    error         VARCHAR,
    config_hash   VARCHAR,
    dry_run       BOOLEAN DEFAULT FALSE
)
"""

DDL_STG_RAW_POLL = """
CREATE TABLE IF NOT EXISTS stg_raw_poll (
    run_id        VARCHAR NOT NULL,
    poll_id       VARCHAR NOT NULL,
    region_id     VARCHAR,
    contest_id    VARCHAR,
    pollster      VARCHAR,
    mode          VARCHAR,
    n             INTEGER,
    fieldwork_start VARCHAR,
    fieldwork_end   VARCHAR,
    quality       DOUBLE,
    source_url    VARCHAR,
    raw_json      VARCHAR,
    fetched_at    VARCHAR,
    PRIMARY KEY (run_id, poll_id)
)
"""

DDL_STG_RAW_POLL_RESULT = """
CREATE TABLE IF NOT EXISTS stg_raw_poll_result (
    run_id        VARCHAR NOT NULL,
    poll_id       VARCHAR NOT NULL,
    cand_id       VARCHAR NOT NULL,
    share         DOUBLE NOT NULL,
    raw_label     VARCHAR,
    PRIMARY KEY (run_id, poll_id, cand_id)
)
"""

DDL_STG_KG_TRIPLE = """
CREATE TABLE IF NOT EXISTS stg_kg_triple (
    run_id        VARCHAR NOT NULL,
    src_doc_id    VARCHAR NOT NULL,
    triple_idx    INTEGER NOT NULL,
    subj          VARCHAR NOT NULL,
    pred          VARCHAR NOT NULL,
    obj           VARCHAR NOT NULL,
    subj_kind     VARCHAR,
    obj_kind      VARCHAR,
    ts            VARCHAR,
    region_id     VARCHAR,
    confidence    DOUBLE,
    source_url    VARCHAR,
    raw_text      VARCHAR,
    PRIMARY KEY (run_id, src_doc_id, triple_idx)
)
"""

DDL_ENTITY_ALIAS = """
CREATE TABLE IF NOT EXISTS entity_alias (
    alias         VARCHAR NOT NULL,
    kind          VARCHAR NOT NULL,
    canonical_id  VARCHAR NOT NULL,
    confidence    DOUBLE DEFAULT 1.0,
    source        VARCHAR,
    created_at    VARCHAR,
    PRIMARY KEY (alias, kind)
)
"""

DDL_UNRESOLVED_ENTITY = """
CREATE TABLE IF NOT EXISTS unresolved_entity (
    run_id        VARCHAR NOT NULL,
    alias         VARCHAR NOT NULL,
    kind          VARCHAR NOT NULL,
    context       VARCHAR,
    suggested_id  VARCHAR,
    status        VARCHAR DEFAULT 'pending',
    PRIMARY KEY (run_id, alias, kind)
)
"""

ALL_DDL = (
    DDL_INGEST_RUN,
    DDL_STG_RAW_POLL,
    DDL_STG_RAW_POLL_RESULT,
    DDL_STG_KG_TRIPLE,
    DDL_ENTITY_ALIAS,
    DDL_UNRESOLVED_ENTITY,
)

STG_TABLES = (
    "ingest_run",
    "stg_raw_poll",
    "stg_raw_poll_result",
    "stg_kg_triple",
    "entity_alias",
    "unresolved_entity",
)

STG_PRIMARY_KEYS: dict[str, tuple[str, ...]] = {
    "ingest_run": ("run_id",),
    "stg_raw_poll": ("run_id", "poll_id"),
    "stg_raw_poll_result": ("run_id", "poll_id", "cand_id"),
    "stg_kg_triple": ("run_id", "src_doc_id", "triple_idx"),
    "entity_alias": ("alias", "kind"),
    "unresolved_entity": ("run_id", "alias", "kind"),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def ensure_stg_tables(con: Any) -> None:
    """모든 stg_* + ingest_run + entity_alias 멱등 생성."""
    for ddl in ALL_DDL:
        con.execute(ddl)


def _qualify(rows: Iterable[dict[str, Any]], cols: list[str]) -> list[tuple[Any, ...]]:
    return [tuple(r.get(c) for c in cols) for r in rows]


def _table_columns(con: Any, table: str) -> list[str]:
    res = con.execute(
        f"SELECT column_name FROM information_schema.columns "
        f"WHERE table_name = '{table}' ORDER BY ordinal_position"
    ).fetchall()
    return [r[0] for r in res]


def _bind_param(con: Any) -> str:
    """dialect 별 단일 파라미터 placeholder."""
    return "%s" if _detect_dialect(con) == "postgres" else "?"


def _detect_dialect(con: Any) -> str:
    """connection 이 Postgres 인지 DuckDB 인지 판별.

    DuckDB connection 은 module 이 ``duckdb``, Postgres async/sync
    connection 은 SQLAlchemy 의 ``Connection``/``AsyncConnection`` 또는
    ``psycopg2``/``asyncpg`` 객체. 가장 단순한 휴리스틱은 module 이름.
    """
    mod = type(con).__module__
    if "duckdb" in mod:
        return "duckdb"
    if "psycopg" in mod or "asyncpg" in mod or "sqlalchemy" in mod:
        return "postgres"
    # default: DuckDB legacy (test fixture 와 호환).
    return "duckdb"


def insert_rows(
    con: Any,
    table: str,
    rows: list[dict[str, Any]],
) -> int:
    """멱등 INSERT — Postgres 는 ON CONFLICT DO NOTHING, DuckDB 는 INSERT OR IGNORE.

    Postgres: ``INSERT ... ON CONFLICT (pk_cols) DO NOTHING`` (표준 SQL).
    DuckDB 1.5: PK conflict 시 자동 reject 가 아니라 raise — ``INSERT OR
    IGNORE INTO`` (DuckDB 0.9+ 지원) 사용.
    """
    if not rows:
        return 0
    if table not in STG_PRIMARY_KEYS:
        raise ValueError(f"unknown staging table: {table}")
    cols = _table_columns(con, table)
    values = _qualify(rows, cols)
    dialect = _detect_dialect(con)

    before = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    if dialect == "postgres":
        # asyncpg/psycopg2 는 ``%s`` 또는 ``$1`` 스타일이지만 SQLAlchemy raw
        # connection 의 driver 별 대응을 위해 paramstyle 을 lazily 결정한다.
        placeholders = ", ".join(["%s"] * len(cols))
        pk_cols = ", ".join(STG_PRIMARY_KEYS[table])
        sql = (
            f"INSERT INTO {table} ({', '.join(cols)}) "
            f"VALUES ({placeholders}) "
            f"ON CONFLICT ({pk_cols}) DO NOTHING"
        )
        try:
            con.executemany(sql, values)
        except Exception:
            # asyncpg 는 paramstyle ``$1`` 만 지원 — fallback.
            placeholders_pg = ", ".join([f"${i+1}" for i in range(len(cols))])
            sql_pg = (
                f"INSERT INTO {table} ({', '.join(cols)}) "
                f"VALUES ({placeholders_pg}) "
                f"ON CONFLICT ({pk_cols}) DO NOTHING"
            )
            for v in values:
                con.execute(sql_pg, *v)
    else:
        placeholders = ", ".join(["?"] * len(cols))
        sql = f"INSERT OR IGNORE INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
        con.executemany(sql, values)
    after = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    return int(after - before)


def upsert_ingest_run(con: Any, row: dict[str, Any]) -> None:
    """ingest_run 행 upsert (DELETE + INSERT). PG/DuckDB 공통."""
    cols = _table_columns(con, "ingest_run")
    values = tuple(row.get(c) for c in cols)
    p = _bind_param(con)
    con.execute(f"DELETE FROM ingest_run WHERE run_id = {p}", [row["run_id"]])
    placeholders = ", ".join([p] * len(cols))
    con.execute(
        f"INSERT INTO ingest_run ({', '.join(cols)}) VALUES ({placeholders})",
        values,
    )


# ---------------------------------------------------------------------------
# Target MERGE helpers (stg_* → 정식 테이블)
# ---------------------------------------------------------------------------
DDL_TARGET_RAW_POLL = """
CREATE TABLE IF NOT EXISTS raw_poll (
    poll_id       VARCHAR PRIMARY KEY,
    region_id     VARCHAR,
    contest_id    VARCHAR,
    pollster      VARCHAR,
    mode          VARCHAR,
    n             INTEGER,
    fieldwork_start VARCHAR,
    fieldwork_end   VARCHAR,
    quality       DOUBLE,
    source_url    VARCHAR,
    raw_json      VARCHAR
)
"""

DDL_TARGET_RAW_POLL_RESULT = """
CREATE TABLE IF NOT EXISTS raw_poll_result (
    poll_id       VARCHAR NOT NULL,
    cand_id       VARCHAR NOT NULL,
    share         DOUBLE NOT NULL,
    raw_label     VARCHAR,
    PRIMARY KEY (poll_id, cand_id)
)
"""


def ensure_target_tables(con: Any) -> None:
    con.execute(DDL_TARGET_RAW_POLL)
    con.execute(DDL_TARGET_RAW_POLL_RESULT)


def merge_stg_raw_poll_to_target(con: Any, run_id: str) -> int:
    """DELETE+INSERT UPSERT — PG/DuckDB 공통 (native MERGE 회피).

    같은 페이로드 재처리 시 INSERT 0 이지만 row 자체는 보존된다.
    """
    ensure_target_tables(con)
    cols = ("poll_id", "region_id", "contest_id", "pollster", "mode", "n",
            "fieldwork_start", "fieldwork_end", "quality", "source_url", "raw_json")
    cols_str = ", ".join(cols)
    p = _bind_param(con)
    # 1) target 에서 같은 poll_id 행 제거 (재실행 시 갱신된 값 반영)
    con.execute(
        f"DELETE FROM raw_poll WHERE poll_id IN ("
        f"  SELECT DISTINCT poll_id FROM stg_raw_poll WHERE run_id = {p}"
        f")",
        [run_id],
    )
    res = con.execute(
        f"INSERT INTO raw_poll ({cols_str}) "
        f"SELECT {cols_str} FROM stg_raw_poll WHERE run_id = {p}",
        [run_id],
    )
    return int(getattr(res, "rowcount", 0) or 0)


def merge_stg_raw_poll_result_to_target(con: Any, run_id: str) -> int:
    ensure_target_tables(con)
    cols = ("poll_id", "cand_id", "share", "raw_label")
    cols_str = ", ".join(cols)
    p = _bind_param(con)
    con.execute(
        f"DELETE FROM raw_poll_result WHERE (poll_id, cand_id) IN ("
        f"  SELECT DISTINCT poll_id, cand_id FROM stg_raw_poll_result "
        f"  WHERE run_id = {p}"
        f")",
        [run_id],
    )
    res = con.execute(
        f"INSERT INTO raw_poll_result ({cols_str}) "
        f"SELECT {cols_str} FROM stg_raw_poll_result WHERE run_id = {p}",
        [run_id],
    )
    return int(getattr(res, "rowcount", 0) or 0)


__all__ = [
    "ensure_stg_tables",
    "ensure_target_tables",
    "insert_rows",
    "upsert_ingest_run",
    "merge_stg_raw_poll_to_target",
    "merge_stg_raw_poll_result_to_target",
    "STG_TABLES",
    "STG_PRIMARY_KEYS",
    "DEFAULT_DB_PATH",
]
