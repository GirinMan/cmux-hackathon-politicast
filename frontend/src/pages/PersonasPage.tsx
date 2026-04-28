import { useState } from 'react';

import BlackoutBanner from '../components/BlackoutBanner';
import CommentThread from '../components/CommentThread';
import PersonaCard from '../components/PersonaCard';
import RequireRegion from '../components/RequireRegion';
import { usePersonas } from '../lib/queries';
import { useBlackout } from '../lib/useBlackout';

export default function PersonasPage() {
  return (
    <RequireRegion>
      {(region) => <PersonasInner region={region} />}
    </RequireRegion>
  );
}

function PersonasInner({ region }: { region: string }) {
  const [seed, setSeed] = useState<number>(0);
  const personas = usePersonas(region, 20, seed);
  const blackout = useBlackout(region);

  return (
    <section>
      <header style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
        <h2 style={{ margin: 0 }}>Personas — {region}</h2>
        <button onClick={() => setSeed(Math.floor(Math.random() * 1_000_000))}>
          새로고침 (seed)
        </button>
        <span className="muted">seed: {seed}</span>
      </header>

      {personas.isLoading ? <p>Loading personas…</p> : null}
      {personas.isError ? (
        <p style={{ color: 'var(--color-fail)' }}>
          Personas 로드 실패: {(personas.error as Error).message}
        </p>
      ) : null}

      {personas.isSuccess ? (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '1rem',
          }}
        >
          {personas.data.map((p) => (
            <PersonaCard key={p.persona_id} persona={p} />
          ))}
        </div>
      ) : null}

      <BlackoutBanner active={blackout.active} endDate={blackout.endDate} />

      <CommentThread scope_type="region" scope_id={region} blackout={blackout.active} />
    </section>
  );
}
