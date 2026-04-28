import { useState } from 'react';

import { useResolveEntity, useUnresolvedEntities } from '../../lib/queries';
import { UnresolvedEntityDTO } from '../../lib/types';

export default function UnresolvedEntitiesPage() {
  const q = useUnresolvedEntities();
  const resolve = useResolveEntity();
  const [edits, setEdits] = useState<Record<string, string>>({});

  function key(e: UnresolvedEntityDTO) {
    return `${e.run_id}|${e.kind}|${e.alias}`;
  }

  return (
    <section>
      <h2>Unresolved Entities</h2>
      {q.isLoading ? <p>Loading…</p> : null}
      {q.isError ? <p style={{ color: 'var(--color-fail)' }}>{(q.error as Error).message}</p> : null}
      {q.isSuccess ? (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid #1f2330' }}>
              <th>run_id</th>
              <th>kind</th>
              <th>alias</th>
              <th>suggested</th>
              <th>canonical_id</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {q.data.map((e) => {
              const k = key(e);
              return (
                <tr key={k} style={{ borderBottom: '1px solid #1f2330' }}>
                  <td><code>{e.run_id.slice(0, 12)}</code></td>
                  <td>{e.kind}</td>
                  <td>{e.alias}</td>
                  <td className="muted">{e.suggested_id ?? '–'}</td>
                  <td>
                    <input
                      value={edits[k] ?? e.suggested_id ?? ''}
                      onChange={(ev) => setEdits({ ...edits, [k]: ev.target.value })}
                      style={{ background: '#0b0e14', color: 'inherit', border: '1px solid #1f2330', padding: '0.25rem 0.5rem' }}
                    />
                  </td>
                  <td>
                    <button
                      disabled={resolve.isPending || !(edits[k] ?? e.suggested_id ?? '').trim()}
                      onClick={() =>
                        resolve.mutate({
                          run_id: e.run_id,
                          alias: e.alias,
                          kind: e.kind,
                          canonical_id: (edits[k] ?? e.suggested_id ?? '').trim(),
                        })
                      }
                    >
                      {resolve.isPending ? '…' : 'Resolve'}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}
