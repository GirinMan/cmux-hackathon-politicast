import { api } from './client'
import type {
  DemographicsResponse,
  FiveRegionsResponse,
  HealthResponse,
  OntologyGraphResponse,
  OccupationMajorResponse,
  OccupationsResponse,
  PersonaDetail,
  PersonaSampleResponse,
  PersonaTextStatsResponse,
  KgSnapshotResponse,
  PolicySummaryResponse,
  RegionsResponse,
  ResultDetailResponse,
  ResultSummaryResponse,
  SchemaResponse,
} from '../types/api'

function clean(params: Record<string, string | number | null | undefined>) {
  const out: Record<string, string | number> = {}
  for (const [k, v] of Object.entries(params)) {
    if (v == null || v === '') continue
    out[k] = v
  }
  return out
}

export async function fetchHealth() {
  const { data } = await api.get<HealthResponse>('/health')
  return data
}

export async function fetchSchema() {
  const { data } = await api.get<SchemaResponse>('/schema')
  return data
}

export async function fetchDemographics(region?: string | null) {
  const { data } = await api.get<DemographicsResponse>('/demographics', {
    params: clean({ region }),
  })
  return data
}

export async function fetchRegions() {
  const { data } = await api.get<RegionsResponse>('/regions')
  return data
}

export async function fetchFiveRegions() {
  const { data } = await api.get<FiveRegionsResponse>('/regions/five')
  return data
}

export async function fetchOccupations(region?: string | null, limit = 30) {
  const { data } = await api.get<OccupationsResponse>('/occupations', {
    params: clean({ region, limit }),
  })
  return data
}

export async function fetchOccupationMajor(region?: string | null) {
  const { data } = await api.get<OccupationMajorResponse>('/occupations/major', {
    params: clean({ region }),
  })
  return data
}

export async function fetchOntologyGraph(
  region?: string | null,
  cluster_limit = 12,
  occupation_limit = 12,
  min_count = 1,
) {
  const { data } = await api.get<OntologyGraphResponse>('/ontology/graph', {
    params: clean({ region, cluster_limit, occupation_limit, min_count }),
  })
  return data
}

export async function fetchResults() {
  const { data } = await api.get<ResultSummaryResponse>('/results')
  return data
}

export async function fetchResultDetail(region: string) {
  const { data } = await api.get<ResultDetailResponse>(`/results/${region}`)
  return data
}

export async function fetchKgSnapshot(region?: string | null, timestep?: number | null) {
  const { data } = await api.get<KgSnapshotResponse>('/kg', {
    params: clean({ region, timestep }),
  })
  return data
}

export async function fetchPolicy() {
  const { data } = await api.get<PolicySummaryResponse>('/policy')
  return data
}

export async function fetchPersonaSample(
  region?: string | null,
  limit = 20,
  seed?: number | null,
) {
  const { data } = await api.get<PersonaSampleResponse>('/personas/sample', {
    params: clean({ region, limit, seed }),
  })
  return data
}

export async function fetchPersonaDetail(uuid: string) {
  const { data } = await api.get<PersonaDetail>(`/personas/${uuid}`)
  return data
}

export async function fetchPersonaTextStats(
  region?: string | null,
  sample_size = 5000,
) {
  const { data } = await api.get<PersonaTextStatsResponse>('/personas/text-stats', {
    params: clean({ region, sample_size }),
  })
  return data
}
