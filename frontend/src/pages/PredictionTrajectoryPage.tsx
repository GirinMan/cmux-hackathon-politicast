import { useMemo, useState } from 'react';

import BlackoutBanner from '../components/BlackoutBanner';
import LineChart, { LineSeries } from '../components/LineChart';
import RequireRegion from '../components/RequireRegion';
import { usePredictionTrajectory, useScenarios } from '../lib/queries';
import { colorFor } from '../lib/partyColors';
import { useBlackout } from '../lib/useBlackout';

export default function PredictionTrajectoryPage() {
  return (
    <RequireRegion>
      {(region) => <PredictionInner region={region} />}
    </RequireRegion>
  );
}

function PredictionInner({ region }: { region: string }) {
  const scenarios = useScenarios(region);
  const [simRunId, setSimRunId] = useState<string | undefined>();
  const traj = usePredictionTrajectory(region, simRunId);
  const blackout = useBlackout(region);

  const series = useMemo<LineSeries[]>(() => {
    if (!traj.isSuccess) return [];
    const points = traj.data;
    const candidates = new Set<string>();
    points.forEach((p) => Object.keys(p.predicted_share).forEach((c) => candidates.add(c)));
    return Array.from(candidates).map((cid) => ({
      name: cid,
      x: points.map((p) => p.date ?? `t${p.timestep}`),
      y: points.map((p) => p.predicted_share[cid] ?? 0),
      color: colorFor(cid),
    }));
  }, [traj.isSuccess, traj.data]);

  return (
    <section>
      <header style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <h2 style={{ margin: 0 }}>Prediction trajectory — {region}</h2>
        <span className="badge badge-warn">prediction-only</span>
      </header>
      <p className="muted" style={{ marginTop: 0 }}>
        Validation gate 통과 전: 공식 예측이 아니다. (`prediction-only` 라벨 강제)
      </p>

      <BlackoutBanner active={blackout.active} endDate={blackout.endDate} />

      {scenarios.isSuccess && scenarios.data.length > 0 ? (
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <span>Sim run:</span>
          <select
            value={simRunId ?? ''}
            onChange={(e) => setSimRunId(e.target.value || undefined)}
            style={{ background: '#11151f', color: 'inherit', padding: '0.25rem 0.5rem' }}
          >
            <option value="">latest</option>
            {scenarios.data.map((s) => (
              <option key={s.scenario_id} value={s.scenario_id}>
                {s.scenario_id}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {traj.isLoading ? <p>Loading…</p> : null}
      {traj.isError ? (
        <p style={{ color: 'var(--color-fail)' }}>{(traj.error as Error).message}</p>
      ) : null}
      {traj.isSuccess ? (
        series.length > 0 ? (
          <LineChart series={series} yLabel="predicted share" xLabel="date" blackout={blackout.active} />
        ) : (
          <p className="muted">no predicted points.</p>
        )
      ) : null}
    </section>
  );
}
