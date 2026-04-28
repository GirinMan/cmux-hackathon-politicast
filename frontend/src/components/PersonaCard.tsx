import { PersonaSampleDTO } from '../lib/types';

export default function PersonaCard({ persona }: { persona: PersonaSampleDTO }) {
  return (
    <article className="card persona-card">
      <header style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
        <strong>#{persona.persona_id.slice(0, 8)}</strong>
        <span className="muted">
          {persona.age ?? '–'} · {persona.gender ?? '–'}
        </span>
      </header>
      <div className="muted" style={{ fontSize: '0.85rem' }}>
        {persona.province ?? '–'} {persona.district ?? ''} · {persona.education ?? '–'}
      </div>
      <p style={{ marginTop: '0.5rem', fontSize: '0.9rem', lineHeight: 1.4 }}>
        {persona.summary || <em className="muted">no summary</em>}
      </p>
    </article>
  );
}
