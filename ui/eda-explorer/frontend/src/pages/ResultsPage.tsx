import { useMemo, useState } from 'react'
import EChart, { type LooseEChartsOption } from '../charts/EChart'
import Card from '../components/Card'
import { EmptyState, ErrorState, LoadingState } from '../components/States'
import {
  useKgSnapshot,
  usePolicy,
  useResultDetail,
  useResults,
} from '../hooks/queries'
import { kgPartyAsset, kgPersonAsset } from '../lib/kgAssetRegistry'
import { useTheme } from '../state/theme'
import type {
  ResultArtifactStatus,
  ResultRegionSummary,
  ScenarioCandidate,
  ScenarioResult,
} from '../types/api'

const NF = new Intl.NumberFormat('ko-KR')
const PF = new Intl.NumberFormat('ko-KR', {
  style: 'percent',
  maximumFractionDigits: 1,
})

const PARTY_COLORS: Record<string, string> = {
  p_dem: '#1764d8',
  p_ppp: '#df2935',
  p_rebuild: '#f97316',
  p_jpp: '#facc15',
  p_indep: '#7c8794',
  p_none: '#a1a1aa',
  abstain: '#a1a1aa',
}

const STATUS_META: Record<string, { label: string; className: string; dot: string }> = {
  live: {
    label: 'live',
    className:
      'border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
    dot: 'bg-emerald-500',
  },
  mock: {
    label: 'mock',
    className:
      'border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300',
    dot: 'bg-amber-500',
  },
  smoke: {
    label: 'smoke',
    className:
      'border-sky-500/40 bg-sky-500/10 text-sky-700 dark:text-sky-300',
    dot: 'bg-sky-500',
  },
  placeholder: {
    label: 'placeholder',
    className:
      'border-zinc-400/40 bg-zinc-500/10 text-zinc-600 dark:text-zinc-300',
    dot: 'bg-zinc-400',
  },
  missing: {
    label: 'missing',
    className:
      'border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-300',
    dot: 'bg-red-500',
  },
}

type BreakdownKey = 'by_age_group' | 'by_education' | 'by_district'

