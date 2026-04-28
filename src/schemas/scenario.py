"""시나리오 시드 JSON 스키마 (_workspace/data/scenarios/*.json).

5 region 시나리오 파일을 모두 로드 가능해야 하므로 옵셔널 필드가 많다.
실측 시나리오들은 `id`/`candidate_id` 같은 이중 표기, `polls`/`raw_polls`
양립 등 alias 가 있다 — populate_by_name + alias 로 흡수한다.

`extra="allow"` 로 시나리오별 metadata (gov_approval, scenario_notes,
counterfactual 등) 도 보존한다.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class Election(BaseModel):
    model_config = ConfigDict(extra="allow")

    election_id: str
    name: Optional[str] = None
    date: Optional[str] = None  # ISO date — 자유 형식 허용
    type: Optional[str] = None


class Contest(BaseModel):
    model_config = ConfigDict(extra="allow")

    contest_id: str
    position_type: Optional[str] = None
    election_id: Optional[str] = None
    region_id: Optional[str] = None


class District(BaseModel):
    model_config = ConfigDict(extra="allow")

    province: Optional[str] = None
    district: Optional[str] = None
    population: Optional[int] = None


class Party(BaseModel):
    model_config = ConfigDict(extra="allow")

    party_id: str
    name: Optional[str] = None
    ideology: float = 0.0


class Candidate(BaseModel):
    """시나리오 후보. `id` 와 `candidate_id` 둘 다 받는다."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str = Field(validation_alias="id")
    candidate_id: Optional[str] = None
    name: str
    party: Optional[str] = None  # party_id
    party_name: Optional[str] = None
    withdrawn: bool = False
    background: Optional[str] = None
    key_pledges: list[str] = Field(default_factory=list)


class Issue(BaseModel):
    model_config = ConfigDict(extra="allow")

    issue_id: str
    name: str
    type: str = "기타"


class NarrativeFrame(BaseModel):
    model_config = ConfigDict(extra="allow")

    frame_id: str
    label: str


class SeedEvent(BaseModel):
    """ElectionEnv._build_context 가 timestep≤t 필터링에 사용하는 정형 이벤트."""

    model_config = ConfigDict(extra="allow")

    timestep: int = 0
    type: str = "event"
    target: Optional[str] = None
    polarity: float = 0.0
    summary: str = ""


class SimulationWindow(BaseModel):
    model_config = ConfigDict(extra="allow")

    t_start: Optional[str] = None
    t_end: Optional[str] = None
    timesteps: Optional[int] = None


class Scenario(BaseModel):
    """시나리오 시드 — _workspace/data/scenarios/{region_id}.json 의 root."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    schema_version: str = "v1"
    scenario_id: str
    region_id: str
    contest_id: str
    label: Optional[str] = None
    gov_approval: Optional[float] = None

    election: Optional[Election] = None
    contest: Optional[Contest] = None
    district: Optional[District] = None

    parties: list[Party] = Field(default_factory=list)
    candidates: list[Candidate] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    frames: list[NarrativeFrame] = Field(default_factory=list)

    # 자유형 이벤트 (KG ingestion source) — 스키마 강제 안 함
    events: list[dict[str, Any]] = Field(default_factory=list)

    # 정형 시뮬 입력
    seed_events: list[SeedEvent] = Field(default_factory=list)

    # 폴 데이터 (양식 두 가지 공존)
    polls: list[dict[str, Any]] = Field(default_factory=list)
    raw_polls: list[dict[str, Any]] = Field(default_factory=list)

    simulation: Optional[SimulationWindow] = None

    election_date: Optional[str] = None
    scenario_notes: Optional[str] = None
