import { useMemo, useState, type ReactNode } from 'react'
import EChart, { type LooseEChartsOption } from '../charts/EChart'
import { EmptyState, ErrorState, LoadingState } from '../components/States'
import { useKgSnapshot, useResultDetail, useResults } from '../hooks/queries'
import { kgNodeAsset } from '../lib/kgAssetRegistry'
import { useFilter } from '../state/filter'
import { useTheme } from '../state/theme'
import type { KgSnapshotResponse, PollTrajectoryPoint } from '../types/api'

const NF = new Intl.NumberFormat('ko-KR')

const KG_ICON_PATHS = {
  election:
    'M5 6.5h14v11H5z M8 10h8 M8 14h6 M8 3.8v4.4 M16 3.8v4.4',
  contest:
    'M12 3.6l7 4.1v8.6l-7 4.1-7-4.1V7.7z M8.4 12h7.2',
  district:
    'M12 21s6-5.5 6-10.2A6 6 0 0 0 6 10.8C6 15.5 12 21 12 21z M12 8.8a2.1 2.1 0 1 0 0 4.2 2.1 2.1 0 0 0 0-4.2z',
  candidate:
    'M12 11a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4z M5.4 20c1.3-4.3 3.4-6.2 6.6-6.2s5.3 1.9 6.6 6.2',
  party:
    'M6.4 21V4 M6.4 4.6c3.7-1.6 6.7 1.7 11.2.2v8.5c-4.5 1.4-7.5-1.8-11.2-.2',
  narrative:
    'M4.8 6.4c3.9-2.3 10.5-2.3 14.4 0v9.1c-3.9-2.3-10.5-2.3-14.4 0z M8 9.3h8 M8 12.2h5.6',
  press:
    'M4 13.7l11.2-5.2v7L4 13.7z M15.2 8.5l4.8-2.2v11.4l-4.8-2.2 M6.5 14.1l1.3 4.6h3.4l-1.8-3.8',
  poll:
    'M5.2 19V5h13.6v14z M8.2 16v-4.2 M12 16V8.7 M15.8 16v-6.1',
  news:
    'M4.5 6.2h15v11.6h-15z M7.3 9.2h5.2 M7.3 12h9.4 M7.3 14.8h6.3',
  person:
    'M12 11.3a3.4 3.4 0 1 0 0-6.8 3.4 3.4 0 0 0 0 6.8z M6.2 19.5c1.2-3.7 3.1-5.4 5.8-5.4s4.6 1.7 5.8 5.4',
  source:
    'M5.2 18.8V6.2h8.4l5.2 5.2v7.4z M13.6 6.2v5.2h5.2 M8.2 14.3h6.8',
  issue:
    'M12 4.2v15.6 M6.5 8.4h11 M7.2 8.4l-3 6h6z M16.8 8.4l-3 6h6z',
  cohort:
    'M5 6.2h14v11.6H5z M5 10h14 M5 13.8h14 M9.7 6.2v11.6 M14.3 6.2v11.6',
  node:
    'M12 4.2a7.8 7.8 0 1 0 0 15.6 7.8 7.8 0 0 0 0-15.6z M12 8.4a3.6 3.6 0 1 0 0 7.2 3.6 3.6 0 0 0 0-7.2z',
} as const

interface NodeTypeMeta {
  label: string
  color: string
  symbol: string
  rank: number
  layer: number
}

const NODE_TYPES: Record<string, NodeTypeMeta> = {
  Election: {
    label: '선거',
    color: '#e8c46b',
    symbol: KG_ICON_PATHS.election,
    rank: 0,
    layer: 0,
  },
  Contest: {
    label: '선거구',
    color: '#9bd06a',
    symbol: KG_ICON_PATHS.contest,
    rank: 1,
    layer: 1,
  },
  District: {
    label: '행정구역',
    color: '#f37a7a',
    symbol: KG_ICON_PATHS.district,
    rank: 2,
    layer: 1,
  },
  Candidate: {
    label: '후보',
    color: '#f0a868',
    symbol: KG_ICON_PATHS.candidate,
    rank: 3,
    layer: 2,
  },
  Party: {
    label: '정당',
    color: '#c87f9e',
    symbol: KG_ICON_PATHS.party,
    rank: 4,
    layer: 2,
  },
  NarrativeFrame: {
    label: '내러티브',
    color: '#b48cd9',
    symbol: KG_ICON_PATHS.narrative,
    rank: 5,
    layer: 3,
  },
  PressConference: {
    label: '기자회견',
    color: '#6fc4d9',
    symbol: KG_ICON_PATHS.press,
    rank: 6,
    layer: 3,
  },
  PollPublication: {
    label: '여론조사',
    color: '#f08fb8',
    symbol: KG_ICON_PATHS.poll,
    rank: 7,
    layer: 3,
  },
  MediaEvent: {
    label: '뉴스 이벤트',
    color: '#6ea0e0',
    symbol: KG_ICON_PATHS.news,
    rank: 8,
    layer: 3,
  },
  News: {
    label: '뉴스',
    color: '#6ea0e0',
    symbol: KG_ICON_PATHS.news,
    rank: 9,
    layer: 3,
  },
  Person: {
    label: '인물',
    color: '#80d4c0',
    symbol: KG_ICON_PATHS.person,
    rank: 10,
    layer: 3,
  },
  Source: {
    label: '출처',
    color: '#8ca1b8',
    symbol: KG_ICON_PATHS.source,
    rank: 11,
    layer: 4,
  },
  PolicyIssue: {
    label: '정책/이슈',
    color: '#d5a36c',
    symbol: KG_ICON_PATHS.issue,
    rank: 12,
    layer: 3,
  },
  CohortPrior: {
    label: '코호트 prior',
    color: '#e5d06f',
    symbol: KG_ICON_PATHS.cohort,
    rank: 13,
    layer: 3,
  },
}

const DEFAULT_NODE: NodeTypeMeta = {
  label: '노드',
  color: '#94a3b8',
  symbol: KG_ICON_PATHS.node,
  rank: 50,
  layer: 3,
}

const RELATION_COLORS: Record<string, string> = {
  inElection: '#e8c46b',
  heldIn: '#f37a7a',
  candidateIn: '#f0a868',
  belongsTo: '#c87f9e',
  publishesPoll: '#f08fb8',
  about: '#7dd3c0',
  framedBy: '#b48cd9',
  covers: '#6ea0e0',
  measures: '#f08fb8',
  memberOf: '#c87f9e',
  runsIn: '#f0a868',
  partOf: '#f37a7a',
  attributedTo: '#8ca1b8',
  speakerIs: '#80d4c0',
  affiliatedTo: '#c87f9e',
  damagesParty: '#f37a7a',
  appliesToRegion: '#d5a36c',
  leansToward: '#e5d06f',
  mentions: '#6fc4d9',
}

