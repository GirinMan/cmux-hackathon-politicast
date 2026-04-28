"""PersonRegistry — `_workspace/data/registries/persons.json` 미러.

비후보 정치인/공인 (현직 대통령, 야권 인사, 도지사 등). 시나리오 events[].mentions
및 KG Person 노드와 일치한다. 후보 본인은 candidates.json 사용.
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Iterable, Optional

from pydantic import BaseModel, ConfigDict, Field


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = (
    REPO_ROOT / "_workspace" / "data" / "registries" / "persons.json"
)


def _normalize(s: str) -> str:
    if not isinstance(s, str):
        return ""
    n = unicodedata.normalize("NFKC", s).lower()
    return "".join(ch for ch in n if not ch.isspace())


class PersonEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    role: Optional[str] = None
    party_id: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)

    def all_names(self) -> list[str]:
        out = [self.name, self.id] + list(self.aliases)
        return [n for n in out if n]


class PersonRegistry(BaseModel):
    model_config = ConfigDict(extra="allow")

    version: str = "v1"
    persons: list[PersonEntry] = Field(default_factory=list)

    def find_by_id(self, person_id: str) -> Optional[PersonEntry]:
        for e in self.persons:
            if e.id == person_id:
                return e
        return None

    def resolve(self, text: str) -> Optional[PersonEntry]:
        """Longest-alias substring match."""
        if not text:
            return None
        norm = _normalize(text)
        best: tuple[int, Optional[PersonEntry]] = (0, None)
        for entry in self.persons:
            for name in entry.all_names():
                key = _normalize(name)
                if not key:
                    continue
                if key in norm and len(key) > best[0]:
                    best = (len(key), entry)
        return best[1]

    def all_keys(self) -> Iterable[str]:
        for entry in self.persons:
            yield entry.id
            yield from entry.aliases


def load_person_registry(path: Path | str | None = None) -> PersonRegistry:
    p = Path(path) if path is not None else DEFAULT_REGISTRY_PATH
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return PersonRegistry.model_validate(data)


__all__ = [
    "DEFAULT_REGISTRY_PATH",
    "PersonEntry",
    "PersonRegistry",
    "load_person_registry",
]