export default function ResultsPage() {
  const { theme } = useTheme()
  const results = useResults()
  const policy = usePolicy()
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null)
  const [breakdownKey, setBreakdownKey] = useState<BreakdownKey>('by_age_group')

  const firstRegion = useMemo(() => {
    const regions = results.data?.regions ?? []
    return (
      regions.find((r) => r.status === 'live')?.region_id ??
      regions[0]?.region_id ??
      null
    )
  }, [results.data?.regions])

  const activeRegion = selectedRegion ?? firstRegion
  const detail = useResultDetail(activeRegion)
  const selectedSummary = results.data?.regions.find(
    (r) => r.region_id === activeRegion,
  )
  const latestTimestep =
    detail.data?.result?.poll_trajectory?.at(-1)?.timestep ??
    detail.data?.result?.timestep_count ??
    null
  const kg = useKgSnapshot(activeRegion, latestTimestep)

  if (results.isLoading) {
    return <LoadingState label="실험 산출물을 불러오는 중..." />
  }
  if (results.error) {
    return <ErrorState error={results.error} retry={results.refetch} />
  }
  if (!results.data) {
    return <EmptyState>결과 index가 비어 있습니다.</EmptyState>
  }

  return (
    <div className="space-y-6">
      <header className="relative overflow-hidden rounded-xl border border-zinc-200 bg-zinc-950 px-5 py-5 text-zinc-50 shadow-sm dark:border-zinc-800">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-400 to-transparent" />
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-medium uppercase text-emerald-300">
              PolitiKAST Experiment Console
            </p>
            <h1 className="mt-2 text-2xl font-semibold">실험 결과</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-300">
              논문 최신본의 local harness outputs를 그대로 읽어 mock, smoke, live
              상태와 런타임 진단을 함께 표시합니다.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <HeroMetric label="live" value={results.data.totals.live_count} />
            <HeroMetric label="mock" value={results.data.totals.mock_count} />
            <HeroMetric label="personas" value={results.data.totals.persona_n} />
            <HeroMetric label="parse fail" value={results.data.totals.parse_fail} />
          </div>
        </div>
      </header>

      {results.data.warnings.length > 0 && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-900 dark:text-amber-100">
          {results.data.warnings.join(' ')}
        </div>
      )}

      <Card
        title="5-region artifact status"
        subtitle={`${results.data.source_files.results_index} · live-first per region`}
        right={
          <button
            type="button"
            onClick={() => results.refetch()}
            className="rounded-md border border-zinc-300 px-2 py-1 text-xs text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            refresh
          </button>
        }
      >
        <div className="grid gap-3 lg:grid-cols-5">
          {results.data.regions.map((region) => (
            <RegionArtifactButton
              key={region.region_id}
              region={region}
              active={region.region_id === activeRegion}
              onClick={() => setSelectedRegion(region.region_id)}
            />
          ))}
        </div>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.4fr_0.8fr]">
        <div className="space-y-6">
          <Card
            title={selectedSummary?.label ?? 'Region detail'}
            subtitle={selectedSummary?.scenario_id ?? 'select a region'}
            right={<StatusBadge status={selectedSummary?.status ?? 'missing'} />}
          >
            {detail.isLoading ? (
              <LoadingState />
            ) : detail.error ? (
              <ErrorState error={detail.error} retry={detail.refetch} />
            ) : detail.data ? (
              <ResultDetailPanel
                result={detail.data.result}
                labels={detail.data.candidate_labels}
                status={detail.data.status}
                paperNote={detail.data.paper_note}
              />
            ) : (
              <EmptyState>선택한 region 결과가 없습니다.</EmptyState>
            )}
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card title="Final vote share" subtitle="final_outcome.vote_share_by_candidate">
              {detail.data ? (
                <EChart
                  option={outcomeOption(detail.data.result, detail.data.candidate_labels)}
                  height={330}
                />
              ) : (
                <LoadingState />
              )}
            </Card>
            <Card title="Poll trajectory" subtitle="support_by_candidate over timestep">
              {detail.data ? (
                <EChart
                  option={trajectoryOption(detail.data.result, detail.data.candidate_labels)}
                  height={330}
                />
              ) : (
                <LoadingState />
              )}
            </Card>
          </div>

          <Card
            title="Demographic breakdown"
            subtitle="age, education, district slices from the selected artifact"
            right={
              <div className="flex rounded-md border border-zinc-200 p-0.5 text-xs dark:border-zinc-700">
                {[
                  ['by_age_group', 'age'],
                  ['by_education', 'edu'],
                  ['by_district', 'district'],
                ].map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setBreakdownKey(key as BreakdownKey)}
                    className={[
                      'rounded px-2 py-1',
                      breakdownKey === key
                        ? 'bg-zinc-900 text-zinc-50 dark:bg-zinc-100 dark:text-zinc-950'
                        : 'text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100',
                    ].join(' ')}
                  >
                    {label}
                  </button>
                ))}
              </div>
            }
          >
            {detail.data ? (
              <EChart
                option={demographicsOption(
                  detail.data.result,
                  detail.data.candidate_labels,
                  breakdownKey,
                  theme,
                )}
                height={390}
              />
            ) : (
              <LoadingState />
            )}
          </Card>
        </div>

        <aside className="space-y-6">
          <Card title="Runtime diagnostics" subtitle="meta.voter_stats + pool_stats">
            <DiagnosticsPanel summary={selectedSummary} result={detail.data?.result} />
          </Card>

          <Card title="Policy envelope" subtitle="policy.json + capacity_probe.json">
            {policy.isLoading ? (
              <LoadingState />
            ) : policy.error ? (
              <ErrorState error={policy.error} retry={policy.refetch} />
            ) : policy.data ? (
            <PolicyPanel data={policy.data} selectedRegion={activeRegion} />
            ) : (
              <EmptyState>policy artifact가 없습니다.</EmptyState>
            )}
          </Card>

          <Card
            title="Ontology events used"
            subtitle={kg.data?.source_path ?? 'region/timestep snapshot'}
            right={kg.data ? <StatusBadge status={kg.data.status} /> : null}
          >
            {kg.isLoading ? (
              <LoadingState />
            ) : kg.error ? (
              <ErrorState error={kg.error} retry={kg.refetch} />
            ) : (
              <KgPanel kgNodes={kg.data?.nodes.length ?? 0} kgEdges={kg.data?.edges.length ?? 0} result={detail.data?.result} />
            )}
          </Card>

          <Card title="Virtual interviews" subtitle="qualitative voter-agent output">
            <InterviewPanel result={detail.data?.result} labels={detail.data?.candidate_labels ?? {}} />
          </Card>
        </aside>
      </div>
    </div>
  )
}

function HeroMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="min-w-24 rounded-lg border border-white/10 bg-white/5 px-3 py-2">
      <div className="text-[10px] uppercase text-zinc-400">{label}</div>
      <div className="mt-1 font-mono text-xl text-white">{NF.format(value)}</div>
    </div>
  )
}

function RegionArtifactButton({
  region,
  active,
  onClick,
}: {
  region: ResultRegionSummary
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'min-h-36 rounded-lg border px-4 py-3 text-left transition-colors',
        active
          ? 'border-emerald-500 bg-emerald-500/10'
          : 'border-zinc-200 hover:border-zinc-400 dark:border-zinc-800 dark:hover:border-zinc-600',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-medium text-zinc-900 dark:text-zinc-100">{region.label}</div>
          <div className="mt-0.5 text-[11px] text-zinc-500 dark:text-zinc-400">
            {region.region_id}
          </div>
        </div>
        <StatusBadge status={region.status} />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
        <SmallDatum label="n" value={region.persona_n} />
        <SmallDatum label="T" value={region.timestep_count} />
        <SmallDatum label="turnout" value={region.turnout == null ? '—' : PF.format(region.turnout)} />
        <SmallDatum label="fail" value={region.parse_fail} />
      </div>
      <div className="mt-3 truncate text-xs text-zinc-600 dark:text-zinc-300">
        {region.winner_label ?? region.winner ?? 'winner 없음'}
      </div>
    </button>
  )
}

function SmallDatum({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="text-[10px] uppercase text-zinc-500 dark:text-zinc-400">{label}</div>
      <div className="font-mono text-sm text-zinc-900 dark:text-zinc-100">
        {typeof value === 'number' ? NF.format(value) : value}
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: ResultArtifactStatus }) {
  const meta = STATUS_META[status] ?? STATUS_META.missing
  return (
    <span
      className={[
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium',
        meta.className,
      ].join(' ')}
    >
      <span className={['h-1.5 w-1.5 rounded-full', meta.dot].join(' ')} />
      {meta.label}
    </span>
  )
}

function ResultDetailPanel({
  result,
  labels,
  status,
  paperNote,
}: {
  result: ScenarioResult
  labels: Record<string, string>
  status: ResultArtifactStatus
  paperNote: string
}) {
  const final = result.final_outcome ?? {}
  const winner = final.winner ? labels[final.winner] ?? final.winner : '—'
  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
      <div className="grid grid-cols-2 gap-3">
        <MetricCell label="winner" value={winner} />
        <MetricCell label="turnout" value={final.turnout == null ? '—' : PF.format(final.turnout)} />
        <MetricCell label="personas" value={NF.format(result.persona_n ?? 0)} />
        <MetricCell label="timesteps" value={NF.format(result.timestep_count ?? 0)} />
      </div>
      <div className="rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-700 dark:border-zinc-800 dark:bg-zinc-950/50 dark:text-zinc-300">
        <div className="flex items-center gap-2">
          <StatusBadge status={status} />
          <span className="font-mono text-xs text-zinc-500 dark:text-zinc-400">
            {result.scenario_id}
          </span>
        </div>
        <p className="mt-3 leading-6">{paperNote}</p>
      </div>
      <div className="lg:col-span-2">
        <CandidateRoster result={result} labels={labels} />
      </div>
    </div>
  )
}

