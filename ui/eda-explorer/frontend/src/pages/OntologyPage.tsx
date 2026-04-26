import { useMemo, useState, type SVGProps } from 'react'
import EChart, { type LooseEChartsOption } from '../charts/EChart'
import { ErrorState, LoadingState } from '../components/States'
import { useFiveRegions, useOntologyGraph, useRegions } from '../hooks/queries'
import { useFilter } from '../state/filter'
import type {
  OntologyCategory,
  OntologyEdge,
  OntologyNode,
} from '../types/api'

const NF = new Intl.NumberFormat('ko-KR')

const CATEGORY_ORDER = [
  'region',
  'province',
  'district',
  'age_group',
  'sex',
  'education_level',
  'occupation',
  'family_type',
  'housing_type',
]

const CATEGORY_VISUALS: Record<
  string,
  { color: string; shape: NodeShape; radius: number }
> = {
  region: { color: '#6fc7df', shape: 'territory', radius: 282 },
  province: { color: '#a9cf82', shape: 'province_grid', radius: 268 },
  district: { color: '#74c4b5', shape: 'target', radius: 248 },
  age_group: { color: '#e0a44a', shape: 'age', radius: 208 },
  sex: { color: '#d98776', shape: 'gender', radius: 136 },
  education_level: { color: '#a493dc', shape: 'edu', radius: 226 },
  occupation: { color: '#d96370', shape: 'pin', radius: 274 },
  family_type: { color: '#c97aa8', shape: 'family', radius: 238 },
  housing_type: { color: '#98a4b4', shape: 'house', radius: 214 },
}

type NodeShape =
  | 'territory'
  | 'province_grid'
  | 'target'
  | 'age'
  | 'gender'
  | 'edu'
  | 'pin'
  | 'family'
  | 'house'

interface CategoryView {
  name: string
  label: string
  color: string
  shape: NodeShape
  count: number
  angle: number
}

interface MapRegion {
  id: string
  name: string
  en: string
  provinceValue: string
  pop: number
  type: 'metro' | 'province'
  cluster: string
}

interface HexCell {
  id: string
  parent: string
  q: number
  r: number
  label: string
  solo?: boolean
  gap?: boolean
}

const KR_REGIONS: MapRegion[] = [
  { id: 'seoul', name: '서울', en: 'Seoul', provinceValue: '서울', pop: 9411, type: 'metro', cluster: '수도권' },
  { id: 'incheon', name: '인천', en: 'Incheon', provinceValue: '인천', pop: 2954, type: 'metro', cluster: '수도권' },
  { id: 'gyeonggi', name: '경기', en: 'Gyeonggi', provinceValue: '경기', pop: 13630, type: 'province', cluster: '수도권' },
  { id: 'gangwon', name: '강원', en: 'Gangwon', provinceValue: '강원', pop: 1536, type: 'province', cluster: '관동' },
  { id: 'chungbuk', name: '충북', en: 'Chungbuk', provinceValue: '충청북', pop: 1592, type: 'province', cluster: '충청' },
  { id: 'chungnam', name: '충남', en: 'Chungnam', provinceValue: '충청남', pop: 2123, type: 'province', cluster: '충청' },
  { id: 'sejong', name: '세종', en: 'Sejong', provinceValue: '세종', pop: 386, type: 'metro', cluster: '충청' },
  { id: 'daejeon', name: '대전', en: 'Daejeon', provinceValue: '대전', pop: 1442, type: 'metro', cluster: '충청' },
  { id: 'jeonbuk', name: '전북', en: 'Jeonbuk', provinceValue: '전북', pop: 1751, type: 'province', cluster: '호남' },
  { id: 'jeonnam', name: '전남', en: 'Jeonnam', provinceValue: '전라남', pop: 1804, type: 'province', cluster: '호남' },
  { id: 'gwangju', name: '광주', en: 'Gwangju', provinceValue: '광주', pop: 1418, type: 'metro', cluster: '호남' },
  { id: 'gyeongbuk', name: '경북', en: 'Gyeongbuk', provinceValue: '경상북', pop: 2569, type: 'province', cluster: '영남' },
  { id: 'daegu', name: '대구', en: 'Daegu', provinceValue: '대구', pop: 2360, type: 'metro', cluster: '영남' },
  { id: 'ulsan', name: '울산', en: 'Ulsan', provinceValue: '울산', pop: 1099, type: 'metro', cluster: '영남' },
  { id: 'gyeongnam', name: '경남', en: 'Gyeongnam', provinceValue: '경상남', pop: 3261, type: 'province', cluster: '영남' },
  { id: 'busan', name: '부산', en: 'Busan', provinceValue: '부산', pop: 3293, type: 'metro', cluster: '영남' },
  { id: 'jeju', name: '제주', en: 'Jeju', provinceValue: '제주', pop: 678, type: 'province', cluster: '제주' },
]