export default function KGPage() {
  const { theme } = useTheme()
  const { filter } = useFilter()
  const results = useResults()
  const [selectedTimestep, setSelectedTimestep] = useState<number | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)

  const firstRegion = useMemo(() => {
    const regions = results.data?.regions ?? []
    return (
      regions.find((r) => r.status === 'live')?.region_id ??
      regions[0]?.region_id ??
      null
    )
  }, [results.data?.regions])

  const activeRegion = filter.region ?? firstRegion
  const kg = useKgSnapshot(activeRegion, selectedTimestep)
  const detail = useResultDetail(activeRegion)
  const activeTimestep = selectedTimestep ?? kg.data?.timestep ?? null

  const nodeIndex = useMemo(() => buildNodeIndex(kg.data), [kg.data])
  const effectiveSelectedNodeId =
    selectedNodeId && nodeIndex.nodes.has(selectedNodeId) ? selectedNodeId : null

  const graphOption = useMemo(() => {
    if (!kg.data) return emptyGraphOption()
    return kgGraphOption(kg.data, theme, effectiveSelectedNodeId)
  }, [kg.data, theme, effectiveSelectedNodeId])

  const graphEvents = useMemo(
    () => ({
      click: (params: unknown) => {
        const event = params as {
          dataType?: string
          data?: Record<string, unknown>
        }
        if (event.dataType !== 'node') return
        const id = readString(event.data ?? null, ['rawId', 'id'], '')
        if (id) setSelectedNodeId(id)
      },
    }),
    [],
  )

  const categoryStats = useMemo(
    () => (kg.data ? kgCategoryStats(kg.data) : []),
    [kg.data],
  )

  const selectedNode = effectiveSelectedNodeId
    ? nodeIndex.nodes.get(effectiveSelectedNodeId) ?? null
    : null
  const selectedLinks = effectiveSelectedNodeId
    ? nodeIndex.links.get(effectiveSelectedNodeId) ?? []
    : []

  if (results.isLoading) {
    return <LoadingState label="region artifacts를 불러오는 중..." />
  }
  if (results.error) {
    return <ErrorState error={results.error} retry={results.refetch} />
  }

  const activeSummary = results.data?.regions.find((region) => region.region_id === activeRegion)
  const activeTimestepPoint =
    detail.data?.result.poll_trajectory.find((point) => point.timestep === activeTimestep) ?? null

  return (
    <div className="dark">
      <div className="relative overflow-hidden rounded-lg border border-[#1f2832] bg-[#0a0e13] text-[#e7e5dc] shadow-2xl shadow-black/30">
        <div
          className="pointer-events-none absolute inset-0 opacity-80"
          style={{
            backgroundImage:
              'radial-gradient(circle at 18% 0%, rgba(125,211,192,0.13), transparent 28%), radial-gradient(circle at 82% 8%, rgba(232,196,107,0.09), transparent 24%), linear-gradient(180deg, rgba(15,20,27,0.96), rgba(10,14,19,1))',
          }}
        />

        <div className="relative">
          <header className="flex flex-col gap-5 border-b border-[#1f2832] px-5 py-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-[#5a6470]">
                Temporal Ontology
              </p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-[#f3efe4]">
                온톨로지
              </h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-[#8f9aa5]">
                region/timestep별 ontology snapshot과 result artifact가 실제로 참조한
                event trail을 함께 확인합니다.
              </p>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <KgMetric label="Nodes" value={kg.data?.nodes.length ?? 0} />
              <KgMetric label="Edges" value={kg.data?.edges.length ?? 0} />
              <KgMetric label="Snapshots" value={kg.data?.snapshots.length ?? 0} />
            </div>
          </header>

          <section className="border-b border-[#1f2832] bg-[#0f141b]/88 px-5 py-4">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="min-w-0">
                <div className="text-sm font-semibold text-[#f3efe4]">
                  {activeSummary?.label ?? activeRegion ?? 'Region'} timeline
                </div>
                <div className="mt-1 truncate font-mono text-[11px] text-[#5a6470]">
                  {kg.data?.source_path ?? 'freshest ontology snapshot selector'}
                </div>
              </div>
              <TimestepControls
                timesteps={kg.data?.available_timesteps ?? []}
                activeTimestep={activeTimestep}
                points={detail.data?.result.poll_trajectory ?? []}
                activePoint={activeTimestepPoint}
                cutoffTs={kg.data?.cutoff_ts ?? null}
                onSelect={setSelectedTimestep}
              />
            </div>
          </section>

          <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
            <section className="overflow-hidden rounded-lg border border-[#1f2832] bg-[#0f141b]">
              <div className="flex flex-col gap-3 border-b border-[#1f2832] px-4 py-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0">
                  <h2 className="text-sm font-semibold text-[#f3efe4]">
                    Ontology snapshot graph
                  </h2>
                  <p className="mt-1 break-all font-mono text-[11px] text-[#5a6470]">
                    {kg.data?.source_path ?? 'source snapshot'}
                  </p>
                </div>
                {kg.data ? <StatusPill status={kg.data.status} pulse /> : null}
              </div>

              <GraphLegend stats={categoryStats} />

              <div
                className="relative min-h-[36rem] border-t border-[#1f2832]"
                style={{
                  backgroundColor: '#0a0e13',
                  backgroundImage:
                    'linear-gradient(rgba(31,40,50,0.55) 1px, transparent 1px), linear-gradient(90deg, rgba(31,40,50,0.55) 1px, transparent 1px), radial-gradient(circle at center, rgba(125,211,192,0.06), transparent 58%)',
                  backgroundSize: '40px 40px, 40px 40px, 100% 100%',
                }}
              >
                {kg.isLoading ? (
                  <div className="px-5">
                    <LoadingState />
                  </div>
                ) : kg.error ? (
                  <div className="p-5">
                    <ErrorState error={kg.error} retry={kg.refetch} />
                  </div>
                ) : kg.data && kg.data.nodes.length > 0 ? (
                  <EChart
                    option={graphOption}
                    height={640}
                    notMerge
                    onEvents={graphEvents}
                  />
                ) : (
                  <div className="p-5">
                    <EmptyState>표시할 ontology node가 없습니다.</EmptyState>
                  </div>
                )}
              </div>
            </section>

            <aside className="space-y-4 xl:sticky xl:top-28 xl:self-start">
              <SidePanel title="Snapshot metadata" subtitle={kg.data?.scenario_id ?? 'scenario'}>
                {kg.data ? (
                  <dl className="space-y-0">
                    <MetaRow label="region" value={kg.data.region_id ?? activeRegion ?? '-'} />
                    <MetaRow
                      label="timestep"
                      value={kg.data.timestep == null ? '-' : `T${kg.data.timestep}`}
                    />
                    <MetaRow
                      label="cutoff"
                      value={formatTimestamp(kg.data.cutoff_ts) ?? '-'}
                    />
                    <MetaRow label="source" value={kg.data.source_path ?? '-'} mono />
                  </dl>
                ) : (
                  <LoadingState />
                )}
              </SidePanel>

              <SidePanel title="Events used by simulation" subtitle="result.kg_events_used">
                {detail.isLoading ? (
                  <LoadingState />
                ) : detail.error ? (
                  <ErrorState error={detail.error} retry={detail.refetch} />
                ) : (
                  <EventTrail events={detail.data?.result.kg_events_used ?? []} />
                )}
              </SidePanel>

              <SidePanel title="Available snapshots" subtitle="all indexed ontology exports">
                <SnapshotList
                  snapshots={kg.data?.snapshots ?? []}
                  activePath={kg.data?.source_path ?? null}
                />
              </SidePanel>
            </aside>
          </div>
        </div>
      </div>
      {selectedNode && (
        <NodeDetailModal
          node={selectedNode}
          links={selectedLinks}
          nodeMap={nodeIndex.nodes}
          sourcePath={kg.data?.source_path ?? null}
          regionId={kg.data?.region_id ?? activeRegion}
          timestep={activeTimestep}
          onClose={() => setSelectedNodeId(null)}
          onSelect={setSelectedNodeId}
        />
      )}
    </div>
  )
}

function TimestepControls({
  timesteps,
  activeTimestep,
  points,
  activePoint,
  cutoffTs,
  onSelect,
}: {
  timesteps: number[]
  activeTimestep: number | null
  points: PollTrajectoryPoint[]
  activePoint: PollTrajectoryPoint | null
  cutoffTs: string | null
  onSelect: (timestep: number) => void
}) {
  if (timesteps.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-[#2a3340] px-3 py-2 font-mono text-[11px] text-[#5a6470]">
        snapshot timestep 없음
      </div>
    )
  }

  const pointsByTimestep = new Map(points.map((point) => [point.timestep, point]))
  const activeDate =
    activePoint?.date ??
    (cutoffTs ? formatTimestamp(cutoffTs) : null) ??
    (activeTimestep == null ? null : `T${activeTimestep}`)
  const activeTurnout =
    activePoint?.turnout_intent == null ? null : `${(activePoint.turnout_intent * 100).toFixed(1)}%`
  const activeVariance =
    activePoint?.consensus_var == null ? null : activePoint.consensus_var.toFixed(3)

  return (
    <div className="w-full max-w-3xl">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
        <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-[#5a6470]">
          timestep
        </span>
        <div className="flex flex-wrap items-center gap-2 font-mono text-[10px] text-[#7a8590]">
          {activeDate && <span>{activeDate}</span>}
          {activeTurnout && <span>turnout {activeTurnout}</span>}
          {activeVariance && <span>var {activeVariance}</span>}
        </div>
      </div>
      <div className="grid gap-2 sm:grid-cols-4">
        {timesteps.map((timestep, index) => {
          const point = pointsByTimestep.get(timestep)
          const active = timestep === activeTimestep
          const dateLabel = point?.date ? shortDate(point.date) : index === timesteps.length - 1 ? 'latest' : 'snapshot'
          const turnout = point?.turnout_intent == null ? null : `${(point.turnout_intent * 100).toFixed(0)}%`
          return (
            <button
              key={timestep}
              type="button"
              onClick={() => onSelect(timestep)}
              className={[
                'relative min-h-16 rounded-lg border px-3 py-2 text-left transition-colors',
                active
                  ? 'border-[#7dd3c0]/55 bg-[#7dd3c0]/12 text-[#7dd3c0] shadow-[0_0_20px_rgba(125,211,192,0.12)]'
                  : 'border-[#1f2832] bg-[#141a23] text-[#8f9aa5] hover:border-[#2a3340] hover:text-[#d4d4d8]',
              ].join(' ')}
            >
              {index > 0 && (
                <span className="absolute right-full top-1/2 hidden h-px w-2 bg-[#2a3340] sm:block" />
              )}
              <span className="block font-mono text-xs font-semibold">T{timestep}</span>
              <span className="mt-1 block truncate text-xs">{dateLabel}</span>
              <span className="mt-1 block font-mono text-[10px] text-[#5a6470]">
                {turnout ? `turnout ${turnout}` : 'KG snapshot'}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function KgMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="min-w-24 rounded-lg border border-[#1f2832] bg-[#0f141b]/80 px-4 py-3 text-right">
      <div className="font-mono text-[9px] uppercase tracking-[0.16em] text-[#5a6470]">
        {label}
      </div>
      <div className="mt-1 font-mono text-xl font-semibold text-[#f3efe4]">
        {NF.format(value)}
      </div>
    </div>
  )
}

function SidePanel({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: ReactNode
}) {
  return (
    <section className="rounded-lg border border-[#1f2832] bg-[#0f141b]/90 px-4 py-4">
      <div className="mb-4">
        <h3 className="text-[13px] font-semibold text-[#f3efe4]">{title}</h3>
        <p className="mt-1 break-all font-mono text-[10px] tracking-[0.04em] text-[#5a6470]">
          {subtitle}
        </p>
      </div>
      {children}
    </section>
  )
}

function StatusPill({ status, pulse = false }: { status: string; pulse?: boolean }) {
  const tone = statusTone(status)
  return (
    <span
      className={[
        'inline-flex items-center gap-2 rounded-full border px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.08em]',
        tone.className,
      ].join(' ')}
    >
      <span
        className={[
          'h-1.5 w-1.5 rounded-full',
          tone.dot,
          pulse && status === 'live' ? 'animate-pulse' : '',
        ].join(' ')}
      />
      {status}
    </span>
  )
}

function statusTone(status: string) {
  if (status === 'live') {
    return {
      className: 'border-[#7dd3c0]/30 bg-[#7dd3c0]/10 text-[#7dd3c0]',
      dot: 'bg-[#7dd3c0]',
    }
  }
  if (status === 'missing') {
    return {
      className: 'border-red-400/30 bg-red-400/10 text-red-300',
      dot: 'bg-red-300',
    }
  }
  return {
    className: 'border-amber-300/30 bg-amber-300/10 text-amber-200',
    dot: 'bg-amber-200',
  }
}

function MetaRow({
  label,
  value,
  mono,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="grid grid-cols-[5.5rem_1fr] gap-3 border-b border-[#1f2832] py-2.5 last:border-b-0">
      <dt className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#5a6470]">
        {label}
      </dt>
      <dd
        className={[
          'min-w-0 break-words text-right text-xs text-[#d8d6cc]',
          mono ? 'font-mono text-[10px] leading-5' : 'font-mono',
        ].join(' ')}
      >
        {value}
      </dd>
    </div>
  )
}

function GraphLegend({
  stats,
}: {
  stats: Array<{ kind: string; label: string; count: number; color: string }>
}) {
  if (stats.length === 0) {
    return (
      <div className="border-b border-[#1f2832] px-4 py-3 font-mono text-[11px] text-[#5a6470]">
        category index 없음
      </div>
    )
  }

  return (
    <div className="flex flex-wrap gap-x-5 gap-y-2 border-b border-[#1f2832] bg-[#141a23]/45 px-4 py-3">
      {stats.map((stat) => (
        <div key={stat.kind} className="inline-flex items-center gap-2 text-[11px] text-[#b0b8c0]">
          <InlineNodeIcon kind={stat.kind} size={16} />
          <span>{stat.label}</span>
          <span className="font-mono text-[10px] text-[#5a6470]">{stat.count}</span>
        </div>
      ))}
    </div>
  )
}

function NodeDetailModal({
  node,
  links,
  nodeMap,
  sourcePath,
  regionId,
  timestep,
  onClose,
  onSelect,
}: {
  node: Record<string, unknown>
  links: Array<Record<string, unknown>>
  nodeMap: Map<string, Record<string, unknown>>
  sourcePath: string | null
  regionId: string | null
  timestep: number | null
  onClose: () => void
  onSelect: (id: string) => void
}) {
  const id = readString(node, ['id', 'event_id', 'name'], 'node')
  const kind = nodeKind(node)
  const meta = metaFor(kind)
  const attrs = readRecord(node.attrs)
  const sourceUrl =
    readString(node, ['source_url', 'url', 'href'], '') ||
    readString(attrs, ['source_url', 'url', 'url_root', 'article_url', 'href'], '')
  const title = readString(node, ['label', 'name', 'title'], id)
  const summary = nodeSummary(node, attrs)
  const profileMeta = profileMetaItems(node, attrs)
  const coreRows = ([
    ['type', meta.label],
    ['id', id],
    ['timestamp', formatTimestamp(readString(node, ['ts'], '')) ?? readString(node, ['ts'], '-')],
    ['region', readString(node, ['region_id'], '-')],
    ['sentiment', formatMaybeNumber(node.sentiment)],
    ['frame', readString(node, ['frame_id'], '-')],
  ] as Array<[string, string]>).filter(([, value]) => value && value !== '-')
  const attrRows = nodeAttrRows(attrs)
  const profileUrl = profileImageUrl(node, attrs)
  const visualKind = kind === 'Candidate' || kind === 'Person' || kind === 'Party' || kind === 'District'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#030508]/78 p-4 text-[#e7e5dc] backdrop-blur-md"
      role="presentation"
      onMouseDown={onClose}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-label={`${title} detail`}
        className="max-h-[92vh] w-full max-w-5xl overflow-hidden rounded-xl border border-[#2a3340] bg-[#0f141b] shadow-[0_30px_100px_rgba(0,0,0,0.58)]"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div
          className="relative border-b border-[#1f2832] px-6 py-6"
          style={{
            background: `linear-gradient(135deg, ${hexToRgba(meta.color, 0.2)}, transparent 58%), #111821`,
          }}
        >
          <button
            type="button"
            onClick={onClose}
            className="absolute right-4 top-4 grid h-9 w-9 place-items-center rounded-full border border-[#2a3340] bg-[#0a0e13]/70 text-xl leading-none text-[#b0b8c0] transition-colors hover:border-[#7dd3c0]/45 hover:text-[#f3efe4]"
            aria-label="Close detail modal"
          >
            ×
          </button>

          <div className="grid gap-5 pr-10 sm:grid-cols-[9.5rem_1fr] sm:items-center">
            <div
              className={[
                'grid h-36 w-36 shrink-0 place-items-center overflow-hidden rounded-full border bg-[#0a0e13]',
                visualKind ? '' : 'rounded-2xl',
              ].join(' ')}
              style={{
                borderColor: hexToRgba(meta.color, 0.55),
                boxShadow: `0 0 0 4px rgba(0,0,0,0.28), 0 18px 42px ${hexToRgba(meta.color, 0.2)}`,
              }}
            >
              <NodeHeroVisual
                node={node}
                attrs={attrs}
                kind={kind}
                title={title}
                color={meta.color}
                profileUrl={profileUrl}
              />
            </div>

            <div className="min-w-0">
              <div
                className="inline-flex items-center gap-2 rounded-full border px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.12em]"
                style={{
                  color: meta.color,
                  borderColor: hexToRgba(meta.color, 0.35),
                  backgroundColor: hexToRgba(meta.color, 0.1),
                }}
              >
                <InlineNodeIcon kind={kind} size={13} />
                {meta.label}
              </div>
              <h2 className="mt-3 break-words text-3xl font-semibold tracking-[-0.02em] text-[#f3efe4]">
                {title}
              </h2>
              {profileMeta.length > 0 && (
                <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-[#8f9aa5]">
                  {profileMeta.map((item, index) => (
                    <span key={`${item}-${index}`} className="inline-flex items-center gap-2">
                      {index > 0 && <span className="text-[#3a4450]">·</span>}
                      <span>{item}</span>
                    </span>
                  ))}
                </div>
              )}
              <div className="mt-3 break-all font-mono text-[11px] text-[#5a6470]">{id}</div>
              {summary && (
                <blockquote
                  className="mt-4 max-w-3xl border-l-2 pl-4 text-sm leading-6 text-[#c7cbd0]"
                  style={{ borderColor: meta.color }}
                >
                  {summary}
                </blockquote>
              )}
            </div>
          </div>
        </div>

        <div className="max-h-[calc(92vh-14rem)] overflow-y-auto p-6">
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_22rem]">
            <div className="space-y-5">
              <ModalSection title="Attributes">
                {attrRows.length > 0 ? (
                  <div className="overflow-hidden rounded-lg border border-[#1f2832]">
                    {attrRows.map(([label, value]) => (
                      <InspectorRow key={label} label={label} value={value} multiline />
                    ))}
                  </div>
                ) : (
                  <EmptyState>기록된 속성이 없습니다.</EmptyState>
                )}
              </ModalSection>

              {kind === 'CohortPrior' && attrs ? <CohortPriorBlock attrs={attrs} /> : null}

              <ModalSection title={`Relations · ${links.length}`}>
                {links.length === 0 ? (
                  <p className="rounded-md border border-dashed border-[#2a3340] px-3 py-2 text-xs text-[#7a8590]">
                    연결된 edge가 없습니다.
                  </p>
                ) : (
                  <div className="grid gap-2 sm:grid-cols-2">
                    {links.map((link, index) => {
                      const source = edgeSource(link)
                      const target = edgeTarget(link)
                      const rel = edgeRel(link, index)
                      const neighborId = source === id ? target : source
                      const neighbor = nodeMap.get(neighborId)
                      const neighborKind = neighbor ? nodeKind(neighbor) : 'node'
                      const neighborMeta = metaFor(neighborKind)
                      return (
                        <button
                          key={`${source}-${target}-${rel}-${index}`}
                          type="button"
                          onClick={() => {
                            if (neighborId) onSelect(neighborId)
                          }}
                          className="grid w-full grid-cols-[22px_1fr_auto] items-center gap-3 rounded-lg border border-[#1f2832] bg-[#141a23]/65 px-3 py-2 text-left transition-colors hover:border-[#2a3340] hover:bg-[#1a2230]"
                        >
                          <InlineNodeIcon kind={neighborKind} size={20} />
                          <span className="min-w-0">
                            <span className="block truncate text-xs font-medium text-[#d8d6cc]">
                              {neighbor
                                ? readString(neighbor, ['label', 'name', 'title'], neighborId)
                                : neighborId}
                            </span>
                            <span className="mt-0.5 block font-mono text-[10px] text-[#5a6470]">
                              {source === id ? '→' : '←'} {rel} · {neighborMeta.label}
                            </span>
                          </span>
                          <span className="font-mono text-[10px] text-[#5a6470]">OPEN</span>
                        </button>
                      )
                    })}
                  </div>
                )}
              </ModalSection>
            </div>

            <div className="space-y-5">
              {sourceUrl && (
                <a
                  href={sourceUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex w-full items-center justify-center rounded-lg border border-[#7dd3c0]/35 bg-[#7dd3c0]/10 px-3 py-2 text-sm font-medium text-[#7dd3c0] transition-colors hover:bg-[#7dd3c0]/15"
                >
                  source 열기
                </a>
              )}

              <ModalSection title="Provenance">
                <div className="overflow-hidden rounded-lg border border-[#1f2832]">
                  {coreRows.map(([label, value]) => (
                    <InspectorRow key={label} label={label} value={value} />
                  ))}
                  <InspectorRow label="snapshot" value={sourcePath ?? '-'} multiline />
                  <InspectorRow label="region" value={regionId ?? '-'} />
                  <InspectorRow label="timestep" value={timestep == null ? '-' : `T${timestep}`} />
                </div>
              </ModalSection>

              <ModalSection title="Tags">
                <div className="flex flex-wrap gap-2">
                  <Tag>{kind}</Tag>
                  {regionId ? <Tag>{regionId}</Tag> : null}
                  {timestep == null ? null : <Tag>T{timestep}</Tag>}
                  <Tag>{links.length} edges</Tag>
                </div>
              </ModalSection>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

function ModalSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.16em] text-[#5a6470]">
        {title}
      </div>
      {children}
    </section>
  )
}

function Tag({ children }: { children: ReactNode }) {
  return (
    <span className="rounded-md border border-[#1f2832] bg-[#141a23] px-2 py-1 font-mono text-[10px] text-[#8f9aa5]">
      {children}
    </span>
  )
}

function NodeHeroVisual({
  node,
  attrs,
  kind,
  title,
  color,
  profileUrl,
}: {
  node: Record<string, unknown>
  attrs: Record<string, unknown> | null
  kind: string
  title: string
  color: string
  profileUrl: string
}) {
  if ((kind === 'Candidate' || kind === 'Person') && profileUrl) {
    return (
      <img
        src={profileUrl}
        alt={`${title} profile`}
        className="h-full w-full object-cover"
        loading="lazy"
      />
    )
  }
  if (kind === 'Candidate' || kind === 'Person') {
    return (
      <ProfilePortrait
        name={title}
        gender={readString(attrs, ['gender'], '')}
        age={readNumber(attrs ?? {}, ['age'], 0)}
        color={color}
        size={144}
      />
    )
  }
  if (kind === 'Party' && profileUrl) {
    return (
      <div className="grid h-[78%] w-[78%] place-items-center rounded-full border border-zinc-200 bg-white p-5 shadow-[0_16px_34px_rgba(0,0,0,0.28)]">
        <img
          src={profileUrl}
          alt={`${title} logo`}
          className="h-full w-full object-contain"
          loading="lazy"
        />
      </div>
    )
  }
  if (kind === 'Party') {
    return <PartyEmblem name={title} color={color} size={144} />
  }
  if (kind === 'District') {
    return <DistrictGlyph name={title} color={color} size={144} />
  }
  return <InlineNodeIcon kind={nodeKind(node)} size={88} />
}

function ProfilePortrait({
  name,
  gender,
  age,
  color,
  size,
}: {
  name: string
  gender: string
  age: number
  color: string
  size: number
}) {
  const seed = Math.abs(hashString(name || 'person'))
  const palettes = [
    { bg: '#253240', skin: '#e5bd9a', hair: '#161d28', accent: color },
    { bg: '#332834', skin: '#d8a86b', hair: '#111018', accent: '#c87f9e' },
    { bg: '#1f3340', skin: '#e6b08a', hair: '#181412', accent: '#6fc4d9' },
    { bg: '#33282a', skin: '#dca48a', hair: '#2a1410', accent: '#f0a868' },
    { bg: '#283328', skin: '#dcb898', hair: '#1a1f10', accent: '#9bd06a' },
  ]
  const palette = palettes[seed % palettes.length]
  const longHair = gender === '여' || (seed % 2 === 1 && gender !== '남')
  const senior = age >= 55
  const initial = name.trim().charAt(0) || '?'
  const clipId = `kg-portrait-${seed}`

  return (
    <svg width={size} height={size} viewBox="0 0 120 120" aria-hidden className="block">
      <defs>
        <clipPath id={clipId}>
          <circle cx="60" cy="60" r="58" />
        </clipPath>
        <linearGradient id={`${clipId}-bg`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={palette.bg} />
          <stop offset="100%" stopColor="#0a0e13" />
        </linearGradient>
      </defs>
      <circle cx="60" cy="60" r="58" fill={`url(#${clipId}-bg)`} stroke={palette.accent} strokeWidth="0.8" opacity="0.95" />
      <g clipPath={`url(#${clipId})`}>
        <path
          d={`M8 120 Q30 ${senior ? 92 : 88} 60 ${senior ? 90 : 86} Q90 ${senior ? 92 : 88} 112 120 Z`}
          fill={palette.accent}
          opacity="0.2"
        />
        <path
          d={`M14 120 Q32 ${senior ? 96 : 92} 60 ${senior ? 94 : 90} Q88 ${senior ? 96 : 92} 106 120 Z`}
          fill={palette.accent}
          opacity="0.34"
        />
        <rect x="52" y="78" width="16" height="14" rx="3" fill={palette.skin} />
        <ellipse cx="60" cy="58" rx="22" ry="26" fill={palette.skin} />
        {longHair ? (
          <path
            d="M35 56 Q32 30 60 28 Q88 30 85 56 L84 78 L78 70 Q76 48 60 48 Q44 48 42 70 L36 78 Z"
            fill={palette.hair}
          />
        ) : (
          <path
            d="M38 50 Q36 28 60 28 Q84 28 82 50 Q78 42 60 42 Q42 42 38 50 Z"
            fill={palette.hair}
          />
        )}
        <circle cx="51" cy="58" r="1.6" fill="#0a0e13" />
        <circle cx="69" cy="58" r="1.6" fill="#0a0e13" />
        <path d="M47 53 L55 52" stroke="#0a0e13" strokeWidth="1.4" strokeLinecap="round" />
        <path d="M65 52 L73 53" stroke="#0a0e13" strokeWidth="1.4" strokeLinecap="round" />
        <path d="M55 73 Q60 76 65 73" stroke="#0a0e13" strokeWidth="1.2" fill="none" strokeLinecap="round" />
        {senior && (
          <>
            <path d="M44 64 Q47 65 49 63" stroke="#0a0e13" strokeWidth="0.5" fill="none" opacity="0.42" />
            <path d="M71 63 Q73 65 76 64" stroke="#0a0e13" strokeWidth="0.5" fill="none" opacity="0.42" />
          </>
        )}
      </g>
      <circle cx="60" cy="60" r="58" fill="none" stroke={palette.accent} strokeWidth="0.8" opacity="0.5" />
      <g transform="translate(96, 96)">
        <circle r="14" fill="#0a0e13" stroke={palette.accent} strokeWidth="1" />
        <text
          textAnchor="middle"
          y="4.5"
          fontSize="13"
          fontWeight="700"
          fill={palette.accent}
        >
          {initial}
        </text>
      </g>
    </svg>
  )
}

function PartyEmblem({ name, color, size }: { name: string; color: string; size: number }) {
  const seed = Math.abs(hashString(name || 'party'))
  const gradientId = `kg-party-${seed}`
  const initial = name.trim().charAt(0) || '?'
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" aria-hidden className="block">
      <defs>
        <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.32" />
          <stop offset="100%" stopColor={color} stopOpacity="0.04" />
        </linearGradient>
      </defs>
      <circle cx="60" cy="60" r="58" fill={`url(#${gradientId})`} stroke={color} strokeWidth="1" />
      <circle cx="60" cy="60" r="44" fill="none" stroke={color} strokeWidth="0.7" opacity="0.42" strokeDasharray="2 4" />
      <path d="M38 36v50 M38 39h42l-9 14 9 14H38" fill="none" stroke={color} strokeWidth="3" strokeLinejoin="round" />
      <text textAnchor="middle" x="58" y="66" fontSize="18" fontWeight="800" fill={color}>
        {initial}
      </text>
    </svg>
  )
}

function DistrictGlyph({ name, color, size }: { name: string; color: string; size: number }) {
  const seed = Math.abs(hashString(name || 'district'))
  const points = Array.from({ length: 9 }, (_, index) => {
    const angle = (index / 9) * Math.PI * 2
    const radius = 38 + ((seed >> (index * 2)) % 14)
    return [60 + Math.cos(angle) * radius, 60 + Math.sin(angle) * radius]
  })
  const path = `${points
    .map(([x, y], index) => `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`)
    .join(' ')} Z`
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" aria-hidden className="block">
      <circle cx="60" cy="60" r="58" fill="#0a0e13" stroke="#2a3340" strokeWidth="1" />
      <path d={path} fill={color} opacity="0.16" stroke={color} strokeWidth="1.4" />
      <path d="M24 60H96 M60 24V96" stroke={color} strokeWidth="0.5" opacity="0.34" />
      <circle cx="60" cy="60" r="3.4" fill={color} />
    </svg>
  )
}

function InspectorRow({
  label,
  value,
  multiline = false,
}: {
  label: string
  value: string
  multiline?: boolean
}) {
  return (
    <div className="grid grid-cols-[5.25rem_1fr] gap-2 border-b border-[#1f2832] px-3 py-2 last:border-b-0">
      <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#5a6470]">
        {label}
      </div>
      <div
        className={[
          'min-w-0 break-words text-right text-xs text-[#d8d6cc]',
          multiline ? 'text-left leading-5' : 'font-mono',
        ].join(' ')}
      >
        {value}
      </div>
    </div>
  )
}

function CohortPriorBlock({ attrs }: { attrs: Record<string, unknown> }) {
  const partyLean = parseDictString(readString(attrs, ['party_lean'], ''))
  const entries = Object.entries(partyLean)
    .filter(([, value]) => Number.isFinite(value))
    .sort(([, a], [, b]) => b - a)
  if (entries.length === 0) return null

  return (
    <div className="mt-4 rounded-md border border-[#2a3340] bg-[#141a23]/70 px-3 py-3">
      <div className="mb-3 flex items-center justify-between gap-3">
        <span className="text-xs font-semibold text-[#f3efe4]">cohort party lean</span>
        <span className="font-mono text-[10px] text-[#7a8590]">
          {readString(attrs, ['age_band'], 'ALL')} · {readString(attrs, ['gender'], 'ALL')}
        </span>
      </div>
      <div className="space-y-2">
        {entries.map(([party, value]) => (
          <div key={party}>
            <div className="mb-1 flex items-center justify-between gap-2 font-mono text-[10px]">
              <span className="text-[#b0b8c0]">{party}</span>
              <span className="text-[#7a8590]">{(value * 100).toFixed(1)}%</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded bg-[#0a0e13]">
              <div
                className="h-full rounded bg-[#e5d06f]"
                style={{ width: `${Math.max(2, Math.min(100, value * 100))}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function InlineNodeIcon({ kind, size }: { kind: string; size: number }) {
  const meta = metaFor(kind)
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden
      className="shrink-0"
      style={{ filter: `drop-shadow(0 0 8px ${hexToRgba(meta.color, 0.24)})` }}
    >
      <path
        d={meta.symbol}
        fill="none"
        stroke={meta.color}
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function EventTrail({
  events,
}: {
  events: Array<{ event_id: string; type: string; target: string; timestep: number }>
}) {
  if (events.length === 0) {
    return <EmptyState>이 result artifact에 기록된 ontology event가 없습니다.</EmptyState>
  }

  return (
    <ol className="max-h-[20rem] space-y-2 overflow-auto pr-1">
      {events.slice(0, 12).map((event, index) => {
        const meta = NODE_TYPES[event.type] ?? DEFAULT_NODE
        return (
          <li
            key={`${event.event_id}-${index}`}
            className="border-l px-3 py-2 text-sm"
            style={{ borderColor: meta.color }}
          >
            <div className="flex items-center justify-between gap-3">
              <span className="font-medium text-[#f3efe4]">{meta.label}</span>
              <span className="rounded bg-[#1a2230] px-1.5 py-0.5 font-mono text-[10px] text-[#7a8590]">
                T{event.timestep}
              </span>
            </div>
            <div className="mt-1 break-words font-mono text-[10px] leading-5 text-[#7a8590]">
              {event.event_id || event.target}
            </div>
          </li>
        )
      })}
    </ol>
  )
}

function SnapshotList({
  snapshots,
  activePath,
}: {
  snapshots: KgSnapshotResponse['snapshots']
  activePath: string | null
}) {
  if (snapshots.length === 0) {
    return <EmptyState>Ontology snapshot index가 비어 있습니다.</EmptyState>
  }
  return (
    <div className="max-h-[22rem] space-y-2 overflow-auto pr-1">
      {snapshots.map((snapshot) => {
        const active = snapshot.path === activePath
        return (
          <div
            key={snapshot.path}
            className={[
              'rounded-md border px-3 py-2 text-xs transition-colors',
              active
                ? 'border-[#7dd3c0]/35 bg-[#7dd3c0]/10'
                : 'border-[#1f2832] bg-[#141a23]/70',
            ].join(' ')}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="min-w-0 truncate font-medium text-[#d8d6cc]">
                {snapshot.region_id ?? 'global'}
              </span>
              <span
                className={[
                  'rounded px-1.5 py-0.5 font-mono text-[10px]',
                  active ? 'bg-[#7dd3c0]/15 text-[#7dd3c0]' : 'bg-[#1a2230] text-[#7a8590]',
                ].join(' ')}
              >
                {snapshot.timestep == null ? 'T-' : `T${snapshot.timestep}`}
              </span>
            </div>
            <div className="mt-1 break-all font-mono text-[10px] leading-5 text-[#5a6470]">
              {snapshot.path}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function buildNodeIndex(kg?: KgSnapshotResponse | null) {
  const nodes = new Map<string, Record<string, unknown>>()
  const links = new Map<string, Array<Record<string, unknown>>>()
  if (!kg) return { nodes, links }

  kg.nodes.forEach((node, index) => {
    nodes.set(nodeId(node, index), node)
  })
  kg.edges.forEach((edge) => {
    const source = edgeSource(edge)
    const target = edgeTarget(edge)
    if (!source || !target) return
    const sourceLinks = links.get(source) ?? []
    sourceLinks.push(edge)
    links.set(source, sourceLinks)
    const targetLinks = links.get(target) ?? []
    targetLinks.push(edge)
    links.set(target, targetLinks)
  })
  return { nodes, links }
}

function nodeAttrRows(attrs: Record<string, unknown> | null) {
  if (!attrs) return []
  const priority = [
    'title',
    'source',
    'source_url',
    'url_root',
    'speaker',
    'party_id',
    'party_name',
    'role',
    'background',
    'key_pledges',
    'notes',
    'additional_context',
    'party_lean',
    'age_band',
    'gender',
    'scope',
    'sample_size',
    'n_polls',
    'publish_ts',
    'provenance',
    'media_type',
    'ideology',
  ]
  const keys = [
    ...priority.filter((key) => Object.prototype.hasOwnProperty.call(attrs, key)),
    ...Object.keys(attrs)
      .filter((key) => !priority.includes(key))
      .sort((a, b) => a.localeCompare(b)),
  ]
  return keys
    .map((key) => [key, formatAttrValue(attrs[key])] as [string, string])
	    .filter(([, value]) => value.length > 0)
}

function nodeSummary(node: Record<string, unknown>, attrs: Record<string, unknown> | null) {
  return (
    readString(node, ['summary', 'description', 'text'], '') ||
    readString(attrs, ['background', 'role', 'title', 'summary', 'notes', 'source'], '')
  )
}

function profileMetaItems(node: Record<string, unknown>, attrs: Record<string, unknown> | null) {
  const kind = nodeKind(node)
  const fields =
    kind === 'Candidate' || kind === 'Person'
      ? ['party_name', 'party', 'party_id', 'role', 'affiliation', 'age']
      : kind === 'Party'
        ? ['ideology', 'seats_assembly', 'founded']
        : kind === 'District'
          ? ['code', 'population', 'households']
          : ['region_id', 'ts', 'frame_id']
  return fields
    .map((field) => {
      const value = readString(attrs, [field], '') || readString(node, [field], '')
      if (!value) return ''
      if (field === 'age') return `${value}세`
      if (field === 'seats_assembly') return `의석 ${value}`
      if (field === 'founded') return `창당 ${value}`
      if (field === 'population') return `인구 ${value}`
      if (field === 'households') return `세대 ${value}`
      return value
    })
    .filter(Boolean)
    .slice(0, 4)
}

function profileImageUrl(
  node: Record<string, unknown>,
  attrs: Record<string, unknown> | null,
) {
  const kind = nodeKind(node)
  return (
    readString(node, ['photo', 'photo_url', 'image_url', 'profile_image', 'portrait_url'], '') ||
    readString(attrs, ['photo', 'photo_url', 'image_url', 'profile_image', 'portrait_url'], '') ||
    kgNodeAsset({
      id: readString(node, ['id', 'event_id', 'name'], ''),
      label: readString(node, ['label', 'name', 'title'], ''),
      kind,
      attrs,
    }) ||
    ''
  )
}

function kgGraphOption(
  kg: KgSnapshotResponse,
  theme: 'dark' | 'light',
  selectedNodeId: string | null,
): LooseEChartsOption {
  const kindCounts = countByKind(kg.nodes)
  const kinds = Array.from(kindCounts.keys()).sort(compareKind)
  const degreeById = degreeMap(kg.edges)
  const selectedAdjacent = selectedNodeId ? adjacentNodeIds(kg.edges, selectedNodeId) : new Set<string>()
  const maxDegree = Math.max(1, ...Array.from(degreeById.values()))
  const layerCounts = new Map<number, number>()
  const layerIndexes = new Map<number, number>()

  for (const node of kg.nodes) {
    const meta = metaFor(nodeKind(node))
    layerCounts.set(meta.layer, (layerCounts.get(meta.layer) ?? 0) + 1)
  }

  const nodes = kg.nodes.map((node, index) => {
    const id = nodeId(node, index)
    const kind = nodeKind(node)
    const meta = metaFor(kind)
    const label = readString(node, ['label', 'name', 'title'], id)
    const count = readNumber(node, ['count', 'weight', 'value'], 1)
    const degree = degreeById.get(id) ?? 0
    const layerIndex = layerIndexes.get(meta.layer) ?? 0
    layerIndexes.set(meta.layer, layerIndex + 1)
    const position = initialPosition(id, meta.layer, layerIndex, layerCounts.get(meta.layer) ?? 1)
    const nodeSize = Math.max(
      24,
      Math.min(58, 22 + (degree / maxDegree) * 20 + Math.log10(count + 1) * 8),
    )
    const attrs = readRecord(node.attrs)
    const metaLine =
      readString(node, ['region_id', 'ts', 'frame_id'], '') ||
      readString(attrs, ['party_name', 'position_type', 'source', 'date', 'contest_id'], '')
    const isSelected = selectedNodeId === id
    const isAdjacent = selectedNodeId == null || selectedAdjacent.has(id) || isSelected
    const visualColor = isSelected ? '#f3efe4' : meta.color

    return {
      id,
      name: truncateLabel(label, 28),
      rawName: label,
      rawId: id,
      value: Math.max(count, degree),
      degree,
      category: kind,
      kindLabel: meta.label,
      metaLine,
      x: position.x,
      y: position.y,
      symbol: svgNodeSymbol(meta.symbol, visualColor, isSelected),
      symbolKeepAspect: true,
      symbolSize: isSelected ? nodeSize + 10 : nodeSize,
      itemStyle: {
        opacity: isAdjacent ? 1 : 0.22,
        shadowBlur: isSelected ? 28 : kind === 'Election' ? 20 : 12,
        shadowColor: hexToRgba(visualColor, isSelected ? 0.46 : 0.22),
      },
      label: {
        show: isSelected || selectedNodeId == null || isAdjacent,
        position: nodeSize > 40 ? 'bottom' : 'right',
        distance: 8,
        color: isSelected ? '#f3efe4' : isAdjacent ? '#b0b8c0' : '#4e5965',
        fontSize: isSelected ? 11 : 10,
        fontWeight: isSelected ? 700 : 500,
        lineHeight: 14,
        overflow: 'truncate',
        width: 104,
      },
      emphasis: {
        focus: 'adjacency',
        scale: 1.16,
        itemStyle: {
          color: '#111923',
          borderColor: '#e7e5dc',
          borderWidth: 2.2,
          shadowBlur: 26,
          shadowColor: hexToRgba(meta.color, 0.45),
        },
        label: {
          color: '#f3efe4',
          fontWeight: 700,
          show: true,
        },
      },
    }
  })

  const links = kg.edges
    .map((edge, index) => {
      const source = readString(edge, ['source', 'src', 'from'], '')
      const target = readString(edge, ['target', 'dst', 'to'], '')
      const rel = readString(edge, ['label', 'rel', 'type', 'kind', 'predicate'], `edge-${index}`)
      const weight = readNumber(edge, ['count', 'weight', 'value'], 1)
      const color = RELATION_COLORS[rel] ?? '#3a4450'
      const isSelectedLink =
        selectedNodeId == null || source === selectedNodeId || target === selectedNodeId
      return {
        source,
        target,
        value: weight,
        rel,
        lineStyle: {
          color: isSelectedLink ? color : '#27313d',
          width: Math.max(0.8, Math.min(4.5, 0.85 + Math.log10(weight + 1) * 1.8)),
          opacity: isSelectedLink ? (rel === 'inElection' ? 0.76 : 0.5) : 0.12,
          curveness: index % 3 === 0 ? 0.16 : 0.08,
        },
        emphasis: {
          lineStyle: {
            color: '#7dd3c0',
            width: 2.2,
            opacity: 0.95,
          },
        },
      }
    })
    .filter((link) => link.source && link.target)

  return {
    backgroundColor: 'transparent',
    color: kinds.map((kind) => metaFor(kind).color),
    tooltip: {
      trigger: 'item',
      confine: true,
      backgroundColor: '#1a2230',
      borderColor: '#2a3340',
      borderWidth: 1,
      padding: [8, 11],
      textStyle: { color: '#e7e5dc', fontSize: 12 },
      formatter: (params: { data?: Record<string, unknown>; dataType?: string }) => {
        const data = params.data ?? {}
        if (params.dataType === 'edge') {
          return [
            `<div style="font-weight:600">${escapeHtml(data.rel)}</div>`,
            `<div style="margin-top:4px;color:#7a8590;font-family:ui-monospace,monospace">${escapeHtml(data.source)} -> ${escapeHtml(data.target)}</div>`,
            `<div style="margin-top:4px;color:#b0b8c0">weight: ${escapeHtml(data.value)}</div>`,
          ].join('')
        }
        return [
          `<div style="font-weight:700">${escapeHtml(data.rawName ?? data.name ?? data.rawId)}</div>`,
          `<div style="margin-top:4px;color:#7dd3c0;font-family:ui-monospace,monospace">${escapeHtml(data.kindLabel ?? data.category)}</div>`,
          data.metaLine
            ? `<div style="margin-top:4px;color:#7a8590;font-family:ui-monospace,monospace">${escapeHtml(data.metaLine)}</div>`
            : '',
          `<div style="margin-top:4px;color:#b0b8c0">degree: ${escapeHtml(data.degree)} · value: ${escapeHtml(data.value)}</div>`,
        ].join('')
      },
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        top: 16,
        left: 10,
        right: 10,
        bottom: 18,
        roam: true,
        draggable: true,
        data: nodes,
        links,
        categories: kinds.map((name) => ({
          name,
          itemStyle: {
            color: '#0a0e13',
            borderColor: metaFor(name).color,
          },
        })),
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 6],
        force: {
          repulsion: 420,
          edgeLength: [92, 190],
          gravity: 0.045,
          friction: 0.72,
          layoutAnimation: true,
        },
        lineStyle: {
          color: '#3a4450',
          opacity: 0.45,
        },
        labelLayout: {
          hideOverlap: true,
        },
        scaleLimit: {
          min: 0.35,
          max: 3.2,
        },
        animationDuration: 1200,
        animationDurationUpdate: 650,
        animationEasingUpdate: 'cubicOut',
      },
    ],
    aria: {
      enabled: true,
      decal: { show: theme === 'light' },
    },
  }
}

function emptyGraphOption(): LooseEChartsOption {
  return {
    backgroundColor: 'transparent',
    title: {
      text: 'Ontology snapshot 없음',
      left: 'center',
      top: 'center',
      textStyle: { color: '#7a8590', fontSize: 14, fontWeight: 500 },
    },
  }
}

function kgCategoryStats(kg: KgSnapshotResponse) {
  const counts = countByKind(kg.nodes)
  return Array.from(counts.entries())
    .sort(([a], [b]) => compareKind(a, b))
    .map(([kind, count]) => ({
      kind,
      count,
      label: metaFor(kind).label,
      color: metaFor(kind).color,
    }))
}

function countByKind(nodes: Array<Record<string, unknown>>) {
  const counts = new Map<string, number>()
  for (const node of nodes) {
    const kind = nodeKind(node)
    counts.set(kind, (counts.get(kind) ?? 0) + 1)
  }
  return counts
}

function adjacentNodeIds(edges: Array<Record<string, unknown>>, selectedNodeId: string) {
  const ids = new Set<string>()
  for (const edge of edges) {
    const source = edgeSource(edge)
    const target = edgeTarget(edge)
    if (source === selectedNodeId && target) ids.add(target)
    if (target === selectedNodeId && source) ids.add(source)
  }
  return ids
}

function degreeMap(edges: Array<Record<string, unknown>>) {
  const degree = new Map<string, number>()
  for (const edge of edges) {
    const source = edgeSource(edge)
    const target = edgeTarget(edge)
    if (!source || !target) continue
    degree.set(source, (degree.get(source) ?? 0) + 1)
    degree.set(target, (degree.get(target) ?? 0) + 1)
  }
  return degree
}

function initialPosition(id: string, layer: number, index: number, total: number) {
  const centerX = 560
  const centerY = 320
  const radii = [0, 142, 258, 360]
  const radius = radii[Math.min(layer, radii.length - 1)] ?? 360
  if (radius === 0) {
    return { x: centerX, y: centerY }
  }
  const angleOffset = layer * 0.38
  const angle = -Math.PI / 2 + angleOffset + ((index + 0.5) / Math.max(1, total)) * Math.PI * 2
  const jitterSeed = hashString(id)
  const jitterX = ((jitterSeed % 23) - 11) * 1.6
  const jitterY = (((jitterSeed >> 3) % 23) - 11) * 1.6
  return {
    x: centerX + Math.cos(angle) * radius + jitterX,
    y: centerY + Math.sin(angle) * radius + jitterY,
  }
}

function compareKind(a: string, b: string) {
  const ma = metaFor(a)
  const mb = metaFor(b)
  if (ma.rank !== mb.rank) return ma.rank - mb.rank
  return a.localeCompare(b)
}

function metaFor(kind: string) {
  return NODE_TYPES[kind] ?? {
    ...DEFAULT_NODE,
    label: kind,
    color: fallbackColor(kind),
  }
}

function nodeId(source: Record<string, unknown>, index: number) {
  return readString(source, ['id', 'event_id', 'name'], `node-${index}`)
}

function nodeKind(source: Record<string, unknown>) {
  return readString(source, ['kind', 'type', 'category'], 'node')
}

function readString(
  source: Record<string, unknown> | null,
  keys: string[],
  fallback: string,
) {
  if (!source) return fallback
  for (const key of keys) {
    const value = source[key]
    if (typeof value === 'string' && value.length > 0) return value
    if (typeof value === 'number') return String(value)
  }
  return fallback
}

function readNumber(source: Record<string, unknown>, keys: string[], fallback: number) {
  for (const key of keys) {
    const value = source[key]
    if (typeof value === 'number' && Number.isFinite(value)) return value
    if (typeof value === 'string') {
      const parsed = Number(value)
      if (Number.isFinite(parsed)) return parsed
    }
  }
  return fallback
}

function edgeSource(edge: Record<string, unknown>) {
  return readString(edge, ['source', 'src', 'from'], '')
}

function edgeTarget(edge: Record<string, unknown>) {
  return readString(edge, ['target', 'dst', 'to'], '')
}

function edgeRel(edge: Record<string, unknown>, index = 0) {
  return readString(edge, ['label', 'rel', 'type', 'kind', 'predicate'], `edge-${index}`)
}

function readRecord(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>
  }
  return null
}

function formatAttrValue(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'string') return value.trim()
  if (typeof value === 'number') return Number.isFinite(value) ? String(value) : ''
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (Array.isArray(value)) return value.map(formatAttrValue).filter(Boolean).join(', ')
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function formatMaybeNumber(value: unknown): string {
  if (typeof value === 'number' && Number.isFinite(value)) return value.toFixed(2)
  if (typeof value === 'string' && value.length > 0) return value
  return '-'
}

function parseDictString(value: string): Record<string, number> {
  if (!value.trim()) return {} as Record<string, number>
  try {
    const parsed = JSON.parse(value.replace(/'/g, '"')) as Record<string, unknown>
    return Object.fromEntries(
      Object.entries(parsed)
        .map(([key, raw]) => [key, Number(raw)] as const)
        .filter(([, raw]) => Number.isFinite(raw)),
    )
  } catch {
    return {} as Record<string, number>
  }
}

function truncateLabel(value: string, max: number) {
  if (value.length <= max) return value
  return `${value.slice(0, max - 1)}…`
}

function shortDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('ko-KR', {
    month: '2-digit',
    day: '2-digit',
  }).format(date)
}

function formatTimestamp(value: string | null) {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('ko-KR', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
}

function hexToRgba(hex: string, alpha: number) {
  const normalized = hex.replace('#', '')
  if (normalized.length !== 6) return `rgba(148,163,184,${alpha})`
  const r = Number.parseInt(normalized.slice(0, 2), 16)
  const g = Number.parseInt(normalized.slice(2, 4), 16)
  const b = Number.parseInt(normalized.slice(4, 6), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

function svgNodeSymbol(path: string, color: string, active: boolean) {
  const stroke = color
  const bg = active ? '#18232d' : '#0a0e13'
  const ringOpacity = active ? '0.82' : '0.46'
  const strokeWidth = active ? '1.9' : '1.65'
  const svg = [
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" preserveAspectRatio="xMidYMid meet">`,
    `<rect width="24" height="24" fill="none"/>`,
    `<circle cx="12" cy="12" r="10.4" fill="${bg}" stroke="${stroke}" stroke-opacity="${ringOpacity}" stroke-width="1.15"/>`,
    `<g vector-effect="non-scaling-stroke">`,
    `<path d="${path}" fill="none" stroke="${stroke}" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round"/>`,
    `</g>`,
    `</svg>`,
  ].join('')
  return `image://data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
}

function fallbackColor(kind: string) {
  const palette = ['#7dd3c0', '#e8c46b', '#f0a868', '#6ea0e0', '#b48cd9', '#f37a7a']
  return palette[Math.abs(hashString(kind)) % palette.length]
}

function hashString(value: string) {
  let hash = 0
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 31 + value.charCodeAt(i)) | 0
  }
  return hash
}

function escapeHtml(value: unknown) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}
