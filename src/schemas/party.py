"""Party registry — `_workspace/data/registries/parties.json` 미러.

election_env.py 의 `_PARTY_LABEL_OVERRIDES` 16개 dict 를 외화한 SoT.
정당(kind="party") 뿐 아니라 응답 버킷(kind="bucket": etc/undecided/no_response)
도 통일 매핑한다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

from pydantic import BaseModel, ConfigDict, Field


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = (
    REPO_ROOT / "_workspace" / "data" / "registries" / "parties.json"
)


class PartyEntry(BaseModel):
    """단일 정당/버킷 항목."""

    model_config = ConfigDict(extra="allow")

    id: str
    display_name: str
    aliases: list[str] = Field(default_factory=list)
    kind: str = "party"  # "party" | "bucket"


class PartyRegistry(BaseModel):
    """`parties.json` 의 단일 진입점."""

    model_config = ConfigDict(extra="allow")

    parties: list[PartyEntry]

    def label_for(self, key: str) -> Optional[str]:
        """``id`` 또는 alias 로 display_name 조회. 없으면 ``None``."""
        if not key:
            return None
        k = str(key)
        for entry in self.parties:
            if entry.id == k or k in entry.aliases:
                return entry.display_name
        return None

    def all_keys(self) -> Iterable[str]:
        for entry in self.parties:
            yield entry.id
            yield from entry.aliases


def load_party_registry(path: Path | str | None = None) -> PartyRegistry:
    p = Path(path) if path is not None else DEFAULT_REGISTRY_PATH
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return PartyRegistry.model_validate(data)


__all__ = [
    "DEFAULT_REGISTRY_PATH",
    "PartyEntry",
    "PartyRegistry",
    "load_party_registry",
]
