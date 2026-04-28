"""KG 노드/엣지 Pydantic 미러.

src/kg/ontology.py 의 dataclass 정의를 그대로 Pydantic 으로 거울 미러링한다.
KG 빌더는 기존 dataclass 를 계속 사용해도 되며 (호환), 외부 도구나 JSON
직렬화/검증 경로에서는 본 모듈을 import 한다.

엣지 라벨 상수는 단일 출처를 위해 여기에 박제한다.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Edge label 상수
# ---------------------------------------------------------------------------
EDGE_LABELS: tuple[str, ...] = (
    "candidateIn",
    "belongsTo",
    "heldIn",
    "inElection",
    "about",
    "mentions",
    "promotes",
    "framedBy",
    "publishesPoll",
    "attributedTo",
)

EVENT_NODE_TYPES: frozenset[str] = frozenset(
    {
        "MediaEvent",
        "ScandalEvent",
        "Investigation",
        "Verdict",
        "PressConference",
        "PollPublication",
    }
)
ACTOR_NODE_TYPES: frozenset[str] = frozenset({"Person", "Source"})
PRIOR_NODE_TYPES: frozenset[str] = frozenset({"CohortPrior"})


# ---------------------------------------------------------------------------
# Election ontology
# ---------------------------------------------------------------------------
class Election(BaseModel):
    model_config = ConfigDict(extra="allow")

    election_id: str
    name: str
    date: str  # ISO datetime
    type: str
    type_node: Literal["Election"] = Field(default="Election", alias="_node_type")


class Contest(BaseModel):
    model_config = ConfigDict(extra="allow")

    contest_id: str
    election_id: str
    region_id: str
    position_type: str


class District(BaseModel):
    model_config = ConfigDict(extra="allow")

    region_id: str
    province: str
    district: Optional[str] = None
    population: Optional[int] = None


class Party(BaseModel):
    model_config = ConfigDict(extra="allow")

    party_id: str
    name: str
    ideology: float = 0.0


class Candidate(BaseModel):
    model_config = ConfigDict(extra="allow")

    candidate_id: str
    contest_id: str
    name: str
    party: str
    withdrawn: bool = False


# ---------------------------------------------------------------------------
# Event/Discourse
# ---------------------------------------------------------------------------
class PolicyIssue(BaseModel):
    model_config = ConfigDict(extra="allow")

    issue_id: str
    name: str
    type: str = "기타"


class NarrativeFrame(BaseModel):
    model_config = ConfigDict(extra="allow")

    frame_id: str
    label: str


class MediaEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_id: str
    ts: str  # ISO datetime — firewall 의 cutoff 비교 기준
    source: str
    title: str
    sentiment: float = 0.0
    frame_id: Optional[str] = None
    type: str = "MediaEvent"
    about: list[str] = Field(default_factory=list)
    mentions: list[str] = Field(default_factory=list)


class ScandalEvent(MediaEvent):
    severity: float = 0.5
    target_candidate_id: Optional[str] = None
    credibility: float = 0.5
    type: str = "ScandalEvent"


class Investigation(MediaEvent):
    target_candidate_id: Optional[str] = None
    stage: Literal["allegation", "probe", "indictment", "trial"] = "allegation"
    type: str = "Investigation"


class Verdict(MediaEvent):
    target_candidate_id: Optional[str] = None
    outcome: Literal["acquittal", "conviction", "appeal"] = "acquittal"
    type: str = "Verdict"


class PressConference(MediaEvent):
    speaker: Optional[str] = None
    party_id: Optional[str] = None
    type: str = "PressConference"


class PollPublication(BaseModel):
    model_config = ConfigDict(extra="allow")

    poll_id: int
    ts: str
    contest_id: str
    sample_size: Optional[int] = None
    leader_candidate: Optional[str] = None
    leader_share: Optional[float] = None
    type: str = "PollPublication"


# ---------------------------------------------------------------------------
# P2/P3 enrichment
# ---------------------------------------------------------------------------
class Person(BaseModel):
    model_config = ConfigDict(extra="allow")

    person_id: str
    name: str
    role: str = ""
    party_id: Optional[str] = None
    type: str = "Person"


class Source(BaseModel):
    model_config = ConfigDict(extra="allow")

    source_id: str
    name: str
    url_root: str = ""
    media_type: str = "newspaper"
    ideology: float = 0.0
    type: str = "Source"


class CohortPrior(BaseModel):
    model_config = ConfigDict(extra="allow")

    cohort_id: str
    age_band: str
    gender: str
    scope: str
    party_lean: dict[str, float] = Field(default_factory=dict)
    region_id: Optional[str] = None
    n_polls: int = 0
    sample_size: int = 0
    source: str = ""
    source_url: str = ""
    publish_ts: Optional[str] = None
    notes: str = ""
    type: str = "CohortPrior"
