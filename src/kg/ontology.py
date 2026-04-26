"""Election + Event/Discourse 온톨로지 (dataclass, no OWL).

KG 노드는 이 dataclass 인스턴스의 ``__dict__``를 attribute로 직렬화하여 저장.
``node_id``는 ``f"{type}:{id_field}"`` 컨벤션 (e.g., ``"Candidate:c_kim"``).

builder.py 가 이 클래스를 networkx MultiDiGraph 노드/엣지로 변환한다.
retriever.py 는 노드 attribute의 ``type`` 필드로 분기 처리.

엣지 라벨 (relation):
  candidateIn   : Candidate → Contest
  belongsTo     : Candidate → Party
  heldIn        : Contest   → District
  inElection    : Contest   → Election
  about         : Event     → Candidate | Party
  mentions      : Event     → PolicyIssue
  promotes      : Party     → NarrativeFrame
  framedBy      : Event     → NarrativeFrame
  publishesPoll : PollPublication → Contest
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional


# ---------------------------------------------------------------------------
# Election ontology
# ---------------------------------------------------------------------------
@dataclass
class Election:
    election_id: str
    name: str
    date: datetime
    type: str  # "local" | "general" | "presidential" | "by_election"


@dataclass
class Contest:
    contest_id: str
    election_id: str
    region_id: str
    position_type: str  # "metropolitan_mayor" | "basic_mayor" | "national_assembly_by_election"


@dataclass
class District:
    region_id: str
    province: str
    district: Optional[str] = None
    population: Optional[int] = None


@dataclass
class Party:
    party_id: str
    name: str
    ideology: float = 0.0  # -1 progressive ↔ +1 conservative


@dataclass
class Candidate:
    candidate_id: str
    contest_id: str
    name: str
    party: str  # party_id
    withdrawn: bool = False


# ---------------------------------------------------------------------------
# Event/Discourse ontology
# ---------------------------------------------------------------------------
@dataclass
class PolicyIssue:
    issue_id: str
    name: str
    type: str = "기타"  # 부동산/경제/환경/안보/교육/...


@dataclass
class NarrativeFrame:
    frame_id: str
    label: str  # "정권심판" / "경제심판" / "안정호소" / "지역개발" / ...


@dataclass
class MediaEvent:
    """뉴스/SNS/논평 등 일반 미디어 이벤트의 base type."""
    event_id: str
    ts: datetime
    source: str
    title: str
    sentiment: float = 0.0  # -1 부정 ↔ +1 긍정
    frame_id: Optional[str] = None
    type: str = "MediaEvent"  # subclass override
    about: list[str] = field(default_factory=list)      # candidate_id | party_id
    mentions: list[str] = field(default_factory=list)   # issue_id


@dataclass
class ScandalEvent(MediaEvent):
    severity: float = 0.5
    target_candidate_id: Optional[str] = None
    credibility: float = 0.5
    type: str = "ScandalEvent"


@dataclass
class Investigation(MediaEvent):
    target_candidate_id: Optional[str] = None
    stage: Literal["allegation", "probe", "indictment", "trial"] = "allegation"
    type: str = "Investigation"


@dataclass
class Verdict(MediaEvent):
    target_candidate_id: Optional[str] = None
    outcome: Literal["acquittal", "conviction", "appeal"] = "acquittal"
    type: str = "Verdict"


@dataclass
class PressConference(MediaEvent):
    speaker: Optional[str] = None
    party_id: Optional[str] = None
    type: str = "PressConference"


@dataclass
class PollPublication:
    poll_id: int
    ts: datetime
    contest_id: str
    sample_size: Optional[int] = None
    leader_candidate: Optional[str] = None
    leader_share: Optional[float] = None
    type: str = "PollPublication"


# ---------------------------------------------------------------------------
# P2/P3 enrichment ontology (2026-04-26) — non-candidate political actors and
# media outlet entities, populated from `_workspace/data/perplexity/{region}.json`.
# ---------------------------------------------------------------------------
@dataclass
class Person:
    """Non-candidate political actor (party leader, cabinet member, opponent
    in a different contest, etc.) referenced by events or candidates."""

    person_id: str
    name: str
    role: str = ""           # e.g. "더불어민주당 대표", "대통령"
    party_id: Optional[str] = None
    type: str = "Person"


@dataclass
class Source:
    """Media outlet / official source entity. Each event may cite one Source
    via the `attributedTo` relation."""

    source_id: str
    name: str
    url_root: str = ""
    media_type: str = "newspaper"  # "newspaper" | "wire" | "broadcast" | "wiki" | "official" | "polling_firm"
    ideology: float = 0.0          # -1 progressive ↔ +1 conservative
    type: str = "Source"


@dataclass
class CohortPrior:
    """Generational/gender × region voter party-lean prior.

    Populated from `_workspace/data/cohort_priors/*.json`. Every prior carries
    a source_url + publish_ts to keep voter agents grounded in real Korean
    polling data (rather than American "younger=progressive" defaults).

    The retriever exposes ``get_cohort_prior(age, gender, region)`` which
    returns the most-specific matching prior (region+age+gender > region+age >
    national+age+gender > national+age).
    """

    cohort_id: str
    age_band: str       # "18-29" | "30-39" | "40-49" | "50-59" | "60-69" | "70+" | "ALL"
    gender: str         # "M" | "F" | "ALL"
    scope: str          # "national" | "region" | "region_special"
    party_lean: dict    # {"ppp": 0.30, "dpk": 0.18, "rebuild": 0.10, "other": 0.05, "undecided": 0.37}
    region_id: Optional[str] = None
    n_polls: int = 0
    sample_size: int = 0
    source: str = ""
    source_url: str = ""
    publish_ts: Optional[datetime] = None
    notes: str = ""
    type: str = "CohortPrior"


# Event-typed node labels — retriever 가 firewall 적용 대상으로 분기.
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


# Non-event node labels added by P2/P3 enrichment — retriever does NOT apply
# the temporal firewall to these (they are reference entities, not occurrences).
ACTOR_NODE_TYPES: frozenset[str] = frozenset({"Person", "Source"})

# Track B prior nodes (cohort × party_lean), populated from
# `_workspace/data/cohort_priors/`.
PRIOR_NODE_TYPES: frozenset[str] = frozenset({"CohortPrior"})
