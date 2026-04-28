"""make_split(region_id) — Phase 6 rolling-origin 데이터 split.

5 region 모두 election_calendar.json 의 windows 를 기반으로 4 윈도우를
도출한다. 서울만 train_2022 (제8회 지방선거 historical) 가 채워지고
나머지 region 은 None 이다.

| Window | 기간 | 용도 |
|---|---|---|
| train_2022 | 2022-01-01 ~ 2022-05-31 | Stage 1/2 calibration (서울만) |
| train_rolling_2026 | 2026-04-01 ~ election_date - 7d | Pre-election polls |
| validation_holdout | train_rolling_2026 의 last 7 days | Hidden poll labels |
| test_2026 | election_date | Post-hoc retrodiction |
"""
from __future__ import annotations

import datetime as dt

from src.schemas.calendar import (
    ElectionCalendar,
    ElectionWindow,
    load_election_calendar,
)
from src.schemas.temporal_split import TemporalSplit
from src.schemas.validation_report import TimeWindow

HOLDOUT_DAYS = 7
ROLLING_START_DEFAULT = dt.date(2026, 4, 1)
TRAIN_2022_START = dt.date(2022, 1, 1)
TRAIN_2022_END = dt.date(2022, 5, 31)

# 서울만 2022년 6월 1일 제8회 전국동시지방선거 historical 활용 가능.
REGIONS_WITH_2022_HISTORICAL = frozenset({"seoul_mayor"})


def _rolling_start(window: ElectionWindow) -> dt.date:
    """Rolling train start = max(fieldwork_start, ROLLING_START_DEFAULT).

    fieldwork_start 가 ROLLING_START_DEFAULT 보다 빠른 보궐(busan/dalseo) 의
    경우 4월 1일 default 를 적용해 구간을 통일한다. 단 election_calendar 가
    더 늦은 fieldwork_start 를 박아두면 그것을 따른다.
    """
    if window.fieldwork_start and window.fieldwork_start > ROLLING_START_DEFAULT:
        return window.fieldwork_start
    return ROLLING_START_DEFAULT


def make_split(
    region_id: str,
    *,
    calendar: ElectionCalendar | None = None,
    holdout_days: int = HOLDOUT_DAYS,
) -> TemporalSplit:
    """Region 1개 → TemporalSplit (election_calendar 검증 통과)."""
    cal = calendar or load_election_calendar()
    win = cal.get(region_id)
    election_date = win.election_date

    rolling_start = _rolling_start(win)
    rolling_end = election_date - dt.timedelta(days=1)
    if rolling_end < rolling_start:
        raise ValueError(
            f"region={region_id}: election_date {election_date} - 1d < rolling_start {rolling_start}"
        )

    holdout_start = rolling_end - dt.timedelta(days=holdout_days - 1)
    if holdout_start < rolling_start:
        raise ValueError(
            f"region={region_id}: rolling window 너무 짧음 — "
            f"holdout_days={holdout_days} 가 rolling [{rolling_start}, {rolling_end}] 안에 들어가지 않음"
        )

    train_rolling = TimeWindow(
        name="train_rolling_2026", start=rolling_start, end=rolling_end
    )
    holdout = TimeWindow(
        name="validation_holdout", start=holdout_start, end=rolling_end
    )
    test_2026 = TimeWindow(
        name="test_2026", start=election_date, end=election_date
    )
    train_2022 = (
        TimeWindow(name="train_2022", start=TRAIN_2022_START, end=TRAIN_2022_END)
        if region_id in REGIONS_WITH_2022_HISTORICAL
        else None
    )

    return TemporalSplit(
        region_id=region_id,
        election_date=election_date,
        train_2022=train_2022,
        train_rolling_2026=train_rolling,
        validation_holdout=holdout,
        test_2026=test_2026,
        notes=f"holdout_days={holdout_days}; rolling_start_default={ROLLING_START_DEFAULT}",
    )


def make_all_splits(
    *,
    calendar: ElectionCalendar | None = None,
    holdout_days: int = HOLDOUT_DAYS,
) -> dict[str, TemporalSplit]:
    """5 region 전부."""
    cal = calendar or load_election_calendar()
    return {
        rid: make_split(rid, calendar=cal, holdout_days=holdout_days)
        for rid in cal.windows.keys()
    }


__all__ = [
    "HOLDOUT_DAYS",
    "ROLLING_START_DEFAULT",
    "REGIONS_WITH_2022_HISTORICAL",
    "make_split",
    "make_all_splits",
]
