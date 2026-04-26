// Mirrors backend/models.py — keep field names identical.

export interface HealthResponse {
  status: 'ok' | 'degraded' | string
  mode: string
  source: string
  persona_core_rows: number
  persona_text_rows: number
  region_tables: string[]
}

export interface ColumnDescriptor {
  name: string
  dtype: string
  nullable: boolean
}

export interface TableDescriptor {
  name: string
  rows: number
  columns: ColumnDescriptor[]
}

export interface SchemaResponse {
  tables: TableDescriptor[]
  notes: string[]
}

export interface CountBucket {
  value: string
  count: number
  pct: number
}

export interface AgeBucket {
  bucket: string
  count: number
  pct: number
}

export interface DemographicsResponse {
  region: string | null
  total: number
  age_buckets: AgeBucket[]
  age_stats: { min: number; avg: number; median: number; max: number } & Record<string, number>
  sex: CountBucket[]
  marital_status: CountBucket[]
  education_level: CountBucket[]
}

export interface ProvinceCount {
  province: string
  count: number
  pct: number
}

export interface RegionsResponse {
  total: number
  provinces: ProvinceCount[]
}

export interface FiveRegionItem {
  key: string
  label_ko: string
  label_en: string
  province: string | null
  district: string | null
  table: string | null
  count: number
  available: boolean
}

export interface FiveRegionsResponse {
  regions: FiveRegionItem[]
}

export interface OccupationItem {
  occupation: string
  count: number
}

export interface OccupationsResponse {
  region: string | null
  total_distinct: number
  top: OccupationItem[]
}

export interface OccupationMajorItem {
  major: string
  count: number
  pct: number
}

export interface OccupationMajorResponse {
  region: string | null
  total: number
  groups: OccupationMajorItem[]
  meta: Record<string, string>
}

export interface PersonaSummary {
  uuid: string
  persona: string | null
  sex: string | null
  age: number | null
  marital_status: string | null
  education_level: string | null
  occupation: string | null
  province: string | null
  district: string | null
}

export interface PersonaSampleResponse {
  region: string | null
  total: number
  samples: PersonaSummary[]
}

export interface PersonaDetail {
  uuid: string
  persona: string | null
  cultural_background: string | null
  skills_and_expertise: string | null
  skills_and_expertise_list: string[]
  hobbies_and_interests: string | null
  hobbies_and_interests_list: string[]
  career_goals_and_ambitions: string | null
  sex: string | null
  age: number | null
  marital_status: string | null
  military_status: string | null
  family_type: string | null
  housing_type: string | null
  education_level: string | null
  bachelors_field: string | null
  occupation: string | null
  district: string | null
  province: string | null
  country: string | null
  professional_persona: string | null
  sports_persona: string | null
  arts_persona: string | null
  travel_persona: string | null
  culinary_persona: string | null
  family_persona: string | null
}

export interface TextStat {
  field: string
  min: number
  avg: number
  p50: number
  p90: number
  max: number
}

export interface PersonaTextStatsResponse {
  region: string | null
  sample_size: number
  stats: TextStat[]
}

export interface OntologyCategory {
  name: string
  label: string
  symbol: string
  color: string
}

export interface OntologyNode {
  id: string
  label: string
  kind: string
  category: string
  count: number
  pct: number
  symbol: string
  color: string
}

export interface OntologyEdge {
  source: string
  target: string
  label: string
  kind: string
  count: number
  weight: number
}

export interface OntologyGraphResponse {
  region: string | null
  total: number
  categories: OntologyCategory[]
  nodes: OntologyNode[]
  edges: OntologyEdge[]
  meta: {
    cluster_source: string
    dimensions: string[]
  }
}

export type ResultArtifactStatus =
  | 'live'
  | 'mock'
  | 'smoke'
  | 'placeholder'
  | 'missing'
  | string

export interface ResultRegionSummary {
  region_id: string
  label: string
  scenario_id: string | null
  status: ResultArtifactStatus
  is_mock: boolean
  persona_n: number
  timestep_count: number
  winner: string | null
  winner_label: string | null
  turnout: number | null
  parse_fail: number
  abstain: number
  total_calls: number
  mean_latency_ms: number | null
  wall_seconds: number | null
  provider: string | null
  model: string | null
  wrote_at: string | null
  path: string | null
  warning: string | null
}

export interface ResultTotals {
  regions_total: number
  live_count: number
  mock_count: number
  smoke_count: number
  placeholder_count: number
  persona_n: number
  parse_fail: number
  abstain: number
  total_calls: number
  wall_seconds: number
  mean_latency_ms: number | null
}

export interface ResultSummaryResponse {
  regions: ResultRegionSummary[]
  totals: ResultTotals
  warnings: string[]
  source_files: Record<string, string>
}

export interface ScenarioCandidate {
  id: string
  name: string
  party: string
}

export interface PollTrajectoryPoint {
  timestep: number
  date: string
  support_by_candidate: Record<string, number>
  turnout_intent: number
  consensus_var: number
}

export interface ScenarioResult {
  scenario_id: string
  region_id: string
  contest_id: string
  timestep_count: number
  persona_n: number
  candidates: ScenarioCandidate[]
  poll_trajectory: PollTrajectoryPoint[]
  final_outcome: {
    turnout: number
    vote_share_by_candidate: Record<string, number>
    winner: string | null
    n_responses?: number
    n_abstain?: number
  }
  demographics_breakdown: Record<string, Record<string, Record<string, number>>>
  virtual_interviews: Array<{
    persona_id: string
    persona_summary: string
    vote: string | null
    reason: string
    key_factors?: string[]
    timestep: number
  }>
  kg_events_used: Array<{
    event_id: string
    type: string
    target: string
    timestep: number
  }>
  meta?: Record<string, unknown>
  is_mock?: boolean
  _placeholder?: boolean
}

export interface ResultDetailResponse {
  region_id: string
  label: string
  scenario_id: string | null
  status: ResultArtifactStatus
  is_mock: boolean
  candidate_labels: Record<string, string>
  candidate_parties: Record<string, string>
  artifact: {
    path: string | null
    wrote_at: string | null
    status: ResultArtifactStatus
    is_mock: boolean
  }
  result: ScenarioResult
  paper_note: string
}

export interface KgSnapshotResponse {
  region_id: string | null
  timestep: number | null
  available_timesteps: number[]
  cutoff_ts: string | null
  scenario_id: string | null
  status: 'live' | 'placeholder' | 'missing' | string
  source_path: string | null
  nodes: Array<Record<string, unknown>>
  edges: Array<Record<string, unknown>>
  snapshots: Array<{
    region_id: string | null
    timestep: number | null
    scenario_id: string | null
    path: string
    is_placeholder: boolean
  }>
}

export interface PolicySummaryResponse {
  provider: string | null
  model: string | null
  regions: Array<{
    region_id: string
    label: string
    persona_n: number | null
    timesteps: number | null
    interview_n: number | null
    weight: number | null
  }>
  capacity_probe: Record<string, unknown> | null
  downscale_ladder: Array<Record<string, unknown>>
  warnings: string[]
  source_files: Record<string, string>
}

export type RegionKey = string
