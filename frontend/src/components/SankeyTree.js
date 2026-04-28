import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/**
 * Phase 6 — Vertical Sankey scenario tree renderer.
 *
 * Pure SVG (no d3 runtime dep). Top → bottom flow; node width and edge
 * stroke proportional to cumulative probability mass; color matches the
 * leader candidate at that node.
 *
 * Props:
 *   - tree: ScenarioTree from `sankeyApi.getTree`
 *   - onNodeClick: drilldown trigger
 *   - candidateColors: optional candidate_id → color override (caller fills
 *     this from the region's candidate roster + partyColors). When absent we
 *     fall back to a stable hash-based palette so the tree always renders.
 */
import { useMemo, useState } from 'react';
import { layoutSankey, } from '../lib/sankeyLayout';
import SankeyNodeTooltip from './SankeyNodeTooltip';
const FALLBACK_PALETTE = [
    '#1e88e5',
    '#e53935',
    '#43a047',
    '#fb8c00',
    '#8e24aa',
    '#fdd835',
    '#26a69a',
    '#7e57c2',
    '#ec407a',
    '#5c6bc0',
];
function hashColor(id, override) {
    if (override)
        return override;
    let hash = 0;
    for (let i = 0; i < id.length; i++) {
        hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
    }
    return FALLBACK_PALETTE[hash % FALLBACK_PALETTE.length] ?? FALLBACK_PALETTE[0];
}
const containerStyle = {
    position: 'relative',
    width: '100%',
    overflowX: 'auto',
};
const emptyStyle = {
    padding: '2rem',
    textAlign: 'center',
    color: '#64748b',
    fontStyle: 'italic',
};
export default function SankeyTree({ tree, onNodeClick, candidateColors, candidateLabels, width, }) {
    const layout = useMemo(() => layoutSankey(tree, width ? { width } : {}), [tree, width]);
    const [hover, setHover] = useState(null);
    const colorForCandidate = (cid) => hashColor(cid, candidateColors?.[cid]);
    if (!layout) {
        return (_jsxs("div", { style: emptyStyle, role: "status", children: ["\uC2DC\uB098\uB9AC\uC624 \uD2B8\uB9AC\uAC00 \uC544\uC9C1 \uBE4C\uB4DC\uB418\uC9C0 \uC54A\uC558\uC2B5\uB2C8\uB2E4. \uAD00\uB9AC\uC790\uAC00", ' ', _jsx("code", { children: "POST /admin/api/scenario-trees/build" }), "\uB85C \uD2B8\uB9AC\uB97C \uB9CC\uB4E4\uBA74 \uD45C\uC2DC\uB429\uB2C8\uB2E4."] }));
    }
    return (_jsxs("div", { style: containerStyle, "data-testid": "sankey-container", children: [_jsxs("svg", { width: layout.width, height: layout.height, viewBox: `0 0 ${layout.width} ${layout.height}`, role: "img", "aria-label": "Vertical Sankey scenario tree", children: [_jsx("g", { "data-testid": "sankey-edges", children: layout.edges.map((e) => (_jsx("path", { d: e.path, fill: "none", stroke: colorForCandidate(e.leader_candidate_id), strokeOpacity: 0.45, strokeWidth: e.width, strokeLinecap: "round" }, e.edge_id))) }), _jsx("g", { "data-testid": "sankey-nodes", children: layout.nodes.map((n) => (_jsxs("g", { transform: `translate(${n.x - n.width / 2}, ${n.y})`, style: { cursor: onNodeClick ? 'pointer' : 'default' }, onMouseEnter: (ev) => setHover({
                                node: n,
                                x: ev.nativeEvent.offsetX,
                                y: ev.nativeEvent.offsetY,
                            }), onMouseMove: (ev) => setHover({
                                node: n,
                                x: ev.nativeEvent.offsetX,
                                y: ev.nativeEvent.offsetY,
                            }), onMouseLeave: () => setHover(null), onClick: () => onNodeClick?.(n.node_id), "data-node-id": n.node_id, "data-source": n.source ?? 'root', children: [_jsx("rect", { width: n.width, height: n.height, rx: 6, ry: 6, fill: colorForCandidate(n.leader_candidate_id), fillOpacity: 0.85, stroke: "#0f172a", strokeWidth: 1 }), _jsxs("text", { x: n.width / 2, y: n.height / 2 + 4, textAnchor: "middle", fontSize: 11, fill: "#0f172a", pointerEvents: "none", children: [(n.cumulative_p * 100).toFixed(0), "%"] })] }, n.node_id))) })] }), hover && (_jsx(SankeyNodeTooltip, { node: hover.node, x: hover.x, y: hover.y, colorForCandidate: colorForCandidate, candidateLabels: candidateLabels }))] }));
}
