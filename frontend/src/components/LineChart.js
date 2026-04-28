import { jsx as _jsx } from "react/jsx-runtime";
import Plot from 'react-plotly.js';
import { BlackoutPlaceholder } from './BlackoutBanner';
export default function LineChart({ series, title, yLabel, xLabel, blackout }) {
    if (blackout)
        return _jsx(BlackoutPlaceholder, {});
    return (_jsx(Plot, { data: series.map((s) => ({
            type: 'scatter',
            mode: 'lines+markers',
            name: s.name,
            x: s.x,
            y: s.y,
            line: s.color ? { color: s.color, width: 2 } : { width: 2 },
            marker: { size: 6 },
        })), layout: {
            title: title ? { text: title } : undefined,
            autosize: true,
            paper_bgcolor: '#11151f',
            plot_bgcolor: '#11151f',
            font: { color: '#d6dae4' },
            margin: { l: 50, r: 20, t: title ? 40 : 20, b: 50 },
            xaxis: { title: { text: xLabel ?? '' }, gridcolor: '#1f2330' },
            yaxis: { title: { text: yLabel ?? '' }, gridcolor: '#1f2330' },
            legend: { orientation: 'h', y: -0.2 },
        }, style: { width: '100%', height: 400 }, useResizeHandler: true, config: { displayModeBar: false, responsive: true } }));
}