const KR_HEX: HexCell[] = [
  { id: 'gyeonggi-n', parent: 'gyeonggi', q: 2, r: 0, label: '경기북부' },
  { id: 'gangwon-n', parent: 'gangwon', q: 3, r: 0, label: '강원북부' },
  { id: 'gangwon-e', parent: 'gangwon', q: 4, r: 0, label: '강원동해' },
  { id: 'incheon', parent: 'incheon', q: 0, r: 1, label: '인천', solo: true },
  { id: 'seoul', parent: 'seoul', q: 1, r: 1, label: '서울', solo: true },
  { id: 'gyeonggi', parent: 'gyeonggi', q: 2, r: 1, label: '경기' },
  { id: 'gangwon', parent: 'gangwon', q: 3, r: 1, label: '강원' },
  { id: 'gangwon-s', parent: 'gangwon', q: 4, r: 1, label: '강원남부' },
  { id: 'chungnam-n', parent: 'chungnam', q: 0, r: 2, label: '충남서해' },
  { id: 'chungnam', parent: 'chungnam', q: 1, r: 2, label: '충남' },
  { id: 'sejong', parent: 'sejong', q: 2, r: 2, label: '세종', solo: true },
  { id: 'chungbuk', parent: 'chungbuk', q: 3, r: 2, label: '충북' },
  { id: 'gyeongbuk-n', parent: 'gyeongbuk', q: 4, r: 2, label: '경북북부' },
  { id: 'chungnam-s', parent: 'chungnam', q: 0, r: 3, label: '충남남부' },
  { id: 'daejeon', parent: 'daejeon', q: 1, r: 3, label: '대전', solo: true },
  { id: 'chungbuk-s', parent: 'chungbuk', q: 2, r: 3, label: '충북남부' },
  { id: 'gyeongbuk', parent: 'gyeongbuk', q: 3, r: 3, label: '경북' },
  { id: 'gyeongbuk-e', parent: 'gyeongbuk', q: 4, r: 3, label: '경북동해' },
  { id: 'jeonbuk-n', parent: 'jeonbuk', q: 0, r: 4, label: '전북서해' },
  { id: 'jeonbuk', parent: 'jeonbuk', q: 1, r: 4, label: '전북' },
  { id: 'jeonbuk-e', parent: 'jeonbuk', q: 2, r: 4, label: '전북동부' },
  { id: 'daegu', parent: 'daegu', q: 3, r: 4, label: '대구', solo: true },
  { id: 'gyeongbuk-s', parent: 'gyeongbuk', q: 4, r: 4, label: '경북남부' },
  { id: 'gwangju', parent: 'gwangju', q: 0, r: 5, label: '광주', solo: true },
  { id: 'jeonnam', parent: 'jeonnam', q: 1, r: 5, label: '전남' },
  { id: 'gyeongnam-w', parent: 'gyeongnam', q: 2, r: 5, label: '경남서부' },
  { id: 'gyeongnam', parent: 'gyeongnam', q: 3, r: 5, label: '경남' },
  { id: 'ulsan', parent: 'ulsan', q: 4, r: 5, label: '울산', solo: true },
  { id: 'jeonnam-s', parent: 'jeonnam', q: 1, r: 6, label: '전남남해' },
  { id: 'gyeongnam-s', parent: 'gyeongnam', q: 2, r: 6, label: '경남남해' },
  { id: 'busan', parent: 'busan', q: 3, r: 6, label: '부산', solo: true },
  { id: 'jeju', parent: 'jeju', q: 1, r: 7, label: '제주', solo: true, gap: true },
  { id: 'jeju-e', parent: 'jeju', q: 2, r: 7, label: '제주동부', gap: true },
]

const KOREA_REGION_OFFSETS: Record<string, { x: number; y: number }> = {
  seoul: { x: -22, y: -4 },
  incheon: { x: -40, y: 4 },
  gyeonggi: { x: -10, y: -12 },
  gangwon: { x: 30, y: -18 },
  chungnam: { x: -34, y: 4 },
  sejong: { x: -8, y: -2 },
  daejeon: { x: -20, y: 4 },
  chungbuk: { x: 6, y: -2 },
  jeonbuk: { x: -26, y: 10 },
  gwangju: { x: -42, y: 16 },
  jeonnam: { x: -24, y: 22 },
  gyeongbuk: { x: 28, y: 0 },
  daegu: { x: 22, y: 8 },
  gyeongnam: { x: 10, y: 28 },
  ulsan: { x: 40, y: 24 },
  busan: { x: 20, y: 40 },
  jeju: { x: -130, y: 152 },
}

const CONTRACT_REGION_TO_PROVINCE: Record<string, string> = {
  seoul_mayor: 'seoul',
  gwangju_mayor: 'gwangju',
  daegu_mayor: 'daegu',
  busan_buk_gap: 'busan',
  daegu_dalseo_gap: 'daegu',
}

function provinceRegionKey(region: MapRegion) {
  return `province:${region.id}`
}

