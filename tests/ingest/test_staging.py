"""staging.py — DDL 멱등성 + insert/MERGE round-trip."""
from __future__ import annotations

import json
import pytest

duckdb = pytest.importorskip("duckdb")

from src.ingest import staging


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    yield c
    c.close()


def test_ensure_stg_tables_idempotent(con) -> None:
    staging.ensure_stg_tables(con)
    staging.ensure_stg_tables(con)  # 두 번 호출해도 raise 없어야
    rows = con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
    ).fetchall()
    names = {r[0] for r in rows}
    for t in staging.STG_TABLES:
        assert t in names, t


def test_insert_rows_returns_count_and_dedups(con) -> None:
    staging.ensure_stg_tables(con)
    rows = [
        {"run_id": "r1", "poll_id": "p1", "region_id": "seoul_mayor",
         "contest_id": "c1", "pollster": "A", "mode": "phone",
         "n": 1000, "fieldwork_start": "2026-05-01", "fieldwork_end": "2026-05-02",
         "quality": 0.9, "source_url": "u", "raw_json": "{}",
         "fetched_at": "2026-05-02T10:00:00+09:00"},
        {"run_id": "r1", "poll_id": "p2", "region_id": "seoul_mayor",
         "contest_id": "c1", "pollster": "B", "mode": "online",
         "n": 800, "fieldwork_start": "2026-05-03", "fieldwork_end": "2026-05-04",
         "quality": 0.8, "source_url": "u2", "raw_json": "{}",
         "fetched_at": "2026-05-04T10:00:00+09:00"},
    ]
    n1 = staging.insert_rows(con, "stg_raw_poll", rows)
    assert n1 == 2
    # 같은 PK 재실행 → INSERT 0 (멱등)
    n2 = staging.insert_rows(con, "stg_raw_poll", rows)
    assert n2 == 0
    total = con.execute("SELECT COUNT(*) FROM stg_raw_poll").fetchone()[0]
    assert total == 2


def test_upsert_ingest_run_replaces_row(con) -> None:
    staging.ensure_stg_tables(con)
    base = {
        "run_id": "r1", "source_id": "s", "started_at": "t0", "finished_at": None,
        "n_fetched": 0, "n_loaded": 0, "n_unresolved": 0, "status": "running",
        "error": None, "config_hash": "h1", "dry_run": False,
    }
    staging.upsert_ingest_run(con, base)
    base2 = dict(base, status="succeeded", finished_at="t1", n_loaded=5)
    staging.upsert_ingest_run(con, base2)
    row = con.execute(
        "SELECT status, n_loaded, finished_at FROM ingest_run WHERE run_id='r1'"
    ).fetchone()
    assert row == ("succeeded", 5, "t1")


def test_merge_stg_raw_poll_to_target_round_trip(con) -> None:
    staging.ensure_stg_tables(con)
    staging.ensure_target_tables(con)
    rows = [
        {"run_id": "r1", "poll_id": "p1", "region_id": "seoul_mayor",
         "contest_id": "c1", "pollster": "A", "mode": "phone", "n": 1000,
         "fieldwork_start": "2026-05-01", "fieldwork_end": "2026-05-02",
         "quality": 0.9, "source_url": "u", "raw_json": "{}",
         "fetched_at": "2026-05-02T10:00:00+09:00"},
    ]
    staging.insert_rows(con, "stg_raw_poll", rows)
    staging.merge_stg_raw_poll_to_target(con, "r1")
    n = con.execute("SELECT COUNT(*) FROM raw_poll WHERE poll_id='p1'").fetchone()[0]
    assert n == 1
    # 두 번째 MERGE — DELETE+INSERT 로 동일 row count 유지 (멱등)
    staging.merge_stg_raw_poll_to_target(con, "r1")
    n = con.execute("SELECT COUNT(*) FROM raw_poll WHERE poll_id='p1'").fetchone()[0]
    assert n == 1


def test_merge_raw_poll_result_round_trip(con) -> None:
    staging.ensure_stg_tables(con)
    staging.ensure_target_tables(con)
    staging.insert_rows(con, "stg_raw_poll_result", [
        {"run_id": "r1", "poll_id": "p1", "cand_id": "c_a", "share": 0.55, "raw_label": "A"},
        {"run_id": "r1", "poll_id": "p1", "cand_id": "c_b", "share": 0.45, "raw_label": "B"},
    ])
    staging.merge_stg_raw_poll_result_to_target(con, "r1")
    n = con.execute("SELECT COUNT(*) FROM raw_poll_result WHERE poll_id='p1'").fetchone()[0]
    assert n == 2


def test_unknown_table_raises(con) -> None:
    staging.ensure_stg_tables(con)
    with pytest.raises(ValueError):
        staging.insert_rows(con, "no_such_table", [{"x": 1}])
