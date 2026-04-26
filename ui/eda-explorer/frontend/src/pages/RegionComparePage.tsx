import { useMemo } from 'react'
import Card from '../components/Card'
import StatGrid from '../components/StatGrid'
import { ErrorState, LoadingState } from '../components/States'
import EChart, { gridDefaults, PALETTE, type LooseEChartsOption } from '../charts/EChart'
import { useDemographicsMany, useFiveRegions } from '../hooks/queries'
import { useTheme } from '../state/theme'
import type { DemographicsResponse, FiveRegionItem } from '../types/api'

const NF = new Intl.NumberFormat('ko-KR')

interface RegionProfile {
  meta: FiveRegionItem
  demographics: DemographicsResponse
}

export default function RegionComparePage() {
  const { theme } = useTheme()
  const regions = useFiveRegions()
  const available = useMemo(
    () => regions.data?.regions.filter((region) => region.available) ?? [],
    [regions.data],
  )
  const queries = useDemographicsMany(available.map((region) => region.key))

  const profiles = useMemo<RegionProfile[]>(() => {
    return available.flatMap((meta, index) => {
      const demographics = queries[index]?.data
      return demographics ? [{ meta, demographics }] : []
    })
  }, [available, queries])

  const loading = regions.isLoading || queries.some((query) => query.isLoading)
  const error =
    regions.error ?? queries.find((query) => query.error)?.error ?? null

  const populationOption = useMemo(
    () => buildBarOption(profiles, 'population', theme),
    [profiles, theme],
  )
  const ageOption = useMemo(
    () => buildBarOption(profiles, 'age', theme),
    [profiles, theme],
  )
  const turnoutShapeOption = useMemo(
    () => buildStackedAgeOption(profiles, theme),
    [profiles, theme],
  )

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">지역 비교</h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
          contract region 5개를 같은 축에서 비교한다. 대구 달서구 갑은 대구시장 region의 부분집합이다.
        </p>
      </header>

      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState
          error={error}
          retry={() => {
            void regions.refetch()
            queries.forEach((query) => void query.refetch())
          }}
        />
      ) : (
        <>
          <StatGrid
            stats={[
              { label: 'regions', value: profiles.length },
              {
                label: 'largest',
                value: profiles[0]?.meta.label_ko ?? '—',
                hint: profiles[0]
                  ? NF.format(profiles[0].demographics.total)
                  : undefined,
              },
              {
                label: 'smallest',
                value: profiles.at(-1)?.meta.label_ko ?? '—',
                hint: profiles.at(-1)
                  ? NF.format(profiles.at(-1)!.demographics.total)
                  : undefined,
              },
              {
                label: 'scope note',
                value: 'contest',
                hint: 'overlap allowed',
              },
            ]}
          />

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <Card title="모집단 크기" subtitle="region별 persona rows">
              <EChart option={populationOption} height={360} />
            </Card>
            <Card title="평균 연령" subtitle="region별 age 평균">
              <EChart option={ageOption} height={360} />
            </Card>
          </div>

          <Card title="연령대 구성" subtitle="count 기준 stacked view">
            <EChart option={turnoutShapeOption} height={420} />
          </Card>

          <Card title="Demographic Matrix" subtitle="sex / education / marital top buckets">
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400 border-b border-zinc-200 dark:border-zinc-800">
                    <th className="py-2 pr-4">region</th>
                    <th className="py-2 pr-4 text-right">rows</th>
                    <th className="py-2 pr-4 text-right">avg age</th>
                    <th className="py-2 pr-4">sex top</th>
                    <th className="py-2 pr-4">education top</th>
                    <th className="py-2 pr-4">marital top</th>
                  </tr>
                </thead>
                <tbody>
                  {profiles.map(({ meta, demographics }) => (
                    <tr
                      key={meta.key}
                      className="border-b border-zinc-100 dark:border-zinc-900"
                    >
                      <td className="py-2 pr-4">
                        <div className="font-medium text-zinc-900 dark:text-zinc-100">
                          {meta.label_ko}
                        </div>
                        <div className="text-[11px] text-zinc-500 dark:text-zinc-400">
                          {meta.key}
                        </div>
                      </td>
                      <td className="py-2 pr-4 text-right tabular-nums">
                        {NF.format(demographics.total)}
                      </td>
                      <td className="py-2 pr-4 text-right tabular-nums">
                        {demographics.age_stats.avg.toFixed(1)}
                      </td>
                      <td className="py-2 pr-4">{bucketLabel(demographics.sex)}</td>
                      <td className="py-2 pr-4">
                        {bucketLabel(demographics.education_level)}
                      </td>
                      <td className="py-2 pr-4">
                        {bucketLabel(demographics.marital_status)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}

function labelFor(region: FiveRegionItem) {
  return region.label_ko.length > 12
    ? `${region.label_ko.slice(0, 12)}…`
    : region.label_ko
}

function buildBarOption(
  profiles: RegionProfile[],
  metric: 'population' | 'age',
  theme: 'light' | 'dark',
): LooseEChartsOption {
  const sorted = [...profiles].sort((a, b) => {
    const av =
      metric === 'population'
        ? a.demographics.total
        : a.demographics.age_stats.avg
    const bv =
      metric === 'population'
        ? b.demographics.total
        : b.demographics.age_stats.avg
    return bv - av
  })
  const values = sorted.map((profile) =>
    metric === 'population'
      ? profile.demographics.total
      : Number(profile.demographics.age_stats.avg.toFixed(1)),
  )
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { ...gridDefaults(theme), left: 130 },
    xAxis: {
      type: 'value',
      axisLabel: {
        color: theme === 'dark' ? PALETTE.textDark : PALETTE.textLight,
        formatter: (value: number) =>
          metric === 'population' ? NF.format(value) : value.toFixed(0),
      },
      splitLine: { lineStyle: { color: theme === 'dark' ? '#27272a' : '#e4e4e7' } },
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: sorted.map((profile) => labelFor(profile.meta)),
      axisLabel: { color: theme === 'dark' ? PALETTE.textDark : PALETTE.textLight },
    },
    series: [
      {
        type: 'bar',
        data: values,
        itemStyle: { color: PALETTE.accent, borderRadius: [0, 4, 4, 0] },
        barMaxWidth: 18,
      },
    ],
  }
}

function buildStackedAgeOption(
  profiles: RegionProfile[],
  theme: 'light' | 'dark',
): LooseEChartsOption {
  const buckets = Array.from(
    new Set(profiles.flatMap((profile) => profile.demographics.age_buckets.map((b) => b.bucket))),
  )
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: (value: number) => NF.format(value),
    },
    legend: {
      type: 'scroll',
      bottom: 0,
      textStyle: { color: theme === 'dark' ? PALETTE.textDark : PALETTE.textLight },
    },
    grid: { ...gridDefaults(theme), left: 130, bottom: 58 },
    xAxis: {
      type: 'value',
      axisLabel: {
        color: theme === 'dark' ? PALETTE.textDark : PALETTE.textLight,
        formatter: (value: number) => NF.format(value),
      },
      splitLine: { lineStyle: { color: theme === 'dark' ? '#27272a' : '#e4e4e7' } },
    },
    yAxis: {
      type: 'category',
      data: profiles.map((profile) => labelFor(profile.meta)),
      axisLabel: { color: theme === 'dark' ? PALETTE.textDark : PALETTE.textLight },
    },
    series: buckets.map((bucket, index) => ({
      name: bucket,
      type: 'bar',
      stack: 'age',
      data: profiles.map((profile) => {
        return profile.demographics.age_buckets.find((b) => b.bucket === bucket)?.count ?? 0
      }),
      itemStyle: {
        color: AGE_COLORS[index % AGE_COLORS.length],
      },
    })),
  }
}

const AGE_COLORS = ['#0f766e', '#0891b2', '#2563eb', '#7c3aed', '#c026d3', '#e11d48', '#ea580c', '#ca8a04']

function bucketLabel(buckets: { value: string; pct: number }[]) {
  const top = [...buckets].sort((a, b) => b.pct - a.pct)[0]
  return top ? `${top.value} ${top.pct.toFixed(1)}%` : '—'
}