export default function OntologyPage() {
  const { filter } = useFilter()
  const [selectedMapRegion, setSelectedMapRegion] = useState<MapRegion | null>(null)
  const [clusterLimit, setClusterLimit] = useState(12)
  const [occupationLimit, setOccupationLimit] = useState(12)
  const [minCount, setMinCount] = useState(1)
  const pageGraph = useOntologyGraph(
    filter.region,
    clusterLimit,
    occupationLimit,
    minCount,
  )
  const modalRegionKey = selectedMapRegion
    ? provinceRegionKey(selectedMapRegion)
    : null
  const modalGraph = useOntologyGraph(
    modalRegionKey,
    clusterLimit,
    occupationLimit,
    minCount,
    modalRegionKey != null,
  )
  const regions = useFiveRegions()
  const provinceRegions = useRegions()

  const regionLabel = useMemo(() => {
    if (!filter.region) return '전체'
    return (
      regions.data?.regions.find((r) => r.key === filter.region)?.label_ko ??
      filter.region
    )
  }, [filter.region, regions.data])

  const pageCategoryIndex = useMemo(() => {
    if (!pageGraph.data) return []
    return buildCategoryIndex(pageGraph.data.categories, pageGraph.data.nodes)
  }, [pageGraph.data])

  const topNodes = useMemo(() => {
    return [...(pageGraph.data?.nodes ?? [])]
      .filter((node) => node.id !== 'root')
      .sort((a, b) => b.count - a.count)
      .slice(0, 12)
  }, [pageGraph.data])

  const selectedProvinceId =
    selectedMapRegion?.id ??
    (filter.region ? CONTRACT_REGION_TO_PROVINCE[filter.region] : null) ??
    null

  const provinceCounts = useMemo(() => {
    return new Map(
      (provinceRegions.data?.provinces ?? []).map((province) => [
        province.province,
        province.count,
      ]),
    )
  }, [provinceRegions.data])

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-medium uppercase text-emerald-600 dark:text-emerald-400">
            Population Distribution
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-zinc-950 dark:text-zinc-50">
            인구 분포
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-600 dark:text-zinc-400">
            region, 행정구역, 연령, 성별, 학력, 직업, 가족·주거 유형을 SQL aggregate
            graph로 묶어 synthetic voter population의 분포 구조를 확인합니다.
          </p>
        </div>

        <div className="grid min-w-[20rem] grid-cols-3 gap-4 rounded-lg border border-zinc-200 bg-white px-4 py-3 dark:border-zinc-800 dark:bg-zinc-900/40">
          <RangeControl
            label="범주"
            value={clusterLimit}
            min={6}
            max={24}
            onChange={setClusterLimit}
          />
          <RangeControl
            label="직업"
            value={occupationLimit}
            min={6}
            max={24}
            onChange={setOccupationLimit}
          />
          <RangeControl
            label="최소"
            value={minCount}
            min={1}
            max={100}
            onChange={setMinCount}
          />
        </div>
      </header>

      {pageGraph.isLoading ? (
        <LoadingState />
      ) : pageGraph.error ? (
        <ErrorState error={pageGraph.error} retry={pageGraph.refetch} />
      ) : pageGraph.data ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <PopulationKpi
              label="Region"
              value={regionLabel}
              sub={pageGraph.data.region ?? 'all'}
            />
            <PopulationKpi
              label="Personas"
              value={NF.format(pageGraph.data.total)}
              sub="synthetic agents"
            />
            <PopulationKpi
              label="Nodes"
              value={NF.format(pageGraph.data.nodes.length)}
              sub={`${pageCategoryIndex.length} categories`}
            />
            <PopulationKpi
              label="Edges"
              value={NF.format(pageGraph.data.edges.length)}
              sub="aggregate links"
            />
          </div>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
            <section className="relative min-h-[720px] overflow-hidden rounded-lg border border-[#1f2832] bg-[#0f141b] text-[#e7e5dc] shadow-sm">
              <div className="flex items-start justify-between gap-4 border-b border-[#1f2832] px-5 py-4">
                <div>
                  <h2 className="text-sm font-semibold">Korea / Hex Population Map</h2>
                  <p className="mt-1 font-mono text-[11px] text-[#7a8590]">
                    {pageGraph.data.meta.cluster_source} ·{' '}
                    {pageGraph.data.meta.dimensions.length} dimensions · 17 regions
                  </p>
                </div>
              </div>

              <HexKoreaMap
                regions={KR_REGIONS}
                provinceCounts={provinceCounts}
                selected={selectedProvinceId}
                onSelect={(region) => {
                  if ((provinceCounts.get(region.provinceValue) ?? 0) <= 0) return
                  setSelectedMapRegion(region)
                }}
              />
            </section>

            <GraphIndexPanel
              categories={pageCategoryIndex}
              topNodes={topNodes}
              regionLabel={regionLabel}
            />
          </div>

          {selectedMapRegion && (
            <RegionGraphModal
              region={selectedMapRegion}
              graph={modalGraph}
              regionKey={modalRegionKey}
              onClose={() => setSelectedMapRegion(null)}
            />
          )}
        </>
      ) : null}
    </div>
  )
}

function RangeControl({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  onChange: (value: number) => void
}) {
  return (
    <label className="min-w-0">
      <span className="flex items-center justify-between gap-2 text-[11px] uppercase text-zinc-500 dark:text-zinc-400">
        <span>{label}</span>
        <span className="font-mono tabular-nums text-zinc-950 dark:text-zinc-50">
          {value}
        </span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="mt-2 h-1 w-full accent-emerald-500"
      />
    </label>
  )
}

function PopulationKpi({
  label,
  value,
  sub,
}: {
  label: string
  value: string
  sub: string
}) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white px-4 py-3 dark:border-zinc-800 dark:bg-zinc-900/40">
      <div className="text-[10px] uppercase text-zinc-500 dark:text-zinc-400">
        {label}
      </div>
      <div className="mt-1 truncate text-xl font-semibold text-zinc-950 dark:text-zinc-50">
        {value}
      </div>
      <div className="mt-1 truncate font-mono text-[11px] text-zinc-500 dark:text-zinc-500">
        {sub}
      </div>
    </div>
  )
}

