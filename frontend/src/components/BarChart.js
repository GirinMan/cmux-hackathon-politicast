import { jsx as _jsx } from "react/jsx-runtime";
import Plot from 'react-plotly.js';
import { BlackoutPlaceholder } from './BlackoutBanner';
export default function BarChart({ labels, values, colors, title, yLabel, blackout }) {
    if (blackout)
        return _jsx(BlackoutPlaceholder, {});
    return (_jsx(Plot, { data: [
            {
                type: 'bar',
                x: labels,
                y: values,
                marker: { color: colors ?? labels.map(() => '#4f7cff') },
            },
        ], layout: {
            title: title ? { text: title } : undefined,
            autosize: true,
            paper_bgcolor: '#11151f',
            plot_bgcolor: '#11151f',
            font: { color: '#d6dae4' },
            margin: { l: 50, r: 20, t: title ? 40 : 20, b: 50 },
            yaxis: { title: { text: yLabel ?? '' }, gridcolor: '#1f2330' },
        }, style: { width: '100%', height: 360 }, useResizeHandler: true, config: { displayModeBar: false, responsive: true } }));
}
