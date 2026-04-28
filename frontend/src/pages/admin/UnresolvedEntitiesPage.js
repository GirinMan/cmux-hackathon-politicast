import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { useResolveEntity, useUnresolvedEntities } from '../../lib/queries';
export default function UnresolvedEntitiesPage() {
    const q = useUnresolvedEntities();
    const resolve = useResolveEntity();
    const [edits, setEdits] = useState({});
    function key(e) {
        return `${e.run_id}|${e.kind}|${e.alias}`;
    }
    return (_jsxs("section", { children: [_jsx("h2", { children: "Unresolved Entities" }), q.isLoading ? _jsx("p", { children: "Loading\u2026" }) : null, q.isError ? _jsx("p", { style: { color: 'var(--color-fail)' }, children: q.error.message }) : null, q.isSuccess ? (_jsxs("table", { style: { width: '100%', borderCollapse: 'collapse' }, children: [_jsx("thead", { children: _jsxs("tr", { style: { textAlign: 'left', borderBottom: '1px solid #1f2330' }, children: [_jsx("th", { children: "run_id" }), _jsx("th", { children: "kind" }), _jsx("th", { children: "alias" }), _jsx("th", { children: "suggested" }), _jsx("th", { children: "canonical_id" }), _jsx("th", {})] }) }), _jsx("tbody", { children: q.data.map((e) => {
                            const k = key(e);
                            return (_jsxs("tr", { style: { borderBottom: '1px solid #1f2330' }, children: [_jsx("td", { children: _jsx("code", { children: e.run_id.slice(0, 12) }) }), _jsx("td", { children: e.kind }), _jsx("td", { children: e.alias }), _jsx("td", { className: "muted", children: e.suggested_id ?? '–' }), _jsx("td", { children: _jsx("input", { value: edits[k] ?? e.suggested_id ?? '', onChange: (ev) => setEdits({ ...edits, [k]: ev.target.value }), style: { background: '#0b0e14', color: 'inherit', border: '1px solid #1f2330', padding: '0.25rem 0.5rem' } }) }), _jsx("td", { children: _jsx("button", { disabled: resolve.isPending || !(edits[k] ?? e.suggested_id ?? '').trim(), onClick: () => resolve.mutate({
                                                run_id: e.run_id,
                                                alias: e.alias,
                                                kind: e.kind,
                                                canonical_id: (edits[k] ?? e.suggested_id ?? '').trim(),
                                            }), children: resolve.isPending ? '…' : 'Resolve' }) })] }, k));
                        }) })] })) : null] }));
}
