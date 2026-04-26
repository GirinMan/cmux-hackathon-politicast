import Card from '../components/Card'
import StatGrid from '../components/StatGrid'
import { EmptyState, ErrorState, LoadingState } from '../components/States'
import { useHealth, usePolicy, useResults, useSchema } from '../hooks/queries'
import type { PolicySummaryResponse, ResultSummaryResponse } from '../types/api'

const NF = new Intl.NumberFormat('ko-KR')

export default function OperationsPage() {
  const health = useHealth()
  const results = useResults()
  const policy = usePolicy()
  const schema = useSchema()

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-medium uppercase text-emerald-600 dark:text-emerald-400">
            Run Operations
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-zinc-950 dark:text-zinc-50">
            운영
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-600 dark:text-zinc-400">
            backend health, result artifact freshness, capacity policy, downscale
            ladder를 한 곳에서 확인합니다.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusChip
            label="API"
            value={health.data?.status ?? 'loading'}
            good={health.data?.status === 'ok'}
          />
          <StatusChip
            label="live"
            value={String(results.data?.totals.live_count ?? '—')}
            good={(results.data?.totals.live_count ?? 0) > 0}
          />
          <StatusChip
            label="policy"
            value={policy.data?.model ?? 'pending'}
            good={!policy.data?.warnings.length}
          />
        </div>
      </header>

      <div className="grid gap-6 xl:grid-cols-[1.25fr_0.9fr]">
        <div className="space-y-6">
          <Card title="Backend and data substrate" subtitle="FastAPI BFF + DuckDB">
            {health.isLoading ? (
              <LoadingState />
            ) : health.error ? (
              <ErrorState error={health.error} retry={health.refetch} />
            ) : health.data ? (
              <StatGrid
                stats={[
                  { label: 'API 상태', value: health.data.status },
                  { label: '데이터 모드', value: health.data.mode },
                  {
                    label: 'persona_core',
                    value: NF.format(health.data.persona_core_rows),
                  },
                  {
                    label: 'persona_text',
                    value: NF.format(health.data.persona_text_rows),
                  },
                  {
                    label: 'region tables',
                    value: health.data.region_tables.length,
                    hint: health.data.region_tables.join(', '),
                  },
                  {
                    label: 'source',
                    value: (
                      <span className="font-mono text-xs break-all">
                        {health.data.source}
                      </span>
                    ),
                  },
                ]}
              />
            ) : null}
          </Card>

          <Card title="Result artifact matrix" subtitle="freshest result per contract region">
            {results.isLoading ? (
              <LoadingState />
            ) : results.error ? (
              <ErrorState error={results.error} retry={results.refetch} />
            ) : results.data ? (
              <ResultMatrix data={results.data} />
            ) : (
              <EmptyState>result index가 비어 있습니다.</EmptyState>
            )}
          </Card>

          <Card title="Policy region plan" subtitle="policy.json region envelope">
            {policy.isLoading ? (
              <LoadingState />
            ) : policy.error ? (
              <ErrorState error={policy.error} retry={policy.refetch} />
            ) : policy.data ? (
              <PolicyTable data={policy.data} />
            ) : (
              <EmptyState>policy artifact가 없습니다.</EmptyState>
            )}
          </Card>
        </div>

        <aside className="space-y-6">
          <Card title="Capacity probe" subtitle="capacity_probe.json">
            {policy.data?.capacity_probe ? (
              <KeyValueList data={policy.data.capacity_probe} maxRows={10} />
            ) : policy.isLoading ? (
              <LoadingState />
            ) : (
              <EmptyState>capacity probe를 읽을 수 없습니다.</EmptyState>
            )}
          </Card>

          <Card title="Downscale ladder" subtitle="fallback policy">
            {policy.data?.downscale_ladder.length ? (
              <div className="space-y-2">
                {policy.data.downscale_ladder.map((step, index) => (
                  <div
                    key={index}
                    className="rounded-lg border border-zinc-200 px-3 py-2 text-sm dark:border-zinc-800"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-medium text-zinc-950 dark:text-zinc-50">
                        Step {index + 1}
                      </span>
                      <span className="font-mono text-xs text-zinc-500 dark:text-zinc-400">
                        {String(step.name ?? step.id ?? step.trigger ?? 'policy')}
                      </span>
                    </div>
                    <div className="mt-2">
                      <KeyValueList data={step} maxRows={5} compact />
                    </div>
                  </div>
                ))}
              </div>
            ) : policy.isLoading ? (
              <LoadingState />
            ) : (
              <EmptyState>downscale ladder가 비어 있습니다.</EmptyState>
            )}
          </Card>

          <Card title="Source files" subtitle="BFF inputs">
            <SourceFiles results={results.data} policy={policy.data} />
          </Card>

          <Card title="Schema notes" subtitle="DuckDB registered tables">
            {schema.isLoading ? (
              <LoadingState />
            ) : schema.error ? (
              <ErrorState error={schema.error} retry={schema.refetch} />
            ) : schema.data ? (
              <div className="space-y-2">
                <div className="text-sm text-zinc-700 dark:text-zinc-300">
                  {NF.format(schema.data.tables.length)} tables
                </div>
                {schema.data.notes.length > 0 ? (
                  <ul className="list-inside list-disc space-y-1 text-xs text-zinc-500 dark:text-zinc-400">
                    {schema.data.notes.map((note, index) => (
                      <li key={index}>{note}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">
                    schema note 없음
                  </p>
                )}
              </div>
            ) : null}
          </Card>
        </aside>
      </div>
    </div>
  )
}

function StatusChip({
  label,
  value,
  good,
}: {
  label: string
  value: string
  good: boolean
}) {
  return (
    <div
      className={[
        'rounded-lg border px-3 py-2',
        good
          ? 'border-emerald-500/40 bg-emerald-500/10'
          : 'border-amber-500/40 bg-amber-500/10',
      ].join(' ')}
    >
      <div className="text-[10px] uppercase text-zinc-500 dark:text-zinc-400">
        {label}
      </div>
      <div className="mt-1 max-w-[11rem] truncate font-mono text-sm font-semibold text-zinc-950 dark:text-zinc-50">
        {value}
      </div>
    </div>
  )
}

function ResultMatrix({ data }: { data: ResultSummaryResponse }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-200 text-left text-xs uppercase text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
            <th className="py-2 pr-4">region</th>
            <th className="py-2 pr-4">status</th>
            <th className="py-2 pr-4 text-right">n</th>
            <th className="py-2 pr-4 text-right">T</th>
            <th className="py-2 pr-4">winner</th>
            <th className="py-2 pr-4 text-right">calls</th>
            <th className="py-2 pr-4">updated</th>
          </tr>
        </thead>
        <tbody>
          {data.regions.map((region) => (
            <tr
              key={region.region_id}
              className="border-b border-zinc-100 dark:border-zinc-900"
            >
              <td className="py-2 pr-4 font-medium">{region.label}</td>
              <td className="py-2 pr-4">
                <ArtifactStatus status={region.status} />
              </td>
              <td className="py-2 pr-4 text-right tabular-nums">
                {NF.format(region.persona_n)}
              </td>
              <td className="py-2 pr-4 text-right tabular-nums">
                {region.timestep_count}
              </td>
              <td className="py-2 pr-4">{region.winner_label ?? '—'}</td>
              <td className="py-2 pr-4 text-right tabular-nums">
                {NF.format(region.total_calls)}
              </td>
              <td className="py-2 pr-4 font-mono text-xs text-zinc-500">
                {region.wrote_at ?? '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {data.warnings.length > 0 && (
        <div className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-900 dark:text-amber-100">
          {data.warnings.join(' ')}
        </div>
      )}
    </div>
  )
}

function PolicyTable({ data }: { data: PolicySummaryResponse }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-200 text-left text-xs uppercase text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
            <th className="py-2 pr-4">region</th>
            <th className="py-2 pr-4 text-right">persona_n</th>
            <th className="py-2 pr-4 text-right">timesteps</th>
            <th className="py-2 pr-4 text-right">interview_n</th>
            <th className="py-2 pr-4 text-right">weight</th>
          </tr>
        </thead>
        <tbody>
          {data.regions.map((region) => (
            <tr
              key={region.region_id}
              className="border-b border-zinc-100 dark:border-zinc-900"
            >
              <td className="py-2 pr-4 font-medium">{region.label}</td>
              <td className="py-2 pr-4 text-right tabular-nums">
                {formatMaybe(region.persona_n)}
              </td>
              <td className="py-2 pr-4 text-right tabular-nums">
                {formatMaybe(region.timesteps)}
              </td>
              <td className="py-2 pr-4 text-right tabular-nums">
                {formatMaybe(region.interview_n)}
              </td>
              <td className="py-2 pr-4 text-right tabular-nums">
                {region.weight == null ? '—' : String(region.weight)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {data.warnings.length > 0 && (
        <div className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-900 dark:text-amber-100">
          {data.warnings.join(' ')}
        </div>
      )}
    </div>
  )
}

function KeyValueList({
  data,
  maxRows,
  compact = false,
}: {
  data: Record<string, unknown>
  maxRows: number
  compact?: boolean
}) {
  const rows = Object.entries(data)
    .filter(([, value]) => value !== undefined)
    .slice(0, maxRows)
  if (rows.length === 0) {
    return <EmptyState>표시할 key가 없습니다.</EmptyState>
  }
  return (
    <dl className={compact ? 'space-y-1' : 'space-y-2'}>
      {rows.map(([key, value]) => (
        <div key={key} className="grid grid-cols-[7.5rem_1fr] gap-2 text-xs">
          <dt className="min-w-0 truncate text-zinc-500 dark:text-zinc-400">
            {key}
          </dt>
          <dd className="min-w-0 break-words font-mono text-zinc-800 dark:text-zinc-200">
            {formatValue(value)}
          </dd>
        </div>
      ))}
    </dl>
  )
}

function SourceFiles({
  results,
  policy,
}: {
  results?: ResultSummaryResponse
  policy?: PolicySummaryResponse
}) {
  const rows = [
    ...Object.entries(results?.source_files ?? {}).map(([key, path]) => ({
      key: `results.${key}`,
      path,
    })),
    ...Object.entries(policy?.source_files ?? {}).map(([key, path]) => ({
      key: `policy.${key}`,
      path,
    })),
  ]
  if (rows.length === 0) {
    return <EmptyState>source file metadata가 없습니다.</EmptyState>
  }
  return (
    <div className="space-y-2">
      {rows.map((row) => (
        <div
          key={row.key}
          className="rounded-lg border border-zinc-200 px-3 py-2 text-xs dark:border-zinc-800"
        >
          <div className="font-medium text-zinc-800 dark:text-zinc-200">
            {row.key}
          </div>
          <div className="mt-1 break-all font-mono text-zinc-500 dark:text-zinc-400">
            {row.path}
          </div>
        </div>
      ))}
    </div>
  )
}

function ArtifactStatus({ status }: { status: string }) {
  const tone =
    status === 'live'
      ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
      : status === 'missing'
        ? 'border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-300'
        : 'border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300'
  return <span className={['rounded-full border px-2 py-0.5 text-xs', tone].join(' ')}>{status}</span>
}

function formatMaybe(value: number | null) {
  return value == null ? '—' : NF.format(value)
}

function formatValue(value: unknown): string {
  if (value == null) return '—'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value)
}
