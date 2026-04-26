/* eslint-disable react-refresh/only-export-components */
import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'
import { useTheme } from '../state/theme'

/**
 * We deliberately accept a loose option type here. ECharts' generated
 * types pin axis/tooltip `type` fields to string literals which fights
 * the dynamic option objects we build per-page; runtime validation is
 * sufficient.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type LooseEChartsOption = Record<string, any>

export interface EChartProps {
  option: LooseEChartsOption
  height?: number | string
  className?: string
  notMerge?: boolean
  onEvents?: Record<string, (params: unknown) => void>
}

/**
 * Thin wrapper around echarts-for-react that wires the active dashboard theme
 * (light/dark) into ECharts via `theme="dark"` and a sensible default style.
 */
export default function EChart({
  option,
  height = 320,
  className,
  notMerge,
  onEvents,
}: EChartProps) {
  const { theme } = useTheme()
  const style = useMemo(() => ({ height, width: '100%' }), [height])
  return (
    <ReactECharts
      key={theme /* re-init on theme change to repaint */}
      option={option as never}
      theme={theme === 'dark' ? 'dark' : undefined}
      style={style}
      className={className}
      notMerge={notMerge}
      onEvents={onEvents}
      opts={{ renderer: 'canvas' }}
    />
  )
}

/** Shared dark/light palette aligned to dashboard accent (emerald). */
export const PALETTE = {
  accent: '#10b981',
  accentSoft: 'rgba(16, 185, 129, 0.55)',
  axisDark: '#52525b',
  axisLight: '#a1a1aa',
  textDark: '#a1a1aa',
  textLight: '#3f3f46',
}

export function gridDefaults(theme: 'dark' | 'light') {
  return {
    left: 56,
    right: 24,
    top: 28,
    bottom: 36,
    containLabel: false,
    borderColor: theme === 'dark' ? PALETTE.axisDark : PALETTE.axisLight,
  }
}
