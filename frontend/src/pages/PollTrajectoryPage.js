import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useMemo } from 'react';
import BlackoutBanner from '../components/BlackoutBanner';
import LineChart from '../components/LineChart';
import RequireRegion from '../components/RequireRegion';
import { usePollTrajectory } from '../lib/queries';
import { colorFor } from '../lib/partyColors';
import { useBlackout } from '../lib/useBlackout';
export default function PollTrajectoryPage() {
    return (_jsx(RequireRegion, { children: (region) => _jsx(PollInner, { region: region }) }));
}
function PollInner({ region }) {
    const traj = usePollTrajectory(region);
    const blackout = useBlackout(region);
    const series = useMemo(() => {
        if (!traj.isSuccess)
            return [];
        const points = traj.data;
        const candidates = new Set();
        points.forEach((p) => Object.keys(p.support_by_candidate).forEach((c) => candidates.add(c)));
        return Array.from(candidates).map((cid) => ({
            name: cid,
            x: points.map((p) => p.date ?? `t${p.timestep}`),
            y: points.map((p) => p.support_by_candidate[cid] ?? 0),
            color: colorFor(cid),
        }));
    }, [traj.isSuccess, traj.data]);
    return (_jsxs("section", { children: [_jsxs("h2", { children: ["Poll trajectory \u2014 ", region] }), _jsx(BlackoutBanner, { active: blackout.active, endDate: blackout.endDate }), traj.isLoading ? _jsx("p", { children: "Loading\u2026" }) : null, traj.isError ? (_jsx("p", { style: { color: 'var(--color-fail)' }, children: traj.error.message })) : null, traj.isSuccess ? (series.length > 0 ? (_jsx(LineChart, { series: series, yLabel: "support share", xLabel: "date", blackout: blackout.active })) : (_jsx("p", { className: "muted", children: "\uC9D1\uACC4\uB41C trajectory \uAC00 \uC5C6\uC2B5\uB2C8\uB2E4." }))) : null] }));
}
