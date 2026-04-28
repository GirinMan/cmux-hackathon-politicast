import { useDataSources } from '../../lib/queries';

export default function DataSourcesPage() {
  const q = useDataSources();
  return (
    <section>
      <h2>Data Sources</h2>
      {q.isLoading ? <p>Loading…</p> : null}
      {q.isError ? <p style={{ color: 'var(--color-fail)' }}>{(q.error as Error).message}</p> : null}
      {q.isSuccess ? (
        <pre className="card" style={{ overflow: 'auto', maxHeight: 600 }}>
          {JSON.stringify(q.data, null, 2)}
        </pre>
      ) : null}
    </section>
  );
}
