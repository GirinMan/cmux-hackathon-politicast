import type { ReactNode } from 'react'

export interface Stat {
  label: ReactNode
  value: ReactNode
  hint?: ReactNode
}

export default function StatGrid({ stats }: { stats: Stat[] }) {
  return (
    <dl className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
      {stats.map((s, i) => (
        <div
          key={i}
          className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white/60 dark:bg-zinc-900/40 px-4 py-3"
        >
          <dt className="text-[11px] uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            {s.label}
          </dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums text-zinc-900 dark:text-zinc-100">
            {s.value}
          </dd>
          {s.hint && (
            <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-0.5">
              {s.hint}
            </p>
          )}
        </div>
      ))}
    </dl>
  )
}
