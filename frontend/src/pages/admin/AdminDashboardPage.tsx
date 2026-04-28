import { Link } from 'react-router-dom';

import { useAuth } from '../../lib/auth';
import { useDataSources, useSimRuns, useUnresolvedEntities } from '../../lib/queries';

export default function AdminDashboardPage() {
  const { username } = useAuth();
  const sims = useSimRuns();
  const sources = useDataSources();
  const unresolved = useUnresolvedEntities();

  return (
    <section>
      <h2>Admin Dashboard</h2>
      <p className="muted">signed in as <code>{username ?? '?'}</code></p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '1rem' }}>
        <Link to="/admin/sim-runs" className="card">
          <h3>Sim Runs</h3>
          <p>{sims.isSuccess ? sims.data.length : '…'} runs</p>
        </Link>
        <Link to="/admin/data-sources" className="card">
          <h3>Data Sources</h3>
          <p>{sources.isSuccess ? Object.keys(sources.data ?? {}).length : '…'} sources</p>
        </Link>
        <Link to="/admin/unresolved" className="card">
          <h3>Unresolved Entities</h3>
          <p>{unresolved.isSuccess ? unresolved.data.length : '…'} pending</p>
        </Link>
      </div>
    </section>
  );
}
