"""ElectionCalendar — 5 region 선거 일정의 단일 진실의 소스.

`_workspace/data/registries/election_calendar.json` 에서 로드하며, 시뮬·KG·
검증 layer 모두 본 모델만 보고 election_date / fieldwork window / blackout
period / timezone 을 결정한다. 인라인 `'2026-06-03'` 하드코딩 제거의 SoT.
"""
from __future__ import annotations

import datetime as dt
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = REPO_ROOT / "_workspace" / "data" / "registries" / "election_calendar.json"


class ElectionWindow(BaseModel):
    """단일 선거 (region_id) 의 일정.

    fieldwork_window 는 선거일 기준 며칠 전부터 여론조사 등록을 받는지의
    상한이다. blackout 은 NESDC 공표 금지 기간 (한국 공직선거법 §108).
    """

    model_config = ConfigDict(extra="forbid")

    region_id: str
    election_id: str
    election_date: dt.date
    position_type: str  # mayor | governor | gap_assembly | gap_local | ...
    timezone: str = "Asia/Seoul"

    fieldwork_start: Optional[dt.date] = None
    fieldwork_end: Optional[dt.date] = None
    blackout_start: Optional[dt.date] = None
    blackout_end: Optional[dt.date] = None

    @field_validator("election_date", "fieldwork_start", "fieldwork_end",
                     "blackout_start", "blackout_end", mode="before")
    @classmethod
    def _coerce_date(cls, v):
        if v is None or isinstance(v, dt.date):
            return v
        if isinstance(v, str):
            return dt.date.fromisoformat(v.split("T")[0])
        raise TypeError(f"unsupported date input: {v!r}")

    @field_validator("blackout_end")
    @classmethod
    def _blackout_order(cls, v, info):
        start = info.data.get("blackout_start")
        if v is not None and start is not None and v < start:
            raise ValueError("blackout_end must be ≥ blackout_start")
        return v

    @field_validator("fieldwork_end")
    @classmethod
    def _fieldwork_order(cls, v, info):
        start = info.data.get("fieldwork_start")
        if v is not None and start is not None and v < start:
            raise ValueError("fieldwork_end must be ≥ fieldwork_start")
        return v

    def in_blackout(self, d: dt.date) -> bool:
        if self.blackout_start is None or self.blackout_end is None:
            return False
        return self.blackout_start <= d <= self.blackout_end


class ElectionCalendar(BaseModel):
    """region_id → ElectionWindow registry."""

    model_config = ConfigDict(extra="forbid")

    version: str = "v1"
    description: str = ""
    windows: dict[str, ElectionWindow] = Field(default_factory=dict)

    def get(self, region_id: str) -> ElectionWindow:
        if region_id not in self.windows:
            raise KeyError(
                f"ElectionCalendar: region_id={region_id!r} 없음 — "
                f"_workspace/data/registries/election_calendar.json 에 등록 필요"
            )
        return self.windows[region_id]

    def election_date_for(self, region_id: str) -> dt.date:
        return self.get(region_id).election_date

    def cutoff_for(self, region_id: str) -> dt.date:
        """KG/시뮬레이션의 firewall 기본 cutoff = election_date - 1d.

        `kg-hardener` 가 의존하는 인터페이스. region 별로 다른 정책이 필요하면
        ElectionWindow 에 cutoff_offset_days 필드를 추가한다 (현재 미사용).
        """
        return self.get(region_id).election_date - dt.timedelta(days=1)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------
@lru_cache(maxsize=4)
def load_election_calendar(path: str | None = None) -> ElectionCalendar:
    """Cached registry loader."""
    p = Path(path) if path else DEFAULT_REGISTRY_PATH
    if not p.exists():
        raise FileNotFoundError(f"election_calendar registry missing: {p}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    return ElectionCalendar.model_validate(raw)


__all__ = [
    "ElectionWindow",
    "ElectionCalendar",
    "load_election_calendar",
    "DEFAULT_REGISTRY_PATH",
]
