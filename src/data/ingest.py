"""Nemotron-Personas-Korea parquet → DB 인제션 + 5 region view.

Phase 4 cutover
---------------
- Default (Postgres): parquet → DuckDB intermediate (in-memory) → PG COPY/INSERT
  via ``tools/migrate_duckdb_to_postgres.py``. 직접 호출은
  ``ingest_to_postgres()`` (신규).
- Legacy (DuckDB file): 기존 ``ingest()`` + ``build_region_views()`` 시그니처 보존.
- Backend 선택은 ``backend.app.db.session.is_postgres_enabled()`` 또는
  ``--backend pg|duckdb`` CLI 플래그.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

import duckdb

from src.schemas.persona import (
    PERSONA_CORE_COLUMNS,
    PERSONA_DISTRICT_CANDIDATES,
    PERSONA_PROVINCE_CANDIDATES,
    PERSONA_TEXT_SUFFIX,
)

# ---------------------------------------------------------------------------
# 경로/상수
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_PATH = REPO_ROOT / "_workspace" / "contracts" / "data_paths.json"

# 컬럼 화이트리스트는 src/schemas/persona.py 가 SoT — 본 모듈은 alias 만 유지.
DEMOGRAPHIC_CORE_CANDIDATES: list[str] = list(PERSONA_CORE_COLUMNS)
_PROVINCE_CANDIDATES: list[str] = list(PERSONA_PROVINCE_CANDIDATES)
_DISTRICT_CANDIDATES: list[str] = list(PERSONA_DISTRICT_CANDIDATES)
_TEXT_PERSONA_SUFFIX = PERSONA_TEXT_SUFFIX


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------
def load_contracts() -> dict[str, Any]:
    with CONTRACTS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def list_parquet_files(parquet_dir: Path) -> list[Path]:
    files = sorted(parquet_dir.glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No parquet files under {parquet_dir}")
    return files


def discover_columns(con: duckdb.DuckDBPyConnection, parquet_glob: str) -> list[str]:
    """첫 번째 parquet 파일에서 컬럼 리스트 추출."""
    rows = con.execute(
        f"SELECT * FROM read_parquet('{parquet_glob}') LIMIT 0"
    ).description
    return [r[0] for r in rows]


def pick_first_existing(candidates: Iterable[str], available: set[str]) -> str | None:
    for c in candidates:
        if c in available:
            return c
    return None


def split_columns(all_cols: list[str]) -> tuple[list[str], list[str]]:
    """*_persona 텍스트 컬럼 vs 데모그래픽 코어 컬럼으로 분리."""
    text_cols = [c for c in all_cols if c.endswith(_TEXT_PERSONA_SUFFIX)]
    core_cols = [c for c in all_cols if c not in text_cols]
    return core_cols, text_cols


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def quote_literal(value: str) -> str:
    """SQL 문자열 리터럴 — 단일 따옴표 escape."""
    return "'" + value.replace("'", "''") + "'"


# ---------------------------------------------------------------------------
# 인제션
# ---------------------------------------------------------------------------
def ingest(
    db_path: Path,
    parquet_dir: Path,
    persona_table: str = "persona_core",
    persona_text_table: str = "persona_text",
) -> dict[str, Any]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    files = list_parquet_files(parquet_dir)
    parquet_glob = str(parquet_dir / "*.parquet")

    con = duckdb.connect(str(db_path))
    try:
        all_cols = discover_columns(con, parquet_glob)
        available = set(all_cols)
        core_cols, text_cols = split_columns(all_cols)

        if "uuid" not in available:
            raise RuntimeError(
                f"Expected `uuid` column in Nemotron parquet, got: {sorted(available)}"
            )

        province_col = pick_first_existing(_PROVINCE_CANDIDATES, available)
        district_col = pick_first_existing(_DISTRICT_CANDIDATES, available)

        # province 컬럼이 core_cols 에 이미 없을 수 있는 후보명을 쓸 경우 누락 방지
        for extra in (province_col, district_col):
            if extra and extra not in core_cols and extra not in text_cols:
                core_cols.append(extra)

        core_cols_quoted = ", ".join(quote_ident(c) for c in core_cols)
        text_cols_quoted = ", ".join(quote_ident(c) for c in ["uuid", *text_cols])

        # 1) persona_core
        con.execute(
            f"""
            CREATE OR REPLACE TABLE {quote_ident(persona_table)} AS
            SELECT {core_cols_quoted}
            FROM read_parquet('{parquet_glob}')
            """
        )
        # uuid PRIMARY KEY 는 DuckDB 에서 ALTER 로 추가
        try:
            con.execute(
                f"ALTER TABLE {quote_ident(persona_table)} "
                f"ADD CONSTRAINT pk_{persona_table}_uuid PRIMARY KEY (uuid)"
            )
        except duckdb.Error:
            # 이미 PK 가 있거나 중복 uuid 가 있을 수 있음 — 멱등 재실행 시 무시
            pass

        # 2) persona_text
        if text_cols:
            con.execute(
                f"""
                CREATE OR REPLACE TABLE {quote_ident(persona_text_table)} AS
                SELECT {text_cols_quoted}
                FROM read_parquet('{parquet_glob}')
                """
            )
            try:
                con.execute(
                    f"ALTER TABLE {quote_ident(persona_text_table)} "
                    f"ADD CONSTRAINT pk_{persona_text_table}_uuid PRIMARY KEY (uuid)"
                )
            except duckdb.Error:
                pass
        else:
            print(
                f"[warn] No *_persona text columns found in parquet; "
                f"skipping `{persona_text_table}`."
            )

        # 카운트 보고
        total = con.execute(
            f"SELECT COUNT(*) FROM {quote_ident(persona_table)}"
        ).fetchone()[0]

        return {
            "files": [str(p) for p in files],
            "total_rows": total,
            "core_columns": core_cols,
            "text_columns": text_cols,
            "province_col": province_col,
            "district_col": district_col,
        }
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Region views
# ---------------------------------------------------------------------------
def build_region_views(
    db_path: Path,
    regions: list[dict[str, Any]],
    province_col: str | None,
    district_col: str | None,
    persona_table: str = "persona_core",
) -> dict[str, int]:
    """`personas_<region_id>` view 생성. 보궐(TBD) 제외."""
    if province_col is None:
        print(
            "[warn] No province column detected; skipping region view creation. "
            "Inspect parquet schema and rerun."
        )
        return {}

    counts: dict[str, int] = {}
    con = duckdb.connect(str(db_path))
    try:
        for r in regions:
            province = r.get("province")
            district = r.get("district")
            if province in (None, "TBD"):
                continue

            view_name = f"personas_{r['id']}"
            where = [f"{quote_ident(province_col)} = {quote_literal(province)}"]
            if district not in (None, "TBD"):
                if district_col is None:
                    print(
                        f"[warn] region {r['id']} requires district='{district}' "
                        f"but no district column available — skipping."
                    )
                    continue
                where.append(
                    f"{quote_ident(district_col)} = {quote_literal(district)}"
                )

            sql = (
                f"CREATE OR REPLACE VIEW {quote_ident(view_name)} AS "
                f"SELECT * FROM {quote_ident(persona_table)} "
                f"WHERE {' AND '.join(where)}"
            )
            con.execute(sql)

            cnt = con.execute(
                f"SELECT COUNT(*) FROM {quote_ident(view_name)}"
            ).fetchone()[0]
            counts[r["id"]] = int(cnt)
        return counts
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Postgres path — DuckDB intermediate 후 SQLAlchemy bulk insert
# ---------------------------------------------------------------------------
def ingest_to_postgres(
    parquet_dir: Path,
    *,
    persona_table: str = "persona_core",
    persona_text_table: str = "persona_text",
    chunk_size: int = 5000,
) -> dict[str, Any]:
    """parquet → 메모리 DuckDB → PG bulk INSERT.

    DuckDB 의 parquet reader 가 워낙 빨라서 staging engine 으로 활용한 뒤
    PG 로 옮긴다. ``tools/migrate_duckdb_to_postgres.py`` 가 동일 path 의
    별도 진입점 (DuckDB 파일 → PG).
    """
    from sqlalchemy import create_engine, text

    from backend.app.db.session import resolve_dsn

    files = list_parquet_files(parquet_dir)
    parquet_glob = str(parquet_dir / "*.parquet")
    mem_con = duckdb.connect(":memory:")

    all_cols = discover_columns(mem_con, parquet_glob)
    available = set(all_cols)
    core_cols, text_cols = split_columns(all_cols)
    if "uuid" not in available:
        raise RuntimeError(f"Expected `uuid` in parquet, got {sorted(available)}")
    province_col = pick_first_existing(_PROVINCE_CANDIDATES, available)
    district_col = pick_first_existing(_DISTRICT_CANDIDATES, available)
    for extra in (province_col, district_col):
        if extra and extra not in core_cols and extra not in text_cols:
            core_cols.append(extra)

    pg = create_engine(resolve_dsn(async_=False), future=True)
    n_inserted = {persona_table: 0, persona_text_table: 0}

    with pg.begin() as con:
        # core
        con.execute(text(f'TRUNCATE "{persona_table}"'))
        cols_str = ", ".join(quote_ident(c) for c in core_cols)
        rows_iter = mem_con.execute(
            f"SELECT {cols_str} FROM read_parquet('{parquet_glob}')"
        )
        while True:
            chunk = rows_iter.fetchmany(chunk_size)
            if not chunk:
                break
            placeholders = ", ".join([":" + c for c in core_cols])
            con.execute(
                text(
                    f'INSERT INTO "{persona_table}" ({cols_str}) '
                    f"VALUES ({placeholders}) ON CONFLICT DO NOTHING"
                ),
                [dict(zip(core_cols, r)) for r in chunk],
            )
            n_inserted[persona_table] += len(chunk)

        # text
        if text_cols:
            con.execute(text(f'TRUNCATE "{persona_text_table}"'))
            t_cols = ["uuid", *text_cols]
            t_cols_str = ", ".join(quote_ident(c) for c in t_cols)
            rows_iter = mem_con.execute(
                f"SELECT {t_cols_str} FROM read_parquet('{parquet_glob}')"
            )
            while True:
                chunk = rows_iter.fetchmany(chunk_size)
                if not chunk:
                    break
                placeholders = ", ".join([":" + c for c in t_cols])
                con.execute(
                    text(
                        f'INSERT INTO "{persona_text_table}" ({t_cols_str}) '
                        f"VALUES ({placeholders}) ON CONFLICT DO NOTHING"
                    ),
                    [dict(zip(t_cols, r)) for r in chunk],
                )
                n_inserted[persona_text_table] += len(chunk)

    mem_con.close()
    pg.dispose()
    return {
        "files": [str(p) for p in files],
        "n_inserted": n_inserted,
        "core_columns": core_cols,
        "text_columns": text_cols,
        "province_col": province_col,
        "district_col": district_col,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    contracts = load_contracts()
    default_db = REPO_ROOT / contracts["duckdb_path"]
    default_parquet = Path(
        os.environ.get("NEMOTRON_PARQUET_DIR", contracts["nemotron_parquet_dir"])
    )

    parser = argparse.ArgumentParser(description="PolitiKAST DB ingestion")
    parser.add_argument(
        "--backend", choices=["duckdb", "pg"], default=None,
        help="명시 안 하면 POLITIKAST_PG_DSN/DATABASE_URL 존재 여부로 자동.",
    )
    parser.add_argument("--db", type=Path, default=default_db)
    parser.add_argument("--parquet-dir", type=Path, default=default_parquet)
    parser.add_argument(
        "--persona-table", default=contracts.get("persona_table", "persona_core")
    )
    parser.add_argument(
        "--persona-text-table",
        default=contracts.get("persona_text_table", "persona_text"),
    )
    args = parser.parse_args(argv)

    backend = args.backend
    if backend is None:
        try:
            from backend.app.db.session import is_postgres_enabled

            backend = "pg" if is_postgres_enabled() else "duckdb"
        except Exception:
            backend = "duckdb"

    print(f"[ingest] parquet dir: {args.parquet_dir}")
    print(f"[ingest] backend: {backend}")
    if backend == "pg":
        info = ingest_to_postgres(
            parquet_dir=args.parquet_dir,
            persona_table=args.persona_table,
            persona_text_table=args.persona_text_table,
        )
        print(f"[ingest] files: {len(info['files'])}")
        print(f"[ingest] n_inserted: {info['n_inserted']}")
        print(
            f"[ingest] province_col={info['province_col']!r} "
            f"district_col={info['district_col']!r}"
        )
        return 0

    print(f"[ingest] duckdb path: {args.db}")
    info = ingest(
        db_path=args.db,
        parquet_dir=args.parquet_dir,
        persona_table=args.persona_table,
        persona_text_table=args.persona_text_table,
    )
    print(f"[ingest] files: {len(info['files'])}")
    print(f"[ingest] total rows: {info['total_rows']:,}")
    print(f"[ingest] core columns ({len(info['core_columns'])}): {info['core_columns']}")
    print(f"[ingest] text columns ({len(info['text_columns'])}): {info['text_columns']}")
    print(
        f"[ingest] province_col={info['province_col']!r} "
        f"district_col={info['district_col']!r}"
    )

    region_counts = build_region_views(
        db_path=args.db,
        regions=contracts["regions"],
        province_col=info["province_col"],
        district_col=info["district_col"],
        persona_table=args.persona_table,
    )
    print("[ingest] region sample sizes:")
    for rid, cnt in region_counts.items():
        print(f"  - {rid}: {cnt:,}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
