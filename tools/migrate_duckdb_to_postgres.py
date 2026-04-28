"""DuckDB → Postgres 멱등 마이그레이션 (Phase 4 cutover).

PoliKAST 의 모든 DuckDB 테이블을 Postgres 로 옮긴다. 멱등 보장:
ON CONFLICT DO NOTHING + 같은 PK 행은 skip. 두 번 실행 시 차분만 INSERT.

Usage
-----
.. code:: bash

    # 1) docker compose up postgres
    # 2) make migrate          # alembic upgrade head
    # 3) tools/migrate_duckdb_to_postgres.py [--duckdb _workspace/db/politikast.duckdb]
    # 4) (선택) mv _workspace/db/politikast.duckdb _workspace/db/_archive/

행 카운트 invariance 검증
------------------------
이전/이후 region_size, raw_poll/raw_poll_result row count, persona_core row
count 가 모두 동일해야 한다. 마이그레이션 끝에 자동 비교 + diff 출력.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger("tools.migrate_duckdb_to_postgres")

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# 옮길 테이블 + PK (PK 충돌 시 skip).
# `personas_<region>` view 는 SELECT 가능하지만 PG 측에서는 별도 view 로 재정의
# 안 함 — 데이터는 persona_core 의 province/district 필터로 backend 가 산출.
TABLES: list[tuple[str, tuple[str, ...]]] = [
    ("persona_core", ("uuid",)),
    ("persona_text", ("uuid",)),
    ("raw_poll", ("poll_id",)),
    ("raw_poll_result", ("poll_id", "candidate_id")),
    ("poll_consensus_daily", ("contest_id", "region_id", "as_of_date", "candidate_id")),
    ("election_result", ("region_id", "contest_id", "candidate_id")),
    ("ingest_run", ("run_id",)),
    ("stg_raw_poll", ("run_id", "poll_id")),
    ("stg_raw_poll_result", ("run_id", "poll_id", "cand_id")),
    ("stg_kg_triple", ("run_id", "src_doc_id", "triple_idx")),
    ("entity_alias", ("alias", "kind")),
    ("unresolved_entity", ("run_id", "alias", "kind")),
]


def _duckdb_tables(con: Any) -> set[str]:
    rows = con.execute(
        "select table_name from information_schema.tables "
        "where table_schema='main'"
    ).fetchall()
    return {r[0] for r in rows}


def _duckdb_columns(con: Any, table: str) -> list[str]:
    rows = con.execute(
        "SELECT column_name FROM information_schema.columns "
        f"WHERE table_name = '{table}' ORDER BY ordinal_position"
    ).fetchall()
    return [r[0] for r in rows]


def _pg_columns(con: Any, table: str) -> list[str]:
    from sqlalchemy import text

    rows = con.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=:t "
            "ORDER BY ordinal_position"
        ),
        {"t": table},
    ).fetchall()
    return [r[0] for r in rows]


def _copy_table(
    duck_con: Any,
    pg_con: Any,
    table: str,
    pk_cols: tuple[str, ...],
    chunk_size: int = 1000,
) -> dict[str, int]:
    """DuckDB 테이블 → Postgres 멱등 INSERT. ON CONFLICT (pk) DO NOTHING."""
    from sqlalchemy import text

    duck_cols = _duckdb_columns(duck_con, table)
    pg_cols = _pg_columns(pg_con, table)
    if not pg_cols:
        return {"copied": 0, "skipped": 0, "error": 0, "missing_target": 1}
    cols = [c for c in duck_cols if c in pg_cols]
    if not cols:
        logger.warning("table=%s 컬럼 교집합 0 — skip", table)
        return {"copied": 0, "skipped": 0, "error": 0, "missing_target": 0}

    cols_str = ", ".join(f'"{c}"' for c in cols)
    pk_str = ", ".join(f'"{c}"' for c in pk_cols)
    placeholders = ", ".join([f":{c}" for c in cols])
    sql = (
        f'INSERT INTO "{table}" ({cols_str}) VALUES ({placeholders}) '
        f"ON CONFLICT ({pk_str}) DO NOTHING"
    )

    cur = duck_con.execute(f"SELECT {cols_str} FROM {table}")
    n_copied = 0
    n_skipped = 0
    n_err = 0
    while True:
        chunk = cur.fetchmany(chunk_size)
        if not chunk:
            break
        rows_payload = [dict(zip(cols, row)) for row in chunk]
        try:
            res = pg_con.execute(text(sql), rows_payload)
            inserted = getattr(res, "rowcount", -1)
            if inserted is not None and inserted >= 0:
                n_copied += inserted
                n_skipped += len(rows_payload) - inserted
            else:
                n_copied += len(rows_payload)
        except Exception as e:
            logger.error("table=%s chunk INSERT 실패: %s", table, e)
            n_err += len(rows_payload)
    return {"copied": n_copied, "skipped": n_skipped, "error": n_err}


def _count_duckdb(con: Any, table: str) -> int:
    if table not in _duckdb_tables(con):
        return -1
    return int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _count_pg(con: Any, table: str) -> int:
    from sqlalchemy import text

    if not _pg_columns(con, table):
        return -1
    return int(con.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar() or 0)


def migrate(
    duckdb_path: Path,
    *,
    dsn: str | None = None,
    tables: Iterable[tuple[str, tuple[str, ...]]] = TABLES,
    chunk_size: int = 1000,
) -> dict[str, Any]:
    import duckdb
    from sqlalchemy import create_engine

    from backend.app.db.session import resolve_dsn

    eff_dsn = dsn or resolve_dsn(async_=False)
    duck_con = duckdb.connect(str(duckdb_path), read_only=True)
    engine = create_engine(eff_dsn, future=True)
    duck_tables = _duckdb_tables(duck_con)
    report: dict[str, Any] = {"dsn": eff_dsn, "duckdb": str(duckdb_path), "tables": {}}

    try:
        with engine.begin() as pg_con:
            for table, pk_cols in tables:
                if table not in duck_tables:
                    logger.info("table=%s 없음 (DuckDB) — skip", table)
                    report["tables"][table] = {"copied": 0, "missing_source": 1}
                    continue
                stats = _copy_table(
                    duck_con, pg_con, table, pk_cols, chunk_size=chunk_size
                )
                pre = _count_duckdb(duck_con, table)
                post = _count_pg(pg_con, table)
                stats["duckdb_count"] = pre
                stats["postgres_count"] = post
                stats["delta"] = (post - pre) if pre >= 0 and post >= 0 else None
                report["tables"][table] = stats
    finally:
        duck_con.close()
        engine.dispose()
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--duckdb",
        type=Path,
        default=REPO_ROOT / "_workspace" / "db" / "politikast.duckdb",
    )
    p.add_argument(
        "--dsn",
        default=None,
        help="Postgres DSN (default: backend.app.db.session.resolve_dsn)",
    )
    p.add_argument("--chunk-size", type=int, default=1000)
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args(argv)
    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s %(message)s")

    if not args.duckdb.exists():
        print(f"DuckDB not found: {args.duckdb}", file=sys.stderr)
        return 2

    report = migrate(args.duckdb, dsn=args.dsn, chunk_size=args.chunk_size)
    print("--- migration report ---")
    for table, stats in report["tables"].items():
        print(f"  {table}: {stats}")
    diffs = [
        (t, s)
        for t, s in report["tables"].items()
        if s.get("delta") not in (0, None)
    ]
    if diffs:
        print(f"warn: {len(diffs)} table(s) row count 불일치 — invariance 검토 필요")
        return 1
    print("ok: row count invariance 통과 — DuckDB 파일 archive 가능.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