function CandidateRoster({
  result,
  labels,
}: {
  result: ScenarioResult
  labels: Record<string, string>
}) {
  const finalShares = result.final_outcome?.vote_share_by_candidate ?? {}
  if (result.candidates.length === 0) return null
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {result.candidates.map((candidate) => {
        const label = labels[candidate.id] ?? candidate.name ?? candidate.id
        const partyLogo = kgPartyAsset({
          id: candidate.party,
          label: candidate.party,
          attrs: { party_id: candidate.party },
        })
        const portrait = kgPersonAsset({
          id: candidate.id,
          label,
          attrs: { candidate_id: candidate.id, name: candidate.name, party: candidate.party },
        })
        const share = finalShares[candidate.id]
        const color = candidateColor(candidate, candidate.id)
        return (
          <article
            key={candidate.id}
            className="relative overflow-hidden rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-3 dark:border-zinc-800 dark:bg-zinc-950/40"
          >
            <div
              className="absolute inset-x-0 top-0 h-1"
              style={{ backgroundColor: color }}
            />
            <div className="flex items-center gap-3">
              <div
                className="grid h-14 w-14 shrink-0 place-items-center overflow-hidden rounded-full border bg-white dark:bg-zinc-900"
                style={{ borderColor: color }}
              >
                {portrait ? (
                  <img
                    src={portrait}
                    alt={`${label} profile`}
                    className="h-full w-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <span className="text-lg font-semibold" style={{ color }}>
                    {label.charAt(0)}
                  </span>
                )}
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                  {label}
                </div>
                <div className="mt-1 flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
                  {partyLogo ? (
                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full border border-zinc-200 bg-white p-1 shadow-sm">
                      <img
                        src={partyLogo}
                        alt={`${candidate.party} logo`}
                        className="h-full w-full object-contain"
                        loading="lazy"
                      />
                    </span>
                  ) : (
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: color }}
                    />
                  )}
                  <span className="truncate">{candidate.party}</span>
                </div>
              </div>
              <div className="font-mono text-sm text-zinc-900 dark:text-zinc-100">
                {typeof share === 'number' ? PF.format(share) : '—'}
              </div>
            </div>
          </article>
        )
      })}
    </div>
  )
}

function MetricCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3 dark:border-zinc-800 dark:bg-zinc-950/40">
      <div className="text-[10px] uppercase text-zinc-500 dark:text-zinc-400">{label}</div>
      <div className="mt-1 truncate font-mono text-lg text-zinc-900 dark:text-zinc-100">
        {value}
      </div>
    </div>
  )
}

function DiagnosticsPanel({
  summary,
  result,
}: {
  summary?: ResultRegionSummary
  result?: ScenarioResult
}) {
  const meta = result?.meta as Record<string, unknown> | undefined
  const voter = (meta?.voter_stats ?? {}) as Record<string, unknown>
  const pool = (meta?.pool_stats ?? {}) as Record<string, unknown>
  const calls = Number(voter.calls ?? pool.total_calls ?? summary?.total_calls ?? 0)
  const parseFail = Number(voter.parse_fail ?? summary?.parse_fail ?? 0)
  const abstain = Number(voter.abstain ?? summary?.abstain ?? 0)
  const failRate = calls > 0 ? parseFail / calls : 0
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <SmallDatum label="calls" value={calls} />
        <SmallDatum label="parse fail" value={parseFail} />
        <SmallDatum label="abstain" value={abstain} />
        <SmallDatum label="fail rate" value={PF.format(failRate)} />
        <SmallDatum label="wall" value={formatSeconds(Number(summary?.wall_seconds ?? 0))} />
        <SmallDatum
          label="latency"
          value={
            summary?.mean_latency_ms == null
              ? '—'
              : `${NF.format(Math.round(summary.mean_latency_ms))} ms`
          }
        />
      </div>
      <div className="rounded-lg border border-zinc-200 px-3 py-2 text-xs dark:border-zinc-800">
        <div className="text-zinc-500 dark:text-zinc-400">provider / model</div>
        <div className="mt-1 break-words font-mono text-zinc-800 dark:text-zinc-200">
          {summary?.provider ?? String(pool.provider ?? '—')} /{' '}
          {summary?.model ?? String(pool.model ?? '—')}
        </div>
      </div>
    </div>
  )
}

