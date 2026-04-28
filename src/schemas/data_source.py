"""DataSource 레지스트리 + IngestRun 메타.

Phase 3 ingestion 파이프라인의 SoT. `_workspace/data/registries/data_sources.json`
이 source 레지스트리이며, 각 source 는 `fetcher_module:parser_module` 으로
실 어댑터 (`src/ingest/adapters/*.py`) 를 식별한다.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = REPO_ROOT / "_workspace" / "data" / "registries" / "data_sources.json"

SourceKind = Literal["structured", "llm"]
TargetKind = Literal["raw_poll", "candidate", "kg_triple", "issue", "person"]
RunStatus = Literal["pending", "running", "succeeded", "failed", "partial"]


class DataSource(BaseModel):
    """단일 데이터 소스 정의 — adapter 가 구현해야 할 계약."""

    model_config = ConfigDict(extra="forbid")

    id: str
    kind: SourceKind
    target_kind: TargetKind
    description: str = ""
    fetcher_module: str  # importlib path to adapter module
    parser_module: Optional[str] = None  # 보통 fetcher 와 동일 모듈
    cadence_hint: str = "manual"  # daily | weekly | manual | event
    schema_version: str = "v1"
    enabled: bool = True
    config: dict = Field(default_factory=dict)


class DataSourceRegistry(BaseModel):
    """data_sources.json 의 root."""

    model_config = ConfigDict(extra="forbid")

    version: str = "v1"
    description: str = ""
    sources: dict[str, DataSource] = Field(default_factory=dict)

    def get(self, source_id: str) -> DataSource:
        if source_id not in self.sources:
            raise KeyError(
                f"DataSourceRegistry: source_id={source_id!r} 없음 — "
                f"_workspace/data/registries/data_sources.json 에 등록 필요"
            )
        return self.sources[source_id]

    def enabled_ids(self) -> list[str]:
        return [sid for sid, s in self.sources.items() if s.enabled]


class IngestRun(BaseModel):
    """단일 ingest 실행의 stdout — `ingest_run` 테이블 row 와 1:1 매핑."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    source_id: str
    started_at: str  # ISO 8601 KST
    finished_at: Optional[str] = None
    n_fetched: int = 0
    n_loaded: int = 0
    n_unresolved: int = 0
    status: RunStatus = "pending"
    error: Optional[str] = None
    config_hash: str = ""
    dry_run: bool = False


@lru_cache(maxsize=4)
def load_data_source_registry(path: Optional[str] = None) -> DataSourceRegistry:
    p = Path(path) if path else DEFAULT_REGISTRY_PATH
    if not p.exists():
        raise FileNotFoundError(f"data_sources registry missing: {p}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    return DataSourceRegistry.model_validate(raw)


__all__ = [
    "DataSource",
    "DataSourceRegistry",
    "IngestRun",
    "load_data_source_registry",
    "DEFAULT_REGISTRY_PATH",
    "SourceKind",
    "TargetKind",
    "RunStatus",
]
