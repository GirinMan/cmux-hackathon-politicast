"""Persona axis registry — `_workspace/data/registries/persona_axes.json` 미러.

VoterAgent 라우팅 / 데모그래픽 분석에서 사용하는 축(education/age/income/region)
의 정의를 박제한다. 라우팅 구현체(`src.sim.routing.RoutingStrategy`)는 이 axis
정의를 따라 페르소나를 버킷에 매핑하면 된다.

PolitiKAST Phase 1 에서는 education axis 만 routing 에 적용되었으나, Phase 2
에서 generic 화하여 income / age 등 추가 축을 IncomeBasedRouting 등 strategy
class 로 등록할 수 있게 한다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = (
    REPO_ROOT / "_workspace" / "data" / "registries" / "persona_axes.json"
)


class NumericBucket(BaseModel):
    """반열림 구간 [min, max) — `cohort.AgeBucket` 과 동일 시맨틱."""

    model_config = ConfigDict(extra="forbid")

    label: str
    min: Optional[float] = None
    max: Optional[float] = None  # exclusive

    def contains(self, value: float) -> bool:
        if self.min is not None and value < self.min:
            return False
        if self.max is not None and value >= self.max:
            return False
        return True


class PersonaAxis(BaseModel):
    """단일 axis 정의."""

    model_config = ConfigDict(extra="allow")

    axis_id: str
    kind: str  # "ordinal_categorical" | "binned_numeric" | "categorical"
    label: str
    persona_fields: list[str] = Field(default_factory=list)
    buckets: list[Any] = Field(default_factory=list)  # str list 또는 NumericBucket list
    buckets_ref: Optional[str] = None
    default_routing: Optional[str] = None

    def numeric_buckets(self) -> list[NumericBucket]:
        out: list[NumericBucket] = []
        for b in self.buckets:
            if isinstance(b, NumericBucket):
                out.append(b)
            elif isinstance(b, dict):
                out.append(NumericBucket.model_validate(b))
        return out

    def extract_field(self, persona: dict[str, Any]) -> Any:
        """persona_fields 우선순위로 값 추출."""
        if not isinstance(persona, dict):
            return None
        for field in self.persona_fields:
            if field in persona and persona[field] not in (None, ""):
                return persona[field]
        return None


class PersonaAxisRegistry(BaseModel):
    model_config = ConfigDict(extra="allow")

    axes: list[PersonaAxis]

    def get(self, axis_id: str) -> Optional[PersonaAxis]:
        for ax in self.axes:
            if ax.axis_id == axis_id:
                return ax
        return None


def load_persona_axes(path: Path | str | None = None) -> PersonaAxisRegistry:
    p = Path(path) if path is not None else DEFAULT_REGISTRY_PATH
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return PersonaAxisRegistry.model_validate(data)


__all__ = [
    "DEFAULT_REGISTRY_PATH",
    "NumericBucket",
    "PersonaAxis",
    "PersonaAxisRegistry",
    "load_persona_axes",
]
