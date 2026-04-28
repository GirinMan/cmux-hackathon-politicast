"""Admin / Internal API DTOs."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class _StrictDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AdminScenarioStatusDTO(_StrictDTO):
    scenario_id: str
    region_id: str
    snapshot_count: int = 0
    last_run_at: Optional[str] = None


class SimResultUploadDTO(BaseModel):
    """외부 시뮬레이터가 보낸 ScenarioResult JSON.

    schema 는 src/schemas/result.py:ScenarioResult 와 동일하지만 backend 에서는
    raw dict 로 받아 src 검증기를 호출 (코드 중복 회피, 양방향 결합 약화).
    """

    model_config = ConfigDict(extra="allow")

    scenario_id: str
    region_id: str
    contest_id: str
    schema_version: str = "v1"
    final_outcome: Optional[dict[str, Any]] = None
    poll_trajectory: list[dict[str, Any]] = Field(default_factory=list)
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class SimResultUploadResponseDTO(_StrictDTO):
    snapshot_path: str
    scenario_id: str
    region_id: str
    bytes_written: int


# ---------------------------------------------------------------------------
# Phase 5 — moderation
# ---------------------------------------------------------------------------
class ReportDTO(_StrictDTO):
    id: str
    target_kind: str
    target_id: str
    reporter_user_id: str
    reason: str
    status: str
    resolution: Optional[str] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    created_at: str


class ResolveReportRequestDTO(_StrictDTO):
    resolution: str  # dismissed | soft_deleted | banned_user


class BanUserRequestDTO(_StrictDTO):
    reason: Optional[str] = None


class AdminCommentDTO(_StrictDTO):
    id: str
    scope_type: str
    scope_id: str
    user_id: str
    user_display_name: str
    body: str
    created_at: str
    edited_count: int = 0
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None


class AdminBoardTopicDTO(_StrictDTO):
    id: str
    region_id: Optional[str] = None
    user_id: str
    user_display_name: str
    title: str
    pinned: bool = False
    comment_count: int = 0
    created_at: str
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None


# ---------------------------------------------------------------------------
# Phase 6 — admin DTOs (scenario tree / calibration / scenario_event)
# ---------------------------------------------------------------------------
class ScenarioTreeMetadataDTO(_StrictDTO):
    """Admin 목록용 — DB row 1개의 메타만."""

    id: str
    region_id: str
    contest_id: str
    as_of: str
    election_date: str
    beam_width: int
    beam_depth: int
    artifact_path: str
    mlflow_run_id: Optional[str] = None
    built_at: str
    built_by: Optional[str] = None
    status: str  # building | complete | failed


class ScenarioTreeListResponseDTO(_StrictDTO):
    data: list[ScenarioTreeMetadataDTO] = Field(default_factory=list)
    page: int = 1
    page_size: int = 20
    total: int = 0


class ScenarioTreeBuildRequestDTO(_StrictDTO):
    region_id: str
    as_of: str  # ISO date
    beam_width: Optional[int] = Field(default=None, ge=1, le=10)
    beam_depth: Optional[int] = Field(default=None, ge=1, le=8)
    k_propose: Optional[int] = Field(default=None, ge=1, le=10)
    proposer: Optional[str] = None  # composite | kg | llm | custom
    seed: Optional[int] = None


class ScenarioTreeBuildResponseDTO(_StrictDTO):
    tree_id: str
    region_id: str
    as_of: str
    status: str  # building | complete | failed
    mlflow_run_id: Optional[str] = None


class MLflowRunSummaryDTO(_StrictDTO):
    run_id: str
    experiment_id: Optional[str] = None
    experiment_name: Optional[str] = None
    run_name: Optional[str] = None
    status: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    region_id: Optional[str] = None
    stage: Optional[str] = None  # 'stage1' | 'stage2' | 'tree_build' | None
    metrics: dict[str, float] = Field(default_factory=dict)
    params: dict[str, str] = Field(default_factory=dict)
    artifact_uri: Optional[str] = None


class MLflowRunListResponseDTO(_StrictDTO):
    data: list[MLflowRunSummaryDTO] = Field(default_factory=list)
    page: int = 1
    page_size: int = 20
    total: int = 0
    tracking_uri: Optional[str] = None
    available: bool = True
    error: Optional[str] = None


class CalibrationStartRequestDTO(_StrictDTO):
    region_id: str
    stage: int = Field(ge=1, le=2)


class CalibrationStartResponseDTO(_StrictDTO):
    region_id: str
    stage: int
    mlflow_run_id: Optional[str] = None
    status: str  # 'started' | 'queued' | 'failed'
    detail: Optional[str] = None


class ScenarioEventDTO(_StrictDTO):
    id: str
    region_id: str
    source: str  # kg_confirmed | llm_hypothetical | custom
    occurs_at: str
    description: str
    candidate_patches: list[dict[str, Any]] = Field(default_factory=list)
    event_patches: list[dict[str, Any]] = Field(default_factory=list)
    prior_p: float
    event_metadata: Optional[dict[str, Any]] = None
    created_at: str
    created_by: Optional[str] = None
    is_active: bool = True


class ScenarioEventListResponseDTO(_StrictDTO):
    data: list[ScenarioEventDTO] = Field(default_factory=list)
    page: int = 1
    page_size: int = 50
    total: int = 0


class ScenarioEventCreateRequestDTO(_StrictDTO):
    region_id: str
    source: str = "custom"  # kg_confirmed | llm_hypothetical | custom
    occurs_at: str  # ISO datetime
    description: str
    candidate_patches: list[dict[str, Any]] = Field(default_factory=list)
    event_patches: list[dict[str, Any]] = Field(default_factory=list)
    prior_p: float = Field(ge=0.0, le=1.0)
    event_metadata: Optional[dict[str, Any]] = None
