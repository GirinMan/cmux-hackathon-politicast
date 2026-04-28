"""ElectionCalendar registry — 5 region 스키마 + 인터페이스 테스트."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from src.schemas.calendar import (
    DEFAULT_REGISTRY_PATH,
    ElectionCalendar,
    ElectionWindow,
    load_election_calendar,
)

EXPECTED_REGIONS = (
    "seoul_mayor",
    "busan_buk_gap",
    "daegu_mayor",
    "gwangju_mayor",
    "daegu_dalseo_gap",
)


def test_default_registry_loads_5_regions() -> None:
    cal = load_election_calendar()
    assert isinstance(cal, ElectionCalendar)
    for r in EXPECTED_REGIONS:
        w = cal.get(r)
        assert w.election_date == dt.date(2026, 6, 3)
        assert w.timezone == "Asia/Seoul"


def test_blackout_window() -> None:
    cal = load_election_calendar()
    w = cal.get("seoul_mayor")
    assert w.blackout_start == dt.date(2026, 5, 28)
    assert w.blackout_end == dt.date(2026, 6, 3)
    assert w.in_blackout(dt.date(2026, 5, 30)) is True
    assert w.in_blackout(dt.date(2026, 5, 27)) is False
    assert w.in_blackout(dt.date(2026, 6, 3)) is True


def test_cutoff_for_returns_election_minus_1d() -> None:
    cal = load_election_calendar()
    assert cal.cutoff_for("seoul_mayor") == dt.date(2026, 6, 2)


def test_unknown_region_raises_keyerror() -> None:
    cal = load_election_calendar()
    with pytest.raises(KeyError):
        cal.get("does_not_exist")


def test_extra_fields_forbidden() -> None:
    with pytest.raises(Exception):
        ElectionWindow(
            region_id="x",
            election_id="x",
            election_date="2026-06-03",
            position_type="mayor",
            unknown="x",  # type: ignore[call-arg]
        )


def test_blackout_order_validated() -> None:
    with pytest.raises(Exception):
        ElectionWindow(
            region_id="x",
            election_id="x",
            election_date="2026-06-03",
            position_type="mayor",
            blackout_start="2026-06-03",
            blackout_end="2026-05-28",
        )


def test_default_registry_path_exists() -> None:
    assert DEFAULT_REGISTRY_PATH.exists(), DEFAULT_REGISTRY_PATH
