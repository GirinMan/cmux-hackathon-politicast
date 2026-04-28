/**
 * Phase 6 — Vertical Sankey scenario tree renderer.
 *
 * Pure SVG (no d3 runtime dep). Top → bottom flow; node width and edge
 * stroke proportional to cumulative probability mass; color matches the
 * leader candidate at that node.
 *
 * Props:
 *   - tree: ScenarioTree from `sankeyApi.getTree`
 *   - onNodeClick: drilldown trigger
 *   - candidateColors: optional candidate_id → color override (caller fills
 *     this from the region's candidate roster + partyColors). When absent we
 *     fall back to a stable hash-based palette so the tree always renders.
 */
import { CSSProperties, useMemo, useState } from 'react';

import {
  layoutSankey,
  type LaidOutNode,
  type SankeyLayout,
} from '../lib/sankeyLayout';
import type { ScenarioTree } from '../lib/sankeyApi';

import SankeyNodeTooltip from './SankeyNodeTooltip';

export interface SankeyTreeProps {
  tree: ScenarioTree | null;
  onNodeClick?: (nodeId: string) => void;
  /** Optional candidate_id → CSS color override. */
  candidateColors?: Record<string, string>;
  /** Optional candidate_id → human-readable name (KR) */
  candidateLabels?: Record<string, string>;
  /** Render width override (defaults to layout default 960). */
  width?: number;
}

const FALLBACK_PALETTE = [
  '#1e88e5',
  '#e53935',
  '#43a047',
  '#fb8c00',
  '#8e24aa',
  '#fdd835',
  '#26a69a',
  '#7e57c2',
  '#ec407a',
  '#5c6bc0',
];

function hashColor(id: string, override?: string): string {
  if (override) return override;
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  }
  return FALLBACK_PALETTE[hash % FALLBACK_PALETTE.length] ?? FALLBACK_PALETTE[0]!;
}

const containerStyle: CSSProperties = {
  position: 'relative',
  width: '100%',
  overflowX: 'auto',
};

const emptyStyle: CSSProperties = {
  padding: '2rem',
  textAlign: 'center',
  color: '#64748b',
  fontStyle: 'italic',
};

export default function SankeyTree({
  tree,
  onNodeClick,
  candidateColors,
  candidateLabels,
  width,
}: SankeyTreeProps) {
  const layout: SankeyLayout | null = useMemo(
    () => layoutSankey(tree, width ? { width } : {}),
    [tree, width],
  );
  const [hover, setHover] = useState<{
    node: LaidOutNode;
    x: number;
    y: number;
  } | null>(null);

  const colorForCandidate = (cid: string) =>
    hashColor(cid, candidateColors?.[cid]);

  if (!layout) {
    return (
      <div style={emptyStyle} role="status">
        시나리오 트리가 아직 빌드되지 않았습니다. 관리자가{' '}
        <code>POST /admin/api/scenario-trees/build</code>로 트리를 만들면 표시됩니다.
      </div>
    );
  }

  return (
    <div style={containerStyle} data-testid="sankey-container">
      <svg
        width={layout.width}
        height={layout.height}
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        role="img"
        aria-label="Vertical Sankey scenario tree"
      >
        {/* Edges first so nodes paint on top */}
        <g data-testid="sankey-edges">
          {layout.edges.map((e) => (
            <path
              key={e.edge_id}
              d={e.path}
              fill="none"
              stroke={colorForCandidate(e.leader_candidate_id)}
              strokeOpacity={0.45}
              strokeWidth={e.width}
              strokeLinecap="round"
            />
          ))}
        </g>
        <g data-testid="sankey-nodes">
          {layout.nodes.map((n) => (
            <g
              key={n.node_id}
              transform={`translate(${n.x - n.width / 2}, ${n.y})`}
              style={{ cursor: onNodeClick ? 'pointer' : 'default' }}
              onMouseEnter={(ev) =>
                setHover({
                  node: n,
                  x: ev.nativeEvent.offsetX,
                  y: ev.nativeEvent.offsetY,
                })
              }
              onMouseMove={(ev) =>
                setHover({
                  node: n,
                  x: ev.nativeEvent.offsetX,
                  y: ev.nativeEvent.offsetY,
                })
              }
              onMouseLeave={() => setHover(null)}
              onClick={() => onNodeClick?.(n.node_id)}
              data-node-id={n.node_id}
              data-source={n.source ?? 'root'}
            >
              <rect
                width={n.width}
                height={n.height}
                rx={6}
                ry={6}
                fill={colorForCandidate(n.leader_candidate_id)}
                fillOpacity={0.85}
                stroke="#0f172a"
                strokeWidth={1}
              />
              <text
                x={n.width / 2}
                y={n.height / 2 + 4}
                textAnchor="middle"
                fontSize={11}
                fill="#0f172a"
                pointerEvents="none"
              >
                {(n.cumulative_p * 100).toFixed(0)}%
              </text>
            </g>
          ))}
        </g>
      </svg>
      {hover && (
        <SankeyNodeTooltip
          node={hover.node}
          x={hover.x}
          y={hover.y}
          colorForCandidate={colorForCandidate}
          candidateLabels={candidateLabels}
        />
      )}
    </div>
  );
}
