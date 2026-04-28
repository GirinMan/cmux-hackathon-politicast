"""LLM strategy contract — `_workspace/contracts/llm_strategy.json` 미러.

Plan A(LiteLLM)/Plan B(CAMEL) 라우팅, 지원 provider, key env 매핑을 박제한다.
SoT는 JSON 파일이고, 본 모듈은 read-only 검증/로딩 헬퍼를 제공한다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT_PATH = REPO_ROOT / "_workspace" / "contracts" / "llm_strategy.json"


class LLMProvider(BaseModel):
    """LiteLLM 공급자 화이트리스트 항목.

    `key_env` 가 None 이면 IAM 기반 (vertex_ai/bedrock).
    """

    model_config = ConfigDict(extra="allow")

    id: str
    key_env: Optional[str] = None
    auth: str
    model_prefix: str
    extra_env: list[str] = Field(default_factory=list)


class LLMPrimaryPath(BaseModel):
    model_config = ConfigDict(extra="allow")

    package: str
    wrapper: str
    model_env: str
    default_model: str
    config: dict[str, Any] = Field(default_factory=dict)


class LLMFallbackEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    order: int
    label: str
    trigger: str
    module: Optional[str] = None


class LLMStrategy(BaseModel):
    """`_workspace/contracts/llm_strategy.json` 의 단일 파싱 진입점."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    decision: str
    rationale: Optional[str] = None
    primary_path: LLMPrimaryPath
    supported_providers: list[LLMProvider]
    fallback_chain: list[LLMFallbackEntry] = Field(default_factory=list)


def load_llm_strategy(path: Path | str | None = None) -> LLMStrategy:
    """JSON 파일을 검증된 `LLMStrategy` 로 로드. 부재 시 FileNotFoundError."""
    p = Path(path) if path is not None else DEFAULT_CONTRACT_PATH
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return LLMStrategy.model_validate(data)


def provider_key_env_map(strategy: LLMStrategy | None = None) -> dict[str, str]:
    """`provider_id -> ENV var name` 매핑. IAM 기반 provider 는 제외."""
    s = strategy or load_llm_strategy()
    return {p.id: p.key_env for p in s.supported_providers if p.key_env}


__all__ = [
    "DEFAULT_CONTRACT_PATH",
    "LLMFallbackEntry",
    "LLMPrimaryPath",
    "LLMProvider",
    "LLMStrategy",
    "load_llm_strategy",
    "provider_key_env_map",
]
