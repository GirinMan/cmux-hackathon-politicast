import { Link } from 'react-router-dom'
import overviewAtlas from '../assets/politikast-command-atlas.png'
import Card from '../components/Card'
import StatGrid from '../components/StatGrid'
import { ErrorState, LoadingState } from '../components/States'
import {
  useFiveRegions,
  useHealth,
  usePolicy,
  useResults,
  useSchema,
} from '../hooks/queries'

const NF = new Intl.NumberFormat('ko-KR')

export default function OverviewPage() {
  const health = useHealth()
  const schema = useSchema()
  const five = useFiveRegions()
  const results = useResults()
  const policy = usePolicy()

  return (
    <div className="space-y-6">
      <header className="relative min-h-[360px] overflow-hidden rounded-lg border border-zinc-200 bg-zinc-950 text-white shadow-sm dark:border-zinc-800">
        <img
          src={overviewAtlas}
          alt=""
          className="absolute inset-0 h-full w-full object-cover opacity-80"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-zinc-950 via-zinc-950/78 to-zinc-950/12" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_24%_18%,rgba(16,185,129,0.18),transparent_32%),linear-gradient(to_bottom,transparent,rgba(9,9,11,0.45))]" />
        <div className="relative z-10 flex min-h-[360px] flex-col justify-between px-5 py-6 sm:px-7">
          <div className="max-w-3xl">
            <p className="text-xs font-medium uppercase text-emerald-300">
              PolitiKAST Project Frontend
            </p>
            <h1 className="mt-3 max-w-2xl text-3xl font-semibold sm:text-4xl">
              선거 시뮬레이션 결과, 온톨로지, 운영 정책을 한 화면에서 추적합니다.
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-zinc-300">
              Nemotron-Personas-Korea 기반 5-region synthetic voter harness와
              temporal ontology, capacity policy, result artifacts를 통합해
              논문 실험과 제출 상태를 확인하는 frontend입니다.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <Link
                to="/results"
                className="rounded-md bg-emerald-400 px-3 py-2 text-sm font-medium text-zinc-950 transition-colors hover:bg-emerald-300"
              >
                결과 보기
              </Link>
              <Link
                to="/operations"
                className="rounded-md border border-white/20 bg-white/10 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-white/15"
              >
                운영 상태
              </Link>
              <Link
                to="/ontology"
                className="rounded-md border border-white/20 bg-white/10 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-white/15"
              >
                온톨로지 탐색
              </Link>
            </div>
          </div>

          <div className="mt-8 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <HeroKpi
              label="API"
              value={health.data?.status ?? 'loading'}
              tone={health.data?.status === 'ok' ? 'good' : 'muted'}
            />
            <HeroKpi
              label="live artifacts"
              value={results.data ? NF.format(results.data.totals.live_count) : '—'}
              hint={`${results.data?.totals.regions_total ?? 5} regions`}
            />
            <HeroKpi
              label="policy model"
              value={policy.data?.model ?? 'pending'}
              hint={policy.data?.provider ?? 'provider'}
            />
            <HeroKpi label="dataset" value="7,000,000" hint="persona texts" />
          </div>
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <WorkbenchLink
          to="/results"
          eyebrow="Experiment"
          title="결과 콘솔"
          text="5-region artifact status, winner, turnout, trajectory, demographic breakdown."
        />
        <WorkbenchLink
          to="/ontology"
          eyebrow="Ontology"
          title="Temporal Ontology"
          text="region/timestep snapshot graph와 result artifact가 사용한 event trail."
        />
        <WorkbenchLink
          to="/operations"
          eyebrow="Run Control"
          title="운영 상태"
          text="policy envelope, capacity probe, snapshot freshness, backend health."
        />
        <WorkbenchLink
          to="/demographics"
          eyebrow="Data"
          title="Synthetic voters"
          text="인구통계, 지역 분포, persona samples, population distribution map."
        />
      </section>

      <Card title="시스템 상태" subtitle="API 연결 및 데이터 소스">
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
                label: 'region 테이블',
                value: health.data.region_tables.length,
                hint: health.data.region_tables.join(', ') || '—',
              },
              {
                label: '소스',
                value: (
                  <span
                    className="font-mono text-xs break-all"
                    title={health.data.source}
                  >
                    {truncate(health.data.source, 40)}
                  </span>
                ),
              },
            ]}
          />
        ) : null}
      </Card>

      <Card
        title="PolitiKAST contract regions"
        subtitle="서울·광주·대구 광역 + 부산 북구 갑·대구 달서구 갑 보궐"
      >
        {five.isLoading ? (
          <LoadingState />
        ) : five.error ? (
          <ErrorState error={five.error} retry={five.refetch} />
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {five.data?.regions.map((r) => (
              <Link
                key={r.key}
                to={r.available ? `/regions?region=${r.key}` : '/regions'}
                className={[
                  'rounded-lg border px-4 py-3 transition-colors group',
                  r.available
                    ? 'border-zinc-200 dark:border-zinc-800 hover:border-emerald-500/60 hover:bg-emerald-500/5'
                    : 'border-dashed border-zinc-300 dark:border-zinc-700 opacity-60',
                ].join(' ')}
              >
                <div className="flex items-baseline justify-between">
                  <span className="font-medium text-zinc-900 dark:text-zinc-100">
                    {r.label_ko}
                  </span>
                  <span className="text-[11px] text-zinc-500 dark:text-zinc-400">
                    {r.label_en}
                  </span>
                </div>
                <div className="mt-2 text-xl font-semibold tabular-nums">
                  {r.available ? NF.format(r.count) : '미정'}
                </div>
                <div className="mt-0.5 text-[11px] text-zinc-500 dark:text-zinc-400">
                  {r.district ?? r.province ?? (r.available ? '—' : 'region 조건 없음')}
                </div>
              </Link>
            ))}
          </div>
        )}
      </Card>

      <Card title="스키마" subtitle="등록된 테이블 및 행 수">
        {schema.isLoading ? (
          <LoadingState />
        ) : schema.error ? (
          <ErrorState error={schema.error} retry={schema.refetch} />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400 border-b border-zinc-200 dark:border-zinc-800">
                  <th className="py-2 pr-4">테이블</th>
                  <th className="py-2 pr-4 text-right">행 수</th>
                  <th className="py-2 pr-4 text-right">컬럼</th>
                </tr>
              </thead>
              <tbody>
                {schema.data?.tables.map((t) => (
                  <tr
                    key={t.name}
                    className="border-b border-zinc-100 dark:border-zinc-900"
                  >
                    <td className="py-2 pr-4 font-mono text-xs">{t.name}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">
                      {NF.format(t.rows)}
                    </td>
                    <td className="py-2 pr-4 text-right tabular-nums">
                      {t.columns.length}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {schema.data && schema.data.notes.length > 0 && (
              <ul className="mt-4 space-y-1.5 text-xs text-zinc-600 dark:text-zinc-400 list-disc list-inside">
                {schema.data.notes.map((n, i) => (
                  <li key={i}>{n}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </Card>

      <Card title="출처 및 라이선스">
        <div className="text-sm text-zinc-700 dark:text-zinc-300 space-y-2 leading-relaxed">
          <p>
            <strong>Nemotron-Personas-Korea v1.0</strong> · NVIDIA Corporation,
            2026-04-20 · CC BY 4.0.
          </p>
          <p>
            <strong>Grounding sources:</strong> KOSIS (통계청 국가통계포털), 대법원
            전자가족관계등록, NHIS 건강검진정보(2024-12-31, KOGL 0유형), KREI 식품소비행태조사
            (2024, KOGL 4유형), NAVER Cloud.
          </p>
          <p>
            <strong>Synthesis:</strong> NeMo Data Designer (Apache-2.0) + PGM
            (인구통계 12) + OCEAN (Big-5) + <code>google/gemma-4-31B-it</code>
            (Apache-2.0).
          </p>
          <p className="text-zinc-500 dark:text-zinc-400 text-xs">
            상세: <code className="font-mono">_workspace/research/nemotron-personas-korea/01_overview.md</code>
          </p>
        </div>
      </Card>
    </div>
  )
}

function HeroKpi({
  label,
  value,
  hint,
  tone = 'muted',
}: {
  label: string
  value: string
  hint?: string
  tone?: 'good' | 'muted'
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-zinc-950/60 px-4 py-3 backdrop-blur">
      <div className="flex items-center gap-2 text-[11px] uppercase text-zinc-400">
        <span
          className={[
            'h-1.5 w-1.5 rounded-full',
            tone === 'good' ? 'bg-emerald-400' : 'bg-zinc-500',
          ].join(' ')}
        />
        {label}
      </div>
      <div className="mt-2 truncate font-mono text-xl font-semibold text-white">
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-zinc-400">{hint}</div>}
    </div>
  )
}

function WorkbenchLink({
  to,
  eyebrow,
  title,
  text,
}: {
  to: string
  eyebrow: string
  title: string
  text: string
}) {
  return (
    <Link
      to={to}
      className="group rounded-lg border border-zinc-200 bg-white p-4 transition-colors hover:border-emerald-500/60 hover:bg-emerald-500/5 dark:border-zinc-800 dark:bg-zinc-900/40 dark:hover:border-emerald-500/60"
    >
      <div className="text-[11px] font-medium uppercase text-emerald-600 dark:text-emerald-400">
        {eyebrow}
      </div>
      <div className="mt-2 flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-zinc-950 dark:text-zinc-50">
          {title}
        </h2>
        <span className="text-zinc-400 transition-transform group-hover:translate-x-0.5">
          →
        </span>
      </div>
      <p className="mt-2 text-sm leading-5 text-zinc-600 dark:text-zinc-400">
        {text}
      </p>
    </Link>
  )
}

function truncate(s: string, n: number): string {
  return s.length > n ? `…${s.slice(-n)}` : s
}
