import type { ReactNode } from 'react'

export function LoadingState({ label = '불러오는 중…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400 py-8">
      <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
      {label}
    </div>
  )
}

export function ErrorState({
  error,
  retry,
}: {
  error: unknown
  retry?: () => void
}) {
  const msg =
    error && typeof error === 'object' && 'message' in error
      ? String((error as Error).message)
      : '알 수 없는 오류'
  return (
    <div className="rounded-lg border border-amber-500/40 bg-amber-500/5 px-4 py-3 text-sm text-amber-800 dark:text-amber-200">
      <p className="font-medium">데이터를 불러오지 못했습니다.</p>
      <p className="mt-1 text-xs opacity-80 break-words">{msg}</p>
      {retry && (
        <button
          type="button"
          onClick={retry}
          className="mt-2 text-xs px-2 py-1 rounded-md ring-1 ring-amber-500/40 hover:bg-amber-500/10"
        >
          다시 시도
        </button>
      )}
    </div>
  )
}

export function EmptyState({ children }: { children?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-zinc-300 dark:border-zinc-700 px-4 py-6 text-sm text-zinc-500 dark:text-zinc-400 text-center">
      {children ?? '표시할 데이터가 없습니다.'}
    </div>
  )
}
