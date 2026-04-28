"""Region service — ElectionCalendar SoT 위에 얇은 매핑."""
from __future__ import annotations

import datetime as dt
import logging
from typing import Optional

from src.schemas.calendar import ElectionWindow, load_election_calendar

from ..schemas.public_dto import RegionDTO, RegionSummaryDTO

logger = logging.getLogger("backend.region")

_REGION_LABELS: dict[str, str] = {
    "seoul_mayor": "서울특별시장",
    "busan_buk_gap": "부산 북구갑 보궐",
    "daegu_mayor": "대구광역시장",
    "gwangju_mayor": "광주광역시장",
    "daegu_dalseo_gap": "대구 달서갑 보궐",
}


class RegionService:
    def list_regions(self, today: Optional[dt.date] = None) -> list[RegionDTO]:
        cal = load_election_calendar()
        today = today or dt.date.today()
        out: list[RegionDTO] = []
        for region_id, win in sorted(cal.windows.items()):
            out.append(self._to_dto(region_id, win, today))
        return out

    def get_region(self, region_id: str, today: Optional[dt.date] = None) -> RegionDTO:
        cal = load_election_calendar()
        win = cal.get(region_id)  # KeyError → router 가 404 변환
        today = today or dt.date.today()
        return self._to_dto(region_id, win, today)

    def get_summary(self, region_id: str) -> RegionSummaryDTO:
        # 실 persona/district count 는 db-postgres rewrite 가 끝나면 src.data.queries
        # 통해 채울 예정. 지금은 placeholder 0.
        # KeyError → 404
        load_election_calendar().get(region_id)
        return RegionSummaryDTO(region_id=region_id)

    # ---- internal ----
    def _to_dto(
        self, region_id: str, win: ElectionWindow, today: dt.date
    ) -> RegionDTO:
        return RegionDTO(
            region_id=region_id,
            name=_REGION_LABELS.get(region_id, region_id),
            election_id=win.election_id,
            election_date=win.election_date.isoformat(),
            position_type=win.position_type,
            timezone=win.timezone,
            in_blackout=win.in_blackout(today),
        )


region_service = RegionService()

__all__ = ["region_service", "RegionService"]