function PolicyPanel({
  data,
  selectedRegion,
}: {
  data: {
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
    warnings: string[]
  }
  selectedRegion: string | null
}) {
  const selectedPlan = data.regions.find((r) => r.region_id === selectedRegion)
  const rpm = data.capacity_probe?.total_rpm
  return (
    <div className="space-y-3 text-sm">
      <div className="grid grid-cols-2 gap-3">
        <SmallDatum label="planned n" value={selectedPlan?.persona_n ?? '—'} />
        <SmallDatum label="planned T" value={selectedPlan?.timesteps ?? '—'} />
        <SmallDatum label="interviews" value={selectedPlan?.interview_n ?? '—'} />
        <SmallDatum label="probe rpm" value={typeof rpm === 'number' ? rpm : '—'} />
      </div>
      <div className="rounded-lg border border-zinc-200 px-3 py-2 text-xs dark:border-zinc-800">
        <div className="text-zinc-500 dark:text-zinc-400">capacity model</div>
        <div className="mt-1 break-words font-mono text-zinc-800 dark:text-zinc-200">
          {data.provider ?? '—'} / {data.model ?? '—'}
        </div>
      </div>
      {data.warnings.length > 0 && (
        <p className="text-xs text-amber-700 dark:text-amber-300">
          {data.warnings.join(' ')}
        </p>
      )}
    </div>
  )
}

