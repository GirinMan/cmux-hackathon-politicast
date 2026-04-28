import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Link, NavLink, Outlet, useSearchParams } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import CookieConsentBanner from './CookieConsentBanner';
import NicknameEditor from './NicknameEditor';
const PUBLIC_NAV = [
    { to: '/personas', label: 'Personas' },
    { to: '/polls', label: 'Polls' },
    { to: '/prediction', label: 'Prediction' },
    { to: '/scenarios', label: 'Scenarios' },
    { to: '/kg', label: 'KG' },
    { to: '/board', label: 'Board' },
];
const ADMIN_NAV = [
    { to: '/admin', label: 'Dashboard' },
    { to: '/admin/sim-runs', label: 'Sim Runs' },
    { to: '/admin/data-sources', label: 'Data Sources' },
    { to: '/admin/unresolved', label: 'Unresolved' },
    { to: '/admin/moderation', label: 'Moderation' },
];
export default function Layout({ admin = false }) {
    const [search] = useSearchParams();
    const region = search.get('region');
    const { token, logout } = useAuth();
    const nav = admin ? ADMIN_NAV : PUBLIC_NAV;
    return (_jsxs("div", { className: "layout", children: [_jsxs("header", { children: [_jsx("h1", { children: _jsx(Link, { to: "/", children: "PolitiKAST" }) }), _jsx("nav", { children: nav.map((item) => {
                            const to = !admin && region ? `${item.to}?region=${region}` : item.to;
                            return (_jsx(NavLink, { to: to, end: true, children: item.label }, item.to));
                        }) }), _jsxs("div", { style: { marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.5rem' }, className: "muted", children: [region ? _jsxs("span", { children: ["region: ", _jsx("code", { children: region })] }) : null, !admin ? _jsx(NicknameEditor, {}) : null, admin && token ? (_jsx("button", { onClick: logout, children: "Logout" })) : null] })] }), _jsx("main", { children: _jsx(Outlet, {}) }), _jsx(CookieConsentBanner, {})] }));
}
