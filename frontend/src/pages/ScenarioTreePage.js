import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
/**
 * Phase 6 — ScenarioTreePage.
 *
 * Vertical Sankey scenario tree (top→down) for the currently-selected region.
 * Drilldown: click a node → fetch BeamNodeDetail and slide-in panel with the
 * poll trajectory + virtual interview excerpts. CommentThread (Phase 5) is
 * mounted at the bottom under scope `scenario_tree` so users can discuss
 * specific scenario branches.
 */
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import BlackoutBanner from '../components/BlackoutBanner';
import CommentThread from '../components/CommentThread';
import RequireRegion from '../components/RequireRegion';
import SankeyTree from '../components/SankeyTree';
import { sankeyApi } from '../lib/sankeyApi';
export default function ScenarioTreePage() {
    return _jsx(RequireRegion, { children: (region) => _jsx(Inner, { region: region }) });
}
function Inner({ region }) {
    const [selectedNode, setSelectedNode] = useState(null);
    const treeQuery = useQuery({
        queryKey: ['scenario-tree', region],
        queryFn: () => sankeyApi.getTree(region),
        staleTime: 60_000,
    });
    const tree = treeQuery.data?.data ?? null;
    const blackout = treeQuery.data?.blackout;
    const detailQuery = useQuery({
        queryKey: ['scenario-tree-node', region, tree?.tree_id, selectedNode],
        queryFn: () => sankeyApi.getNodeDetail(region, tree.tree_id, selectedNode),
        enabled: !!(tree?.tree_id && selectedNode),
        staleTime: 30_000,
    });
    const candidateLabels = undefined;
    // Hide AI tree during blackout if backend says hides_ai
    const hideAi = !!(blackout?.in_blackout && blackout?.hides_ai);
    return (_jsxs("section", { style: { display: 'grid', gap: '1.5rem' }, children: [_jsxs("header", { children: [_jsxs("h2", { style: { marginBottom: '0.25rem' }, children: ["\uC2DC\uB098\uB9AC\uC624 \uD2B8\uB9AC \u2014 ", region] }), _jsx("p", { style: { color: '#64748b', fontSize: 13, marginTop: 0 }, children: "\uD604\uC7AC \uC2DC\uC810\uC5D0\uC11C \uBC1C\uC0DD \uAC00\uB2A5\uD55C \uC774\uBCA4\uD2B8 \uBD84\uAE30\uC640 \uAC01 \uBD84\uAE30\uC758 \uB204\uC801 \uD655\uB960 / \uC120\uB450 \uD6C4\uBCF4\uB97C \uBCF4\uC5EC\uC8FC\uB294 vertical Sankey \uCC28\uD2B8\uC785\uB2C8\uB2E4. \uB178\uB4DC\uB97C \uD074\uB9AD\uD558\uBA74 \uD574\uB2F9 \uBD84\uAE30\uC758 voter sim \uACB0\uACFC\uB97C \uD655\uC778\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4." })] }), _jsx(BlackoutBanner, { active: !!blackout?.in_blackout, endDate: blackout?.end_date }), treeQuery.isLoading && _jsx("p", { children: "\uD2B8\uB9AC \uB85C\uB529 \uC911\u2026" }), treeQuery.isError && (_jsx("p", { role: "alert", style: { color: '#e57373' }, children: "\uC2DC\uB098\uB9AC\uC624 \uD2B8\uB9AC\uB97C \uBD88\uB7EC\uC624\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4." })), hideAi ? (_jsx("p", { style: { fontStyle: 'italic', color: '#94a3b8' }, children: "\uBE14\uB799\uC544\uC6C3 \uAE30\uAC04\uC774\uB77C AI \uC2DC\uB098\uB9AC\uC624 \uD2B8\uB9AC\uAC00 \uC228\uACA8\uC84C\uC2B5\uB2C8\uB2E4. \uB313\uAE00 \uD1A0\uB860\uC740 \uC815\uC0C1 \uC774\uC6A9 \uAC00\uB2A5\uD569\uB2C8\uB2E4." })) : (_jsx(SankeyTree, { tree: tree, onNodeClick: setSelectedNode, candidateLabels: candidateLabels })), selectedNode && (_jsx(NodeDetailPanel, { isLoading: detailQuery.isLoading, isError: detailQuery.isError, detail: detailQuery.data ?? null, onClose: () => setSelectedNode(null) })), tree && (_jsxs("div", { style: { borderTop: '1px solid #2d3748', paddingTop: '1rem' }, children: [_jsx("h3", { children: "\uC2DC\uB098\uB9AC\uC624 \uD2B8\uB9AC \uD1A0\uB860" }), _jsx(CommentThread, { scope_type: "scenario", scope_id: `scenario_tree:${tree.tree_id}`, blackout: !!blackout?.in_blackout })] }))] }));
}
function NodeDetailPanel({ isLoading, isError, detail, onClose, }) {
    return (_jsxs("aside", { role: "dialog", "aria-label": "\uC2DC\uB098\uB9AC\uC624 \uB178\uB4DC \uC0C1\uC138", style: {
            position: 'fixed',
            right: 0,
            top: 0,
            height: '100vh',
            width: 'min(420px, 90vw)',
            background: '#0f172a',
            color: '#e2e8f0',
            borderLeft: '1px solid #334155',
            padding: '1rem',
            overflowY: 'auto',
            boxShadow: '-4px 0 18px rgba(0,0,0,0.35)',
            zIndex: 30,
        }, children: [_jsx("button", { type: "button", onClick: onClose, style: {
                    float: 'right',
                    background: 'transparent',
                    color: '#cbd5e1',
                    border: '1px solid #334155',
                    borderRadius: 4,
                    padding: '0.25rem 0.5rem',
                    cursor: 'pointer',
                }, children: "\uB2EB\uAE30 \u2715" }), isLoading && _jsx("p", { children: "\uB178\uB4DC \uC0C1\uC138 \uB85C\uB529 \uC911\u2026" }), isError && (_jsx("p", { role: "alert", style: { color: '#e57373' }, children: "\uB178\uB4DC \uC815\uBCF4\uB97C \uBD88\uB7EC\uC624\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4." })), detail && (_jsxs("div", { children: [_jsx("h4", { style: { marginTop: 0 }, children: detail.label }), _jsxs("p", { style: { color: '#94a3b8', fontSize: 12 }, children: ["depth ", detail.depth, " \u00B7 \uB204\uC801 \uD655\uB960", ' ', (detail.cumulative_p * 100).toFixed(1), "%", detail.source ? ` · 소스 ${detail.source}` : ''] }), _jsx("h5", { children: "\uC608\uCE21 vote share" }), _jsx("ul", { style: { paddingLeft: '1rem', margin: 0 }, children: Object.entries(detail.predicted_shares)
                            .sort((a, b) => b[1] - a[1])
                            .map(([cid, share]) => (_jsxs("li", { children: [cid, " \u2014 ", (share * 100).toFixed(1), "%"] }, cid))) }), detail.poll_trajectory.length > 0 && (_jsxs(_Fragment, { children: [_jsxs("h5", { children: ["Poll trajectory (", detail.poll_trajectory.length, " pts)"] }), _jsx("ol", { style: { paddingLeft: '1rem', margin: 0, fontSize: 12 }, children: detail.poll_trajectory.slice(0, 6).map((p) => (_jsxs("li", { children: ["t=", p.timestep, ' ', Object.entries(p.support_by_candidate)
                                            .map(([k, v]) => `${k}:${(v * 100).toFixed(0)}%`)
                                            .join(' / ')] }, p.timestep))) })] })), detail.virtual_interview_excerpts.length > 0 && (_jsxs(_Fragment, { children: [_jsx("h5", { children: "\uAC00\uC0C1 \uC778\uD130\uBDF0 \uBC1C\uCDCC" }), _jsx("ul", { style: { paddingLeft: '1rem', margin: 0, fontSize: 12 }, children: detail.virtual_interview_excerpts.map((q, i) => (_jsxs("li", { style: { marginBottom: 4 }, children: ["\u201C", q, "\u201D"] }, i))) })] }))] }))] }));
}
