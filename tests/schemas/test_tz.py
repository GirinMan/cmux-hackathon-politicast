"""src/utils/tz — KST 헬퍼 단위 테스트."""
from __future__ import annotations

import datetime as dt

from src.utils.tz import KST, get_timezone, now_kst


def test_kst_offset_is_plus_9() -> None:
    assert KST.utcoffset(None) == dt.timedelta(hours=9)


def test_get_timezone_korean_regions_returns_kst() -> None:
    for r in ("seoul_mayor", "busan_buk_gap", "daegu_mayor",
              "gwangju_mayor", "incheon_x", "korea_x"):
        assert get_timezone(r) == KST


def test_get_timezone_explicit_name_overrides() -> None:
    assert get_timezone(tz_name="UTC") == dt.timezone.utc
    assert get_timezone("seoul_mayor", tz_name="Asia/Seoul") == KST


def test_now_kst_has_kst_tzinfo() -> None:
    n = now_kst()
    assert n.tzinfo is not None
    assert n.utcoffset() == dt.timedelta(hours=9)
