"""TemporalSplit — Phase 6 데이터 split 정의 (rolling-origin window).

5 region 각각에 대해 train_2022 / train_rolling_2026 / validation_holdout
/ test_2026 4 개의 시간 윈도우를 박제한다. `src/data/temporal_split.py`
::make_split(region_id) 가 election_calendar.json 과 충돌하지 않도록
Pydantic 검증으로 보장한다.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.schemas.validation_report import TimeWindow


class TemporalSplit(BaseModel):
    """region 1개의 4-window split."""

    model_config = ConfigDict(extra="forbid")

    region_id: str
    election_date: dt.date

    train_2022: Optional[TimeWindow] = None  # 2022 지방선거 historical (서울만)
    train_rolling_2026: TimeWindow
    validation_holdout: TimeWindow  # train_rolling_2026 의 last 7 days
    test_2026: TimeWindow  # 선거일 — 종료 후 retrodiction

    notes: str = ""

    @model_validator(mode="after")
    def _validate_windows(self) -> "TemporalSplit":
        # validation_holdout 은 train_rolling_2026 안에 들어와야 한다
        rolling = self.train_rolling_2026
        holdout = self.validation_holdout
        if not (rolling.start <= holdout.start and holdout.end <= rolling.end):
            raise ValueError(
                f"validation_holdout {holdout.start}..{holdout.end} must lie within "
                f"train_rolling_2026 {rolling.start}..{rolling.end}"
            )
        # test_2026 은 election_date 를 포함해야 한다
        if not self.test_2026.contains(self.election_date):
            raise ValueError(
                f"test_2026 {self.test_2026.start}..{self.test_2026.end} must "
                f"include election_date {self.election_date}"
            )
        # rolling 끝 ≤ election_date (학습은 선거 전까지만)
        if rolling.end > self.election_date:
            raise ValueError(
                f"train_rolling_2026.end {rolling.end} must be ≤ election_date {self.election_date}"
            )
        # train_2022 가 있으면 2022-01-01 ~ 2022-12-31 안에 들어와야 한다
        if self.train_2022 is not None:
            if not (dt.date(2022, 1, 1) <= self.train_2022.start
                    and self.train_2022.end <= dt.date(2022, 12, 31)):
                raise ValueError(
                    f"train_2022 must lie within 2022 calendar year, got "
                    f"{self.train_2022.start}..{self.train_2022.end}"
                )
        return self


__all__ = ["TemporalSplit"]
