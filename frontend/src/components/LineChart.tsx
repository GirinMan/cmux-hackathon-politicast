import Plot from 'react-plotly.js';

import { BlackoutPlaceholder } from './BlackoutBanner';

export interface LineSeries {
  name: string;
  x: (string | number)[];
  y: number[];
  color?: string;
}

interface Props {
  series: LineSeries[];
  title?: string;
  yLabel?: string;
  xLabel?: string;
  /** true 면 차트 대신 placeholder 만 렌더 (공직선거법 §108). */
  blackout?: boolean;
}

export default function LineChart({ series, title, yLabel, xLabel, blackout }: Props) {
  if (blackout) return <BlackoutPlaceholder />;
  return (
    <Plot
      data={series.map((s) => ({
        type: 'scatter',
        mode: 'lines+markers',
        name: s.name,
        x: s.x,
        y: s.y,
        line: s.color ? { color: s.color, width: 2 } : { width: 2 },
        marker: { size: 6 },
      }))}
      layout={{
        title: title ? { text: title } : undefined,
        autosize: true,
        paper_bgcolor: '#11151f',
        plot_bgcolor: '#11151f',
        font: { color: '#d6dae4' },
        margin: { l: 50, r: 20, t: title ? 40 : 20, b: 50 },
        xaxis: { title: { text: xLabel ?? '' }, gridcolor: '#1f2330' },
        yaxis: { title: { text: yLabel ?? '' }, gridcolor: '#1f2330' },
        legend: { orientation: 'h', y: -0.2 },
      }}
      style={{ width: '100%', height: 400 }}
      useResizeHandler
      config={{ displayModeBar: false, responsive: true }}
    />
  );
}
