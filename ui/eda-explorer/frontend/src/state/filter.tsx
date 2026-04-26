/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  type ReactNode,
} from 'react'
import { useSearchParams } from 'react-router-dom'

/**
 * Global filters that all pages may consult. Backed by URL query string so
 * that links/refreshes restore the same view. Backend may ignore filters it
 * doesn't support; that's OK.
 */
export interface GlobalFilter {
  region: string | null // contract region id from /api/regions/five
  province: string | null // 약식 표기 (e.g., '서울', '경기')
  sex: string | null // '여자' | '남자' | null
  ageMin: number | null
  ageMax: number | null
}

interface FilterCtx {
  filter: GlobalFilter
  set: (patch: Partial<GlobalFilter>) => void
  reset: () => void
}

const Ctx = createContext<FilterCtx | null>(null)

const KEYS: (keyof GlobalFilter)[] = [
  'region',
  'province',
  'sex',
  'ageMin',
  'ageMax',
]

function paramOrNull(p: URLSearchParams, k: string): string | null {
  const v = p.get(k)
  return v == null || v === '' ? null : v
}

function parseFilter(p: URLSearchParams): GlobalFilter {
  const num = (k: string) => {
    const v = paramOrNull(p, k)
    if (v == null) return null
    const n = Number(v)
    return Number.isFinite(n) ? n : null
  }
  return {
    region: paramOrNull(p, 'region'),
    province: paramOrNull(p, 'province'),
    sex: paramOrNull(p, 'sex'),
    ageMin: num('ageMin'),
    ageMax: num('ageMax'),
  }
}

export function FilterProvider({ children }: { children: ReactNode }) {
  const [params, setParams] = useSearchParams()

  const filter = useMemo(() => parseFilter(params), [params])

  const set = useCallback(
    (patch: Partial<GlobalFilter>) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          for (const k of KEYS) {
            if (!(k in patch)) continue
            const v = patch[k]
            if (v == null || v === '') next.delete(k)
            else next.set(k, String(v))
          }
          return next
        },
        { replace: true },
      )
    },
    [setParams],
  )

  const reset = useCallback(() => {
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        for (const k of KEYS) next.delete(k)
        return next
      },
      { replace: true },
    )
  }, [setParams])

  const value = useMemo<FilterCtx>(() => ({ filter, set, reset }), [filter, set, reset])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useFilter(): FilterCtx {
  const v = useContext(Ctx)
  if (!v) throw new Error('useFilter must be inside FilterProvider')
  return v
}

/** Convert filter to a flat record suitable for axios `params`. */
export function filterToParams(f: GlobalFilter): Record<string, string> {
  const out: Record<string, string> = {}
  for (const k of KEYS) {
    const v = f[k]
    if (v == null || v === '') continue
    out[k] = String(v)
  }
  return out
}
