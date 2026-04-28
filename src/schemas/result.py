"""ScenarioResult — 시뮬레이션 출력 SoT.

기존 _workspace/contracts/result_schema.json 의 모든 필드를 매핑하되 실제
snapshot 다양성(`cost_usd`, `iam_mode`, `is_cache_artifact` 등 후추가 필드)을
수용하기 위해 nested dict 영역은 `extra="allow"` 로 둔다.

엄격 검증이 필요한 호출자는 `ScenarioResult.model_validate(data)` 가 아니라
`validate_strict(data)` (out of scope, 후속 phase) 를 호출한다.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Atomic blocks
# ---------------------------------------------------------------------------
class CandidateRef(BaseModel):
    """ScenarioResult.candidates[] — 시나리오 Candidate 의 축약형."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str = ""
    party: str = ""


class PollTrajectoryPoint(BaseModel):
    model_config = ConfigDict(extra="allow")

    timestep: int
    date: Optional[str] = None
    support_by_candidate: dict[str, float] = Field(default_factory=dict)
    turnout_intent: Optional[float] = None
    consensus_var: Optional[float] = None


class FinalOutcome(BaseModel):
    model_config = ConfigDict(extra="allow")

    turnout: Optional[float] = None
    vote_share_by_candidate: dict[str, float] = Field(default_factory=dict)
    winner: Optional[str] = None
    n_responses: Optional[int] = None
    n_abstain: Optional[int] = None


class DemographicsBreakdown(BaseModel):
    """집계 키 셋(by_age_group/by_education/by_district)은 고정이지만
    값(셀) 셋은 데이터에 따라 가변이라 자유로운 dict 로 둔다."""

    model_config = ConfigDict(extra="allow")

    by_age_group: dict[str, dict[str, float]] = Field(default_factory=dict)
    by_education: dict[str, dict[str, float]] = Field(default_factory=dict)
    by_district: dict[str, dict[str, float]] = Field(default_factory=dict)


class VirtualInterview(BaseModel):
    model_config = ConfigDict(extra="allow")

    persona_id: str
    persona_summary: str = ""
    vote: Optional[str] = None
    reason: str = ""
    key_factors: list[str] = Field(default_factory=list)
    timestep: Optional[int] = None


class KgEventUsed(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_id: Optional[str] = None
    type: Optional[str] = None
    target: Optional[str] = None
    timestep: Optional[int] = None


# ---------------------------------------------------------------------------
# Validation block (single source of truth — eval/metrics.py 에서 생산)
# ---------------------------------------------------------------------------
class ValidationMetrics(BaseModel):
    """공식 여론조사 vs 시뮬 비교 4종 지표."""

    model_config = ConfigDict(extra="forbid")

    mae: Optional[float] = None
    rmse: Optional[float] = None
    margin_error: Optional[float] = None
    leader_match: Optional[bool] = None

    # Phase: 평가 메트릭 확장 (calibration / divergence / collapse 진단)
    # 모두 Optional — 기존 19개 snapshot 은 None 으로 로드됨.
    brier: Optional[float] = None
    ece: Optional[float] = None
    js_divergence: Optional[float] = None
    collapse_flag: Optional[bool] = None


class ValidationByCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    simulated_share: Optional[float] = None
    official_consensus: Optional[float] = None
    error: Optional[float] = None


class OfficialPollValidation(BaseModel):
    model_config = ConfigDict(extra="allow")

    target_series: str  # poll_consensus_daily | scenario_fallback_v1 | prediction_only | ...
    method_version: str = "weighted_v1"
    cutoff_ts: str
    as_of_date: Optional[str] = None
    source_poll_ids: list[str] = Field(default_factory=list)
    metrics: ValidationMetrics = Field(default_factory=ValidationMetrics)
    by_candidate: dict[str, ValidationByCandidate] = Field(default_factory=dict)

    # 컨텍스트 플래그 — 분기에 따라 일부만 채워짐
    poll_targets_visible_to_agents: Optional[bool] = None
    prediction_only: Optional[bool] = None
    counterfactual_prediction: Optional[bool] = None
    reason: Optional[str] = None
    intervention_id: Optional[str] = None
    base_region_id: Optional[str] = None
    calibration_profile: Optional[str] = None
    frozen_params: Optional[bool] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Meta — 후추가 필드가 가장 많은 영역. extra="allow" 로 넓게.
# ---------------------------------------------------------------------------
class Meta(BaseModel):
    model_config = ConfigDict(extra="allow")

    env: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    wall_seconds: Optional[float] = None
    policy_version: Optional[str] = None
    concurrency: Optional[int] = None
    features: list[str] = Field(default_factory=list)

    effective_provider: Optional[str] = None
    effective_model: Optional[str] = None
    actual_keys_used: Optional[int] = None
    llm_cache_enabled: Optional[bool] = None
    final_poll_feedback_enabled: Optional[bool] = None
    poll_targets_visible_to_agents: Optional[bool] = None

    # 가변 nested dict 들 — 검증 부담을 피하고 실측 다양성을 수용
    counterfactual: Optional[dict[str, Any]] = None
    pool_stats: Optional[dict[str, Any]] = None
    voter_stats: Optional[dict[str, Any]] = None

    official_poll_validation: Optional[OfficialPollValidation] = None


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------
class ScenarioResult(BaseModel):
    """단일 시나리오 시뮬 출력. _workspace/snapshots/results/*.json 의 root."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    schema_version: str = "v1"
    scenario_id: str
    region_id: str
    contest_id: str
    timestep_count: int = 0
    persona_n: int = 0

    candidates: list[CandidateRef] = Field(default_factory=list)
    poll_trajectory: list[PollTrajectoryPoint] = Field(default_factory=list)
    final_outcome: Optional[FinalOutcome] = None
    demographics_breakdown: DemographicsBreakdown = Field(default_factory=DemographicsBreakdown)
    virtual_interviews: list[VirtualInterview] = Field(default_factory=list)
    kg_events_used: list[KgEventUsed] = Field(default_factory=list)
    meta: Meta = Field(default_factory=Meta)
