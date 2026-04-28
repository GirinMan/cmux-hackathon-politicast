import { useSimRuns } from '../../lib/queries';

export default function SimRunsPage() {
  const q = useSimRuns();
  return (
    <section>
      <h2>Sim Runs</h2>
      {q.isLoading ? <p>Loading…</p> : null}
      {q.isError ? <p style={{ color: 'var(--color-fail)' }}>{(q.error as Error).message}</p> : null}
      {q.isSuccess ? (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid #1f2330' }}>
              <th>run_id</th>
              <th>region</th>
              <th>scenario</th>
              <th>status</th>
              <th>MAE</th>
              <th>started_at</th>
            </tr>
          </thead>
          <tbody>
            {q.data.map((r) => (
              <tr key={r.run_id} style={{ borderBottom: '1px solid #1f2330' }}>
                <td><code>{r.run_id.slice(0, 12)}</code></td>
                <td>{r.region_id}</td>
                <td>{r.scenario_id ?? '–'}</td>
                <td>
                  <span
                    className={`badge ${r.status === 'completed' ? 'badge-pass' : r.status === 'failed' ? 'badge-fail' : 'badge-warn'}`}
                  >
                    {r.status}
                  </span>
                </td>
                <td>{r.mae?.toFixed(3) ?? '–'}</td>
                <td>{r.started_at ?? '–'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}
