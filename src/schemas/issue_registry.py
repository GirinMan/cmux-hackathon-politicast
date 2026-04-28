"""IssueRegistry — `_workspace/data/registries/issues.json` 미러.

5 region 시나리오 issues[] 의 합집합 + alias. EntityResolver 의 rule 단계가
issue_id 정규화에 사용한다.
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Iterable, Optional

from pydantic import BaseModel, ConfigDict, Field


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = (
    REPO_ROOT / "_workspace" / "data" / "registries" / "issues.json"
)


def _normalize(s: str) -> str:
    if not isinstance(s, str):
        return ""
    n = unicodedata.normalize("NFKC", s).lower()
    return "".join(ch for ch in n if not ch.isspace())


class IssueEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    type: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)

    def all_names(self) -> list[str]:
        out = [self.name, self.id] + list(self.aliases)
        return [n for n in out if n]


class IssueRegistry(BaseModel):
    model_config = ConfigDict(extra="allow")

    version: str = "v1"
    issues: list[IssueEntry] = Field(default_factory=list)

    def find_by_id(self, issue_id: str) -> Optional[IssueEntry]:
        for e in self.issues:
            if e.id == issue_id:
                return e
        return None

    def resolve(self, text: str) -> Optional[IssueEntry]:
        """Longest-alias substring match (NFKC + lowercase + whitespace strip)."""
        if not text:
            return None
        norm = _normalize(text)
        best: tuple[int, Optional[IssueEntry]] = (0, None)
        for entry in self.issues:
            for name in entry.all_names():
                key = _normalize(name)
                if not key:
                    continue
                if key in norm and len(key) > best[0]:
                    best = (len(key), entry)
        return best[1]

    def all_keys(self) -> Iterable[str]:
        for entry in self.issues:
            yield entry.id
            yield from entry.aliases


def load_issue_registry(path: Path | str | None = None) -> IssueRegistry:
    p = Path(path) if path is not None else DEFAULT_REGISTRY_PATH
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return IssueRegistry.model_validate(data)


__all__ = [
    "DEFAULT_REGISTRY_PATH",
    "IssueEntry",
    "IssueRegistry",
    "load_issue_registry",
]
