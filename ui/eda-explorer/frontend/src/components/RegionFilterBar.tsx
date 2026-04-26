import { useFilter } from '../state/filter'
import { useFiveRegions } from '../hooks/queries'

const COMPACT_FORMAT = new Intl.NumberFormat('ko-KR')

export default function RegionFilterBar() {
  const { filter, set, reset } = useFilter()
  const { data, isLoading } = useFiveRegions()
  const regions = data?.regions ?? []

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <span className="text-zinc-500 dark:text-zinc-400 mr-1">Region</span>
      <button
        type="button"
        onClick={() => set({ region: null })}
        className={chipClass(filter.region == null)}
      >
        전체
      </button>
      {regions.map((r) => {
        const active = filter.region === r.key
        const disabled = !r.available
        return (
          <button
            key={r.key}
            type="button"
            disabled={disabled}
            onClick={() => set({ region: active ? null : r.key })}
            className={chipClass(active, disabled)}
            title={`${r.label_ko} · ${COMPACT_FORMAT.format(r.count)} 명`}
          >
            <span className="max-w-[8.5rem] truncate">{r.label_ko}</span>
            <span className="ml-1.5 text-[10px] tabular-nums text-zinc-500 dark:text-zinc-400">
              {COMPACT_FORMAT.format(r.count)}
            </span>
          </button>
        )
      })}
      {isLoading && <span className="px-2 py-1 text-zinc-400">…</span>}
      {filter.region != null && (
        <button
          type="button"
          onClick={reset}
          className="ml-2 px-2 py-1 rounded-md text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100"
        >
          초기화
        </button>
      )}
    </div>
  )
}

function chipClass(active: boolean, disabled = false) {
  if (disabled)
    return 'inline-flex items-center px-2.5 py-1 rounded-full ring-1 ring-zinc-200 dark:ring-zinc-800 text-zinc-400 dark:text-zinc-600 cursor-not-allowed'
  return active
    ? 'inline-flex items-center px-2.5 py-1 rounded-full ring-1 ring-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
    : 'inline-flex items-center px-2.5 py-1 rounded-full ring-1 ring-zinc-200 dark:ring-zinc-800 text-zinc-700 dark:text-zinc-300 hover:ring-zinc-400 dark:hover:ring-zinc-600'
}
