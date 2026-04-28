import { Link, NavLink, Outlet, useSearchParams } from 'react-router-dom';

import { useAuth } from '../lib/auth';
import CookieConsentBanner from './CookieConsentBanner';
import NicknameEditor from './NicknameEditor';

interface LayoutProps {
  admin?: boolean;
}

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

export default function Layout({ admin = false }: LayoutProps) {
  const [search] = useSearchParams();
  const region = search.get('region');
  const { token, logout } = useAuth();
  const nav = admin ? ADMIN_NAV : PUBLIC_NAV;
  return (
    <div className="layout">
      <header>
        <h1>
          <Link to="/">PolitiKAST</Link>
        </h1>
        <nav>
          {nav.map((item) => {
            const to = !admin && region ? `${item.to}?region=${region}` : item.to;
            return (
              <NavLink key={item.to} to={to} end>
                {item.label}
              </NavLink>
            );
          })}
        </nav>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.5rem' }} className="muted">
          {region ? <span>region: <code>{region}</code></span> : null}
          {!admin ? <NicknameEditor /> : null}
          {admin && token ? (
            <button onClick={logout}>Logout</button>
          ) : null}
        </div>
      </header>
      <main>
        <Outlet />
      </main>
      <CookieConsentBanner />
    </div>
  );
}
