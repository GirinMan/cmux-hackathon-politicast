"""Pydantic 응답 모델 — frontend OpenAPI 자동 검증 대상."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------- /api/health ----------------
class HealthResponse(BaseModel):
    status: str = Field(description="ok | degraded")
    mode: str = Field(description="데이터 소스 모드 ('duckdb' or 'parquet')")
    source: str = Field(description="DuckDB 파일 경로 또는 parquet glob")
    persona_core_rows: int
    persona_text_rows: int
    region_tables: list[str]


# ---------------- /api/schema ----------------
class ColumnDescriptor(BaseModel):
    name: str
    dtype: str
    nullable: bool


class TableDescriptor(BaseModel):
    name: str
    rows: int
    columns: list[ColumnDescriptor]


class SchemaResponse(BaseModel):
    tables: list[TableDescriptor]
    notes: list[str]


# ---------------- /api/demographics ----------------
class CountBucket(BaseModel):
    value: str
    count: int
    pct: float


class AgeBucket(BaseModel):
    bucket: str
    count: int
    pct: float


class DemographicsResponse(BaseModel):
    region: Optional[str] = Field(default=None, description="region 필터 (key) 또는 전체")
    total: int
    age_buckets: list[AgeBucket]
    age_stats: dict[str, float]  # min/avg/median/max
    sex: list[CountBucket]
    marital_status: list[CountBucket]
    education_level: list[CountBucket]


# ---------------- /api/regions ----------------
class ProvinceCount(BaseModel):
    province: str
    count: int
    pct: float


class RegionsResponse(BaseModel):
    total: int
    provinces: list[ProvinceCount]


class FiveRegionItem(BaseModel):
    key: str
    label_ko: str
    label_en: str
    province: Optional[str] = None
    district: Optional[str] = None
    table: Optional[str] = None
    count: int
    available: bool = Field(description="region 테이블 또는 데이터 존재 여부")


class FiveRegionsResponse(BaseModel):
    regions: list[FiveRegionItem]


# ---------------- /api/occupations ----------------
class OccupationItem(BaseModel):
    occupation: str
    count: int


class OccupationsResponse(BaseModel):
    region: Optional[str] = None
    total_distinct: int
    top: list[OccupationItem]


class OccupationMajorItem(BaseModel):
    major: str
    count: int
    pct: float


class OccupationMajorResponse(BaseModel):
    region: Optional[str] = None
    total: int
    groups: list[OccupationMajorItem]
    meta: dict[str, str]


# ---------------- /api/personas ----------------
class PersonaSummary(BaseModel):
    uuid: str
    persona: Optional[str] = None
    sex: Optional[str] = None
    age: Optional[int] = None
    marital_status: Optional[str] = None
    education_level: Optional[str] = None
    occupation: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None


class PersonaSampleResponse(BaseModel):
    region: Optional[str] = None
    total: int
    samples: list[PersonaSummary]


class PersonaDetail(BaseModel):
    uuid: str
    # core
    persona: Optional[str] = None
    cultural_background: Optional[str] = None
    skills_and_expertise: Optional[str] = None
    skills_and_expertise_list: list[str] = []
    hobbies_and_interests: Optional[str] = None
    hobbies_and_interests_list: list[str] = []
    career_goals_and_ambitions: Optional[str] = None
    # demographics
    sex: Optional[str] = None
    age: Optional[int] = None
    marital_status: Optional[str] = None
    military_status: Optional[str] = None
    family_type: Optional[str] = None
    housing_type: Optional[str] = None
    education_level: Optional[str] = None
    bachelors_field: Optional[str] = None
    occupation: Optional[str] = None
    district: Optional[str] = None
    province: Optional[str] = None
    country: Optional[str] = None
    # text (persona_text)
    professional_persona: Optional[str] = None
    sports_persona: Optional[str] = None
    arts_persona: Optional[str] = None
    travel_persona: Optional[str] = None
    culinary_persona: Optional[str] = None
    family_persona: Optional[str] = None


class TextStat(BaseModel):
    field: str
    min: int
    avg: float
    p50: int
    p90: int
    max: int


class PersonaTextStatsResponse(BaseModel):
    region: Optional[str] = None
    sample_size: int
    stats: list[TextStat]


# ---------------- /api/ontology/graph ----------------
class OntologyCategory(BaseModel):
    name: str
    label: str
    symbol: str
    color: str


class OntologyNode(BaseModel):
    id: str
    label: str
    kind: str
    category: str
    count: int
    pct: float
    symbol: str
    color: str


class OntologyEdge(BaseModel):
    source: str
    target: str
    label: str
    kind: str
    count: int
    weight: float


class OntologyGraphMeta(BaseModel):
    cluster_source: str
    dimensions: list[str]


class OntologyGraphResponse(BaseModel):
    region: Optional[str] = None
    total: int
    categories: list[OntologyCategory]
    nodes: list[OntologyNode]
    edges: list[OntologyEdge]
    meta: OntologyGraphMeta


# ---------------- /api/results + /api/kg + /api/policy ----------------
class ResultRegionSummary(BaseModel):
    region_id: str
    label: str
    scenario_id: Optional[str] = None
    status: str = Field(description="live | mock | smoke | placeholder | missing")
    is_mock: bool = False
    persona_n: int = 0
    timestep_count: int = 0
    winner: Optional[str] = None
    winner_label: Optional[str] = None
    turnout: Optional[float] = None
    parse_fail: int = 0
    abstain: int = 0
    total_calls: int = 0
    mean_latency_ms: Optional[float] = None
    wall_seconds: Optional[float] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    wrote_at: Optional[str] = None
    path: Optional[str] = None
    warning: Optional[str] = None


class ResultTotals(BaseModel):
    regions_total: int
    live_count: int
    mock_count: int
    smoke_count: int
    placeholder_count: int
    persona_n: int
    parse_fail: int
    abstain: int
    total_calls: int
    wall_seconds: float
    mean_latency_ms: Optional[float] = None


class ResultSummaryResponse(BaseModel):
    regions: list[ResultRegionSummary]
    totals: ResultTotals
    warnings: list[str]
    source_files: dict[str, str]


class ResultDetailResponse(BaseModel):
    region_id: str
    label: str
    scenario_id: Optional[str] = None
    status: str
    is_mock: bool
    candidate_labels: dict[str, str]
    candidate_parties: dict[str, str]
    artifact: dict[str, Any]
    result: dict[str, Any]
    paper_note: str


class KgSnapshotInfo(BaseModel):
    region_id: Optional[str] = None
    timestep: Optional[int] = None
    scenario_id: Optional[str] = None
    path: str
    is_placeholder: bool = False


class KgSnapshotResponse(BaseModel):
    region_id: Optional[str] = None
    timestep: Optional[int] = None
    available_timesteps: list[int]
    cutoff_ts: Optional[str] = None
    scenario_id: Optional[str] = None
    status: str = Field(description="live | placeholder | missing")
    source_path: Optional[str] = None
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    snapshots: list[KgSnapshotInfo]


class PolicyRegionPlan(BaseModel):
    region_id: str
    label: str
    persona_n: Optional[int] = None
    timesteps: Optional[int] = None
    interview_n: Optional[int] = None
    weight: Optional[float] = None


class PolicySummaryResponse(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    regions: list[PolicyRegionPlan]
    capacity_probe: Optional[dict[str, Any]] = None
    downscale_ladder: list[dict[str, Any]]
    warnings: list[str]
    source_files: dict[str, str]
