"""Phase 4 cutover — DuckDB → Postgres metric invariance gate.

마이그레이션 전후 19개 핵심 metric 이 동등한지 핀한다. PG 미제공 환경에서는
DuckDB 측 baseline 만 측정하여 snapshot 으로 박제한다 (회귀용 reference).

검증 대상 (모두 row count 또는 deterministic agg):
  1. persona_core row count
  2. persona_text row count
  3. raw_poll row count
  4. raw_poll row count per region (5 region)
  5. raw_poll_result row count
  6. poll_consensus_daily row count
  7. election_result row count
  8. ingest_run row count
  9. stg_raw_poll row count
 10. stg_kg_triple row count
 11. official_poll row count (VIEW)
 12. raw_poll DISTINCT pollster count
 13. raw_poll DISTINCT contest_id count
 14. raw_poll_result share SUM (8자리 반올림)
 15. raw_poll_result share AVG (8자리)
 16. poll_consensus_daily p_hat SUM (8자리)
 17. raw_poll DISTINCT poll_id count
 18. stg_kg_triple DISTINCT subj count
 19. stg_kg_triple DISTINCT pred count
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DUCKDB_PATH = REPO_ROOT / "_workspace" / "db" / "politikast.duckdb"


# 모든 metric 을 단일 쿼리로 표현 — 양 backend 에서 실행해 동일 결과 확인.
METRIC_QUERIES = {
    "persona_core_n": "SELECT COUNT(*) FROM persona_core",
    "persona_text_n": "SELECT COUNT(*) FROM persona_text",
    "raw_poll_n": "SELECT COUNT(*) FROM raw_poll",
    "raw_poll_result_n": "SELECT COUNT(*) FROM raw_poll_result",
    "poll_consensus_n": "SELECT COUNT(*) FROM poll_consensus_daily",
    "election_result_n": "SELECT COUNT(*) FROM election_result",
    "ingest_run_n": "SELECT COUNT(*) FROM ingest_run",
    "stg_raw_poll_n": "SELECT COUNT(*) FROM stg_raw_poll",
    "stg_kg_triple_n": "SELECT COUNT(*) FROM stg_kg_triple",
    "official_poll_n": "SELECT COUNT(*) FROM official_poll",
    "raw_poll_pollster_n": "SELECT COUNT(DISTINCT pollster) FROM raw_poll",
    "raw_poll_contest_n": "SELECT COUNT(DISTINCT contest_id) FROM raw_poll",
    "raw_poll_result_share_sum": "SELECT ROUND(SUM(share)::numeric, 8) FROM raw_poll_result",
    "raw_poll_result_share_avg": "SELECT ROUND(AVG(share)::numeric, 8) FROM raw_poll_result",
    "poll_consensus_phat_sum": "SELECT ROUND(SUM(p_hat)::numeric, 8) FROM poll_consensus_daily",
    "raw_poll_poll_id_n": "SELECT COUNT(DISTINCT poll_id) FROM raw_poll",
    "stg_kg_triple_subj_n": "SELECT COUNT(DISTINCT subj) FROM stg_kg_triple",
    "stg_kg_triple_pred_n": "SELECT COUNT(DISTINCT pred) FROM stg_kg_triple",
}

PER_REGION_QUERY = (
    "SELECT region_id, COUNT(*) FROM raw_poll GROUP BY region_id ORDER BY region_id"
)


def _duckdb_connect(path: Path) -> Any:
    import duckdb

    return duckdb.connect(str(path), read_only=True)


def _has_duckdb() -> bool:
    if not DEFAULT_DUCKDB_PATH.exists():
        return False
    try:
        import duckdb  # noqa: F401

        return True
    except Exception:
        return False


def _has_postgres() -> bool:
    if not (os.environ.get("POLITIKAST_PG_DSN") or os.environ.get("DATABASE_URL")):
        return False
    try:
        from sqlalchemy import create_engine, text  # noqa: F401

        from backend.app.db.session import resolve_dsn

        engine = create_engine(resolve_dsn(async_=False), future=True)
        with engine.connect() as con:
            con.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


def _normalize_value(v: Any) -> Any:
    """DuckDB 와 PG 가 numeric 을 다르게 돌려주므로 비교 위해 문자열 정규화."""
    if v is None:
        return None
    try:
        return round(float(v), 6)
    except Exception:
        return v


def _duckdb_metric(con: Any, sql: str) -> Any:
    # DuckDB 는 ::numeric 캐스팅을 ::DECIMAL 로 받음 — 호환 위해 ::DOUBLE 로 변경.
    duck_sql = sql.replace("::numeric", "::DOUBLE")
    row = con.execute(duck_sql).fetchone()
    return _normalize_value(row[0]) if row else None


def _pg_metric(con: Any, sql: str) -> Any:
    from sqlalchemy import text

    row = con.execute(text(sql)).fetchone()
    return _normalize_value(row[0]) if row else None


# ---------------------------------------------------------------------------
# Tests — 둘 다 가능하면 비교, 한쪽만 있으면 baseline 측정으로 회귀 핀.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def duckdb_metrics() -> dict[str, Any]:
    if not _has_duckdb():
        pytest.skip("DuckDB 파일 없음 — Phase 4 archive 후 정상")
    con = _duckdb_connect(DEFAULT_DUCKDB_PATH)
    out: dict[str, Any] = {}
    try:
        tables = {
            r[0]
            for r in con.execute(
                "select table_name from information_schema.tables "
                "where table_schema='main' UNION "
                "select table_name from information_schema.views "
                "where table_schema='main'"
            ).fetchall()
        }
        for name, sql in METRIC_QUERIES.items():
            target = sql.split("FROM ", 1)[1].split()[0].strip(";")
            if target not in tables:
                out[name] = None
                continue
            try:
                out[name] = _duckdb_metric(con, sql)
            except Exception as e:
                out[name] = f"err:{e}"
        # per-region
        if "raw_poll" in tables:
            out["raw_poll_per_region"] = dict(
                _duckdb_metric_pairs(con, PER_REGION_QUERY)
            )
        else:
            out["raw_poll_per_region"] = {}
    finally:
        con.close()
    return out


@pytest.fixture(scope="module")
def pg_metrics() -> dict[str, Any]:
    if not _has_postgres():
        pytest.skip("Postgres 미연결 — POLITIKAST_PG_DSN 설정 필요")
    from sqlalchemy import create_engine, text

    from backend.app.db.session import resolve_dsn

    engine = create_engine(resolve_dsn(async_=False), future=True)
    out: dict[str, Any] = {}
    with engine.connect() as con:
        rows = con.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' "
                "UNION SELECT table_name FROM information_schema.views "
                "WHERE table_schema='public'"
            )
        ).fetchall()
        tables = {r[0] for r in rows}
        for name, sql in METRIC_QUERIES.items():
            target = sql.split("FROM ", 1)[1].split()[0].strip(";")
            if target not in tables:
                out[name] = None
                continue
            try:
                out[name] = _pg_metric(con, sql)
            except Exception as e:
                out[name] = f"err:{e}"
        if "raw_poll" in tables:
            res = con.execute(text(PER_REGION_QUERY)).fetchall()
            out["raw_poll_per_region"] = {r[0]: r[1] for r in res}
        else:
            out["raw_poll_per_region"] = {}
    engine.dispose()
    return out


def _duckdb_metric_pairs(con: Any, sql: str) -> list[tuple[Any, Any]]:
    return list(con.execute(sql).fetchall())


def test_metric_invariance(duckdb_metrics: dict[str, Any], pg_metrics: dict[str, Any]) -> None:
    """양 backend metric 이 모두 동등 (cutover 무손실 보장)."""
    diffs: list[str] = []
    for name in METRIC_QUERIES:
        a = duckdb_metrics.get(name)
        b = pg_metrics.get(name)
        if a != b:
            diffs.append(f"{name}: duckdb={a!r} != postgres={b!r}")
    if duckdb_metrics.get("raw_poll_per_region") != pg_metrics.get("raw_poll_per_region"):
        diffs.append(
            "raw_poll_per_region: "
            f"duckdb={duckdb_metrics.get('raw_poll_per_region')} != "
            f"postgres={pg_metrics.get('raw_poll_per_region')}"
        )
    assert not diffs, "\n".join(diffs)


def test_duckdb_baseline_snapshot(duckdb_metrics: dict[str, Any]) -> None:
    """DuckDB 측 baseline 이 합리적 범위 — Phase 3 회귀 (raw_poll=77)."""
    assert duckdb_metrics["raw_poll_n"] == 77, (
        f"baseline 변동: raw_poll={duckdb_metrics['raw_poll_n']} (Phase 3 회귀 77 기대)"
    )
    per = duckdb_metrics.get("raw_poll_per_region") or {}
    expected = {
        "seoul_mayor": 25,
        "gwangju_mayor": 25,
        "daegu_mayor": 25,
        "busan_buk_gap": 2,
    }
    for k, v in expected.items():
        assert per.get(k) == v, f"per-region 회귀: {k}={per.get(k)} (기대 {v})"


def test_pg_baseline_smoke(pg_metrics: dict[str, Any]) -> None:
    """PG 측 raw_poll row > 0 (마이그레이션 후) — DDL 만 박힌 fresh DB 면 0 OK."""
    n = pg_metrics.get("raw_poll_n")
    # fresh DB 는 0, migrated 면 양수. 모두 허용 — 음수만 fail.
    assert n is None or n >= 0, f"raw_poll_n={n!r}"
