"""make_split — 5 region rolling-origin window 회귀 테스트."""
from __future__ import annotations

import datetime as dt

import pytest

from src.data.temporal_split import (
    HOLDOUT_DAYS,
    REGIONS_WITH_2022_HISTORICAL,
    make_all_splits,
    make_split,
)
from src.schemas.calendar import load_election_calendar


EXPECTED_REGIONS = (
    "seoul_mayor",
    "busan_buk_gap",
    "daegu_mayor",
    "gwangju_mayor",
    "daegu_dalseo_gap",
)


@pytest.mark.parametrize("region_id", EXPECTED_REGIONS)
def test_make_split_basic(region_id: str) -> None:
    split = make_split(region_id)
    assert split.region_id == region_id
    cal = load_election_calendar()
    assert split.election_date == cal.election_date_for(region_id)
    # holdout 은 정확히 last 7 days
    holdout = split.validation_holdout
    rolling = split.train_rolling_2026
    assert holdout.end == rolling.end
    assert (holdout.end - holdout.start).days == HOLDOUT_DAYS - 1
    # rolling.end < election_date (학습은 선거 전까지)
    assert rolling.end < split.election_date
    # test_2026 는 선거일 1일짜리
    assert split.test_2026.start == split.test_2026.end == split.election_date


def test_train_2022_only_for_seoul() -> None:
    splits = make_all_splits()
    for rid, s in splits.items():
        if rid in REGIONS_WITH_2022_HISTORICAL:
            assert s.train_2022 is not None
            assert s.train_2022.start.year == 2022
        else:
            assert s.train_2022 is None


def test_seoul_window_concrete_values() -> None:
    s = make_split("seoul_mayor")
    assert s.election_date == dt.date(2026, 6, 3)
    assert s.train_rolling_2026.start == dt.date(2026, 4, 19)  # fieldwork_start
    assert s.train_rolling_2026.end == dt.date(2026, 6, 2)
    assert s.validation_holdout.start == dt.date(2026, 5, 27)
    assert s.validation_holdout.end == dt.date(2026, 6, 2)


def test_busan_uses_rolling_start_default_when_fieldwork_earlier() -> None:
    # busan_buk_gap fieldwork_start = 2026-04-01 == ROLLING_START_DEFAULT
    s = make_split("busan_buk_gap")
    assert s.train_rolling_2026.start == dt.date(2026, 4, 1)


def test_unknown_region_raises() -> None:
    with pytest.raises(KeyError):
        make_split("does_not_exist")


def test_holdout_too_long_raises() -> None:
    with pytest.raises(ValueError):
        make_split("seoul_mayor", holdout_days=999)
