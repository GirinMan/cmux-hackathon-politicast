"""Timezone helpers — region 별 tz 결정.

PolitiKAST 는 현재 한국 5 region 만 다루므로 기본값은 KST(+09:00). 향후
다국가 확장 시 ElectionCalendar.window.timezone 을 우선 사용한다.

이 모듈은 인라인 `dt.timezone(dt.timedelta(hours=9))` 사용을 한 곳으로
모은다 — 회귀 추적과 lint 게이트가 단일 위치를 가리키도록.
"""
from __future__ import annotations

import datetime as dt

# IANA 명 → fixed offset 매핑 (zoneinfo 의존 회피, 한국 외 고정 ±09:00 만 사용)
_TZ_OFFSETS: dict[str, dt.timezone] = {
    "Asia/Seoul": dt.timezone(dt.timedelta(hours=9), name="KST"),
    "KST": dt.timezone(dt.timedelta(hours=9), name="KST"),
    "UTC": dt.timezone.utc,
}

KST = _TZ_OFFSETS["Asia/Seoul"]
"""Korea Standard Time, +09:00. Sentinel singleton for legacy callers."""


def get_timezone(region_id: str | None = None, *, tz_name: str | None = None) -> dt.timezone:
    """region_id 또는 IANA tz 이름으로 tzinfo 결정.

    - 명시 ``tz_name`` 우선
    - 없으면 region_id 가 한국 region(`seoul_*`, `busan_*`, `daegu_*`, `gwangju_*`,
      `incheon_*`, `gyeonggi_*`, `kr_*`) 이면 KST
    - 그 외엔 KST 기본 (현재 데이터셋이 모두 한국)
    """
    if tz_name:
        return _TZ_OFFSETS.get(tz_name, KST)
    if region_id is None:
        return KST
    rid = region_id.lower()
    if rid.startswith(("seoul", "busan", "daegu", "gwangju", "incheon",
                       "gyeonggi", "ulsan", "jeju", "kr_", "korea")):
        return KST
    return KST


def now_kst() -> dt.datetime:
    """Current wall-clock in KST (replaces ad-hoc `dt.datetime.now(kst)`)."""
    return dt.datetime.now(KST)


__all__ = ["KST", "get_timezone", "now_kst"]
