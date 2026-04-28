"""Blackout policy — ElectionCalendar.in_blackout 위에 얇은 정책 레이어.

- POLITIKAST_BLACKOUT_HIDE_AI=1 (default): blackout 기간엔 AI 차트(시뮬 outcome,
  poll trajectory, prediction trajectory) 응답이 빈 list + blackout=true 메타.
- 0: 메타만 표시하고 데이터는 그대로 노출.

페르소나, KG, 댓글, 게시판은 항상 노출 — 정책 영향 없음.
"""
from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass
from typing import Optional

from src.schemas.calendar import ElectionWindow, load_election_calendar


@dataclass
class BlackoutMeta:
    in_blackout: bool
    end_date: Optional[str] = None  # ISO date | None
    hides_ai: bool = True
    region_id: Optional[str] = None


def _hides_ai_default() -> bool:
    raw = os.environ.get("POLITIKAST_BLACKOUT_HIDE_AI", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def get_status(region_id: str, today: Optional[dt.date] = None) -> BlackoutMeta:
    """region_id 의 blackout 상태. 미등록 region 은 in_blackout=False."""
    today = today or dt.date.today()
    try:
        cal = load_election_calendar()
        window: ElectionWindow = cal.get(region_id)
    except (FileNotFoundError, KeyError):
        return BlackoutMeta(
            in_blackout=False, hides_ai=_hides_ai_default(), region_id=region_id
        )
    return BlackoutMeta(
        in_blackout=window.in_blackout(today),
        end_date=window.blackout_end.isoformat() if window.blackout_end else None,
        hides_ai=_hides_ai_default(),
        region_id=region_id,
    )


def should_hide_ai(meta: BlackoutMeta) -> bool:
    return bool(meta.in_blackout and meta.hides_ai)


__all__ = ["BlackoutMeta", "get_status", "should_hide_ai"]
