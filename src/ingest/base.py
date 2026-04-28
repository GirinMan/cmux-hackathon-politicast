"""SourceAdapter Protocol + IngestRunContext.

Adapter 계약 (src/ingest/adapters/*.py 가 구현):
    fetch(ctx)  -> FetchPayload    : 외부에서 raw 페이로드 수집 (HTTP / LLM / file)
    parse(payload, ctx) -> ParseResult : staging row 형태로 정형화

ParseResult 가 갖는 row dict 들은 `staging.insert_rows(...)` 가 stg_* 테이블에
INSERT 한다. resolver/MERGE 는 PipelineRunner 가 책임.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable

from src.schemas.data_source import SourceKind, TargetKind


# ---------------------------------------------------------------------------
# Data envelopes
# ---------------------------------------------------------------------------
@dataclass
class FetchPayload:
    """Adapter.fetch 의 출력 — parse 가 처리할 raw 데이터 envelope."""

    source_id: str
    items: list[dict[str, Any]] = field(default_factory=list)
    fetched_at: Optional[str] = None  # ISO 8601 KST
    cursor: Optional[str] = None  # next-page / since-token
    notes: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParseResult:
    """Adapter.parse 의 출력 — staging insert 직전 row 모음.

    rows 의 dict 키는 stg_* 테이블 컬럼명과 동일해야 한다 (`staging.py`
    의 컬럼 사양과 일치). table 이 곧 stg_* 테이블 이름.
    """

    table: str  # "stg_raw_poll" | "stg_raw_poll_result" | "stg_kg_triple" | ...
    rows: list[dict[str, Any]] = field(default_factory=list)
    unresolved: list[dict[str, Any]] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestRunContext:
    """Adapter 가 실 환경에 접근할 때 사용하는 단일 입구."""

    run_id: str
    source_id: str
    db_conn: Any = None  # duckdb.DuckDBPyConnection
    llm_pool: Any = None
    resolver: Any = None
    since_date: Optional[str] = None  # ISO 8601 (filter 기준)
    dry_run: bool = False
    config: dict[str, Any] = field(default_factory=dict)
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("ingest"))


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------
@runtime_checkable
class SourceAdapter(Protocol):
    """모든 ingest adapter 가 구현해야 하는 표면."""

    source_id: str
    kind: SourceKind
    target_kind: TargetKind

    def fetch(self, ctx: IngestRunContext) -> FetchPayload:  # pragma: no cover - protocol
        ...

    def parse(self, payload: FetchPayload, ctx: IngestRunContext) -> ParseResult:  # pragma: no cover
        ...


__all__ = [
    "SourceAdapter",
    "IngestRunContext",
    "FetchPayload",
    "ParseResult",
]
