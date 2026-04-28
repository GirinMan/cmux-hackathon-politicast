#!/usr/bin/env python
"""Ensure ground-truth views/tables exist in DuckDB.

`official_poll` 은 raw_poll/raw_poll_result 위의 VIEW 라 실제 데이터 시드는
data ingestion (src/data/ingest.py + 기존 큐레이션 스크립트) 의 책임이다.
본 스크립트는 (1) VIEW 와 election_result TABLE 을 멱등하게 생성하고
(2) 현재 row 수를 보고한다. 선거 결과(2026-06-03 이후) 시드 INSERT 가
필요해지면 별도 인자로 확장한다.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

from src.data.ground_truth import DEFAULT_DB_PATH, ensure_tables


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()

    con = duckdb.connect(str(args.db), read_only=False)
    try:
        ensure_tables(con)
        rows_view = 0
        try:
            rows_view = con.execute("SELECT COUNT(*) FROM official_poll").fetchone()[0]
        except duckdb.Error:
            pass
        rows_tbl = con.execute("SELECT COUNT(*) FROM election_result").fetchone()[0]
    finally:
        con.close()

    print(f"[seed_ground_truth] db={args.db}")
    print(f"  official_poll (view) rows: {rows_view}")
    print(f"  election_result (table) rows: {rows_tbl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
