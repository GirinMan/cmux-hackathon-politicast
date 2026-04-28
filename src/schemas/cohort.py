"""Age bucket registry — `_workspace/data/registries/age_buckets.json` 미러.

election_env.py 의 `_age_group` 하드코딩을 외화. 반열림 구간 [min, max) 사용
(max=None = 무제한). 비교(`<`)로 매칭. dashboard/논문에서 동일 라벨을 공유한다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = (
    REPO_ROOT / "_workspace" / "data" / "registries" / "age_buckets.json"
)


class AgeBucket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    min: Optional[int] = None
    max: Optional[int] = None  # exclusive upper bound; None = 무제한

    def contains(self, age: int) -> bool:
        if self.min is not None and age < self.min:
            return False
        if self.max is not None and age >= self.max:
            return False
        return True


class AgeBuckets(BaseModel):
    model_config = ConfigDict(extra="allow")

    buckets: list[AgeBucket]
    unknown_label: str = "unknown"

    def bucket_for(self, age: Any) -> str:
        try:
            a = int(age)
        except (TypeError, ValueError):
            return self.unknown_label
        for bucket in self.buckets:
            if bucket.contains(a):
                return bucket.label
        return self.unknown_label

    def labels(self) -> list[str]:
        return [b.label for b in self.buckets]


def load_age_buckets(path: Path | str | None = None) -> AgeBuckets:
    p = Path(path) if path is not None else DEFAULT_REGISTRY_PATH
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return AgeBuckets.model_validate(data)


# Process-wide singleton — election_env / dashboard 에서 import.
DEFAULT_AGE_BUCKETS: AgeBuckets = (
    load_age_buckets() if DEFAULT_REGISTRY_PATH.exists() else AgeBuckets(
        buckets=[
            AgeBucket(label="20s", min=0, max=30),
            AgeBucket(label="30s", min=30, max=40),
            AgeBucket(label="40s", min=40, max=50),
            AgeBucket(label="50s", min=50, max=60),
            AgeBucket(label="60s+", min=60, max=None),
        ]
    )
)


__all__ = [
    "AgeBucket",
    "AgeBuckets",
    "DEFAULT_AGE_BUCKETS",
    "DEFAULT_REGISTRY_PATH",
    "load_age_buckets",
]