function HexKoreaMap({
  regions,
  provinceCounts,
  selected,
  onSelect,
}: {
  regions: MapRegion[]
  provinceCounts: Map<string, number>
  selected: string | null
  onSelect: (region: MapRegion) => void
}) {
  const [hovered, setHovered] = useState<string | null>(null)
  const width = 920
  const height = 880
  const size = 42
  const positioned = useMemo(() => {
    const points = KR_HEX.map((cell) => {
      const point = hexToPixel(cell.q, cell.r, size)
      const shapeOffset = KOREA_REGION_OFFSETS[cell.parent] ?? { x: 0, y: 0 }
      return {
        ...cell,
        x: point.x + shapeOffset.x,
        y: point.y + shapeOffset.y,
      }
    })
    const xs = points.map((point) => point.x)
    const ys = points.map((point) => point.y)
    const minX = Math.min(...xs)
    const maxX = Math.max(...xs)
    const minY = Math.min(...ys)
    const maxY = Math.max(...ys)
    const offsetX = (width - (maxX - minX)) / 2 - minX
    const offsetY = (height - (maxY - minY)) / 2 - minY
    return points.map((point) => ({
      ...point,
      x: point.x + offsetX + 8,
      y: point.y + offsetY,
    }))
  }, [])

  const maxProvinceCount = useMemo(
    () => Math.max(1, ...regions.map((region) => provinceCounts.get(region.provinceValue) ?? 0)),
    [provinceCounts, regions],
  )

  const centers = useMemo(() => {
    const byParent = new Map<string, typeof positioned>()
    positioned.forEach((cell) => {
      const bucket = byParent.get(cell.parent) ?? []
      bucket.push(cell)
      byParent.set(cell.parent, bucket)
    })
    return new Map(
      [...byParent.entries()].map(([id, cells]) => [
        id,
        {
          x: cells.reduce((sum, cell) => sum + cell.x, 0) / cells.length,
          y: cells.reduce((sum, cell) => sum + cell.y, 0) / cells.length,
        },
      ]),
    )
  }, [positioned])

  return (
    <div className="relative flex min-h-[654px] items-center justify-center overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_52%_46%,rgba(125,211,192,0.2),transparent_34%),radial-gradient(circle_at_42%_70%,rgba(57,98,103,0.28),transparent_34%),linear-gradient(180deg,rgba(18,25,33,0.94),rgba(8,13,19,0.98))]" />
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="relative z-10 h-[704px] w-full"
        role="img"
        aria-label="South Korea province hex block map"
      >
        <defs>
          <radialGradient id="hex-map-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#7dd3c0" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#7dd3c0" stopOpacity="0" />
          </radialGradient>
        </defs>

        <g fontFamily="ui-monospace, monospace" fontSize="9.5" fill="#50606c" letterSpacing="2">
          <text x="58" y="98">SUDOGWON · 수도권</text>
          <text x="58" y="260">CHUNGCHEONG · 충청</text>
          <text x="58" y="490">HONAM · 호남</text>
          <text x={width - 58} y="98" textAnchor="end">GANGWON · 관동</text>
          <text x={width - 58} y="430" textAnchor="end">YEONGNAM · 영남</text>
          <text x={width - 58} y={height - 94} textAnchor="end">JEJU · 제주</text>
        </g>

        <circle cx={width / 2} cy={height / 2} r="270" fill="url(#hex-map-glow)" />

        <g>
          {positioned.map((cell) => {
            const region = regions.find((item) => item.id === cell.parent)
            if (!region) return null
            const dataCount = provinceCounts.get(region.provinceValue) ?? 0
            const isAvailable = dataCount > 0
            const isSelected = selected === cell.parent
            const isHovered = hovered === cell.parent && isAvailable
            const ratio = mapCountRatio(dataCount, maxProvinceCount)
            const fill = isAvailable
              ? mapRegionFill(region, ratio, isSelected)
              : '#14202a'
            const stroke = isAvailable
              ? mapRegionStroke(region, ratio, isHovered, isSelected)
              : '#2d3b46'
            const strokeWidth = isSelected ? 2.7 : isHovered ? 2 : 1 + ratio * 1.1
            const opacity = selected && !isSelected
              ? 0.58 + ratio * 0.26
              : isAvailable
                ? 0.8 + ratio * 0.2
                : 0.34
            const cellSize = cell.parent === 'jeju' ? size * 0.73 : size - 2
            const points = hexCorners(cell.x, cell.y, cellSize)
              .map(([x, y]) => `${x},${y}`)
              .join(' ')
            return (
              <g
                key={cell.id}
                className={[
                  'population-hex-cell',
                  isAvailable ? 'cursor-pointer' : 'cursor-not-allowed',
                ].join(' ')}
                opacity={opacity}
                onClick={() => {
                  if (isAvailable) onSelect(region)
                }}
                onMouseEnter={() => {
                  if (isAvailable) setHovered(cell.parent)
                }}
                onMouseLeave={() => setHovered(null)}
              >
                <title>
                  {region.name} · {formatMapCount(dataCount)}
                </title>
                <polygon
                  points={points}
                  fill={fill}
                  stroke={stroke}
                  strokeWidth={strokeWidth}
                />
                {(isSelected || isHovered) && (
                  <circle
                    cx={cell.x}
                    cy={cell.y - cellSize * 0.43}
                    r={isSelected ? 3.2 : 2.4}
                    fill={isSelected ? '#f1fffb' : '#b8ffec'}
                    opacity="0.88"
                  />
                )}
              </g>
            )
          })}
        </g>

        <g fontFamily="-apple-system, system-ui, sans-serif" pointerEvents="none">
          {[...centers.entries()].map(([id, center]) => {
            const region = regions.find((item) => item.id === id)
            if (!region) return null
            const isSelected = selected === id
            const isHovered = hovered === id
            const dataCount = provinceCounts.get(region.provinceValue) ?? 0
            const isAvailable = dataCount > 0
            const ratio = mapCountRatio(dataCount, maxProvinceCount)
            const labelColor = isSelected || isHovered
              ? '#f4fffb'
              : isAvailable
                ? `hsl(165 18% ${58 + ratio * 22}%)`
                : '#53616c'
            const countColor = isSelected || isHovered
              ? '#b8ffec'
              : isAvailable
                ? `hsl(166 22% ${42 + ratio * 22}%)`
                : '#46525c'
            return (
              <g key={id} transform={`translate(${center.x},${center.y})`}>
                <text
                  textAnchor="middle"
                  fontSize={isSelected ? 13 : 10.8}
                  fontWeight={isSelected || isHovered ? 700 : 560}
                  fill={labelColor}
                  y="-5"
                >
                  {region.name}
                </text>
                <text
                  textAnchor="middle"
                  fontSize="8.8"
                  fill={countColor}
                  y="10"
                  fontFamily="ui-monospace, monospace"
                  letterSpacing="0.6"
                >
                  {formatMapCount(dataCount)}
                </text>
              </g>
            )
          })}
        </g>

        <text
          x={width / 2}
          y={height - 24}
          textAnchor="middle"
          fontSize="10.5"
          fill="#5b6470"
          fontFamily="ui-monospace, monospace"
          letterSpacing="1.4"
        >
          데이터가 있는 시·도를 클릭하면 force-directed 인구 그래프가 열립니다
        </text>
      </svg>
    </div>
  )
}

