import { RegionDTO } from '../lib/types';

interface Props {
  regions: RegionDTO[];
  value: string | null;
  onChange: (regionId: string, contestId?: string) => void;
  disabled?: boolean;
}

export default function RegionSelector({ regions, value, onChange, disabled }: Props) {
  return (
    <div role="radiogroup" aria-label="Region selector" className="region-selector">
      {regions.map((r) => {
        const active = value === r.region_id;
        return (
          <button
            key={r.region_id}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={disabled}
            onClick={() => onChange(r.region_id, r.election_id)}
            className={`card region-card${active ? ' active' : ''}`}
            style={{
              cursor: 'pointer',
              border: active ? '2px solid var(--color-accent)' : '1px solid #1f2330',
              minWidth: 220,
              textAlign: 'left',
              background: active ? '#1a2030' : '#11151f',
              color: 'inherit',
            }}
          >
            <div style={{ fontWeight: 600 }}>{r.name}</div>
            <div className="muted" style={{ fontSize: '0.85rem' }}>
              {r.region_id} · {r.position_type}
            </div>
            <div className="muted" style={{ fontSize: '0.85rem' }}>
              election: {r.election_date}
            </div>
            {r.in_blackout ? <span className="badge badge-warn">blackout</span> : null}
          </button>
        );
      })}
    </div>
  );
}
