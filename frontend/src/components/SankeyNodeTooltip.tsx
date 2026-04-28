/**
 * Phase 6 — Sankey hover tooltip.
 *
 * Description (한국어 라벨) + per-candidate vote share bars + cumulative_p +
 * source 배지. Stateless; positioned by parent <SankeyTree> using transform.
 */
import { CSSProperties } from 'react';

import type { LaidOutNode } from '../lib/sankeyLayout';

export interface SankeyNodeTooltipProps {
  node: LaidOutNode;
  colorForCandidate: (candidateId: string) => string;
  /** Pixel position relative to the SVG container */
  x: number;
  y: number;
  /** Optional translation map for candidate id → display name */
  candidateLabels?: Record<string, string>;
}

const SOURCE_BADGE: Record<string, { label: string; bg: string }> = {
  kg_confirmed: { label: 'KG 확정', bg: '#1f6feb' },
  llm_hypothetical: { label: 'LLM 가설', bg: '#9b59b6' },
  custom: { label: 'Custom', bg: '#fb8c00' },
};

const containerStyle: CSSProperties = {
  position: 'absolute',
  pointerEvents: 'none',
  background: '#0f172a',
  color: '#e2e8f0',
  border: '1px solid #334155',
  borderRadius: 8,
  padding: '0.6rem 0.75rem',
  fontSize: 12,
  lineHeight: 1.4,
  maxWidth: 280,
  boxShadow: '0 4px 18px rgba(0,0,0,0.35)',
  zIndex: 20,
};

export default function SankeyNodeTooltip({
  node,
  colorForCandidate,
  x,
  y,
  candidateLabels,
}: SankeyNodeTooltipProps) {
  const sourceBadge = node.source ? SOURCE_BADGE[node.source] : null;
  const sortedShares = Object.entries(node.predicted_shares)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);
  return (
    <div
      role="tooltip"
      style={{
        ...containerStyle,
        transform: `translate(${x + 12}px, ${y + 12}px)`,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        {sourceBadge && (
          <span
            style={{
              background: sourceBadge.bg,
              color: '#fff',
              padding: '2px 6px',
              borderRadius: 4,
              fontSize: 10,
              fontWeight: 600,
            }}
          >
            {sourceBadge.label}
          </span>
        )}
        <span style={{ fontSize: 11, color: '#94a3b8' }}>
          누적 확률 {(node.cumulative_p * 100).toFixed(1)}%
        </span>
      </div>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>{node.label}</div>
      {sortedShares.length > 0 && (
        <div style={{ display: 'grid', gap: 4 }}>
          {sortedShares.map(([cid, share]) => {
            const pct = share * 100;
            const label = candidateLabels?.[cid] ?? cid;
            const color = colorForCandidate(cid);
            return (
              <div key={cid} style={{ display: 'grid', gap: 2 }}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: 11,
                    color: '#cbd5e1',
                  }}
                >
                  <span>{label}</span>
                  <span>{pct.toFixed(1)}%</span>
                </div>
                <div
                  style={{
                    height: 6,
                    borderRadius: 3,
                    background: '#1e293b',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: `${Math.min(100, pct)}%`,
                      height: '100%',
                      background: color,
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
