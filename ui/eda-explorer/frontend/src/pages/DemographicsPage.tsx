import { useMemo } from 'react'
import Card from '../components/Card'
import StatGrid from '../components/StatGrid'
import { ErrorState, LoadingState } from '../components/States'
import EChart, { gridDefaults, PALETTE } from '../charts/EChart'
import { useDemographics } from '../hooks/queries'
import { useFilter } from '../state/filter'
import { useTheme } from '../state/theme'
import type { CountBucket } from '../types/api'

const NF = new Intl.NumberFormat('ko-KR')
const PCT = (v: number) => `${v.toFixed(1)}%`

export default function DemographicsPage() {
  const { filter } = useFilter()
  const { theme } = useTheme()
  const { data, isLoading, error, refetch } = useDemographics(filter.region)

  const ageOption = useMemo(() => {
    if (!data) return {}
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: gridDefaults(theme),
      xAxis: {
        type: 'category',
        data: data.age_buckets.map((b) => b.bucket),
        axisLabel: { color: theme === 'dark' ? PALETTE.textDark : PALETTE.textLight },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          color: theme === 'dark' ? PALETTE.textDark : PALETTE.textLight,
          formatter: (v: number) => NF.format(v),
        },
        splitLine: {
          lineStyle: { color: theme === 'dark' ? '#27272a' : '#e4e4e7' },
        },
      },
      series: [
        {
          type: 'bar',
          data: data.age_buckets.map((b) => b.count),
          itemStyle: { color: PALETTE.accent, borderRadius: [4, 4, 0, 0] },
          barMaxWidth: 48,
        },
      ],
    }
  }, [data, theme])

  const sexOption = useMemo(() => {
    if (!data) return {}
    return {
      tooltip: {
        trigger: 'item',
        formatter: (p: { name: string; value: number; percent: number }) =>
          `${p.name}<br/>${NF.format(p.value)} · ${p.percent.toFixed(2)}%`,
      },
      legend: {
        bottom: 0,
        textStyle: { color: theme === 'dark' ? PALETTE.textDark : PALETTE.textLight },
      },
      series: [
        {
          type: 'pie',
          radius: ['52%', '78%'],
          center: ['50%', '46%'],
          avoidLabelOverlap: true,
          itemStyle: { borderColor: theme === 'dark' ? '#0a0a0a' : '#fff', borderWidth: 2 },
          label: { color: theme === 'dark' ? '#e4e4e7' : '#27272a' },
          data: data.sex.map((b, i) => ({
            name: b.value,
            value: b.count,
            itemStyle: {
              color: i === 0 ? PALETTE.accent : '#a1a1aa',
            },
          })),
        },
      ],
    }
  }, [data, theme])

  const maritalOption = useMemo(() => barOption(data?.marital_status, theme), [data, theme])
  const educationOption = useMemo(
    () => barOption(data?.education_level, theme, true),
    [data, theme],
  )

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">인구통계</h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
          연령 / 성별 / 결혼상태 / 학력 분포 (region 필터 적용 가능). KOSIS 인구주택총조사 분류
          + KSCO 직업분류 8차와 1:1 호환.
        </p>
      </header>

      {isLoading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState error={error} retry={refetch} />
      ) : data ? (
        <>
          <StatGrid
            stats={[
              {
                label: 'region',
                value: filter.region ?? '전체',
                hint: `${NF.format(data.total)} 명`,
              },
              { label: '연령 평균', value: data.age_stats.avg.toFixed(1), hint: '만 19세 이상' },
              { label: '연령 중위', value: data.age_stats.median.toFixed(0) },
              {
                label: '연령 범위',
                value: `${data.age_stats.min}–${data.age_stats.max}`,
              },
            ]}
          />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card title="연령 분포" subtitle="10년 단위 버킷">
              <EChart option={ageOption} height={320} />
            </Card>
            <Card title="성별" subtitle="여자 / 남자 (sex 필드 — gender 부재)">
              <EChart option={sexOption} height={320} />
            </Card>
            <Card title="결혼 상태" subtitle="배우자있음 / 미혼 / 사별 / 이혼">
              <EChart option={maritalOption} height={320} />
            </Card>
            <Card title="학력" subtitle="무학 → 대학원 (서수 정렬)">
              <EChart option={educationOption} height={360} />
            </Card>
          </div>
        </>
      ) : null}
    </div>
  )
}

function barOption(
  buckets: CountBucket[] | undefined,
  theme: 'light' | 'dark',
  horizontal = false,
) {
  if (!buckets) return {}
  const labels = buckets.map((b) => b.value)
  const counts = buckets.map((b) => b.count)
  const grid = gridDefaults(theme)
  const valueAxis = {
    type: 'value' as const,
    axisLabel: {
      color: theme === 'dark' ? PALETTE.textDark : PALETTE.textLight,
      formatter: (v: number) => NF.format(v),
    },
    splitLine: {
      lineStyle: { color: theme === 'dark' ? '#27272a' : '#e4e4e7' },
    },
  }
  const categoryAxis = {
    type: 'category' as const,
    data: labels,
    axisLabel: {
      color: theme === 'dark' ? PALETTE.textDark : PALETTE.textLight,
      interval: 0,
      formatter: (v: string) => (v.length > 10 ? `${v.slice(0, 10)}…` : v),
    },
  }
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: { name: string; value: number }[]) => {
        const p = params[0]
        const total = counts.reduce((a, b) => a + b, 0)
        const pct = total > 0 ? (p.value / total) * 100 : 0
        return `${p.name}<br/>${NF.format(p.value)} · ${PCT(pct)}`
      },
    },
    grid: { ...grid, left: horizontal ? 110 : grid.left },
    xAxis: horizontal ? valueAxis : categoryAxis,
    yAxis: horizontal ? { ...categoryAxis, inverse: true } : valueAxis,
    series: [
      {
        type: 'bar',
        data: counts,
        itemStyle: {
          color: PALETTE.accent,
          borderRadius: horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0],
        },
        barMaxWidth: horizontal ? 18 : 48,
      },
    ],
  }
}
