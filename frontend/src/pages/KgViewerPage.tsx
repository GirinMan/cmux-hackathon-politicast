import { useState } from 'react';

import KgGraph from '../components/KgGraph';
import RequireRegion from '../components/RequireRegion';
import { useKgSubgraph } from '../lib/queries';
import { KgNodeDTO } from '../lib/types';

export default function KgViewerPage() {
  return (
    <RequireRegion>
      {(region) => <Inner region={region} />}
    </RequireRegion>
  );
}

function Inner({ region }: { region: string }) {
  const [personaId, setPersonaId] = useState<string>('');
  const sg = useKgSubgraph(region, personaId || undefined);
  const [selected, setSelected] = useState<KgNodeDTO | null>(null);

  return (
    <section>
      <header style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <h2 style={{ margin: 0 }}>KG — {region}</h2>
        <input
          placeholder="persona_id (optional)"
          value={personaId}
          onChange={(e) => setPersonaId(e.target.value)}
          style={{ padding: '0.4rem 0.75rem', background: '#11151f', color: 'inherit', border: '1px solid #1f2330', borderRadius: 4 }}
        />
      </header>

      {sg.isLoading ? <p>Loading subgraph…</p> : null}
      {sg.isError ? (
        <p style={{ color: 'var(--color-fail)' }}>{(sg.error as Error).message}</p>
      ) : null}

      {sg.isSuccess ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 3fr) minmax(0, 1fr)', gap: '1rem' }}>
          <KgGraph
            nodes={sg.data.nodes}
            edges={sg.data.edges}
            onNodeClick={setSelected}
          />
          <aside className="card">
            <h3 style={{ marginTop: 0 }}>Selected</h3>
            {selected ? (
              <dl>
                <dt>id</dt><dd>{selected.id}</dd>
                <dt>kind</dt><dd>{selected.kind}</dd>
                <dt>label</dt><dd>{selected.label}</dd>
                <dt>ts</dt><dd>{selected.ts ?? '–'}</dd>
              </dl>
            ) : (
              <p className="muted">노드를 클릭하면 상세가 표시됩니다.</p>
            )}
          </aside>
        </div>
      ) : null}
    </section>
  );
}
