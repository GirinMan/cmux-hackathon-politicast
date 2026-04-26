import { useMemo, useState, type CSSProperties, type ReactNode } from 'react'
import Card from '../components/Card'
import { EmptyState, ErrorState, LoadingState } from '../components/States'
import {
  usePersonaDetail,
  usePersonaSample,
  useResultDetail,
  useResults,
} from '../hooks/queries'
import { useFilter } from '../state/filter'
import type { PersonaDetail, PersonaSummary, ScenarioResult } from '../types/api'
import personaFacetsHero from '../assets/persona-facets-hero.png'

const NF = new Intl.NumberFormat('ko-KR')

const FACETS = [
  {
    label: '인구통계',
    body: '성별, 연령, 혼인, 군 복무, 지역 조건이 기본 stratification 축을 만듭니다.',
  },
  {
    label: '생활 기반',
    body: '가구 형태, 주거 유형, 시도와 구군은 지역 선거 맥락과 연결됩니다.',
  },
  {
    label: '학력·직업',
    body: '학력, 전공, 직업은 LLM routing과 정책 선호 prior의 핵심 신호입니다.',
  },
  {
    label: '기술·취향',
    body: 'skills, hobbies list는 에이전트 응답의 구체적 생활감을 보강합니다.',
  },
  {
    label: '서사 필드',
    body: '직업·가족·문화·여행·요리·예술 서사가 인터뷰와 투표 이유를 풍부하게 합니다.',
  },
]

export default function PersonasPage() {
  const { filter } = useFilter()
  const [seed, setSeed] = useState<number>(() => Math.floor(Math.random() * 1000))
  const [openUuid, setOpenUuid] = useState<string | null>(null)
  const [selectedUuid, setSelectedUuid] = useState<string | null>(null)

  const sample = usePersonaSample(filter.region, 24, seed)

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">페르소나</h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
          다층 합성 인구 프로필의 구성 요소를 훑고, 랜덤 샘플 24명의 실제 필드를 확인합니다.
        </p>
      </header>

      <Card
        title="페르소나 구성"
        subtitle="텍스트 길이는 설명력이 낮으므로, 실제 모델 입력에서 쓰이는 특성 층위를 중심으로 봅니다."
      >
        <PersonaFacetIntro />
      </Card>

      <Card
        title={`페르소나 샘플 ${filter.region ? `· ${filter.region}` : ''}`}
        subtitle={`전체 ${sample.data ? NF.format(sample.data.total) : '—'} 명 중 24명 랜덤 추출`}
        right={
          <button
            type="button"
            onClick={() => setSeed(Math.floor(Math.random() * 1000))}
            className="text-xs px-3 py-1.5 rounded-md ring-1 ring-zinc-300 dark:ring-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-900"
          >
            새로고침 (seed)
          </button>
        }
      >
        {sample.isLoading ? (
          <LoadingState />
        ) : sample.error ? (
          <ErrorState error={sample.error} retry={sample.refetch} />
        ) : (
          <PersonaSampleExplorer
            samples={sample.data?.samples ?? []}
            selectedUuid={selectedUuid}
            onSelect={setSelectedUuid}
            onOpen={setOpenUuid}
          />
        )}
      </Card>

      <InterviewSection regionFilter={filter.region} />

      {openUuid && (
        <PersonaModal uuid={openUuid} onClose={() => setOpenUuid(null)} />
      )}
    </div>
  )
}

