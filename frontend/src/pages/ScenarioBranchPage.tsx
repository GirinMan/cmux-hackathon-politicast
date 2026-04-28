import { useState } from 'react';

import BarChart from '../components/BarChart';
import BlackoutBanner from '../components/BlackoutBanner';
import CommentThread from '../components/CommentThread';
import RequireRegion from '../components/RequireRegion';
import { useScenarioOutcome, useScenarios } from '../lib/queries';
import { colorFor } from '../lib/partyColors';
import { ScenarioDTO } from '../lib/types';
import { useBlackout } from '../lib/useBlackout';

export default function ScenarioBranchPage() {
  return (
    <RequireRegion>
      {(region) => <Inner region={region} />}
    </RequireRegion>
  );
}

function Inner({ region }: { region: string }) {
  const scenarios = useScenarios(region);
  const [active, setActive] = useState<ScenarioDTO | null>(null);
  const blackout = useBlackout(region);

  return (
    <section>
      <h2>Scenarios — {region}</h2>
      <BlackoutBanner active={blackout.active} endDate={blackout.endDate} />
      {scenarios.isLoading ? <p>Loading…</p> : null}
      {scenarios.isError ? (
        <p style={{ color: 'var(--color-fail)' }}>{(scenarios.error as Error).message}</p>
      ) : null}

      {scenarios.isSuccess ? (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '1rem',
          }}
        >
          {scenarios.data.map((s) => (
            <button
              key={s.scenario_id}
              type="button"
              className="card"
              onClick={() => setActive(s)}
              style={{
                textAlign: 'left',
                background: '#11151f',
                color: 'inherit',
                cursor: 'pointer',
                border: '1px solid #1f2330',
              }}
            >
              <strong>{s.scenario_id}</strong>
              <div className="muted" style={{ fontSize: '0.85rem' }}>
                contest: {s.contest_id} · T={s.timesteps} · n={s.persona_n}
              </div>
              <div className="muted" style={{ fontSize: '0.85rem' }}>
                {s.candidates.length} candidates
              </div>
            </button>
          ))}
        </div>
      ) : null}

      {active ? (
        <OutcomeModal
          region={region}
          scenario={active}
          onClose={() => setActive(null)}
          blackout={blackout.active}
        />
      ) : null}

      <CommentThread
        scope_type="scenario"
        scope_id={active?.scenario_id ?? region}
        blackout={blackout.active}
      />
    </section>
  );
}

function OutcomeModal({
  region,
  scenario,
  onClose,
  blackout,
}: {
  region: string;
  scenario: ScenarioDTO;
  onClose: () => void;
  blackout?: boolean;
}) {
  const outcome = useScenarioOutcome(region, scenario.scenario_id);

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{ minWidth: 420, maxWidth: 720 }}
        onClick={(e) => e.stopPropagation()}
      >
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>{scenario.scenario_id}</h3>
          <button onClick={onClose}>닫기</button>
        </header>

        {outcome.isLoading ? <p>Loading outcome…</p> : null}
        {outcome.isError ? (
          <p style={{ color: 'var(--color-fail)' }}>{(outcome.error as Error).message}</p>
        ) : null}

        {outcome.isSuccess ? (
          <>
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', margin: '0.75rem 0' }}>
              <span>winner:</span>
              <strong>{outcome.data.winner ?? '-'}</strong>
              {outcome.data.validation_metrics?.leader_match === true ? (
                <span className="badge badge-pass">leader_match</span>
              ) : null}
              {outcome.data.validation_metrics?.leader_match === false ? (
                <span className="badge badge-fail">leader_mismatch</span>
              ) : null}
              {typeof outcome.data.validation_metrics?.mae === 'number' ? (
                <span className="badge">MAE {outcome.data.validation_metrics.mae.toFixed(3)}</span>
              ) : null}
            </div>
            <BarChart
              labels={Object.keys(outcome.data.vote_share_by_candidate)}
              values={Object.values(outcome.data.vote_share_by_candidate)}
              colors={Object.keys(outcome.data.vote_share_by_candidate).map((cid) =>
                colorFor(scenario.candidates.find((c) => c.cand_id === cid)?.party_id),
              )}
              yLabel="vote share"
              blackout={blackout}
            />
          </>
        ) : null}
      </div>
    </div>
  );
}
