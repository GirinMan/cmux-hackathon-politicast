import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState } from 'react';
import BarChart from '../components/BarChart';
import BlackoutBanner from '../components/BlackoutBanner';
import CommentThread from '../components/CommentThread';
import RequireRegion from '../components/RequireRegion';
import { useScenarioOutcome, useScenarios } from '../lib/queries';
import { colorFor } from '../lib/partyColors';
import { useBlackout } from '../lib/useBlackout';
export default function ScenarioBranchPage() {
    return (_jsx(RequireRegion, { children: (region) => _jsx(Inner, { region: region }) }));
}
function Inner({ region }) {
    const scenarios = useScenarios(region);
    const [active, setActive] = useState(null);
    const blackout = useBlackout(region);
    return (_jsxs("section", { children: [_jsxs("h2", { children: ["Scenarios \u2014 ", region] }), _jsx(BlackoutBanner, { active: blackout.active, endDate: blackout.endDate }), scenarios.isLoading ? _jsx("p", { children: "Loading\u2026" }) : null, scenarios.isError ? (_jsx("p", { style: { color: 'var(--color-fail)' }, children: scenarios.error.message })) : null, scenarios.isSuccess ? (_jsx("div", { style: {
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                    gap: '1rem',
                }, children: scenarios.data.map((s) => (_jsxs("button", { type: "button", className: "card", onClick: () => setActive(s), style: {
                        textAlign: 'left',
                        background: '#11151f',
                        color: 'inherit',
                        cursor: 'pointer',
                        border: '1px solid #1f2330',
                    }, children: [_jsx("strong", { children: s.scenario_id }), _jsxs("div", { className: "muted", style: { fontSize: '0.85rem' }, children: ["contest: ", s.contest_id, " \u00B7 T=", s.timesteps, " \u00B7 n=", s.persona_n] }), _jsxs("div", { className: "muted", style: { fontSize: '0.85rem' }, children: [s.candidates.length, " candidates"] })] }, s.scenario_id))) })) : null, active ? (_jsx(OutcomeModal, { region: region, scenario: active, onClose: () => setActive(null), blackout: blackout.active })) : null, _jsx(CommentThread, { scope_type: "scenario", scope_id: active?.scenario_id ?? region, blackout: blackout.active })] }));
}
function OutcomeModal({ region, scenario, onClose, blackout, }) {
    const outcome = useScenarioOutcome(region, scenario.scenario_id);
    return (_jsx("div", { role: "dialog", "aria-modal": "true", style: {
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 50,
        }, onClick: onClose, children: _jsxs("div", { className: "card", style: { minWidth: 420, maxWidth: 720 }, onClick: (e) => e.stopPropagation(), children: [_jsxs("header", { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' }, children: [_jsx("h3", { style: { margin: 0 }, children: scenario.scenario_id }), _jsx("button", { onClick: onClose, children: "\uB2EB\uAE30" })] }), outcome.isLoading ? _jsx("p", { children: "Loading outcome\u2026" }) : null, outcome.isError ? (_jsx("p", { style: { color: 'var(--color-fail)' }, children: outcome.error.message })) : null, outcome.isSuccess ? (_jsxs(_Fragment, { children: [_jsxs("div", { style: { display: 'flex', gap: '0.75rem', alignItems: 'center', margin: '0.75rem 0' }, children: [_jsx("span", { children: "winner:" }), _jsx("strong", { children: outcome.data.winner ?? '-' }), outcome.data.validation_metrics?.leader_match === true ? (_jsx("span", { className: "badge badge-pass", children: "leader_match" })) : null, outcome.data.validation_metrics?.leader_match === false ? (_jsx("span", { className: "badge badge-fail", children: "leader_mismatch" })) : null, typeof outcome.data.validation_metrics?.mae === 'number' ? (_jsxs("span", { className: "badge", children: ["MAE ", outcome.data.validation_metrics.mae.toFixed(3)] })) : null] }), _jsx(BarChart, { labels: Object.keys(outcome.data.vote_share_by_candidate), values: Object.values(outcome.data.vote_share_by_candidate), colors: Object.keys(outcome.data.vote_share_by_candidate).map((cid) => colorFor(scenario.candidates.find((c) => c.cand_id === cid)?.party_id)), yLabel: "vote share", blackout: blackout })] })) : null] }) }));
}
