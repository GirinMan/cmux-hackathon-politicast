import { useMemo } from 'react'
import Card from '../components/Card'
import StatGrid from '../components/StatGrid'
import { ErrorState, LoadingState } from '../components/States'
import EChart, { gridDefaults, PALETTE } from '../charts/EChart'
import {
  useFiveRegions,
  useOccupationMajor,
  useOccupations,
  useRegions,
} from '../hooks/queries'
import { useFilter } from '../state/filter'
import { useTheme } from '../state/theme'

const NF = new Intl.NumberFormat('ko-KR')

export default function RegionsPage() {
  const { filter } = useFilter()
  const { theme } = useTheme()
  const provinces = useRegions()
  const five = useFiveRegions()
  const occupations = useOccupations(filter.region, 20)
  const occupationMajor = useOccupationMajor(filter.region)

  const provinceOption = useMemo(() => {
    if (!provinces.data) return {}
    const data = [...provinces.data.provinces].sort((a, b) => b.count - a.count)
    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: { name: string; value: number }[]) => {
          const p = params[0]
          const total = provinces.data!.total
          return `${p.name}<br/>${NF.format(p.value)} · ${(
            (p.value / total) *
            100
          ).toFixed(2)}%`
        },
      },
      grid: { ...gridDefaults(theme), left: 80 },
      xAxis: {
        type: 'value',
        axisLabel: {
          color: theme === 'dark' ? PALETTE.textDark : PALETTE.textLight,
          formatter: (v: number) => NF.format(v),
        },
        splitLine: {
          lineStyle: { color: theme === 'dark' ? '#27272a' : '#e4e4e7' },
        },
      },
      yAxis: {
        type: 'category',
        inverse: true,
        data: data.map((p) => p.province),
        axisLabel: {
          color: theme === 'dark' ? PALETTE.textDark : PALETTE.textLight,
        },
      },
      series: [
        {
          type: 'bar',
          data: data.map((p) => p.count),
          itemStyle: { color: PALETTE.accent, borderRadius: [0, 4, 4, 0] },
          barMaxWidth: 16,
        },
      ],
    }
  }, [provinces.data, theme])

  const occupationOption = useMemo(() => {
    if (!occupations.data) return {}
    const items = [...occupations.data.top]
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { ...gridDefaults(theme), left: 130 },
      xAxis: {
        type: 'value',
        axisLabel: {
          color: theme === 'dark' ? PALETTE.textDark : PALETTE.textLight,
          formatter: (v: number) => NF.format(v),
        },
        splitLine: {
          lineStyle: { color: theme === 'dark' ? '#27272a' : '#e4e4e7' },
        },
      },
      yAxis: {
        type: 'category',
        inverse: true,
        data: items.map((o) => o.occupation),
        axisLabel: {
          color: theme === 'dark' ? PALETTE.textDark : PALETTE.textLight,
          formatter: (v: string) => (v.length > 14 ? `${v.slice(0, 14)}…` : v),
        },
      },
      series: [
        {
          type: 'bar',
          data: items.map((o) => o.count),
          itemStyle: { color: PALETTE.accent, borderRadius: [0, 4, 4, 0] },
          barMaxWidth: 14,
        },
      ],
    }
  }, [occupations.data, theme])

  const occupationMajorOption = useMemo(() => {
    if (!occupationMajor.data) return {}
    const items = [...occupationMajor.data.groups]
    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: { name: string; value: number }[]) => {
          const p = params[0]
          const group = items.find((item) => item.major === p.name)
          return `${p.name}<br/>${NF.format(p.value)} · ${group?.pct.toFixed(1) ?? '0.0'}%`
        },
      },
      grid: { ...gridDefaults(theme), left: 170 },
      xAxis: {
        type: 'value',
        axisLabel: {
          color: theme === 'dark' ? PALETTE.textDark : PALETTE.textLight,
          formatter: (v: number) => NF.format(v),
        },
        splitLine: {
          lineStyle: { color: theme === 'dark' ? '#27272a' : '#e4e4e7' },
        },
      },
      yAxis: {
        type: 'category',
        inverse: true,
        data: items.map((item) => item.major),
        axisLabel: {
          color: theme === 'dark' ? PALETTE.textDark : PALETTE.textLight,
          formatter: (v: string) => (v.length > 16 ? `${v.slice(0, 16)}…` : v),
        },
      },
      series: [
        {
          type: 'bar',
          data: items.map((item) => item.count),
          itemStyle: {
            color: (params: { dataIndex: number }) =>
              MAJOR_COLORS[params.dataIndex % MAJOR_COLORS.length],
            borderRadius: [0, 4, 4, 0],
          },
          barMaxWidth: 16,
        },
      ],
    }
  }, [occupationMajor.data, theme])

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">지역</h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
          17 시도 분포 + PolitiKAST contract region 매칭. 상단 region 칩으로 직업 차트가 즉시 갱신됩니다.
          <span className="ml-2 text-xs text-zinc-500">
            (province 약식 표기: '경상남' / '전북' 등 비일관)
          </span>
        </p>
      </header>

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
              <div
                key={r.key}
                className={[
                  'rounded-lg border px-4 py-3',
                  r.available
                    ? filter.region === r.key
                      ? 'border-emerald-500/60 bg-emerald-500/5'
                      : 'border-zinc-200 dark:border-zinc-800'
                    : 'border-dashed border-zinc-300 dark:border-zinc-700 opacity-60',
                ].join(' ')}
              >
                <div className="flex items-baseline justify-between">
                  <span className="font-medium">{r.label_ko}</span>
                  <span className="text-[11px] text-zinc-500 dark:text-zinc-400">
                    {r.label_en}
                  </span>
                </div>
                <div className="mt-2 text-xl font-semibold tabular-nums">
                  {r.available ? NF.format(r.count) : '미정'}
                </div>
                <div className="mt-0.5 text-[11px] text-zinc-500 dark:text-zinc-400 truncate">
                  {r.district ?? r.province ?? 'region 조건 없음'}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="시도(province) 분포" subtitle="17 광역, 행 수 내림차순">
          {provinces.isLoading ? (
            <LoadingState />
          ) : provinces.error ? (
            <ErrorState error={provinces.error} retry={provinces.refetch} />
          ) : (
            <>
              <StatGrid
                stats={[
                  { label: '총 행', value: NF.format(provinces.data?.total ?? 0) },
                  {
                    label: '최대 시도',
                    value: provinces.data?.provinces[0]?.province ?? '—',
                    hint: provinces.data
                      ? `${NF.format(provinces.data.provinces[0]?.count ?? 0)} 명`
                      : undefined,
                  },
                ]}
              />
              <div className="mt-4">
                <EChart option={provinceOption} height={460} />
              </div>
            </>
          )}
        </Card>

        <Card
          title={`직업 Top 20 ${filter.region ? `· ${filter.region}` : ''}`}
          subtitle={`distinct 직업 수: ${
            occupations.data ? NF.format(occupations.data.total_distinct) : '—'
          }`}
        >
          {occupations.isLoading ? (
            <LoadingState />
          ) : occupations.error ? (
            <ErrorState error={occupations.error} retry={occupations.refetch} />
          ) : (
            <EChart option={occupationOption} height={460} />
          )}
        </Card>
      </div>

      <Card
        title={`직업 대분류 ${filter.region ? `· ${filter.region}` : ''}`}
        subtitle={occupationMajor.data?.meta.target_taxonomy ?? 'KSCO major groups'}
      >
        {occupationMajor.isLoading ? (
          <LoadingState />
        ) : occupationMajor.error ? (
          <ErrorState error={occupationMajor.error} retry={occupationMajor.refetch} />
        ) : (
          <EChart option={occupationMajorOption} height={440} />
        )}
      </Card>
    </div>
  )
}

const MAJOR_COLORS = [
  '#0f766e',
  '#2563eb',
  '#7c3aed',
  '#c026d3',
  '#e11d48',
  '#ea580c',
  '#ca8a04',
  '#65a30d',
  '#0891b2',
  '#4f46e5',
  '#64748b',
]
