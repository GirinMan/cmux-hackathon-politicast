import type { ReactNode } from 'react'

export interface CardProps {
  title?: ReactNode
  subtitle?: ReactNode
  right?: ReactNode
  children: ReactNode
  className?: string
}

export default function Card({
  title,
  subtitle,
  right,
  children,
  className,
}: CardProps) {
  return (
    <section
      className={[
        'rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/40',
        'shadow-sm hover:shadow transition-shadow',
        className ?? '',
      ].join(' ')}
    >
      {(title || right) && (
        <header className="flex items-start gap-3 px-5 pt-4 pb-2">
          <div className="flex-1 min-w-0">
            {title && (
              <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 truncate">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                {subtitle}
              </p>
            )}
          </div>
          {right && <div className="shrink-0">{right}</div>}
        </header>
      )}
      <div className="px-5 py-4">{children}</div>
    </section>
  )
}
