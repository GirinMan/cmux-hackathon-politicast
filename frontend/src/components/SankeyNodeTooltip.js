import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
const SOURCE_BADGE = {
    kg_confirmed: { label: 'KG 확정', bg: '#1f6feb' },
    llm_hypothetical: { label: 'LLM 가설', bg: '#9b59b6' },
    custom: { label: 'Custom', bg: '#fb8c00' },
};
const containerStyle = {
    position: 'absolute',
    pointerEvents: 'none',
    background: '#0f172a',
    color: '#e2e8f0',
    border: '1px solid #334155',
    borderRadius: 8,
    padding: '0.6rem 0.75rem',
    fontSize: 12,
    lineHeight: 1.4,
    maxWidth: 280,
    boxShadow: '0 4px 18px rgba(0,0,0,0.35)',
    zIndex: 20,
};
export default function SankeyNodeTooltip({ node, colorForCandidate, x, y, candidateLabels, }) {
    const sourceBadge = node.source ? SOURCE_BADGE[node.source] : null;
    const sortedShares = Object.entries(node.predicted_shares)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 6);
    return (_jsxs("div", { role: "tooltip", style: {
            ...containerStyle,
            transform: `translate(${x + 12}px, ${y + 12}px)`,
        }, children: [_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }, children: [sourceBadge && (_jsx("span", { style: {
                            background: sourceBadge.bg,
                            color: '#fff',
                            padding: '2px 6px',
                            borderRadius: 4,
                            fontSize: 10,
                            fontWeight: 600,
                        }, children: sourceBadge.label })), _jsxs("span", { style: { fontSize: 11, color: '#94a3b8' }, children: ["\uB204\uC801 \uD655\uB960 ", (node.cumulative_p * 100).toFixed(1), "%"] })] }), _jsx("div", { style: { fontWeight: 600, marginBottom: 8 }, children: node.label }), sortedShares.length > 0 && (_jsx("div", { style: { display: 'grid', gap: 4 }, children: sortedShares.map(([cid, share]) => {
                    const pct = share * 100;
                    const label = candidateLabels?.[cid] ?? cid;
                    const color = colorForCandidate(cid);
                    return (_jsxs("div", { style: { display: 'grid', gap: 2 }, children: [_jsxs("div", { style: {
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    fontSize: 11,
                                    color: '#cbd5e1',
                                }, children: [_jsx("span", { children: label }), _jsxs("span", { children: [pct.toFixed(1), "%"] })] }), _jsx("div", { style: {
                                    height: 6,
                                    borderRadius: 3,
                                    background: '#1e293b',
                                    overflow: 'hidden',
                                }, children: _jsx("div", { style: {
                                        width: `${Math.min(100, pct)}%`,
                                        height: '100%',
                                        background: color,
                                    } }) })] }, cid));
                }) }))] }));
}