function KgPanel({
  kgNodes,
  kgEdges,
  result,
}: {
  kgNodes: number
  kgEdges: number
  result?: ScenarioResult
}) {
  const events = result?.kg_events_used ?? []
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-3">
        <SmallDatum label="nodes" value={kgNodes} />
        <SmallDatum label="edges" value={kgEdges} />
        <SmallDatum label="events" value={events.length} />
      </div>
      {events.length === 0 ? (
        <EmptyState>이 artifact에는 kg_events_used가 없습니다.</EmptyState>
      ) : (
        <div className="max-h-72 space-y-2 overflow-auto pr-1">
          {events.map((event, index) => (
            <div
              key={`${event.event_id}-${index}`}
              className="rounded-lg border border-zinc-200 px-3 py-2 text-xs dark:border-zinc-800"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-zinc-900 dark:text-zinc-100">
                  {event.type}
                </span>
                <span className="text-zinc-500 dark:text-zinc-400">t={event.timestep}</span>
              </div>
              <div className="mt-1 truncate text-zinc-600 dark:text-zinc-300">
                {event.event_id} → {event.target}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function InterviewPanel({
  result,
  labels,
}: {
  result?: ScenarioResult
  labels: Record<string, string>
}) {
  const interviews = result?.virtual_interviews ?? []
  if (interviews.length === 0) {
    return <EmptyState>virtual_interviews가 없습니다.</EmptyState>
  }
  return (
    <div className="max-h-96 space-y-3 overflow-auto pr-1">
      {interviews.map((item) => (
        <figure
          key={item.persona_id}
          className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-3 dark:border-zinc-800 dark:bg-zinc-950/40"
        >
          <blockquote className="text-sm leading-6 text-zinc-800 dark:text-zinc-200">
            “{item.reason}”
          </blockquote>
          <figcaption className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">
            {labels[item.vote ?? ''] ?? item.vote ?? 'abstain'} · t={item.timestep}
          </figcaption>
          {item.key_factors && item.key_factors.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {item.key_factors.map((factor) => (
                <span
                  key={factor}
                  className="rounded-full bg-zinc-200 px-2 py-0.5 text-[11px] text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
                >
                  {factor}
                </span>
              ))}
            </div>
          )}
        </figure>
      ))}
    </div>
  )
}

function outcomeOption(
  result: ScenarioResult,
  labels: Record<string, string>,
): LooseEChartsOption {
  const shares = result.final_outcome?.vote_share_by_candidate ?? {}
  const candidates = candidateMap(result.candidates)
  const items = Object.entries(shares).sort((a, b) => b[1] - a[1])
  if (items.length === 0) {
    return emptyOption('final_outcome 비어있음')
  }
  return {
    grid: { left: 120, right: 32, top: 16, bottom: 32 },
    tooltip: { trigger: 'axis', valueFormatter: (v: number) => PF.format(v) },
    xAxis: { type: 'value', max: Math.max(1, Math.max(...items.map(([, v]) => v)) * 1.15), axisLabel: { formatter: pctAxis } },
    yAxis: { type: 'category', data: items.map(([id]) => labels[id] ?? id), axisLabel: { width: 108, overflow: 'truncate' } },
    series: [
      {
        type: 'bar',
        data: items.map(([id, value]) => ({
          value,
          itemStyle: { color: candidateColor(candidates[id], id) },
        })),
        label: { show: true, position: 'right', formatter: ({ value }: { value: number }) => PF.format(value) },
        barWidth: 18,
      },
    ],
  }
}

function trajectoryOption(
  result: ScenarioResult,
  labels: Record<string, string>,
): LooseEChartsOption {
  const trajectory = result.poll_trajectory ?? []
  if (trajectory.length === 0) {
    return emptyOption('poll_trajectory 비어있음')
  }
  const candidates = candidateMap(result.candidates)
  const ids = result.candidates.map((c) => c.id)
  return {
    grid: { left: 46, right: 18, top: 36, bottom: 42 },
    tooltip: { trigger: 'axis', valueFormatter: (v: number) => PF.format(v) },
    legend: { top: 0, type: 'scroll' },
    xAxis: { type: 'category', data: trajectory.map((p) => p.date ?? `t=${p.timestep}`) },
    yAxis: { type: 'value', min: 0, max: 1, axisLabel: { formatter: pctAxis } },
    series: ids.map((id) => ({
      name: labels[id] ?? id,
      type: 'line',
      smooth: true,
      symbolSize: 8,
      lineStyle: { width: 3 },
      itemStyle: { color: candidateColor(candidates[id], id) },
      data: trajectory.map((p) => p.support_by_candidate?.[id] ?? 0),
    })),
  }
}

function demographicsOption(
  result: ScenarioResult,
  labels: Record<string, string>,
  key: BreakdownKey,
  theme: 'dark' | 'light',
): LooseEChartsOption {
  const breakdown = result.demographics_breakdown?.[key] ?? {}
  const segments = Object.keys(breakdown)
  if (segments.length === 0) {
    return emptyOption(`${key} 비어있음`)
  }
  const ids = Array.from(
    new Set(segments.flatMap((segment) => Object.keys(breakdown[segment] ?? {}))),
  )
  const candidates = candidateMap(result.candidates)
  return {
    color: ids.map((id) => candidateColor(candidates[id], id)),
    grid: { left: 46, right: 18, top: 34, bottom: key === 'by_district' ? 92 : 44 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v: number) => PF.format(v) },
    legend: { top: 0, type: 'scroll' },
    xAxis: {
      type: 'category',
      data: segments,
      axisLabel: {
        interval: 0,
        rotate: key === 'by_district' ? 35 : 0,
        color: theme === 'dark' ? '#a1a1aa' : '#52525b',
      },
    },
    yAxis: { type: 'value', min: 0, max: 1, axisLabel: { formatter: pctAxis } },
    series: ids.map((id) => ({
      name: labels[id] ?? id,
      type: 'bar',
      stack: 'share',
      data: segments.map((segment) => breakdown[segment]?.[id] ?? 0),
    })),
  }
}

function emptyOption(text: string): LooseEChartsOption {
  return {
    graphic: {
      type: 'text',
      left: 'center',
      top: 'middle',
      style: { text, fill: '#71717a', fontSize: 13 },
    },
  }
}

function candidateMap(candidates: ScenarioCandidate[]) {
  return Object.fromEntries(candidates.map((c) => [c.id, c]))
}

function candidateColor(candidate: ScenarioCandidate | undefined, id: string) {
  return PARTY_COLORS[candidate?.party ?? id] ?? '#10b981'
}

function pctAxis(value: number) {
  return `${Math.round(value * 100)}%`
}

function formatSeconds(value: number) {
  if (!Number.isFinite(value) || value <= 0) return '—'
  if (value < 60) return `${value.toFixed(1)}s`
  return `${Math.floor(value / 60)}m ${Math.round(value % 60)}s`
}
