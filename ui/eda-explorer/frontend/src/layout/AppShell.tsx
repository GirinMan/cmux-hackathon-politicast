import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useTheme } from '../state/theme'
import { useHealth } from '../hooks/queries'
import RegionFilterBar from '../components/RegionFilterBar'

const NAV = [
  { to: '/overview', label: '개요', section: 'overview' },
  { to: '/results', label: '결과', section: 'results' },
  { to: '/ontology', label: '온톨로지', section: 'kg' },
  { to: '/operations', label: '운영', section: 'operations' },
  { to: '/demographics', label: '데이터', section: 'data' },
]

const DATA_NAV = [
  { to: '/demographics', label: '인구통계', hint: 'KOSIS' },
  { to: '/regions', label: '지역', hint: '분포' },
  { to: '/regions/compare', label: '지역 비교', hint: '5-region' },
  { to: '/personas', label: '페르소나', hint: 'samples' },
  { to: '/population', label: '인구 분포', hint: 'map' },
]

export default function AppShell() {
  const { theme, toggle } = useTheme()
  const { data: health } = useHealth()
  const status = health?.status ?? 'loading'
  const location = useLocation()
  const isDataSection = DATA_NAV.some(
    (item) =>
      location.pathname === item.to || location.pathname.startsWith(`${item.to}/`),
  )

  return (
    <div className="min-h-full flex flex-col bg-zinc-50 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100">
      <header className="sticky top-0 z-30 backdrop-blur supports-[backdrop-filter]:bg-white/70 dark:supports-[backdrop-filter]:bg-zinc-950/70 border-b border-zinc-200 dark:border-zinc-800">
        <div className="mx-auto max-w-7xl px-6 py-3 flex items-center gap-6">
          <NavLink to="/" className="flex items-center gap-2 group">
            <span className="text-emerald-600 dark:text-emerald-400 font-mono text-sm">
              ◎
            </span>
            <span className="font-semibold">PolitiKAST</span>
            <span className="text-xs text-zinc-500 dark:text-zinc-400 hidden md:inline">
              Election Simulation Frontend
            </span>
          </NavLink>

          <nav className="hidden md:flex items-center gap-1 ml-4 text-sm">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  navClass(isActive || (n.section === 'data' && isDataSection))
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>

          <nav className="md:hidden flex items-center gap-1 ml-2 text-sm overflow-x-auto">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  navClass(isActive || (n.section === 'data' && isDataSection))
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-3">
            <HealthBadge status={status} />
            <button
              type="button"
              onClick={toggle}
              className="text-xs px-2 py-1 rounded-md border border-zinc-300 dark:border-zinc-700 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-900"
              title="테마 토글"
            >
              {theme === 'dark' ? '라이트' : '다크'}
            </button>
          </div>
        </div>

        {isDataSection && (
          <div className="border-t border-zinc-200/70 dark:border-zinc-800/70">
            <div className="mx-auto max-w-7xl px-6 py-2 flex flex-col gap-2 sm:flex-row sm:items-center">
              <div className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                <span className="font-medium text-zinc-700 dark:text-zinc-300">
                  Data
                </span>
                <span className="hidden sm:inline">source, cohorts, graph</span>
              </div>
              <nav className="flex w-fit rounded-lg border border-zinc-200 bg-zinc-100/70 p-1 text-xs dark:border-zinc-800 dark:bg-zinc-900/70">
                {DATA_NAV.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end
                    className={({ isActive }) =>
                      [
                        'group flex items-center gap-2 rounded-md px-3 py-1.5 transition-colors',
                        isActive
                          ? 'bg-white text-zinc-950 shadow-sm dark:bg-zinc-100 dark:text-zinc-950'
                          : 'text-zinc-600 hover:bg-white/70 hover:text-zinc-950 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100',
                      ].join(' ')
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <span className="font-medium">{item.label}</span>
                        <span
                          className={[
                            'hidden rounded px-1.5 py-0.5 text-[10px] sm:inline',
                            isActive
                              ? 'bg-zinc-900 text-zinc-100 dark:bg-zinc-800 dark:text-zinc-100'
                              : 'bg-zinc-200 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400',
                          ].join(' ')}
                        >
                          {item.hint}
                        </span>
                      </>
                    )}
                  </NavLink>
                ))}
              </nav>
            </div>
          </div>
        )}

        <div className="mx-auto max-w-7xl px-6 py-2 border-t border-zinc-200/60 dark:border-zinc-800/60">
          <RegionFilterBar />
        </div>
      </header>

      <main className="mx-auto max-w-7xl w-full px-6 py-8 flex-1">
        <Outlet />
      </main>

      <footer className="mx-auto max-w-7xl w-full px-6 py-6 border-t border-zinc-200 dark:border-zinc-800 text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
        <p>
          PolitiKAST frontend는 simulation result, temporal ontology, capacity policy, 그리고 NVIDIA의{' '}
          <a
            className="underline hover:text-emerald-600 dark:hover:text-emerald-400"
            href="https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea"
            target="_blank"
            rel="noreferrer"
          >
            Nemotron-Personas-Korea v1.0 (CC BY 4.0)
          </a>
          를 함께 표시합니다. 원본 데이터셋은 KOSIS·대법원·NHIS·KREI·NAVER Cloud 자료를 기반으로 합성되었습니다.
        </p>
      </footer>
    </div>
  )
}

function navClass(active: boolean) {
  return [
    'px-3 py-1.5 rounded-md transition-colors whitespace-nowrap',
    active
      ? 'bg-zinc-900 text-zinc-50 dark:bg-zinc-100 dark:text-zinc-900'
      : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:text-zinc-100 dark:hover:bg-zinc-900',
  ].join(' ')
}

function HealthBadge({ status }: { status: string }) {
  const tone =
    status === 'ok'
      ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 ring-emerald-500/30'
      : status === 'degraded'
        ? 'bg-amber-500/15 text-amber-700 dark:text-amber-300 ring-amber-500/30'
        : 'bg-zinc-500/15 text-zinc-600 dark:text-zinc-400 ring-zinc-500/30'
  return (
    <span
      className={[
        'text-[11px] font-medium px-2 py-0.5 rounded-full ring-1',
        tone,
      ].join(' ')}
      title={`API status: ${status}`}
    >
      ● {status}
    </span>
  )
}
