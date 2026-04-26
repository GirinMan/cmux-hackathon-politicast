import { Link } from 'react-router-dom'
import overviewAtlas from '../assets/politikast-command-atlas.png'
import Card from '../components/Card'
import { ErrorState, LoadingState } from '../components/States'
import {
  useFiveRegions,
  useHealth,
  usePolicy,
  useResults,
} from '../hooks/queries'

const NF = new Intl.NumberFormat('ko-KR')

const BADGES: Array<{ label: string; value: string; tone: BadgeTone }> = [
  { label: 'paper', value: 'EN 33p · KO 39p', tone: 'info' },
  { label: 'validation', value: '3/3 leader_match', tone: 'good' },
  { label: 'MAE', value: '0.5066 → 0.1782 (2.84×)', tone: 'info' },
  { label: 'forecast', value: 'prediction-only', tone: 'warn' },
  { label: 'track', value: 'AI Safety & Security', tone: 'danger' },
]

const FAILURE_MODES: Array<{ failure: string; mechanism: string }> = [
  {
    failure: 'LLM이 검증되지 않은 forecast를 confident하게 출력',
    mechanism:
      'Hidden-label validation gate · MAE / leader-agreement gate 통과 전까지 `prediction-only` 플래그 강제',
  },
  {
    failure: '미래 여론조사 결과가 이전 prompt로 leak',
    mechanism:
      '**Temporal Information Firewall** · 모든 KG fact는 `cutoff_ts` 보유, voter at t는 τ ≤ t fact만 조회. self-test 7/7 PASS',
  },
  {
    failure: 'LLM이 미국식 stereotype("young = progressive")으로 default',
    mechanism:
      '**CohortPrior** 노드(age × gender × region) — Gallup Korea / SisaIN / KStat / RealMeter / Hankyoreh 출처 15개 prior를 voter prompt에 직접 주입',
  },
  {
    failure: '성공만 publicize되고 실패는 사라짐',
    mechanism:
      'Failed gate · prediction-only region · KG narrative gap을 Validation Gate page와 paper results table에 명시',
  },
]

const KEY_RESULTS: Array<{
  region: string
  stage: string
  mae: string
  rmse: string
  leader: boolean
  verdict: string
  highlight?: boolean
}> = [
  {
    region: 'Seoul mayor',
    stage: 'Baseline clean (n=200, T=2)',
    mae: '0.5702',
    rmse: '0.5702',
    leader: false,
    verdict: 'FAIL',
  },
  {
    region: 'Seoul mayor',
    stage: 'R6 full (KG A+B)',
    mae: '0.3745',
    rmse: '0.3745',
    leader: true,
    verdict: 'FAIL · cohort over-amp at n=200',
    highlight: true,
  },
  {
    region: 'Busan Buk-gu A',
    stage: 'Baseline clean',
    mae: '0.4444',
    rmse: '0.4743',
    leader: false,
    verdict: 'FAIL',
  },
  {
    region: 'Busan Buk-gu A',
    stage: 'R6 full (KG A+B)',
    mae: '0.1062',
    rmse: '0.1287',
    leader: true,
    verdict: 'Borderline (~2.1×)',
    highlight: true,
  },
  {
    region: 'Daegu mayor',
    stage: 'Baseline clean',
    mae: '0.5052',
    rmse: '0.5886',
    leader: false,
    verdict: 'FAIL',
  },
  {
    region: 'Daegu mayor',
    stage: 'R6 full (KG A+B)',
    mae: '0.0538',
    rmse: '0.0700',
    leader: true,
    verdict: 'Near-PASS (1.08×)',
    highlight: true,
  },
]

const LLM_STACK: Array<{ role: string; model: string; note: string }> = [
  { role: 'dev / cheap', model: 'gemini-3.1-flash-lite-preview', note: 'no thinking, free' },
  { role: 'prod voter (normal)', model: 'gpt-5.4-nano', note: 'persona-conditional' },
  { role: 'prod voter (educated)', model: 'gpt-5.4-mini', note: 'bachelor cutoff' },
  { role: 'interview', model: 'claude-sonnet-4-6', note: 'qualitative output' },
  { role: 'base', model: 'LLMPool + LiteLLM', note: 'CAMEL Plan-B optional' },
]

