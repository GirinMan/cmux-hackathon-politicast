"""PipelineRunner end-to-end — mock adapter 1개로 smoke."""
from __future__ import annotations

import sys
import types

import pytest

duckdb = pytest.importorskip("duckdb")

from src.ingest.base import FetchPayload, IngestRunContext, ParseResult
from src.ingest.pipeline import PipelineRunner, load_adapter
from src.schemas.data_source import (
    DataSource,
    DataSourceRegistry,
)


# ---- mock adapter module factory ----
def _install_mock_module(name: str, table: str = "stg_raw_poll") -> None:
    mod = types.ModuleType(name)

    class _Adapter:
        source_id = "mock_src"
        kind = "structured"
        target_kind = "raw_poll"

        def fetch(self, ctx: IngestRunContext) -> FetchPayload:
            return FetchPayload(
                source_id=self.source_id,
                items=[{"poll_id": "mock_p1", "n": 1000}],
                fetched_at="2026-04-26T10:00:00+09:00",
            )

        def parse(self, payload: FetchPayload, ctx: IngestRunContext) -> ParseResult:
            rows = []
            for it in payload.items:
                rows.append({
                    "poll_id": it["poll_id"],
                    "region_id": "seoul_mayor",
                    "contest_id": "seoul_mayor_2026",
                    "pollster": "MOCK",
                    "mode": "phone",
                    "n": it["n"],
                    "fieldwork_start": "2026-05-01",
                    "fieldwork_end": "2026-05-02",
                    "quality": 0.9,
                    "source_url": "mock://x",
                    "raw_json": "{}",
                    "fetched_at": payload.fetched_at,
                })
            return ParseResult(table=table, rows=rows)

    mod.get_adapter = lambda: _Adapter()  # type: ignore[attr-defined]
    sys.modules[name] = mod


@pytest.fixture
def runner_with_mock():
    mod_name = "tests.ingest._mock_adapter_smoke"
    _install_mock_module(mod_name)
    reg = DataSourceRegistry(
        sources={
            "mock_src": DataSource(
                id="mock_src", kind="structured", target_kind="raw_poll",
                fetcher_module=mod_name,
                description="mock", enabled=True,
            )
        }
    )
    con = duckdb.connect(":memory:")
    runner = PipelineRunner(registry=reg, db_conn=con)
    yield runner, con
    con.close()
    sys.modules.pop(mod_name, None)


def test_load_adapter_returns_protocol_compliant(runner_with_mock) -> None:
    runner, _ = runner_with_mock
    src = runner.registry.get("mock_src")
    adp = load_adapter(src)
    assert hasattr(adp, "fetch") and hasattr(adp, "parse")
    assert adp.kind == "structured"


def test_pipeline_smoke_dry_run(runner_with_mock) -> None:
    runner, con = runner_with_mock
    report = runner.run(source_ids=["mock_src"], dry_run=True)
    assert len(report.runs) == 1
    r = report.runs[0]
    assert r.status == "succeeded", r.error
    assert r.n_fetched == 1
    assert r.n_loaded == 1
    # dry_run 이므로 target 으로 MERGE 되지 않음
    target_rows = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='raw_poll'"
    ).fetchone()[0]
    # ensure_target_tables 자체는 호출되지 않음 → 0
    assert target_rows == 0
    # ingest_run row 가 succeeded 로 남음
    status = con.execute(
        "SELECT status, n_loaded, dry_run FROM ingest_run WHERE source_id='mock_src'"
    ).fetchone()
    assert status[0] == "succeeded"
    assert status[1] == 1
    assert status[2] is True


def test_pipeline_smoke_full_run_merges_target(runner_with_mock) -> None:
    runner, con = runner_with_mock
    report = runner.run(source_ids=["mock_src"], dry_run=False)
    assert report.all_succeeded
    n_target = con.execute("SELECT COUNT(*) FROM raw_poll WHERE poll_id='mock_p1'").fetchone()[0]
    assert n_target == 1


def test_pipeline_idempotent_second_run(runner_with_mock) -> None:
    runner, con = runner_with_mock
    runner.run(source_ids=["mock_src"], dry_run=False)
    n_after_first = con.execute("SELECT COUNT(*) FROM raw_poll").fetchone()[0]
    runner.run(source_ids=["mock_src"], dry_run=False)
    n_after_second = con.execute("SELECT COUNT(*) FROM raw_poll").fetchone()[0]
    # 같은 poll_id — DELETE+INSERT 로 row 수 보존
    assert n_after_first == n_after_second == 1
    # 두 번째 run 은 새 run_id 라서 stg INSERT 가 발생 (PK = run_id+poll_id)
    n_stg = con.execute("SELECT COUNT(*) FROM stg_raw_poll").fetchone()[0]
    assert n_stg == 2


def test_unknown_source_id_returns_failed_report(runner_with_mock) -> None:
    runner, _ = runner_with_mock
    report = runner.run(source_ids=["does_not_exist"])
    assert len(report.runs) == 1
    assert report.runs[0].status == "failed"
    assert "does_not_exist" in (report.runs[0].error or "")
