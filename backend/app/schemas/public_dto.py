"""Public API response DTOs.

frontend codegen 의 입력 — 명시적 필드만 노출 (extra='forbid').
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class _StrictDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegionDTO(_StrictDTO):
    region_id: str
    name: str
    election_id: str
    election_date: str  # ISO date
    position_type: str
    timezone: str = "Asia/Seoul"
    in_blackout: Optional[bool] = None


class RegionSummaryDTO(_StrictDTO):
    region_id: str
    n_personas: int = 0
    n_districts: int = 0
    n_candidates: int = 0


class CandidateDTO(_StrictDTO):
    cand_id: str
    name: str = ""
    party_id: Optional[str] = None
    party_label: Optional[str] = None


class PollPointDTO(_StrictDTO):
    timestep: int
    date: Optional[str] = None
    support_by_candidate: dict[str, float] = Field(default_factory=dict)
    turnout_intent: Optional[float] = None
    consensus_var: Optional[float] = None


class PredictionPointDTO(_StrictDTO):
    """target_series=prediction_only 시리즈 — model output, no held-out label."""

    timestep: int
    date: Optional[str] = None
    predicted_share: dict[str, float] = Field(default_factory=dict)
    margin_top2: Optional[float] = None
    leader: Optional[str] = None


class PersonaSampleDTO(_StrictDTO):
    persona_id: str
    age: Optional[int] = None
    gender: Optional[str] = None
    education: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    summary: str = ""


class ScenarioDTO(_StrictDTO):
    scenario_id: str
    region_id: str
    contest_id: str
    election_date: Optional[str] = None
    candidates: list[CandidateDTO] = Field(default_factory=list)
    timesteps: int = 0
    persona_n: int = 0


class ScenarioOutcomeDTO(_StrictDTO):
    scenario_id: str
    region_id: str
    target_series: Optional[str] = None
    final_vote_share: dict[str, float] = Field(default_factory=dict)
    winner: Optional[str] = None
    turnout: Optional[float] = None
    metrics: dict[str, Optional[float]] = Field(default_factory=dict)


class KGNodeDTO(_StrictDTO):
    id: str
    kind: Optional[str] = None
    label: Optional[str] = None
    ts: Optional[str] = None


class KGEdgeDTO(_StrictDTO):
    src: str
    dst: str
    pred: str
    ts: Optional[str] = None
    confidence: Optional[float] = None


class KGSubgraphDTO(_StrictDTO):
    region_id: str
    cutoff: Optional[str] = None
    nodes: list[KGNodeDTO] = Field(default_factory=list)
    edges: list[KGEdgeDTO] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 5 — community + blackout
# ---------------------------------------------------------------------------
class BlackoutMetaDTO(_StrictDTO):
    in_blackout: bool = False
    end_date: Optional[str] = None  # ISO date
    hides_ai: bool = True
    region_id: Optional[str] = None


class PollTrajectoryResponseDTO(_StrictDTO):
    data: list[PollPointDTO] = Field(default_factory=list)
    blackout: BlackoutMetaDTO = Field(default_factory=BlackoutMetaDTO)


class PredictionTrajectoryResponseDTO(_StrictDTO):
    data: list[PredictionPointDTO] = Field(default_factory=list)
    blackout: BlackoutMetaDTO = Field(default_factory=BlackoutMetaDTO)


class ScenarioOutcomeResponseDTO(_StrictDTO):
    data: Optional[ScenarioOutcomeDTO] = None
    blackout: BlackoutMetaDTO = Field(default_factory=BlackoutMetaDTO)


class AnonUserDTO(_StrictDTO):
    id: str
    display_name: str
    created_at: str
    banned: bool = False


class UpdateNicknameRequestDTO(_StrictDTO):
    display_name: str


class CommentDTO(_StrictDTO):
    id: str
    scope_type: str
    scope_id: str
    parent_id: Optional[str] = None
    user_id: str
    user_display_name: str
    body: str
    created_at: str
    updated_at: Optional[str] = None
    edited_count: int = 0
    deleted_at: Optional[str] = None


class CommentListResponseDTO(_StrictDTO):
    data: list[CommentDTO] = Field(default_factory=list)
    page: int = 1
    page_size: int = 50
    total: int = 0


class CommentCreateRequestDTO(_StrictDTO):
    scope_type: str
    scope_id: str
    body: str
    parent_id: Optional[str] = None


class CommentUpdateRequestDTO(_StrictDTO):
    body: str


class ReportRequestDTO(_StrictDTO):
    reason: str


class BoardTopicDTO(_StrictDTO):
    id: str
    region_id: Optional[str] = None
    user_id: str
    user_display_name: str
    title: str
    body: str
    created_at: str
    updated_at: Optional[str] = None
    pinned: bool = False
    comment_count: int = 0
    deleted_at: Optional[str] = None


class BoardTopicListResponseDTO(_StrictDTO):
    data: list[BoardTopicDTO] = Field(default_factory=list)
    page: int = 1
    page_size: int = 20
    total: int = 0


class BoardTopicDetailDTO(_StrictDTO):
    topic: BoardTopicDTO
    first_comments: list[CommentDTO] = Field(default_factory=list)


class CreateTopicRequestDTO(_StrictDTO):
    region_id: Optional[str] = None
    title: str
    body: str


class UpdateTopicRequestDTO(_StrictDTO):
    title: Optional[str] = None
    body: Optional[str] = None


# ---------------------------------------------------------------------------
# Phase 6 — Scenario tree (Vertical Sankey) public DTOs
# ---------------------------------------------------------------------------
class ScenarioTreeNodeDTO(_StrictDTO):
    """Sankey 가 그릴 최소 정보 — node 한 개."""

    node_id: str
    parent_id: Optional[str] = None
    depth: int
    # 한국어 라벨 (이벤트 description). root 는 ``"현재 (as_of)"`` 등.
    label: str
    # source 배지 — KG/LLM/custom. root 는 None.
    source: Optional[str] = None
    # 부모로부터 이 node 로 이어진 이벤트의 prior (root child 이상에만 존재).
    prior_p: Optional[float] = None
    # root 부터 이 node 까지의 누적 확률 — Sankey 의 폭에 매핑.
    cumulative_p: float
    # leader 후보 id — Sankey color 매핑 (`partyColors.ts` 재사용).
    leader_candidate_id: str
    # candidate_id → vote share. tooltip 의 막대그래프에 사용.
    predicted_shares: dict[str, float] = Field(default_factory=dict)
    children: list[str] = Field(default_factory=list)
    occurs_at: Optional[str] = None


class ScenarioTreeDTO(_StrictDTO):
    tree_id: str
    region_id: str
    contest_id: str
    as_of: str
    election_date: str
    root_id: str
    nodes: list[ScenarioTreeNodeDTO] = Field(default_factory=list)
    mlflow_run_id: Optional[str] = None
    built_at: Optional[str] = None


class ScenarioTreeResponseDTO(_StrictDTO):
    """공개 응답 — blackout flag 동봉."""

    data: Optional[ScenarioTreeDTO] = None
    blackout: BlackoutMetaDTO = Field(default_factory=BlackoutMetaDTO)


class BeamNodeDetailDTO(_StrictDTO):
    """Drilldown 패널 — 사용자가 노드 클릭 시 노출."""

    tree_id: str
    node_id: str
    region_id: str
    parent_id: Optional[str] = None
    depth: int
    label: str
    source: Optional[str] = None
    prior_p: Optional[float] = None
    cumulative_p: float
    leader_candidate_id: str
    predicted_shares: dict[str, float] = Field(default_factory=dict)
    sim_result_ref: Optional[str] = None
    poll_trajectory: list[PollPointDTO] = Field(default_factory=list)
    virtual_interview_excerpts: list[str] = Field(default_factory=list)
    event_metadata: dict[str, Optional[str]] = Field(default_factory=dict)
