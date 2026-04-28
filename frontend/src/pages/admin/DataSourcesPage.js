import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useDataSources } from '../../lib/queries';
export default function DataSourcesPage() {
    const q = useDataSources();
    return (_jsxs("section", { children: [_jsx("h2", { children: "Data Sources" }), q.isLoading ? _jsx("p", { children: "Loading\u2026" }) : null, q.isError ? _jsx("p", { style: { color: 'var(--color-fail)' }, children: q.error.message }) : null, q.isSuccess ? (_jsx("pre", { className: "card", style: { overflow: 'auto', maxHeight: 600 }, children: JSON.stringify(q.data, null, 2) })) : null] }));
}