const NOT_THIS: string[] = [
  '**2026 선거 forecast가 아닙니다.** strict MAE gate는 어느 region도 cleanly pass하지 못했습니다. Seoul은 leader agreement만 통과, Daegu는 gate의 1.08×.',
  '**완성된 social-science 도구가 아닙니다.** base utility term은 stylized age × education × party prior로, KOSIS / NEC / panel-survey에 fitting되지 않았습니다.',
  '**인간 숙의의 대체재가 아닙니다.** synthetic persona + LLM cohort lean estimate는 19세 미만, 세분화된 gender identity, 진행 중 후보 disclosure를 표현할 수 없습니다.',
]

export default function OverviewPage() {
  const health = useHealth()
  const five = useFiveRegions()
  const results = useResults()
  const policy = usePolicy()

  return (
    <div className="space-y-6">
      <header className="relative min-h-[420px] overflow-hidden rounded-lg border border-zinc-200 bg-zinc-950 text-white shadow-sm dark:border-zinc-800">
        <img
          src={overviewAtlas}
          alt=""
          className="absolute inset-0 h-full w-full object-cover opacity-80"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-zinc-950 via-zinc-950/80 to-zinc-950/15" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_24%_18%,rgba(16,185,129,0.18),transparent_32%),linear-gradient(to_bottom,transparent,rgba(9,9,11,0.45))]" />
        <div className="relative z-10 flex min-h-[420px] flex-col justify-between px-5 py-6 sm:px-7">
          <div className="max-w-3xl">
            <p className="text-xs font-medium uppercase tracking-wider text-emerald-300">
              PolitiKAST · Team 기린맨 · 12-hour hackathon · 2026-04-26
            </p>
            <h1 className="mt-3 max-w-2xl text-3xl font-semibold leading-tight sm:text-4xl">
              한국 지방선거 유권자 궤적의{' '}
              <span className="text-emerald-300">validation-first</span>{' '}
              multi-agent 시뮬레이션
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-zinc-300">
              합성 한국 유권자 인구(Nemotron-Personas-Korea, 7M) + 시간형 정치
              Knowledge Graph + LLM voter agent를 결합해, 모집단이{' '}
              <strong className="text-zinc-100">먼저 hold-out 공식 여론조사
              궤적을 재현</strong>한 뒤에야 선거 결과 주장을 허용합니다.
            </p>

            <blockquote className="mt-5 max-w-2xl border-l-2 border-emerald-400/70 pl-4 text-sm italic leading-6 text-zinc-200">
              "Forecast"는 validation gate를 통과하기 전까지 사용할 수 없는
              단어입니다. 모든 산출물은 simulated vote share가 시계열 정렬된
              NESDC 공식 여론조사를, clean no-cache·no-leak 프로토콜에서
              재현하기 전까지 <code className="font-mono">prediction-only</code>{' '}
              라벨을 달고 운반됩니다.
            </blockquote>

            <div className="mt-5 flex flex-wrap gap-2">
              {BADGES.map((b) => (
                <Badge key={`${b.label}-${b.value}`} {...b} />
              ))}
            </div>

            <div className="mt-5 flex flex-wrap gap-2">
              <Link
                to="/results"
                className="rounded-md bg-emerald-400 px-3 py-2 text-sm font-medium text-zinc-950 transition-colors hover:bg-emerald-300"
              >
                결과 콘솔 →
              </Link>
              <Link
                to="/personas"
                className="rounded-md border border-white/20 bg-white/10 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-white/15"
              >
                Voter agent 인터뷰
              </Link>
              <Link
                to="/ontology"
                className="rounded-md border border-white/20 bg-white/10 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-white/15"
              >
                Temporal KG
              </Link>
              <Link
                to="/population"
                className="rounded-md border border-white/20 bg-white/10 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-white/15"
              >
                인구 분포
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

      <Card
        title="Why this matters · the safety problem"
        subtitle="frontier LLM의 unvalidated forecast 실패 모드와 PolitiKAST의 메커니즘"
      >
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-200 text-left text-[11px] uppercase tracking-wide text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
                <th className="w-1/2 py-2 pr-4">Failure mode</th>
                <th className="py-2">PolitiKAST mechanism</th>
              </tr>
            </thead>
            <tbody>
              {FAILURE_MODES.map((row, i) => (
                <tr
                  key={i}
                  className="border-b border-zinc-100 align-top last:border-0 dark:border-zinc-900"
                >
                  <td className="py-3 pr-4 text-zinc-700 dark:text-zinc-300">
                    {row.failure}
                  </td>
                  <td
                    className="py-3 text-zinc-800 dark:text-zinc-200"
                    dangerouslySetInnerHTML={{ __html: renderEm(row.mechanism) }}
                  />
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card
        title="Key result · 12-hour hackathon snapshot"
        subtitle="3 rated regions에 대한 clean no-cache official-poll validation gate, baseline vs R6 full enrichment"
        right={
          <span className="rounded-md bg-emerald-500/10 px-2.5 py-1 text-[11px] font-semibold text-emerald-700 dark:text-emerald-300">
            mean MAE 0.5066 → 0.1782 · 2.84× tighter
          </span>
        }
      >
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-200 text-left text-[11px] uppercase tracking-wide text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
                <th className="py-2 pr-4">Region</th>
                <th className="py-2 pr-4">Stage</th>
                <th className="py-2 pr-4 text-right">MAE</th>
                <th className="py-2 pr-4 text-right">RMSE</th>
                <th className="py-2 pr-4">leader_match</th>
                <th className="py-2">Verdict</th>
              </tr>
            </thead>
            <tbody>
              {KEY_RESULTS.map((r, i) => (
                <tr
                  key={i}
                  className={[
                    'border-b border-zinc-100 last:border-0 dark:border-zinc-900',
                    r.highlight ? 'bg-emerald-500/5' : '',
                  ].join(' ')}
                >
                  <td className="py-2 pr-4 font-medium text-zinc-900 dark:text-zinc-100">
                    {r.region}
                  </td>
                  <td className="py-2 pr-4 text-zinc-700 dark:text-zinc-300">
                    {r.stage}
                  </td>
                  <td
                    className={[
                      'py-2 pr-4 text-right font-mono tabular-nums',
                      r.highlight ? 'font-semibold text-emerald-700 dark:text-emerald-300' : '',
                    ].join(' ')}
                  >
                    {r.mae}
                  </td>
                  <td className="py-2 pr-4 text-right font-mono tabular-nums text-zinc-600 dark:text-zinc-400">
                    {r.rmse}
                  </td>
                  <td className="py-2 pr-4">
                    <span
                      className={[
                        'rounded-full px-2 py-0.5 text-[11px] font-semibold',
                        r.leader
                          ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                          : 'bg-zinc-200 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-400',
                      ].join(' ')}
                    >
                      {r.leader ? 'true' : 'false'}
                    </span>
                  </td>
                  <td className="py-2 text-xs text-zinc-700 dark:text-zinc-300">
                    {r.verdict}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 text-xs leading-5 text-zinc-500 dark:text-zinc-400">
          Track A (정치 narrative — PressConference 127 / Source 127 / MediaEvent 96 /
          damagesParty 84) + Track B (CohortPrior 20 nodes) enrichment 후
          100%-sweep region이 5/5 → 0/3로 하락. Gwangju / Daegu Dalseo-gu A는
          후보 단위 NESDC label 부재로{' '}
          <code className="font-mono">target_series=prediction_only</code>로
          gate에서 분리 (게이트 win으로 카운트 X).
        </p>
      </Card>

      <Card
        title="Architecture"
        subtitle="Validation gate가 hidden-label로 분리된 데이터 흐름"
      >
        <ArchitectureDiagram />
        <div className="mt-5 grid gap-2 md:grid-cols-2 xl:grid-cols-5">
          {LLM_STACK.map((s) => (
            <div
              key={s.role}
              className="rounded-md border border-zinc-200 bg-white px-3 py-2 dark:border-zinc-800 dark:bg-zinc-950/40"
            >
              <div className="text-[10px] uppercase text-zinc-500 dark:text-zinc-400">
                {s.role}
              </div>
              <div className="mt-1 truncate font-mono text-xs text-zinc-900 dark:text-zinc-100">
                {s.model}
              </div>
              <div className="mt-0.5 text-[11px] text-zinc-500 dark:text-zinc-400">
                {s.note}
              </div>
            </div>
          ))}
        </div>
      </Card>

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
          title="Temporal KG"
          text="region/timestep snapshot graph + result artifact가 사용한 event trail."
        />
        <WorkbenchLink
          to="/personas"
          eyebrow="Voter agent"
          title="합성 페르소나 + 인터뷰"
          text="24명 합성 voter 카드 + 시뮬에서 voter agent가 남긴 vote / reason / key_factors."
        />
        <WorkbenchLink
          to="/population"
          eyebrow="Data"
          title="인구 분포"
          text="17개 시·도 헥스맵, 후보·여론조사 ground-truth와의 정합성 점검."
        />
      </section>

      <Card
        title="Contract regions"
        subtitle="서울·광주·대구 광역 + 부산 북구 갑·대구 달서구 갑 보궐"
      >
        {five.isLoading ? (
          <LoadingState />
        ) : five.error ? (
          <ErrorState error={five.error} retry={five.refetch} />
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {five.data?.regions.map((r) => (
              <Link
                key={r.key}
                to={r.available ? `/results?region=${r.key}` : '/regions'}
                className={[
                  'group rounded-lg border px-4 py-3 transition-colors',
                  r.available
                    ? 'border-zinc-200 hover:border-emerald-500/60 hover:bg-emerald-500/5 dark:border-zinc-800'
                    : 'border-dashed border-zinc-300 opacity-60 dark:border-zinc-700',
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

      <Card
        title="What this is *not*"
        subtitle="Limitations이 paper에 명시된 그대로, 여기서도 가려두지 않습니다"
      >
        <ul className="space-y-2.5 text-sm leading-6 text-zinc-700 dark:text-zinc-300">
          {NOT_THIS.map((line, i) => (
            <li
              key={i}
              className="flex gap-3 border-l-2 border-amber-400/50 pl-3"
              dangerouslySetInnerHTML={{ __html: renderEm(line) }}
            />
          ))}
        </ul>
      </Card>

      <Card title="출처 및 라이선스">
        <div className="space-y-2 text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
          <p>
            <strong>Nemotron-Personas-Korea v1.0</strong> · NVIDIA, CC BY 4.0 · 7M
            합성 한국인 페르소나 (KOSIS / 대법원 / NHIS / KREI 통계 기반).
          </p>
          <p>
            <strong>NESDC poll metadata</strong> · 한국 중앙선거여론조사심의위원회
            공개 등록 (`pollGubuncd=VT026`) · 학술 검증 용도. 1,487 폴.
          </p>
          <p>
            <strong>Cohort priors</strong> · Gallup Korea / SisaIN / KStat /
            RealMeter / Hankyoreh cross-tab 인용, 각 prior에 <code>source_url</code>{' '}
            동봉.
          </p>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            논문: <code className="font-mono">paper/elex-kg-final.pdf</code>
            (EN, 33p) · <code className="font-mono">paper/elex-kg-final-ko.pdf</code>
            (KO, 39p) · author{' '}
            <a
              href="mailto:sjlee@bhsn.ai"
              className="underline decoration-dotted underline-offset-2 hover:text-emerald-600"
            >
              Seongjin Lee
            </a>
          </p>
        </div>
      </Card>
    </div>
  )
}

type BadgeTone = 'good' | 'info' | 'warn' | 'danger'

function Badge({ label, value, tone }: { label: string; value: string; tone: BadgeTone }) {
  const palette: Record<BadgeTone, string> = {
    good: 'border-emerald-400/40 bg-emerald-500/15 text-emerald-200',
    info: 'border-sky-400/40 bg-sky-500/15 text-sky-200',
    warn: 'border-amber-400/40 bg-amber-500/15 text-amber-200',
    danger: 'border-rose-400/40 bg-rose-500/15 text-rose-200',
  }
  return (
    <span
      className={[
        'inline-flex items-center gap-2 rounded-md border px-2.5 py-1 text-[11px] font-medium',
        palette[tone],
      ].join(' ')}
    >
      <span className="uppercase tracking-wider opacity-80">{label}</span>
      <span className="font-mono">{value}</span>
    </span>
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

function ArchitectureDiagram() {
  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_auto_1fr_auto_1fr]">
      <ArchNode
        title="Synthetic voter pool"
        body="Nemotron-Personas-Korea (7M) → DuckDB region-aware sampling"
        accent="emerald"
      />
      <ArchArrow />
      <ArchNode
        title="Voter agents"
        body="LLMPool + LiteLLM, persona-conditional routing (nano / mini / sonnet) — secret-ballot JSON 응답"
        accent="sky"
      />
      <ArchArrow />
      <ArchNode
        title="Vote share"
        body="poll consensus → final outcome → Validation Gate (MAE / RMSE / leader_match)"
        accent="emerald"
      />

      <ArchNode
        title="Temporal KG (τ ≤ t)"
        body="Election + Discourse ontology · Track A facts · Track B CohortPrior · Firewall 7/7"
        accent="violet"
        span
      />
      <div className="hidden lg:col-span-1 lg:block" />
      <div className="rounded-lg border border-dashed border-amber-400/40 bg-amber-500/5 p-3 text-xs leading-5 text-amber-700 dark:text-amber-300">
        <strong className="block text-amber-700 dark:text-amber-300">
          NESDC official polls
        </strong>
        <span className="text-amber-600/80 dark:text-amber-200/80">
          1,487 폴 · raw_poll + raw_poll_result + poll_consensus_daily ·{' '}
          <em>HIDDEN LABEL</em> · validation gate에서만 사용
        </span>
      </div>
      <div className="hidden lg:col-span-1 lg:block" />
      <div className="hidden lg:col-span-1 lg:block" />
    </div>
  )
}

function ArchNode({
  title,
  body,
  accent,
  span,
}: {
  title: string
  body: string
  accent: 'emerald' | 'sky' | 'violet'
  span?: boolean
}) {
  const accentMap = {
    emerald: 'border-emerald-500/50 bg-emerald-500/5 text-emerald-700 dark:text-emerald-300',
    sky: 'border-sky-500/50 bg-sky-500/5 text-sky-700 dark:text-sky-300',
    violet: 'border-violet-500/50 bg-violet-500/5 text-violet-700 dark:text-violet-300',
  }
  return (
    <div
      className={[
        'rounded-lg border p-3',
        accentMap[accent],
        span ? 'lg:col-span-1' : '',
      ].join(' ')}
    >
      <div className="text-xs font-semibold uppercase tracking-wide">{title}</div>
      <p className="mt-1.5 text-xs leading-5 text-zinc-700 dark:text-zinc-300">
        {body}
      </p>
    </div>
  )
}

function ArchArrow() {
  return (
    <div className="flex items-center justify-center text-zinc-400">
      <span className="hidden font-mono text-xs lg:inline">▶</span>
      <span className="font-mono text-xs lg:hidden">▼</span>
    </div>
  )
}

function renderEm(s: string): string {
  const escaped = s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  return escaped
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code class="font-mono text-[12px]">$1</code>')
}