function InterviewSection({ regionFilter }: { regionFilter: string | null }) {
  const results = useResults()
  const fallbackRegion =
    results.data?.regions.find(
      (r) => r.status === 'live' && (r.persona_n ?? 0) > 0,
    )?.region_id ??
    results.data?.regions[0]?.region_id ??
    null
  const targetRegion = regionFilter ?? fallbackRegion
  const detail = useResultDetail(targetRegion)
  const labels = detail.data?.candidate_labels ?? {}
  const parties = detail.data?.candidate_parties ?? {}
  const result: ScenarioResult | undefined = detail.data?.result
  const interviews = useMemo(() => result?.virtual_interviews ?? [], [result])

  const timesteps = useMemo(() => {
    const set = new Set<number>()
    for (const it of interviews) set.add(it.timestep)
    return Array.from(set).sort((a, b) => a - b)
  }, [interviews])
  const [tsFilter, setTsFilter] = useState<number | 'all'>('all')
  const [voteFilter, setVoteFilter] = useState<string | 'all'>('all')

  const voteIds = useMemo(() => {
    const set = new Set<string>()
    for (const it of interviews) if (it.vote) set.add(it.vote)
    return Array.from(set)
  }, [interviews])

  const visible = useMemo(
    () =>
      interviews.filter(
        (it) =>
          (tsFilter === 'all' || it.timestep === tsFilter) &&
          (voteFilter === 'all' || (it.vote ?? 'abstain') === voteFilter),
      ),
    [interviews, tsFilter, voteFilter],
  )

  const subtitle = targetRegion
    ? `region=${targetRegion} · 총 ${NF.format(interviews.length)} 응답 · 표시 ${NF.format(visible.length)}`
    : '응답 region이 선택되지 않았습니다.'

  return (
    <Card
      title="시뮬레이션 인터뷰"
      subtitle={subtitle}
      right={
        timesteps.length > 0 || voteIds.length > 0 ? (
          <div className="flex flex-wrap items-center gap-2 text-[11px]">
            {timesteps.length > 0 && (
              <select
                value={tsFilter === 'all' ? 'all' : String(tsFilter)}
                onChange={(e) =>
                  setTsFilter(e.target.value === 'all' ? 'all' : Number(e.target.value))
                }
                className="rounded-md border border-zinc-300 bg-white px-2 py-1 dark:border-zinc-700 dark:bg-zinc-950"
              >
                <option value="all">timestep · all</option>
                {timesteps.map((t) => (
                  <option key={t} value={t}>{`t=${t}`}</option>
                ))}
              </select>
            )}
            {voteIds.length > 0 && (
              <select
                value={voteFilter}
                onChange={(e) => setVoteFilter(e.target.value)}
                className="rounded-md border border-zinc-300 bg-white px-2 py-1 dark:border-zinc-700 dark:bg-zinc-950"
              >
                <option value="all">vote · all</option>
                {voteIds.map((id) => (
                  <option key={id} value={id}>
                    {labels[id] ?? id}
                  </option>
                ))}
              </select>
            )}
          </div>
        ) : null
      }
    >
      {!targetRegion ? (
        <EmptyState>region을 선택하면 voter agent 응답이 표시됩니다.</EmptyState>
      ) : detail.isLoading ? (
        <LoadingState />
      ) : detail.error ? (
        <ErrorState error={detail.error} retry={detail.refetch} />
      ) : interviews.length === 0 ? (
        <EmptyState>이 region 결과에 virtual_interviews가 없습니다.</EmptyState>
      ) : (
        <InterviewGrid
          interviews={visible}
          labels={labels}
          parties={parties}
        />
      )}
    </Card>
  )
}

function InterviewGrid({
  interviews,
  labels,
  parties,
}: {
  interviews: ScenarioResult['virtual_interviews']
  labels: Record<string, string>
  parties: Record<string, string>
}) {
  if (interviews.length === 0) {
    return <EmptyState>현재 필터에 해당하는 응답이 없습니다.</EmptyState>
  }
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {interviews.map((item, idx) => {
        const voteId = item.vote ?? 'abstain'
        const accent = voteAccent(voteId)
        return (
          <article
            key={`${item.persona_id}-${item.timestep}-${idx}`}
            className="relative flex flex-col gap-3 overflow-hidden rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950/40"
          >
            <span
              className="absolute left-0 top-0 h-full w-1"
              style={{ backgroundColor: accent }}
              aria-hidden
            />
            <header className="flex items-center justify-between gap-2 pl-1">
              <span
                className="rounded-full px-2 py-0.5 text-[11px] font-semibold"
                style={{ color: accent, backgroundColor: `${accent}1f` }}
              >
                {labels[voteId] ?? (voteId === 'abstain' ? '기권' : voteId)}
                {parties[voteId] ? ` · ${parties[voteId]}` : ''}
              </span>
              <span className="font-mono text-[11px] text-zinc-500 dark:text-zinc-400">
                t={item.timestep} · {item.persona_id.slice(0, 8)}
              </span>
            </header>
            <blockquote className="pl-1 text-sm leading-6 text-zinc-800 dark:text-zinc-200">
              “{item.reason}”
            </blockquote>
            {item.key_factors && item.key_factors.length > 0 && (
              <div className="flex flex-wrap gap-1 pl-1">
                {item.key_factors.map((factor) => (
                  <span
                    key={factor}
                    className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
                  >
                    {factor}
                  </span>
                ))}
              </div>
            )}
          </article>
        )
      })}
    </div>
  )
}