function RegionGraphModal({
  region,
  graph,
  regionKey,
  onClose,
}: {
  region: MapRegion
  graph: ReturnType<typeof useOntologyGraph>
  regionKey: string | null
  onClose: () => void
}) {
  const categories = useMemo(() => {
    if (!graph.data) return []
    return buildCategoryIndex(graph.data.categories, graph.data.nodes)
  }, [graph.data])
  const topNodes = useMemo(() => {
    return [...(graph.data?.nodes ?? [])]
      .filter((node) => node.id !== 'root')
      .sort((a, b) => b.count - a.count)
      .slice(0, 8)
  }, [graph.data])

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#06090d]/80 p-5 backdrop-blur-md"
      onClick={onClose}
    >
      <section
        className="flex h-[min(860px,92vh)] w-[min(1280px,100%)] flex-col overflow-hidden rounded-lg border border-[#2a3340] bg-[#0f141b] text-[#e7e5dc] shadow-[0_30px_80px_rgba(0,0,0,0.62),0_0_0_1px_rgba(125,211,192,0.08)]"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex items-start justify-between border-b border-[#1f2832] px-7 py-5">
          <div>
            <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.18em] text-[#7dd3c0]">
              Region force-directed distribution
            </p>
            <h2 className="flex items-baseline gap-3 text-3xl font-semibold">
              {region.name}
              <span className="font-mono text-sm font-normal tracking-[0.04em] text-[#5a6470]">
                {region.en}
              </span>
            </h2>
            <div className="mt-2 flex items-center gap-2 text-xs text-[#7a8590]">
              <span>{region.cluster}</span>
              <span className="text-[#3a4450]">·</span>
              <span>{region.type === 'metro' ? 'metropolitan' : 'province'}</span>
              <span className="text-[#3a4450]">·</span>
              <span>{(region.pop / 1000).toFixed(1)}M baseline</span>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="h-8 w-8 rounded-md border border-[#1f2832] text-lg leading-none text-[#7a8590] transition-colors hover:border-[#2a3340] hover:bg-[#141a23] hover:text-[#e7e5dc]"
            aria-label="닫기"
          >
            ×
          </button>
        </header>

        <div className="grid min-h-0 flex-1 lg:grid-cols-[1fr_280px]">
          <div className="min-h-0 border-r border-[#1f2832]">
            {graph.isLoading ? (
              <div className="p-6">
                <LoadingState />
              </div>
            ) : graph.error ? (
              <div className="p-6">
                <ErrorState error={graph.error} retry={graph.refetch} />
              </div>
            ) : graph.data ? (
              <PopulationForceGraph
                nodes={graph.data.nodes}
                edges={graph.data.edges}
                categories={categories}
                regionLabel={region.name}
              />
            ) : null}
          </div>

          <aside className="min-h-0 overflow-y-auto px-6 py-5">
            <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-[#5a6470]">
              Dominant nodes
            </h3>
            <div className="mt-4 space-y-3">
              {topNodes.map((node) => {
                const visual = visualFor(node.category, node.category, node.color)
                return (
                  <div key={node.id} className="text-xs">
                    <div className="mb-1 flex items-baseline justify-between gap-2">
                      <span className="truncate text-[#b0b8c0]">{node.label}</span>
                      <span className="font-mono text-[11px] text-[#7a8590]">
                        {node.pct.toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-[3px] overflow-hidden rounded bg-[#1a2230]">
                      <div
                        className="h-full rounded"
                        style={{
                          width: `${Math.min(100, node.pct)}%`,
                          backgroundColor: visual.color,
                        }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="my-5 h-px bg-[#1f2832]" />

            <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-[#5a6470]">
              Categories
            </h3>
            <div className="mt-4 space-y-2">
              {categories.map((category) => (
                <div
                  key={category.name}
                  className="grid grid-cols-[10px_1fr_auto] items-center gap-2 text-xs"
                >
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: category.color }}
                  />
                  <span className="truncate text-[#b0b8c0]">{category.label}</span>
                  <span className="font-mono text-[11px] text-[#5a6470]">
                    {category.count}
                  </span>
                </div>
              ))}
            </div>
          </aside>
        </div>

        <footer className="flex justify-between border-t border-[#1f2832] px-7 py-3 font-mono text-[10px] uppercase tracking-[0.08em] text-[#5a6470]">
          <span>{regionKey ?? 'no-region-data'}</span>
          <span>drag nodes, zoom or pan to inspect adjacency</span>
        </footer>
      </section>
    </div>
  )
}

function PopulationForceGraph({
  nodes,
  edges,
  categories,
  regionLabel,
}: {
  nodes: OntologyNode[]
  edges: OntologyEdge[]
  categories: CategoryView[]
  regionLabel: string
}) {
  const option = useMemo(
    () => buildForceGraphOption(nodes, edges, categories, regionLabel),
    [nodes, edges, categories, regionLabel],
  )

  return (
    <div className="relative min-h-[654px] overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(125,211,192,0.07),transparent_42%),linear-gradient(180deg,rgba(20,26,35,0.2),rgba(10,14,19,0.4))]" />
      <EChart
        option={option}
        height={654}
        notMerge
        className="relative z-10"
      />
      <div className="absolute bottom-3 left-4 right-4 z-20 flex flex-wrap gap-x-4 gap-y-2 rounded-md border border-[#1f2832] bg-[#0a0e13]/85 px-3 py-2 font-mono text-[10px] text-[#7a8590] backdrop-blur">
        {categories.map((category) => (
          <span key={category.name} className="inline-flex items-center gap-2">
            <svg width="15" height="15" viewBox="-8 -8 16 16" aria-hidden>
              <NodeGlyph
                shape={category.shape}
                size={12}
                color={category.color}
              />
            </svg>
            {category.label.toLowerCase()}
          </span>
        ))}
      </div>
    </div>
  )
}

function GraphIndexPanel({
  categories,
  topNodes,
  regionLabel,
}: {
  categories: CategoryView[]
  topNodes: OntologyNode[]
  regionLabel: string
}) {
  const totalNodes = categories.reduce((sum, category) => sum + category.count, 0)
  return (
    <aside className="self-start rounded-lg border border-[#1f2832] bg-[#0f141b] px-5 py-5 text-[#e7e5dc] xl:sticky xl:top-28">
      <section>
        <h2 className="text-sm font-semibold">Graph Index</h2>
        <p className="mt-1 font-mono text-[11px] text-[#5a6470]">
          node categories · {totalNodes} total
        </p>
        <div className="mt-4 space-y-2">
          {categories.map((category) => (
            <div
              key={category.name}
              className="grid grid-cols-[14px_1fr_auto] items-center gap-2 text-xs"
            >
              <svg width="14" height="14" viewBox="-8 -8 16 16" aria-hidden>
                <NodeGlyph
                  shape={category.shape}
                  size={10}
                  color={category.color}
                />
              </svg>
              <span className="truncate text-[#b0b8c0]">{category.label}</span>
              <span className="font-mono text-[11px] text-[#7a8590]">
                {category.count}
              </span>
            </div>
          ))}
        </div>
      </section>

      <div className="my-5 h-px bg-[#1f2832]" />

      <section>
        <h2 className="text-sm font-semibold">Top nodes</h2>
        <p className="mt-1 font-mono text-[11px] text-[#5a6470]">
          {regionLabel === '전체' ? 'across all personas' : `in ${regionLabel}`}
        </p>
        <div className="mt-4 space-y-3">
          {topNodes.map((node) => {
            const visual = visualFor(node.category, node.category, node.color)
            return (
              <div key={node.id} className="text-xs">
                <div className="mb-1 flex items-baseline justify-between gap-2">
                  <span className="truncate text-[#b0b8c0]">{node.label}</span>
                  <span className="font-mono text-[11px] text-[#7a8590]">
                    {node.pct.toFixed(1)}%
                  </span>
                </div>
                <div className="h-[3px] overflow-hidden rounded bg-[#1a2230]">
                  <div
                    className="h-full rounded transition-[width]"
                    style={{
                      width: `${Math.min(100, node.pct)}%`,
                      backgroundColor: visual.color,
                    }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </section>
    </aside>
  )
}

function buildForceGraphOption(
  nodes: OntologyNode[],
  edges: OntologyEdge[],
  categories: CategoryView[],
  regionLabel: string,
): LooseEChartsOption {
  const categoryByName = new Map(categories.map((category) => [category.name, category]))
  const maxCount = Math.max(1, ...nodes.map((node) => node.count))
  const nodeIds = new Set(nodes.map((node) => node.id))

  const graphNodes = nodes.map((node) => {
    const visual =
      categoryByName.get(node.category) ??
      visualFor(node.category, node.category, node.color)
    const weight = Math.log1p(node.count) / Math.log1p(maxCount)
    const isRoot = node.id === 'root'
    const size = isRoot ? 48 : Math.max(14, Math.min(38, 12 + weight * 28))
    const label = isRoot ? regionLabel : shortLabel(node.label, 18)

    return {
      id: node.id,
      name: label,
      rawLabel: node.label,
      category: visual.label,
      categoryName: visual.label,
      value: node.count,
      pct: node.pct,
      kind: node.kind,
      draggable: true,
      fixed: false,
      symbol: echartsSymbolFor(visual.shape),
      symbolKeepAspect: true,
      symbolSize: size,
      itemStyle: {
        color: isRoot ? 'rgba(10,14,19,0.9)' : 'rgba(10,14,19,0.58)',
        borderColor: visual.color,
        borderWidth: isRoot ? 2.6 : 2,
        shadowBlur: isRoot ? 18 : 7,
        shadowColor: `${visual.color}44`,
      },
      label: {
        show: isRoot || node.kind === 'region' || node.kind === 'province' || node.pct >= 7,
        color: '#e7e5dc',
        fontSize: isRoot ? 13 : 10,
        fontWeight: isRoot ? 700 : 500,
        formatter: '{b}',
      },
      emphasis: {
        focus: 'adjacency',
        label: {
          show: true,
          color: '#ffffff',
          fontSize: 12,
        },
        itemStyle: {
          color: 'rgba(10,14,19,0.78)',
          borderWidth: 2.8,
          shadowBlur: 20,
          shadowColor: `${visual.color}78`,
        },
      },
    }
  })

  const graphEdges = edges
    .filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
    .map((edge) => {
      const isCoOccurrence = edge.kind === 'co_occurrence'
      const width = Math.max(0.7, Math.min(4.2, 0.65 + Math.sqrt(edge.weight * 100)))
      return {
        source: edge.source,
        target: edge.target,
        value: edge.count,
        weight: edge.weight,
        labelText: edge.label,
        kind: edge.kind,
        lineStyle: {
          color: isCoOccurrence ? '#7a8590' : 'source',
          width,
          opacity: isCoOccurrence ? 0.22 : 0.42,
          curveness: isCoOccurrence ? 0.18 : 0.06,
        },
        emphasis: {
          lineStyle: {
            opacity: 0.86,
            width: Math.min(6, width + 1.8),
          },
        },
      }
    })

  return {
    backgroundColor: 'transparent',
    color: categories.map((category) => category.color),
    tooltip: {
      trigger: 'item',
      confine: true,
      borderColor: '#2a3340',
      backgroundColor: 'rgba(15,20,27,0.96)',
      textStyle: { color: '#e7e5dc', fontSize: 12 },
      formatter: (params: {
        dataType?: string
        name?: string
        data?: Record<string, unknown>
      }) => {
        const data = params.data ?? {}
        if (params.dataType === 'edge') {
          return [
            `<strong>${String(data.labelText ?? 'link')}</strong>`,
            `${String(data.kind ?? 'edge')} · ${NF.format(Number(data.value ?? 0))}`,
            `weight ${Number(data.weight ?? 0).toFixed(3)}`,
          ].join('<br/>')
        }
        return [
          `<strong>${String(data.rawLabel ?? params.name ?? 'node')}</strong>`,
          `${String(data.categoryName ?? 'node')} · ${NF.format(Number(data.value ?? 0))}`,
          `${Number(data.pct ?? 0).toFixed(2)}% of selected population`,
        ].join('<br/>')
      },
    },
    animation: true,
    animationDuration: 1600,
    animationDurationUpdate: 950,
    animationEasingUpdate: 'cubicInOut',
    series: [
      {
        name: 'Population distribution',
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        layoutAnimation: true,
        zoom: 0.62,
        center: ['49%', '52%'],
        scaleLimit: { min: 0.35, max: 2.2 },
        cursor: 'move',
        top: 42,
        right: 54,
        bottom: 100,
        left: 54,
        categories: categories.map((category) => ({
          name: category.label,
          itemStyle: { color: category.color },
        })),
        data: graphNodes,
        links: graphEdges,
        lineStyle: {
          color: 'source',
          opacity: 0.32,
          curveness: 0.08,
        },
        force: {
          repulsion: [90, 270],
          edgeLength: [92, 198],
          gravity: 0.055,
          friction: 0.55,
          layoutAnimation: true,
        },
        emphasis: {
          focus: 'adjacency',
        },
      },
    ],
  }
}

function echartsSymbolFor(shape: NodeShape) {
  switch (shape) {
    case 'territory':
      return 'path://M0,-1 L0.82,-0.42 L0.62,0.72 L-0.18,1 L-0.86,0.3 L-0.58,-0.72 Z'
    case 'province_grid':
      return 'path://M0,-1 L0.87,-0.5 L0.87,0.5 L0,1 L-0.87,0.5 L-0.87,-0.5 Z M-0.87,0 H0.87 M-0.43,-0.75 L0.43,0.75 M0.43,-0.75 L-0.43,0.75'
    case 'target':
      return 'path://M0,-1 A1,1 0 1,1 -0.01,-1 M0,-0.58 A0.58,0.58 0 1,1 -0.01,-0.58 M0,-0.17 A0.17,0.17 0 1,1 -0.01,-0.17'
    case 'age':
      return 'path://M0,-1 A1,1 0 1,1 -0.01,-1 M0,0 L0,-0.66 M0,0 L0.54,0.26'
    case 'gender':
      return 'path://M-0.52,-0.25 A0.34,0.34 0 1,1 -0.53,-0.25 M0.52,-0.25 A0.34,0.34 0 1,1 0.51,-0.25 M-0.26,0.02 H0.26 M-0.52,0.1 V0.72 M-0.78,0.46 H-0.26 M0.52,0.1 L0.9,0.58 M0.72,0.58 H0.9 V0.4'
    case 'edu':
      return 'path://M-0.95,0.26 L0,-0.82 L0.95,0.26 L0,0.74 Z M-0.58,0.42 V0.82 H0.58 V0.42 M0.95,0.26 V0.74'
    case 'pin':
      return 'path://M0,1 L-0.52,0.08 A0.62,0.62 0 1,1 0.52,0.08 Z M0,-0.22 A0.22,0.22 0 1,1 -0.01,-0.22'
    case 'family':
      return 'path://M-0.48,-0.22 A0.3,0.3 0 1,1 -0.49,-0.22 M0.48,-0.22 A0.3,0.3 0 1,1 0.47,-0.22 M0,0.08 A0.34,0.34 0 1,1 -0.01,0.08 M-0.82,0.9 C-0.66,0.48 -0.3,0.42 0,0.64 C0.3,0.42 0.66,0.48 0.82,0.9'
    case 'house':
      return 'path://M-0.9,-0.08 L0,-0.88 L0.9,-0.08 V0.84 H-0.9 Z M-0.25,0.84 V0.28 H0.25 V0.84 M0.44,-0.5 V-0.82 H0.68 V-0.28'
    default:
      return 'path://M0,-1 A1,1 0 1,1 -0.01,-1 M0,-0.52 A0.52,0.52 0 1,1 -0.01,-0.52'
  }
}

function buildCategoryIndex(
  categories: OntologyCategory[],
  nodes: OntologyNode[],
): CategoryView[] {
  const counts = new Map<string, number>()
  nodes.forEach((node) => {
    counts.set(node.category, (counts.get(node.category) ?? 0) + 1)
  })

  const sorted = [...categories]
    .filter((category) => (counts.get(category.name) ?? 0) > 0)
    .sort((a, b) => {
      const ai = CATEGORY_ORDER.indexOf(a.name)
      const bi = CATEGORY_ORDER.indexOf(b.name)
      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi)
    })

  return sorted.map((category, index) => {
    const visual = visualFor(category.name, category.label, category.color)
    return {
      ...visual,
      count: counts.get(category.name) ?? 0,
      angle: -Math.PI / 2 + (index / Math.max(1, sorted.length)) * Math.PI * 2,
    }
  })
}

function visualFor(name: string, label: string, fallbackColor: string) {
  const visual = CATEGORY_VISUALS[name] ?? {
    color: fallbackColor,
    shape: 'target' as NodeShape,
    radius: 236,
  }
  return {
    name,
    label,
    color: visual.color,
    shape: visual.shape,
    count: 0,
    angle: 0,
  }
}

function NodeGlyph({
  shape,
  size,
  color,
}: {
  shape: NodeShape
  size: number
  color: string
}) {
  const r = size / 2
  const strokeWidth = 1.25
  const common = {
    fill: 'none',
    stroke: color,
    strokeWidth,
    vectorEffect: 'non-scaling-stroke',
  } satisfies Partial<SVGElementProps>

  switch (shape) {
    case 'territory':
      return (
        <g>
          <path
            d={`M 0 ${-r} L ${r * 0.82} ${-r * 0.42} L ${r * 0.62} ${r * 0.72} L ${-r * 0.18} ${r} L ${-r * 0.86} ${r * 0.3} L ${-r * 0.58} ${-r * 0.72} Z`}
            {...common}
          />
          <path
            d={`M ${-r * 0.4} ${-r * 0.2} L ${r * 0.16} ${-r * 0.45} L ${r * 0.46} ${r * 0.1} L ${-r * 0.08} ${r * 0.48}`}
            {...common}
            opacity="0.62"
          />
        </g>
      )
    case 'province_grid':
      return (
        <g>
          <polygon
            points={`0,${-r} ${r * 0.87},${-r * 0.5} ${r * 0.87},${r * 0.5} 0,${r} ${-r * 0.87},${r * 0.5} ${-r * 0.87},${-r * 0.5}`}
            {...common}
          />
          <line x1={-r * 0.87} y1="0" x2={r * 0.87} y2="0" stroke={color} strokeWidth="0.75" opacity="0.7" />
          <line x1={-r * 0.43} y1={-r * 0.75} x2={r * 0.43} y2={r * 0.75} stroke={color} strokeWidth="0.75" opacity="0.7" />
          <line x1={r * 0.43} y1={-r * 0.75} x2={-r * 0.43} y2={r * 0.75} stroke={color} strokeWidth="0.75" opacity="0.7" />
        </g>
      )
    case 'target':
      return (
        <g>
          <circle r={r} {...common} />
          <circle r={r * 0.58} {...common} opacity="0.72" />
          <circle r={r * 0.18} fill={color} opacity="0.7" />
        </g>
      )
    case 'age':
      return (
        <g>
          <circle r={r} {...common} />
          <line x1="0" y1="0" x2="0" y2={-r * 0.66} stroke={color} strokeWidth="1.35" strokeLinecap="round" />
          <line x1="0" y1="0" x2={r * 0.54} y2={r * 0.26} stroke={color} strokeWidth="1.35" strokeLinecap="round" />
          <path d={`M 0 ${-r} A ${r} ${r} 0 0 1 ${r * 0.86} ${r * 0.5}`} {...common} strokeWidth="1.7" />
        </g>
      )
    case 'gender':
      return (
        <g>
          <circle cx={-r * 0.52} cy={-r * 0.25} r={r * 0.34} {...common} />
          <circle cx={r * 0.52} cy={-r * 0.25} r={r * 0.34} {...common} />
          <line x1={-r * 0.18} y1={-r * 0.04} x2={r * 0.18} y2={-r * 0.04} stroke={color} strokeWidth="1" opacity="0.72" />
          <line x1={-r * 0.52} y1={r * 0.1} x2={-r * 0.52} y2={r * 0.72} stroke={color} strokeWidth="1.15" />
          <line x1={-r * 0.76} y1={r * 0.43} x2={-r * 0.28} y2={r * 0.43} stroke={color} strokeWidth="1.15" />
          <line x1={r * 0.52} y1={r * 0.1} x2={r * 0.88} y2={r * 0.58} stroke={color} strokeWidth="1.15" />
          <path d={`M ${r * 0.66} ${r * 0.58} H ${r * 0.88} V ${r * 0.36}`} {...common} />
        </g>
      )
    case 'edu':
      return (
        <g>
          <polygon
            points={`${-r * 0.95},${r * 0.26} 0,${-r * 0.82} ${r * 0.95},${r * 0.26} 0,${r * 0.74}`}
            {...common}
          />
          <path d={`M ${-r * 0.58} ${r * 0.42} V ${r * 0.82} H ${r * 0.58} V ${r * 0.42}`} {...common} opacity="0.72" />
          <line x1={r * 0.95} y1={r * 0.26} x2={r * 0.95} y2={r * 0.74} stroke={color} strokeWidth="0.9" opacity="0.76" />
        </g>
      )
    case 'pin':
      return (
        <g>
          <path
            d={`M 0 ${r} L ${-r * 0.7} ${-r * 0.1} A ${r * 0.7} ${r * 0.7} 0 1 1 ${r * 0.7} ${-r * 0.1} Z`}
            {...common}
          />
          <circle cx="0" cy={-r * 0.25} r={r * 0.24} {...common} opacity="0.78" />
        </g>
      )
    case 'family':
      return (
        <g>
          <circle cx={-r * 0.48} cy={-r * 0.22} r={r * 0.3} {...common} />
          <circle cx={r * 0.48} cy={-r * 0.22} r={r * 0.3} {...common} />
          <circle cx="0" cy={r * 0.08} r={r * 0.34} {...common} />
          <path
            d={`M ${-r * 0.82} ${r * 0.9} C ${-r * 0.66} ${r * 0.48} ${-r * 0.3} ${r * 0.42} 0 ${r * 0.64} C ${r * 0.3} ${r * 0.42} ${r * 0.66} ${r * 0.48} ${r * 0.82} ${r * 0.9}`}
            {...common}
          />
        </g>
      )
    case 'house':
      return (
        <g>
          <path
            d={`M ${-r} ${-r * 0.15} L 0 ${-r} L ${r} ${-r * 0.15} L ${r} ${r * 0.85} L ${-r} ${r * 0.85} Z`}
            {...common}
          />
          <rect x={-r * 0.25} y={r * 0.2} width={r * 0.5} height={r * 0.65} fill="none" stroke={color} strokeWidth="0.8" opacity="0.8" />
        </g>
      )
    default:
      return (
        <g>
          <circle r={r} {...common} />
          <circle r={r * 0.55} fill="none" stroke={color} strokeWidth="0.65" opacity="0.6" />
          <circle r={r * 0.18} fill={color} opacity="0.7" />
        </g>
      )
  }
}

type SVGElementProps = SVGProps<SVGElement>

function shortLabel(label: string, max: number) {
  return label.length > max ? `${label.slice(0, max)}…` : label
}

function formatMapCount(count: number) {
  if (count <= 0) return 'no data'
  if (count >= 100_000) return `${Math.round(count / 1000)}k`
  if (count >= 10_000) return `${(count / 1000).toFixed(1)}k`
  return NF.format(count)
}

function clamp01(value: number) {
  return Math.max(0, Math.min(1, value))
}

function mapCountRatio(count: number, maxCount: number) {
  if (count <= 0 || maxCount <= 0) return 0
  return clamp01(Math.sqrt(count / maxCount))
}

function mapRegionFill(region: MapRegion, ratio: number, selected: boolean) {
  if (selected) return 'hsl(164 42% 30%)'
  const hue = region.type === 'metro' ? 172 : 156
  const saturation = region.type === 'metro' ? 42 : 36
  const lightness = 14 + ratio * 20
  return `hsl(${hue} ${saturation}% ${lightness}%)`
}

function mapRegionStroke(
  region: MapRegion,
  ratio: number,
  hovered: boolean,
  selected: boolean,
) {
  if (selected) return '#c9fff3'
  if (hovered) return '#f0fffb'
  const hue = region.type === 'metro' ? 174 : 158
  return `hsl(${hue} 46% ${36 + ratio * 30}%)`
}

function hexToPixel(q: number, r: number, size: number) {
  return {
    x: size * Math.sqrt(3) * (q + (r % 2) * 0.5),
    y: size * 1.46 * r,
  }
}

function hexCorners(cx: number, cy: number, size: number) {
  const points: Array<[number, number]> = []
  for (let i = 0; i < 6; i += 1) {
    const angle = (Math.PI / 3) * i + Math.PI / 6
    points.push([
      cx + size * Math.cos(angle),
      cy + size * Math.sin(angle),
    ])
  }
  return points
}
