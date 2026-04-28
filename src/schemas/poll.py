"""여론조사 스키마.

- RawPoll: 시나리오 raw_polls[] 또는 DuckDB raw_poll 테이블의 단일 row.
- PollConsensusDaily: aggregate_poll_response 가 아니라 외부 NESDC 등록 폴
  weighted aggregation (poll_consensus_daily). election_env._consensus_from_duckdb
  쿼리 결과 row 와 일치.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RawPoll(BaseModel):
    """단일 여론조사 row — 시나리오 raw_polls[] 의 한 항목."""

    model_config = ConfigDict(extra="allow")

    pollster: str
    mode: str = "phone"  # phone | online | mixed | ...
    n: int = 1000
    day: Optional[int] = None       # election - 30d 기준 offset (legacy)
    ts: Optional[str] = None        # ISO datetime (preferred)
    quality: float = 1.0
    shares: dict[str, float] = Field(default_factory=dict)  # candidate_id → share
    poll_id: Optional[str] = None


class PollConsensusDaily(BaseModel):
    """poll_consensus_daily 테이블 row — election_env._consensus_from_duckdb 출력."""

    model_config = ConfigDict(extra="allow")

    contest_id: str
    region_id: str
    as_of_date: str  # ISO date
    candidate_id: str
    p_hat: float
    var: Optional[float] = None
    method_version: str = "weighted_v1"
    source_poll_ids: list[str] = Field(default_factory=list)
