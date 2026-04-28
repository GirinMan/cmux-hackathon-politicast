import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import KgGraph from '../components/KgGraph';
import RequireRegion from '../components/RequireRegion';
import { useKgSubgraph } from '../lib/queries';
export default function KgViewerPage() {
    return (_jsx(RequireRegion, { children: (region) => _jsx(Inner, { region: region }) }));
}
function Inner({ region }) {
    const [personaId, setPersonaId] = useState('');
    const sg = useKgSubgraph(region, personaId || undefined);
    const [selected, setSelected] = useState(null);
    return (_jsxs("section", { children: [_jsxs("header", { style: { display: 'flex', alignItems: 'center', gap: '0.75rem' }, children: [_jsxs("h2", { style: { margin: 0 }, children: ["KG \u2014 ", region] }), _jsx("input", { placeholder: "persona_id (optional)", value: personaId, onChange: (e) => setPersonaId(e.target.value), style: { padding: '0.4rem 0.75rem', background: '#11151f', color: 'inherit', border: '1px solid #1f2330', borderRadius: 4 } })] }), sg.isLoading ? _jsx("p", { children: "Loading subgraph\u2026" }) : null, sg.isError ? (_jsx("p", { style: { color: 'var(--color-fail)' }, children: sg.error.message })) : null, sg.isSuccess ? (_jsxs("div", { style: { display: 'grid', gridTemplateColumns: 'minmax(0, 3fr) minmax(0, 1fr)', gap: '1rem' }, children: [_jsx(KgGraph, { nodes: sg.data.nodes, edges: sg.data.edges, onNodeClick: setSelected }), _jsxs("aside", { className: "card", children: [_jsx("h3", { style: { marginTop: 0 }, children: "Selected" }), selected ? (_jsxs("dl", { children: [_jsx("dt", { children: "id" }), _jsx("dd", { children: selected.id }), _jsx("dt", { children: "kind" }), _jsx("dd", { children: selected.kind }), _jsx("dt", { children: "label" }), _jsx("dd", { children: selected.label }), _jsx("dt", { children: "ts" }), _jsx("dd", { children: selected.ts ?? '–' })] })) : (_jsx("p", { className: "muted", children: "\uB178\uB4DC\uB97C \uD074\uB9AD\uD558\uBA74 \uC0C1\uC138\uAC00 \uD45C\uC2DC\uB429\uB2C8\uB2E4." }))] })] })) : null] }));
}
