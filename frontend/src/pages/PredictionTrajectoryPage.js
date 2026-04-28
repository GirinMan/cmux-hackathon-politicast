import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useMemo, useState } from 'react';
import BlackoutBanner from '../components/BlackoutBanner';
import LineChart from '../components/LineChart';
import RequireRegion from '../components/RequireRegion';
import { usePredictionTrajectory, useScenarios } from '../lib/queries';
import { colorFor } from '../lib/partyColors';
import { useBlackout } from '../lib/useBlackout';
export default function PredictionTrajectoryPage() {
    return (_jsx(RequireRegion, { children: (region) => _jsx(PredictionInner, { region: region }) }));
}
function PredictionInner({ region }) {
    const scenarios = useScenarios(region);
    const [simRunId, setSimRunId] = useState();
    const traj = usePredictionTrajectory(region, simRunId);
    const blackout = useBlackout(region);
    const series = useMemo(() => {
        if (!traj.isSuccess)
            return [];
        const points = traj.data;
        const candidates = new Set();
        points.forEach((p) => Object.keys(p.predicted_share).forEach((c) => candidates.add(c)));
        return Array.from(candidates).map((cid) => ({
            name: cid,
            x: points.map((p) => p.date ?? `t${p.timestep}`),
            y: points.map((p) => p.predicted_share[cid] ?? 0),
            color: colorFor(cid),
        }));
    }, [traj.isSuccess, traj.data]);
    return (_jsxs("section", { children: [_jsxs("header", { style: { display: 'flex', alignItems: 'center', gap: '1rem' }, children: [_jsxs("h2", { style: { margin: 0 }, children: ["Prediction trajectory \u2014 ", region] }), _jsx("span", { className: "badge badge-warn", children: "prediction-only" })] }), _jsx("p", { className: "muted", style: { marginTop: 0 }, children: "Validation gate \uD1B5\uACFC \uC804: \uACF5\uC2DD \uC608\uCE21\uC774 \uC544\uB2C8\uB2E4. (`prediction-only` \uB77C\uBCA8 \uAC15\uC81C)" }), _jsx(BlackoutBanner, { active: blackout.active, endDate: blackout.endDate }), scenarios.isSuccess && scenarios.data.length > 0 ? (_jsxs("label", { style: { display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }, children: [_jsx("span", { children: "Sim run:" }), _jsxs("select", { value: simRunId ?? '', onChange: (e) => setSimRunId(e.target.value || undefined), style: { background: '#11151f', color: 'inherit', padding: '0.25rem 0.5rem' }, children: [_jsx("option", { value: "", children: "latest" }), scenarios.data.map((s) => (_jsx("option", { value: s.scenario_id, children: s.scenario_id }, s.scenario_id)))] })] })) : null, traj.isLoading ? _jsx("p", { children: "Loading\u2026" }) : null, traj.isError ? (_jsx("p", { style: { color: 'var(--color-fail)' }, children: traj.error.message })) : null, traj.isSuccess ? (series.length > 0 ? (_jsx(LineChart, { series: series, yLabel: "predicted share", xLabel: "date", blackout: blackout.active })) : (_jsx("p", { className: "muted", children: "no predicted points." }))) : null] }));
}
