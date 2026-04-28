"""Ground truth — 공식 여론조사 + 선거 결과.

DuckDB 테이블 official_poll, election_result 의 row shape 와 Python 측
표현. src/data/ground_truth.py 의 loader 가 SELECT 결과를 이 모델로 감싼다.

스키마 출처:
- official_poll: NESDC 등록 여론조사 + 시나리오 raw_polls 의 큐레이션 묶음.
- election_result: 선관위 공식 개표 결과 (선거일 후 채워짐).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class OfficialPollSnapshot(BaseModel):
    """official_poll 테이블 row — 단일 (region, as_of_date, pollster, candidate)."""

    model_config = ConfigDict(extra="forbid")

    region_id: str
    contest_id: str
    as_of_date: str  # ISO date
    pollster: str
    mode: str = "phone"
    n: int = 0
    candidate_id: str
    share: float
    source_url: Optional[str] = None
    ingested_at: Optional[str] = None


class ElectionResult(BaseModel):
    """election_result 테이블 row — 선거일 확정 개표 결과."""

    model_config = ConfigDict(extra="forbid")

    region_id: str
    contest_id: str
    election_date: str  # ISO date
    candidate_id: str
    vote_share: float
    votes: Optional[int] = None
    turnout: Optional[float] = None
    is_winner: bool = False
    source_url: Optional[str] = None
    ingested_at: Optional[str] = None
