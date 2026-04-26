import { useQueries, useQuery } from '@tanstack/react-query'
import {
  fetchDemographics,
  fetchFiveRegions,
  fetchHealth,
  fetchOntologyGraph,
  fetchOccupationMajor,
  fetchOccupations,
  fetchPersonaDetail,
  fetchPersonaSample,
  fetchPersonaTextStats,
  fetchKgSnapshot,
  fetchPolicy,
  fetchRegions,
  fetchResultDetail,
  fetchResults,
  fetchSchema,
} from '../api/endpoints'

export function useHealth() {
  return useQuery({ queryKey: ['health'], queryFn: fetchHealth, staleTime: 30_000 })
}

export function useSchema() {
  return useQuery({ queryKey: ['schema'], queryFn: fetchSchema })
}

export function useDemographics(region?: string | null) {
  return useQuery({
    queryKey: ['demographics', region ?? null],
    queryFn: () => fetchDemographics(region),
  })
}

export function useDemographicsMany(regions: string[]) {
  return useQueries({
    queries: regions.map((region) => ({
      queryKey: ['demographics', region],
      queryFn: () => fetchDemographics(region),
      enabled: regions.length > 0,
    })),
  })
}

export function useRegions() {
  return useQuery({ queryKey: ['regions'], queryFn: fetchRegions })
}

export function useFiveRegions() {
  return useQuery({ queryKey: ['regions', 'five'], queryFn: fetchFiveRegions })
}

export function useOccupations(region?: string | null, limit = 30) {
  return useQuery({
    queryKey: ['occupations', region ?? null, limit],
    queryFn: () => fetchOccupations(region, limit),
  })
}

export function useOccupationMajor(region?: string | null) {
  return useQuery({
    queryKey: ['occupations', 'major', region ?? null],
    queryFn: () => fetchOccupationMajor(region),
  })
}

export function useOntologyGraph(
  region?: string | null,
  clusterLimit = 12,
  occupationLimit = 12,
  minCount = 1,
  enabled = true,
) {
  return useQuery({
    queryKey: [
      'ontology',
      'graph',
      region ?? null,
      clusterLimit,
      occupationLimit,
      minCount,
    ],
    queryFn: () =>
      fetchOntologyGraph(region, clusterLimit, occupationLimit, minCount),
    enabled,
  })
}

export function useResults() {
  return useQuery({
    queryKey: ['results'],
    queryFn: fetchResults,
    refetchInterval: 10_000,
  })
}

export function useResultDetail(region?: string | null) {
  return useQuery({
    queryKey: ['results', region ?? null],
    queryFn: () => fetchResultDetail(region as string),
    enabled: !!region,
    refetchInterval: 10_000,
  })
}

export function useKgSnapshot(region?: string | null, timestep?: number | null) {
  return useQuery({
    queryKey: ['kg', region ?? null, timestep ?? null],
    queryFn: () => fetchKgSnapshot(region, timestep),
    enabled: !!region,
  })
}

export function usePolicy() {
  return useQuery({
    queryKey: ['policy'],
    queryFn: fetchPolicy,
    staleTime: 30_000,
  })
}

export function usePersonaSample(
  region?: string | null,
  limit = 20,
  seed?: number | null,
) {
  return useQuery({
    queryKey: ['personas', 'sample', region ?? null, limit, seed ?? null],
    queryFn: () => fetchPersonaSample(region, limit, seed),
  })
}

export function usePersonaDetail(uuid: string | null) {
  return useQuery({
    queryKey: ['personas', 'detail', uuid],
    queryFn: () => fetchPersonaDetail(uuid as string),
    enabled: !!uuid,
  })
}

export function usePersonaTextStats(region?: string | null, sample_size = 5000) {
  return useQuery({
    queryKey: ['personas', 'text-stats', region ?? null, sample_size],
    queryFn: () => fetchPersonaTextStats(region, sample_size),
  })
}
