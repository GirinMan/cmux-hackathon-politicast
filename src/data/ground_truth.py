"""Ground truth loader — official_poll (VIEW) + election_result (TABLE).

Phase 4 cutover
---------------
- Postgres: official_poll VIEW 는 Alembic migration 이 박는다 (raw SQL,
  `backend/app/db/models.OFFICIAL_POLL_VIEW_SQL`). election_result 는 ORM.
  ``ensure_tables(con)`` 는 멱등 fallback 보호로만 동작.
- DuckDB legacy: 기존 동작과 동일 — VIEW/TABLE 멱등 CREATE.

`load_official_poll` / `load_election_result` 는 시그니처 보존.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from src.schemas.ground_truth import ElectionResult, OfficialPollSnapshot

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = REPO_ROOT / "_workspace" / "db" / "politikast.duckdb"


_OFFICIAL_POLL_VIEW_SQL = """
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

_ELECTION_RESULT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS election_result (
    region_id      VARCHAR NOT NULL,
    contest_id     VARCHAR NOT NULL,
    election_date  DATE    NOT NULL,
    candidate_id   VARCHAR NOT NULL,
    vote_share     DOUBLE PRECISION NOT NULL,
    votes          INTEGER,
    turnout        DOUBLE PRECISION,
    is_winner      BOOLEAN DEFAULT FALSE,
    source_url     VARCHAR,
    ingested_at    TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (region_id, contest_id, candidate_id)
)
"""


def _use_postgres() -> bool:
    try:
        from backend.app.db.session import is_postgres_enabled

        return is_postgres_enabled()
    except Exception:
        return False


def _connect_legacy(db_path: Path | None = None, *, read_only: bool = True) -> Any:
    import duckdb

    return duckdb.connect(str(db_path or DEFAULT_DB_PATH), read_only=read_only)


def _connect_pg() -> Any:
    """SQLAlchemy 동기 connection — `con.execute(text(sql))` 인터페이스."""
    from sqlalchemy import create_engine, text  # noqa: F401

    from backend.app.db.session import resolve_dsn

    engine = create_engine(resolve_dsn(async_=False), future=True)
    return engine.connect()


def ensure_tables(con: Any) -> None:
    """멱등하게 official_poll VIEW + election_result TABLE 보장.

    Postgres 환경에선 Alembic migration 이 우선 박는다. 본 함수는 fresh DB /
    test fixture 를 위한 fallback.
    """
    mod = type(con).__module__
    if "duckdb" in mod:
        # DuckDB DOUBLE PRECISION 표현 호환 (FLOAT/DOUBLE 모두 허용).
        ddl = _ELECTION_RESULT_TABLE_SQL.replace(
            "DOUBLE PRECISION", "DOUBLE"
        ).replace("VARCHAR,", "VARCHAR,").replace(
            "vote_share     DOUBLE NOT NULL",
            "vote_share     DOUBLE  NOT NULL",
        )
        con.execute(ddl)
        tables = {
            r[0]
            for r in con.execute(
                "select table_name from information_schema.tables "
                "where table_schema='main'"
            ).fetchall()
        }
        if {"raw_poll", "raw_poll_result"}.issubset(tables):
            con.execute(_OFFICIAL_POLL_VIEW_SQL)
        return

    # Postgres: assume Alembic 이 ORM 모델로 election_result 를 만들었다.
    # VIEW 는 보호적으로 CREATE OR REPLACE.
    from sqlalchemy import text

    pg_election_ddl = _ELECTION_RESULT_TABLE_SQL  # PG 에서도 동일 형식 OK
    con.execute(text(pg_election_ddl))
    rows = con.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name IN ('raw_poll','raw_poll_result')"
        )
    ).fetchall()
    if len(rows) >= 2:
        con.execute(text(_OFFICIAL_POLL_VIEW_SQL))


def _table_exists(con: Any, name: str) -> bool:
    mod = type(con).__module__
    if "duckdb" in mod:
        rows = con.execute(
            "select table_name from information_schema.tables "
            "where table_schema='main'"
        ).fetchall()
        return name in {r[0] for r in rows}
    from sqlalchemy import text

    rows = con.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name=:n "
            "UNION SELECT table_name FROM information_schema.views "
            "WHERE table_schema='public' AND table_name=:n"
        ),
        {"n": name},
    ).fetchall()
    return bool(rows)


def load_official_poll(
    region_id: str,
    *,
    as_of: Optional[str] = None,
    db_path: Path | None = None,
) -> list[OfficialPollSnapshot]:
    """region_id (옵션: as_of date 이전까지) 의 공식 여론조사 row 리스트."""
    cols = (
        "region_id contest_id as_of_date pollster mode n "
        "candidate_id share source_url ingested_at"
    ).split()

    if _use_postgres():
        from sqlalchemy import text

        con = _connect_pg()
        try:
            if not _table_exists(con, "official_poll"):
                return []
            sql = (
                "SELECT region_id, contest_id, as_of_date, pollster, mode, n, "
                "candidate_id, share, source_url, ingested_at "
                "FROM official_poll WHERE region_id = :rid"
            )
            params: dict[str, Any] = {"rid": region_id}
            if as_of is not None:
                sql += " AND as_of_date <= :asof"
                params["asof"] = as_of
            sql += " ORDER BY as_of_date DESC, pollster, candidate_id"
            rows = con.execute(text(sql), params).fetchall()
        finally:
            con.close()
        return [OfficialPollSnapshot(**dict(zip(cols, tuple(row)))) for row in rows]

    con = _connect_legacy(db_path)
    try:
        tables = {
            r[0]
            for r in con.execute(
                "select table_name from information_schema.tables "
                "where table_schema='main'"
            ).fetchall()
        }
        if "official_poll" not in tables:
            return []
        sql = (
            "SELECT region_id, contest_id, as_of_date, pollster, mode, n, "
            "candidate_id, share, source_url, ingested_at "
            "FROM official_poll WHERE region_id = ?"
        )
        params_list: list = [region_id]
        if as_of is not None:
            sql += " AND as_of_date <= ?"
            params_list.append(as_of)
        sql += " ORDER BY as_of_date DESC, pollster, candidate_id"
        rows = con.execute(sql, params_list).fetchall()
    finally:
        con.close()
    return [OfficialPollSnapshot(**dict(zip(cols, row))) for row in rows]


def load_election_result(
    region_id: str,
    *,
    db_path: Path | None = None,
) -> list[ElectionResult]:
    cols = (
        "region_id contest_id election_date candidate_id vote_share "
        "votes turnout is_winner source_url ingested_at"
    ).split()

    if _use_postgres():
        from sqlalchemy import text

        con = _connect_pg()
        try:
            if not _table_exists(con, "election_result"):
                return []
            rows = con.execute(
                text(
                    "SELECT region_id, contest_id, "
                    "CAST(election_date AS VARCHAR), candidate_id, vote_share, "
                    "votes, turnout, is_winner, source_url, "
                    "CAST(ingested_at AS VARCHAR) "
                    "FROM election_result WHERE region_id = :rid "
                    "ORDER BY contest_id, candidate_id"
                ),
                {"rid": region_id},
            ).fetchall()
        finally:
            con.close()
        return [ElectionResult(**dict(zip(cols, tuple(row)))) for row in rows]

    con = _connect_legacy(db_path)
    try:
        tables = {
            r[0]
            for r in con.execute(
                "select table_name from information_schema.tables "
                "where table_schema='main'"
            ).fetchall()
        }
        if "election_result" not in tables:
            return []
        rows = con.execute(
            "SELECT region_id, contest_id, "
            "CAST(election_date AS VARCHAR), candidate_id, vote_share, "
            "votes, turnout, is_winner, source_url, "
            "CAST(ingested_at AS VARCHAR) "
            "FROM election_result WHERE region_id = ? "
            "ORDER BY contest_id, candidate_id",
            [region_id],
        ).fetchall()
    finally:
        con.close()
    return [ElectionResult(**dict(zip(cols, row))) for row in rows]
