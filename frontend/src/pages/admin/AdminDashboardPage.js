import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Link } from 'react-router-dom';
import { useAuth } from '../../lib/auth';
import { useDataSources, useSimRuns, useUnresolvedEntities } from '../../lib/queries';
export default function AdminDashboardPage() {
    const { username } = useAuth();
    const sims = useSimRuns();
    const sources = useDataSources();
    const unresolved = useUnresolvedEntities();
    return (_jsxs("section", { children: [_jsx("h2", { children: "Admin Dashboard" }), _jsxs("p", { className: "muted", children: ["signed in as ", _jsx("code", { children: username ?? '?' })] }), _jsxs("div", { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '1rem' }, children: [_jsxs(Link, { to: "/admin/sim-runs", className: "card", children: [_jsx("h3", { children: "Sim Runs" }), _jsxs("p", { children: [sims.isSuccess ? sims.data.length : '…', " runs"] })] }), _jsxs(Link, { to: "/admin/data-sources", className: "card", children: [_jsx("h3", { children: "Data Sources" }), _jsxs("p", { children: [sources.isSuccess ? Object.keys(sources.data ?? {}).length : '…', " sources"] })] }), _jsxs(Link, { to: "/admin/unresolved", className: "card", children: [_jsx("h3", { children: "Unresolved Entities" }), _jsxs("p", { children: [unresolved.isSuccess ? unresolved.data.length : '…', " pending"] })] })] })] }));
}
