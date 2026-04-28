"""PolitiKAST ingestion pipeline.

3 layer:
  - base.py     : SourceAdapter Protocol + IngestRunContext
  - staging.py  : DuckDB stg_* 테이블 멱등 DDL + MERGE 헬퍼
  - pipeline.py : PipelineRunner — registry → adapter → staging → target

Adapter 들은 `src/ingest/adapters/*.py` 에 위치하며 각각
`get_adapter() -> SourceAdapter` 를 export 한다 (importlib 동적 로드).
"""
from __future__ import annotations

from .base import (
    FetchPayload,
    IngestRunContext,
    ParseResult,
    SourceAdapter,
)

__all__ = [
    "SourceAdapter",
    "IngestRunContext",
    "FetchPayload",
    "ParseResult",
]