const VOTE_PALETTE = [
  '#34d399',
  '#60a5fa',
  '#fbbf24',
  '#fb7185',
  '#a78bfa',
  '#22d3ee',
  '#f472b6',
]

function voteAccent(voteId: string) {
  if (voteId === 'abstain') return '#71717a'
  let hash = 0
  for (let i = 0; i < voteId.length; i += 1) {
    hash = (hash * 31 + voteId.charCodeAt(i)) >>> 0
  }
  return VOTE_PALETTE[hash % VOTE_PALETTE.length]
}

function PersonaFacetIntro() {
  return (
    <div className="grid gap-5 lg:grid-cols-[1.45fr_0.9fr]">
      <div className="relative overflow-hidden rounded-lg border border-zinc-200 bg-zinc-950 dark:border-zinc-800">
        <img
          src={personaFacetsHero}
          alt="A layered synthetic persona profile showing demographics, household, education, occupation, hobbies, and narrative context as connected visual facets."
          className="aspect-[16/8] h-full w-full object-cover object-center opacity-95"
        />
        <div className="pointer-events-none absolute inset-0 ring-1 ring-inset ring-white/10" />
      </div>

      <div className="flex flex-col justify-between gap-4">
        <div>
          <p className="text-sm leading-6 text-zinc-700 dark:text-zinc-300">
            이 데이터셋의 페르소나는 긴 문장 묶음이 아니라, 선거 시뮬레이션에서
            개인을 설명하는 여러 층의 입력 상태입니다. 아래 샘플 카드는 이 층들이
            실제 개인 프로필로 어떻게 결합되는지 확인하는 용도입니다.
          </p>
        </div>
        <div className="space-y-3">
          {FACETS.map((facet, index) => (
            <div
              key={facet.label}
              className="grid grid-cols-[2.25rem_1fr] gap-3 border-t border-zinc-200 pt-3 first:border-t-0 first:pt-0 dark:border-zinc-800"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-zinc-100 font-mono text-xs text-emerald-700 ring-1 ring-zinc-200 dark:bg-zinc-900 dark:text-emerald-300 dark:ring-zinc-800">
                {String(index + 1).padStart(2, '0')}
              </div>
              <div>
                <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                  {facet.label}
                </h3>
                <p className="mt-1 text-xs leading-5 text-zinc-600 dark:text-zinc-400">
                  {facet.body}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function PersonaSampleExplorer({
  samples,
  selectedUuid,
  onSelect,
  onOpen,
}: {
  samples: PersonaSummary[]
  selectedUuid: string | null
  onSelect: (uuid: string) => void
  onOpen: (uuid: string) => void
}) {
  if (samples.length === 0) {
    return <EmptyState>선택한 region에 표시할 persona sample이 없습니다.</EmptyState>
  }

  const selected =
    samples.find((persona) => persona.uuid === selectedUuid) ?? samples[0]

  return (
    <div className="grid gap-4 xl:grid-cols-[0.82fr_1.18fr]">
      <PersonaSpotlight p={selected} onOpen={() => onOpen(selected.uuid)} />

      <div className="min-w-0">
        <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h3 className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">
              Sample deck
            </h3>
            <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
              색상 ID, demographic 좌표, model-facing signal을 빠르게 비교합니다.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            {samples.length} sampled profiles
          </div>
        </div>
        <div className="grid gap-2 md:grid-cols-2">
          {samples.map((persona, index) => (
            <PersonaDeckCard
              key={persona.uuid}
              p={persona}
              index={index}
              active={persona.uuid === selected.uuid}
              onSelect={() => onSelect(persona.uuid)}
              onOpen={() => onOpen(persona.uuid)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

function PersonaSpotlight({
  p,
  onOpen,
}: {
  p: PersonaSummary
  onOpen: () => void
}) {
  const accent = personaAccent(p.uuid)
  const name = personaName(p.persona)
  return (
    <section
      className="relative overflow-hidden rounded-lg border bg-zinc-950 p-4 text-white"
      style={{ borderColor: accent.border } as CSSProperties}
    >
      <div
        className="absolute inset-0 opacity-70"
        style={{
          background: `radial-gradient(circle at 18% 16%, ${accent.glow}, transparent 34%), linear-gradient(135deg, rgba(24,24,27,0.35), rgba(9,9,11,0.96))`,
        }}
      />
      <div className="absolute -right-10 -top-12 h-44 w-44 rounded-full border border-white/10" />
      <div className="absolute bottom-0 right-0 h-px w-2/3 bg-gradient-to-r from-transparent via-white/20 to-transparent" />

      <div className="relative z-10">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-medium uppercase text-zinc-400">
              Selected persona
            </p>
            <h3 className="mt-2 text-2xl font-semibold">{name}</h3>
            <p className="mt-1 text-sm text-zinc-300">
              {p.sex ?? '—'} · {p.age ?? '—'}세 · {p.province ?? '지역 미상'}
            </p>
          </div>
          <div
            className="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg border text-xl font-semibold"
            style={{
              borderColor: accent.border,
              backgroundColor: accent.panel,
              color: accent.text,
            }}
          >
            {name.slice(0, 1)}
          </div>
        </div>

        <blockquote className="mt-5 border-l-2 border-white/20 pl-4 text-base leading-7 text-zinc-100">
          {p.persona ?? '요약 persona 텍스트가 없습니다.'}
        </blockquote>

        <div className="mt-5 grid grid-cols-2 gap-2">
          <PersonaFact label="occupation" value={p.occupation} />
          <PersonaFact label="education" value={p.education_level} />
          <PersonaFact label="district" value={p.district} />
          <PersonaFact label="uuid" value={`${p.uuid.slice(0, 10)}...`} mono />
        </div>

        <div className="mt-5 space-y-3">
          <SignalRow label="age" value={normalizeNumber(p.age, 18, 85)} accent={accent.text} />
          <SignalRow
            label="education"
            value={educationScore(p.education_level)}
            accent={accent.text}
          />
          <SignalRow label="geo" value={hashToUnit(p.district ?? p.province ?? p.uuid)} accent={accent.text} />
        </div>

        <button
          type="button"
          onClick={onOpen}
          className="mt-6 rounded-md border border-white/20 bg-white/10 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-white/15"
        >
          전체 필드 보기
        </button>
      </div>
    </section>
  )
}

function PersonaDeckCard({
  p,
  index,
  active,
  onSelect,
  onOpen,
}: {
  p: PersonaSummary
  index: number
  active: boolean
  onSelect: () => void
  onOpen: () => void
}) {
  const accent = personaAccent(p.uuid)
  const name = personaName(p.persona)
  return (
    <article
      className={[
        'group rounded-lg border bg-white transition-colors dark:bg-zinc-950/30',
        active
          ? 'border-emerald-500/80 ring-1 ring-emerald-500/30'
          : 'border-zinc-200 hover:border-zinc-400 dark:border-zinc-800 dark:hover:border-zinc-600',
      ].join(' ')}
    >
      <button type="button" onClick={onSelect} className="block w-full p-3 text-left">
        <div className="flex items-start gap-3">
          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border text-sm font-semibold"
            style={{
              borderColor: accent.border,
              backgroundColor: accent.panel,
              color: accent.text,
            }}
          >
            {String(index + 1).padStart(2, '0')}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <h4 className="truncate text-sm font-semibold text-zinc-950 dark:text-zinc-50">
                {name}
              </h4>
              <span className="shrink-0 text-[11px] text-zinc-500 dark:text-zinc-400">
                {p.sex ?? '—'} · {p.age ?? '—'}
              </span>
            </div>
            <p className="mt-1 line-clamp-2 text-xs leading-5 text-zinc-600 dark:text-zinc-400">
              {p.persona ?? '—'}
            </p>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-1 text-[11px] text-zinc-500 dark:text-zinc-400">
          {p.occupation && <Pill>{compactLabel(p.occupation, 16)}</Pill>}
          {p.education_level && <Pill>{compactLabel(p.education_level, 12)}</Pill>}
          {(p.district || p.province) && (
            <Pill>{compactLabel(p.district ?? p.province ?? '', 16)}</Pill>
          )}
        </div>

        <div className="mt-3 grid grid-cols-3 gap-1">
          <MiniSignal value={normalizeNumber(p.age, 18, 85)} color={accent.text} />
          <MiniSignal value={educationScore(p.education_level)} color={accent.text} />
          <MiniSignal value={hashToUnit(p.occupation ?? p.uuid)} color={accent.text} />
        </div>
      </button>
      <div className="border-t border-zinc-100 px-3 py-2 dark:border-zinc-900">
        <button
          type="button"
          onClick={onOpen}
          className="text-xs font-medium text-zinc-500 transition-colors hover:text-emerald-600 dark:text-zinc-400 dark:hover:text-emerald-300"
        >
          상세 필드 열기
        </button>
      </div>
    </article>
  )
}

function Pill({ children }: { children: ReactNode }) {
  return (
    <span className="px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800/80">
      {children}
    </span>
  )
}

function PersonaFact({
  label,
  value,
  mono,
}: {
  label: string
  value: string | number | null | undefined
  mono?: boolean
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">
      <div className="text-[10px] uppercase text-zinc-500">{label}</div>
      <div
        className={[
          'mt-1 truncate text-sm text-zinc-100',
          mono ? 'font-mono text-xs' : '',
        ].join(' ')}
      >
        {value == null || value === '' ? '—' : value}
      </div>
    </div>
  )
}

function SignalRow({
  label,
  value,
  accent,
}: {
  label: string
  value: number
  accent: string
}) {
  const pct = Math.max(8, Math.min(100, Math.round(value * 100)))
  return (
    <div className="grid grid-cols-[5.5rem_1fr_2.5rem] items-center gap-2 text-xs">
      <span className="uppercase text-zinc-500">{label}</span>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full"
          style={{ width: `${pct}%`, backgroundColor: accent }}
        />
      </div>
      <span className="text-right font-mono text-zinc-400">{pct}</span>
    </div>
  )
}

function MiniSignal({ value, color }: { value: number; color: string }) {
  const pct = Math.max(10, Math.min(100, Math.round(value * 100)))
  return (
    <div className="h-1.5 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
      <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
    </div>
  )
}

function PersonaModal({ uuid, onClose }: { uuid: string; onClose: () => void }) {
  const { data, isLoading, error, refetch } = usePersonaDetail(uuid)
  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-40 flex items-center justify-center p-4 bg-zinc-950/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="max-w-3xl w-full max-h-[88vh] overflow-y-auto rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="sticky top-0 z-10 flex items-center justify-between px-5 py-3 border-b border-zinc-200 dark:border-zinc-800 bg-white/90 dark:bg-zinc-950/90 backdrop-blur">
          <div className="min-w-0">
            <h3 className="text-sm font-semibold">페르소나 상세</h3>
            <p className="text-[11px] font-mono text-zinc-500 dark:text-zinc-400 truncate">
              {uuid}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-xs px-2 py-1 rounded-md ring-1 ring-zinc-300 dark:ring-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-900"
          >
            닫기 (Esc)
          </button>
        </header>
        <div className="px-5 py-4">
          {isLoading ? (
            <LoadingState />
          ) : error ? (
            <ErrorState error={error} retry={refetch} />
          ) : data ? (
            <PersonaBody p={data} />
          ) : null}
        </div>
      </div>
    </div>
  )
}

const TEXT_FIELDS: { key: keyof PersonaDetail; label: string }[] = [
  { key: 'persona', label: 'persona (concise)' },
  { key: 'professional_persona', label: 'professional' },
  { key: 'sports_persona', label: 'sports' },
  { key: 'arts_persona', label: 'arts' },
  { key: 'travel_persona', label: 'travel' },
  { key: 'culinary_persona', label: 'culinary' },
  { key: 'family_persona', label: 'family' },
  { key: 'cultural_background', label: 'cultural_background' },
  { key: 'skills_and_expertise', label: 'skills_and_expertise' },
  { key: 'hobbies_and_interests', label: 'hobbies_and_interests' },
  { key: 'career_goals_and_ambitions', label: 'career_goals_and_ambitions' },
]

function PersonaBody({ p }: { p: PersonaDetail }) {
  return (
    <div className="space-y-4 text-sm">
      <dl className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
        <Fact k="sex" v={p.sex} />
        <Fact k="age" v={p.age} />
        <Fact k="marital" v={p.marital_status} />
        <Fact k="military" v={p.military_status} />
        <Fact k="family" v={p.family_type} />
        <Fact k="housing" v={p.housing_type} />
        <Fact k="education" v={p.education_level} />
        <Fact k="bachelors" v={p.bachelors_field} />
        <Fact k="occupation" v={p.occupation} />
        <Fact k="province" v={p.province} />
        <Fact k="district" v={p.district} />
        <Fact k="country" v={p.country} />
      </dl>

      {p.skills_and_expertise_list.length > 0 && (
        <ChipList label="skills_and_expertise_list" items={p.skills_and_expertise_list} />
      )}
      {p.hobbies_and_interests_list.length > 0 && (
        <ChipList label="hobbies_and_interests_list" items={p.hobbies_and_interests_list} />
      )}

      <div className="space-y-3">
        {TEXT_FIELDS.map(({ key, label }) => {
          const v = p[key] as string | null
          if (!v) return null
          return (
            <div key={key as string}>
              <h4 className="text-[11px] uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-1">
                {label}
              </h4>
              <p className="text-sm text-zinc-800 dark:text-zinc-200 leading-relaxed whitespace-pre-line">
                {v}
              </p>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function Fact({ k, v }: { k: string; v: string | number | null | undefined }) {
  return (
    <div className="rounded-md border border-zinc-200 dark:border-zinc-800 px-2 py-1.5">
      <div className="text-[10px] uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
        {k}
      </div>
      <div className="text-sm text-zinc-800 dark:text-zinc-100 break-words">
        {v == null || v === '' ? '—' : String(v)}
      </div>
    </div>
  )
}

function ChipList({ label, items }: { label: string; items: string[] }) {
  return (
    <div>
      <h4 className="text-[11px] uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-1">
        {label}
      </h4>
      <div className="flex flex-wrap gap-1.5">
        {items.map((s, i) => (
          <span
            key={i}
            className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 ring-1 ring-emerald-500/30"
          >
            {s}
          </span>
        ))}
      </div>
    </div>
  )
}

function personaName(text: string | null | undefined) {
  if (!text) return 'Persona'
  const match = text.match(/^([가-힣A-Za-z0-9·.-]{2,8})\s+씨는/)
  return match?.[1] ?? 'Persona'
}

function compactLabel(value: string, max: number) {
  return value.length > max ? `${value.slice(0, max - 1)}…` : value
}

function normalizeNumber(value: number | null | undefined, min: number, max: number) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 0.5
  return Math.max(0, Math.min(1, (value - min) / (max - min)))
}

function educationScore(value: string | null | undefined) {
  if (!value) return 0.35
  if (value.includes('대학원') || value.includes('박사') || value.includes('석사')) {
    return 0.95
  }
  if (value.includes('4년제')) return 0.78
  if (value.includes('전문대')) return 0.62
  if (value.includes('고등')) return 0.44
  if (value.includes('중학')) return 0.28
  return 0.52
}

function hashToUnit(value: string) {
  let hash = 0
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 31 + value.charCodeAt(i)) % 997
  }
  return hash / 996
}

function personaAccent(uuid: string) {
  const palette = [
    {
      text: '#34d399',
      border: 'rgba(52, 211, 153, 0.55)',
      panel: 'rgba(16, 185, 129, 0.12)',
      glow: 'rgba(16, 185, 129, 0.32)',
    },
    {
      text: '#22d3ee',
      border: 'rgba(34, 211, 238, 0.52)',
      panel: 'rgba(34, 211, 238, 0.11)',
      glow: 'rgba(34, 211, 238, 0.26)',
    },
    {
      text: '#fbbf24',
      border: 'rgba(251, 191, 36, 0.5)',
      panel: 'rgba(251, 191, 36, 0.11)',
      glow: 'rgba(251, 191, 36, 0.23)',
    },
    {
      text: '#60a5fa',
      border: 'rgba(96, 165, 250, 0.5)',
      panel: 'rgba(96, 165, 250, 0.11)',
      glow: 'rgba(96, 165, 250, 0.24)',
    },
    {
      text: '#fb7185',
      border: 'rgba(251, 113, 133, 0.48)',
      panel: 'rgba(251, 113, 133, 0.1)',
      glow: 'rgba(251, 113, 133, 0.22)',
    },
  ]
  return palette[Math.floor(hashToUnit(uuid) * palette.length) % palette.length]
}
