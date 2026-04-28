/**
 * Phase 6 — ScenarioTreePage.
 *
 * Vertical Sankey scenario tree (top→down) for the currently-selected region.
 * Drilldown: click a node → fetch BeamNodeDetail and slide-in panel with the
 * poll trajectory + virtual interview excerpts. CommentThread (Phase 5) is
 * mounted at the bottom under scope `scenario_tree` so users can discuss
 * specific scenario branches.
 */
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import BlackoutBanner from '../components/BlackoutBanner';
import CommentThread from '../components/CommentThread';
import RequireRegion from '../components/RequireRegion';
import SankeyTree from '../components/SankeyTree';
import { sankeyApi } from '../lib/sankeyApi';
import type { BeamNodeDetail } from '../lib/sankeyApi';

export default function ScenarioTreePage() {
  return <RequireRegion>{(region) => <Inner region={region} />}</RequireRegion>;
}

function Inner({ region }: { region: string }) {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const treeQuery = useQuery({
    queryKey: ['scenario-tree', region],
    queryFn: () => sankeyApi.getTree(region),
    staleTime: 60_000,
  });

  const tree = treeQuery.data?.data ?? null;
  const blackout = treeQuery.data?.blackout;

  const detailQuery = useQuery({
    queryKey: ['scenario-tree-node', region, tree?.tree_id, selectedNode],
    queryFn: () =>
      sankeyApi.getNodeDetail(region, tree!.tree_id, selectedNode!),
    enabled: !!(tree?.tree_id && selectedNode),
    staleTime: 30_000,
  });

  const candidateLabels: Record<string, string> | undefined = undefined;
  // Hide AI tree during blackout if backend says hides_ai
  const hideAi = !!(blackout?.in_blackout && blackout?.hides_ai);

  return (
    <section style={{ display: 'grid', gap: '1.5rem' }}>
      <header>
        <h2 style={{ marginBottom: '0.25rem' }}>시나리오 트리 — {region}</h2>
        <p style={{ color: '#64748b', fontSize: 13, marginTop: 0 }}>
          현재 시점에서 발생 가능한 이벤트 분기와 각 분기의 누적 확률 / 선두
          후보를 보여주는 vertical Sankey 차트입니다. 노드를 클릭하면 해당
          분기의 voter sim 결과를 확인할 수 있습니다.
        </p>
      </header>

      <BlackoutBanner active={!!blackout?.in_blackout} endDate={blackout?.end_date} />

      {treeQuery.isLoading && <p>트리 로딩 중…</p>}
      {treeQuery.isError && (
        <p role="alert" style={{ color: '#e57373' }}>
          시나리오 트리를 불러오지 못했습니다.
        </p>
      )}

      {hideAi ? (
        <p style={{ fontStyle: 'italic', color: '#94a3b8' }}>
          블랙아웃 기간이라 AI 시나리오 트리가 숨겨졌습니다. 댓글 토론은 정상
          이용 가능합니다.
        </p>
      ) : (
        <SankeyTree
          tree={tree}
          onNodeClick={setSelectedNode}
          candidateLabels={candidateLabels}
        />
      )}

      {selectedNode && (
        <NodeDetailPanel
          isLoading={detailQuery.isLoading}
          isError={detailQuery.isError}
          detail={detailQuery.data ?? null}
          onClose={() => setSelectedNode(null)}
        />
      )}

      {tree && (
        <div style={{ borderTop: '1px solid #2d3748', paddingTop: '1rem' }}>
          <h3>시나리오 트리 토론</h3>
          <CommentThread
            scope_type="scenario_tree"
            scope_id={tree.tree_id}
            blackout={!!blackout?.in_blackout}
          />
        </div>
      )}
    </section>
  );
}

interface NodeDetailPanelProps {
  isLoading: boolean;
  isError: boolean;
  detail: BeamNodeDetail | null;
  onClose: () => void;
}

function NodeDetailPanel({
  isLoading,
  isError,
  detail,
  onClose,
}: NodeDetailPanelProps) {
  return (
    <aside
      role="dialog"
      aria-label="시나리오 노드 상세"
      style={{
        position: 'fixed',
        right: 0,
        top: 0,
        height: '100vh',
        width: 'min(420px, 90vw)',
        background: '#0f172a',
        color: '#e2e8f0',
        borderLeft: '1px solid #334155',
        padding: '1rem',
        overflowY: 'auto',
        boxShadow: '-4px 0 18px rgba(0,0,0,0.35)',
        zIndex: 30,
      }}
    >
      <button
        type="button"
        onClick={onClose}
        style={{
          float: 'right',
          background: 'transparent',
          color: '#cbd5e1',
          border: '1px solid #334155',
          borderRadius: 4,
          padding: '0.25rem 0.5rem',
          cursor: 'pointer',
        }}
      >
        닫기 ✕
      </button>
      {isLoading && <p>노드 상세 로딩 중…</p>}
      {isError && (
        <p role="alert" style={{ color: '#e57373' }}>
          노드 정보를 불러오지 못했습니다.
        </p>
      )}
      {detail && (
        <div>
          <h4 style={{ marginTop: 0 }}>{detail.label}</h4>
          <p style={{ color: '#94a3b8', fontSize: 12 }}>
            depth {detail.depth} · 누적 확률{' '}
            {(detail.cumulative_p * 100).toFixed(1)}%
            {detail.source ? ` · 소스 ${detail.source}` : ''}
          </p>
          <h5>예측 vote share</h5>
          <ul style={{ paddingLeft: '1rem', margin: 0 }}>
            {Object.entries(detail.predicted_shares)
              .sort((a, b) => b[1] - a[1])
              .map(([cid, share]) => (
                <li key={cid}>
                  {cid} — {(share * 100).toFixed(1)}%
                </li>
              ))}
          </ul>
          {detail.poll_trajectory.length > 0 && (
            <>
              <h5>Poll trajectory ({detail.poll_trajectory.length} pts)</h5>
              <ol style={{ paddingLeft: '1rem', margin: 0, fontSize: 12 }}>
                {detail.poll_trajectory.slice(0, 6).map((p) => (
                  <li key={p.timestep}>
                    t={p.timestep}{' '}
                    {Object.entries(p.support_by_candidate)
                      .map(([k, v]) => `${k}:${(v * 100).toFixed(0)}%`)
                      .join(' / ')}
                  </li>
                ))}
              </ol>
            </>
          )}
          {detail.virtual_interview_excerpts.length > 0 && (
            <>
              <h5>가상 인터뷰 발췌</h5>
              <ul style={{ paddingLeft: '1rem', margin: 0, fontSize: 12 }}>
                {detail.virtual_interview_excerpts.map((q, i) => (
                  <li key={i} style={{ marginBottom: 4 }}>
                    “{q}”
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </aside>
  );
}
