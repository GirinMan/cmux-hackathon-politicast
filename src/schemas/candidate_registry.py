"""CandidateRegistry — `_workspace/data/registries/candidates.json` 미러.

5 region × 후보 alias 시드. EntityResolver 가 rule 단계에서 본 registry 를
import 해 한국어 이름 / 한자 / 영문 표기 / 공백 변형 alias 로 1:1 매핑한다.

KG builder 도 후보 노드 생성 시 alias 를 합쳐 noisy news 본문 매칭이 가능하다.
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Iterable, Optional

from pydantic import BaseModel, ConfigDict, Field


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = (
    REPO_ROOT / "_workspace" / "data" / "registries" / "candidates.json"
)


class CandidateEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    party_id: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)

    def all_names(self) -> list[str]:
        out = [self.name] + list(self.aliases)
        return [n for n in out if n]


class CandidateRegistry(BaseModel):
    """`candidates.json` 의 root."""

    model_config = ConfigDict(extra="allow")

    version: str = "v1"
    regions: dict[str, list[CandidateEntry]] = Field(default_factory=dict)

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------
    def for_region(self, region_id: str) -> list[CandidateEntry]:
        return list(self.regions.get(region_id, []))

    def all_entries(self) -> Iterable[tuple[str, CandidateEntry]]:
        for region_id, entries in self.regions.items():
            for entry in entries:
                yield region_id, entry

    def find_by_id(self, candidate_id: str) -> Optional[CandidateEntry]:
        for _, entry in self.all_entries():
            if entry.id == candidate_id:
                return entry
        return None

    def resolve(
        self,
        text: str,
        region_id: Optional[str] = None,
    ) -> Optional[CandidateEntry]:
        """이름/alias 부분일치로 후보 찾기. region_id 지정 시 그 region 안에서만.

        텍스트는 NFKC 정규화 + lowercase + whitespace 제거하여 alias 와 비교.
        가장 긴 alias 매치를 우선 (한자/영문/한글 변형 충돌 방지).
        """
        if not text:
            return None
        norm_text = _normalize(text)
        scope = (
            self.for_region(region_id)
            if region_id is not None
            else [e for _, e in self.all_entries()]
        )
        best: tuple[int, Optional[CandidateEntry]] = (0, None)
        for entry in scope:
            for name in entry.all_names():
                key = _normalize(name)
                if not key:
                    continue
                if key in norm_text and len(key) > best[0]:
                    best = (len(key), entry)
        return best[1]


def _normalize(s: str) -> str:
    if not isinstance(s, str):
        return ""
    n = unicodedata.normalize("NFKC", s).lower()
    return "".join(ch for ch in n if not ch.isspace())


def load_candidate_registry(path: Path | str | None = None) -> CandidateRegistry:
    p = Path(path) if path is not None else DEFAULT_REGISTRY_PATH
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return CandidateRegistry.model_validate(data)


__all__ = [
    "CandidateEntry",
    "CandidateRegistry",
    "DEFAULT_REGISTRY_PATH",
    "load_candidate_registry",
]
