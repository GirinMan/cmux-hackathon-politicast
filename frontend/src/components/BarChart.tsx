import Plot from 'react-plotly.js';

import { BlackoutPlaceholder } from './BlackoutBanner';

interface Props {
  labels: string[];
  values: number[];
  colors?: string[];
  title?: string;
  yLabel?: string;
  blackout?: boolean;
}

export default function BarChart({ labels, values, colors, title, yLabel, blackout }: Props) {
  if (blackout) return <BlackoutPlaceholder />;
  return (
    <Plot
      data={[
        {
          type: 'bar',
          x: labels,
          y: values,
          marker: { color: colors ?? labels.map(() => '#4f7cff') },
        },
      ]}
      layout={{
        title: title ? { text: title } : undefined,
        autosize: true,
        paper_bgcolor: '#11151f',
        plot_bgcolor: '#11151f',
        font: { color: '#d6dae4' },
        margin: { l: 50, r: 20, t: title ? 40 : 20, b: 50 },
        yaxis: { title: { text: yLabel ?? '' }, gridcolor: '#1f2330' },
      }}
      style={{ width: '100%', height: 360 }}
      useResizeHandler
      config={{ displayModeBar: false, responsive: true }}
    />
  );
}
