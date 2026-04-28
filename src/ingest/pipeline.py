"""PipelineRunner — registry 기반 ingest orchestration.

흐름:
  1. data_sources.json 로드, 활성 source 결정
  2. 각 source 에 대해 run_id 생성 → ingest_run 'running' INSERT
  3. importlib 로 adapter 모듈 import → get_adapter() 호출
  4. adapter.fetch(ctx) → adapter.parse(payload, ctx)
  5. ParseResult.unresolved → unresolved_entity INSERT (resolver hand-off)
  6. ParseResult.rows → stg_* INSERT (멱등)
  7. dry_run 아니면 stg → target MERGE
  8. ingest_run 'succeeded'/'failed' UPDATE

CLI: `python -m src.ingest.pipeline --source nesdc_poll --dry-run`
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib
import json
import logging
import os
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from src.schemas.data_source import (
    DataSource,
    DataSourceRegistry,
    IngestRun,
    load_data_source_registry,
)
from src.utils.tz import now_kst

from . import staging
from .base import FetchPayload, IngestRunContext, ParseResult, SourceAdapter

logger = logging.getLogger("ingest.pipeline")


# ---------------------------------------------------------------------------
# Result envelope
# ---------------------------------------------------------------------------
@dataclass
class SourceRunReport:
    run_id: str
    source_id: str
    status: str
    n_fetched: int = 0
    n_loaded: int = 0
    n_unresolved: int = 0
    error: Optional[str] = None
    dry_run: bool = False


@dataclass
class PipelineReport:
    runs: list[SourceRunReport] = field(default_factory=list)

    @property
    def all_succeeded(self) -> bool:
        return all(r.status == "succeeded" for r in self.runs)


# ---------------------------------------------------------------------------
# Adapter loader
# ---------------------------------------------------------------------------
def load_adapter(source: DataSource) -> SourceAdapter:
    """importlib 로 adapter 모듈 로드 후 `get_adapter()` 호출."""
    mod = importlib.import_module(source.fetcher_module)
    if not hasattr(mod, "get_adapter"):
        raise AttributeError(
            f"{source.fetcher_module}: get_adapter() 함수가 없음"
        )
    adapter = mod.get_adapter()
    if not hasattr(adapter, "fetch") or not hasattr(adapter, "parse"):
        raise TypeError(
            f"{source.fetcher_module}.get_adapter(): SourceAdapter Protocol 미준수"
        )
    return adapter


def _config_hash(source: DataSource, since: Optional[str]) -> str:
    payload = {
        "source_id": source.id,
        "schema_version": source.schema_version,
        "config": source.config,
        "since": since,
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
class PipelineRunner:
    """여러 source 를 순차 실행. 단일 source 실패가 다른 source 를 막지 않음."""

    def __init__(
        self,
        *,
        registry: Optional[DataSourceRegistry] = None,
        db_conn: Any = None,
        llm_pool: Any = None,
        resolver: Any = None,
    ) -> None:
        self.registry = registry or load_data_source_registry()
        self.db_conn = db_conn
        self.llm_pool = llm_pool
        self.resolver = resolver

    # ---- public ----
    def run(
        self,
        source_ids: Optional[Iterable[str]] = None,
        since: Optional[str] = None,
        dry_run: bool = False,
    ) -> PipelineReport:
        if self.db_conn is None:
            self.db_conn = self._open_db()
        staging.ensure_stg_tables(self.db_conn)

        ids = list(source_ids) if source_ids else self.registry.enabled_ids()
        report = PipelineReport()
        for sid in ids:
            try:
                source = self.registry.get(sid)
            except KeyError as e:
                report.runs.append(
                    SourceRunReport(
                        run_id="-", source_id=sid, status="failed",
                        error=str(e), dry_run=dry_run,
                    )
                )
                continue
            if not source.enabled:
                logger.info("skip disabled source: %s", sid)
                continue
            report.runs.append(self._run_one(source, since=since, dry_run=dry_run))
        return report

    # ---- internals ----
    def _open_db(self) -> Any:
        try:
            import duckdb  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"duckdb import failed: {e}")
        path = staging.DEFAULT_DB_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        return duckdb.connect(str(path))

    def _run_one(
        self, source: DataSource, *, since: Optional[str], dry_run: bool
    ) -> SourceRunReport:
        run_id = f"{source.id}-{now_kst().strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}"
        ts_start = now_kst().isoformat()
        run = IngestRun(
            run_id=run_id,
            source_id=source.id,
            started_at=ts_start,
            status="running",
            config_hash=_config_hash(source, since),
            dry_run=dry_run,
        )
        staging.upsert_ingest_run(self.db_conn, run.model_dump())

        report = SourceRunReport(
            run_id=run_id, source_id=source.id, status="running", dry_run=dry_run
        )
        try:
            adapter = load_adapter(source)
            ctx = IngestRunContext(
                run_id=run_id,
                source_id=source.id,
                db_conn=self.db_conn,
                llm_pool=self.llm_pool,
                resolver=self.resolver,
                since_date=since,
                dry_run=dry_run,
                config=dict(source.config),
                logger=logger.getChild(source.id),
            )
            payload = adapter.fetch(ctx)
            assert isinstance(payload, FetchPayload), "fetch() must return FetchPayload"
            report.n_fetched = len(payload.items)

            parsed = adapter.parse(payload, ctx)
            assert isinstance(parsed, ParseResult), "parse() must return ParseResult"

            # add run_id stamp to every staging row (멱등 PK 일부)
            stamped = [{"run_id": run_id, **row} for row in parsed.rows]
            unresolved_stamped = [{"run_id": run_id, **row} for row in parsed.unresolved]

            n_loaded = staging.insert_rows(self.db_conn, parsed.table, stamped)
            n_unresolved = 0
            if unresolved_stamped:
                n_unresolved = staging.insert_rows(
                    self.db_conn, "unresolved_entity", unresolved_stamped
                )
            report.n_loaded = n_loaded
            report.n_unresolved = n_unresolved

            # MERGE → target (best-effort, 매핑 없는 target_kind 는 noop)
            if not dry_run:
                self._merge_target(parsed.table, run_id)

            run.n_fetched = report.n_fetched
            run.n_loaded = report.n_loaded
            run.n_unresolved = report.n_unresolved
            run.status = "succeeded"
            run.finished_at = now_kst().isoformat()
            staging.upsert_ingest_run(self.db_conn, run.model_dump())
            report.status = "succeeded"
        except Exception as e:
            logger.exception("ingest failed: %s", source.id)
            run.status = "failed"
            run.error = f"{type(e).__name__}: {e}"
            run.finished_at = now_kst().isoformat()
            staging.upsert_ingest_run(self.db_conn, run.model_dump())
            report.status = "failed"
            report.error = run.error
        return report

    def _merge_target(self, stg_table: str, run_id: str) -> None:
        if stg_table == "stg_raw_poll":
            staging.merge_stg_raw_poll_to_target(self.db_conn, run_id)
        elif stg_table == "stg_raw_poll_result":
            staging.merge_stg_raw_poll_result_to_target(self.db_conn, run_id)
        # stg_kg_triple → kg-merger 의 staging_loader 가 책임. orchestrator 는 noop.
        # entity_alias 는 어댑터/resolver 가 직접 INSERT.


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", action="append", default=None,
                    help="실행할 source id (반복 가능). 미지정 시 enabled 전체.")
    ap.add_argument("--since", default=None,
                    help="ISO 8601 — 이 시점 이후 데이터만 fetch (어댑터 해석).")
    ap.add_argument("--dry-run", action="store_true",
                    help="staging 까진 진행, target MERGE 생략.")
    ap.add_argument("--status", action="store_true",
                    help="ingest_run 테이블에서 최근 N개 row 출력 후 종료.")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--log-level", default="INFO")
    return ap


def _print_status(con: Any, limit: int) -> None:
    rows = con.execute(
        "SELECT run_id, source_id, status, n_fetched, n_loaded, n_unresolved, "
        "started_at, finished_at FROM ingest_run "
        "ORDER BY started_at DESC LIMIT ?",
        [limit],
    ).fetchall()
    if not rows:
        print("(empty)")
        return
    print("run_id | source_id | status | n_fetched | n_loaded | n_unresolved | started_at")
    for r in rows:
        print(" | ".join(str(v) if v is not None else "-" for v in r))


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_argparser().parse_args(argv)
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    runner = PipelineRunner()
    if runner.db_conn is None:
        runner.db_conn = runner._open_db()
    staging.ensure_stg_tables(runner.db_conn)

    if args.status:
        _print_status(runner.db_conn, args.limit)
        return 0

    report = runner.run(source_ids=args.source, since=args.since, dry_run=args.dry_run)
    for r in report.runs:
        print(json.dumps({
            "run_id": r.run_id, "source_id": r.source_id,
            "status": r.status, "n_fetched": r.n_fetched, "n_loaded": r.n_loaded,
            "n_unresolved": r.n_unresolved, "error": r.error,
            "dry_run": r.dry_run,
        }, ensure_ascii=False))
    return 0 if report.all_succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
