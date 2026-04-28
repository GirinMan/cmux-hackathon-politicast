import { useMemo } from 'react';

import BlackoutBanner from '../components/BlackoutBanner';
import LineChart, { LineSeries } from '../components/LineChart';
import RequireRegion from '../components/RequireRegion';
import { usePollTrajectory } from '../lib/queries';
import { colorFor } from '../lib/partyColors';
import { useBlackout } from '../lib/useBlackout';

export default function PollTrajectoryPage() {
  return (
    <RequireRegion>
      {(region) => <PollInner region={region} />}
    </RequireRegion>
  );
}

function PollInner({ region }: { region: string }) {
  const traj = usePollTrajectory(region);
  const blackout = useBlackout(region);

  const series = useMemo<LineSeries[]>(() => {
    if (!traj.isSuccess) return [];
    const points = traj.data;
    const candidates = new Set<string>();
    points.forEach((p) => Object.keys(p.support_by_candidate).forEach((c) => candidates.add(c)));
    return Array.from(candidates).map((cid) => ({
      name: cid,
      x: points.map((p) => p.date ?? `t${p.timestep}`),
      y: points.map((p) => p.support_by_candidate[cid] ?? 0),
      color: colorFor(cid),
    }));
  }, [traj.isSuccess, traj.data]);

  return (
    <section>
      <h2>Poll trajectory — {region}</h2>
      <BlackoutBanner active={blackout.active} endDate={blackout.endDate} />
      {traj.isLoading ? <p>Loading…</p> : null}
      {traj.isError ? (
        <p style={{ color: 'var(--color-fail)' }}>
          {(traj.error as Error).message}
        </p>
      ) : null}
      {traj.isSuccess ? (
        series.length > 0 ? (
          <LineChart series={series} yLabel="support share" xLabel="date" blackout={blackout.active} />
        ) : (
          <p className="muted">집계된 trajectory 가 없습니다.</p>
        )
      ) : null}
    </section>
  );
}
