/**
 * Phase 6 — SankeyTree + sankeyLayout unit tests.
 *
 * Located at `frontend/src/__tests__/` because vitest only scans this tree.
 * (The plan referenced `tests/components/test_SankeyTree.test.tsx` for
 * symmetry with the python suite — that path is reserved for E2E + python
 * harness tests, not vitest.)
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import SankeyTree from '../components/SankeyTree';
import { layoutSankey } from '../lib/sankeyLayout';
import type { ScenarioTree } from '../lib/sankeyApi';

const TREE: ScenarioTree = {
  tree_id: 'tree-1',
  region_id: 'seoul_mayor',
  contest_id: 'seoul_mayor_2026',
  as_of: '2026-04-26',
  election_date: '2026-06-03',
  root_id: 'n0',
  built_at: '2026-04-28T00:00:00+00:00',
  mlflow_run_id: null,
  nodes: [
    {
      node_id: 'n0',
      parent_id: null,
      depth: 0,
      label: '현재 (2026-04-26)',
      source: null,
      prior_p: null,
      cumulative_p: 1.0,
      leader_candidate_id: 'c_dem',
      predicted_shares: { c_dem: 0.55, c_ppp: 0.45 },
      children: ['n1', 'n2'],
      occurs_at: null,
    },
    {
      node_id: 'n1',
      parent_id: 'n0',
      depth: 1,
      label: '후보 사퇴',
      source: 'kg_confirmed',
      prior_p: 0.4,
      cumulative_p: 0.4,
      leader_candidate_id: 'c_ppp',
      predicted_shares: { c_dem: 0.45, c_ppp: 0.55 },
      children: [],
      occurs_at: '2026-05-15T00:00:00+09:00',
    },
    {
      node_id: 'n2',
      parent_id: 'n0',
      depth: 1,
      label: '논란 발생',
      source: 'llm_hypothetical',
      prior_p: 0.6,
      cumulative_p: 0.6,
      leader_candidate_id: 'c_dem',
      predicted_shares: { c_dem: 0.62, c_ppp: 0.38 },
      children: [],
      occurs_at: '2026-05-20T00:00:00+09:00',
    },
  ],
};

describe('layoutSankey', () => {
  it('returns null for empty tree', () => {
    expect(layoutSankey(null)).toBeNull();
  });

  it('positions nodes top-to-bottom by depth', () => {
    const layout = layoutSankey(TREE);
    expect(layout).not.toBeNull();
    const root = layout!.byId.n0!;
    const child = layout!.byId.n1!;
    expect(child.y).toBeGreaterThan(root.y);
  });

  it('emits an edge per non-root node', () => {
    const layout = layoutSankey(TREE)!;
    const childIds = layout.edges.map((e) => e.child_id).sort();
    expect(childIds).toEqual(['n1', 'n2']);
  });
});

describe('<SankeyTree>', () => {
  it('renders empty state when tree is null', () => {
    render(<SankeyTree tree={null} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders nodes + edges + handles click', () => {
    const onClick = vi.fn();
    const { container } = render(
      <SankeyTree tree={TREE} onNodeClick={onClick} />,
    );
    // 3 nodes => 3 <g data-node-id="...">
    const nodes = container.querySelectorAll('[data-node-id]');
    expect(nodes.length).toBe(3);
    const root = container.querySelector('[data-node-id="n0"]')!;
    fireEvent.click(root);
    expect(onClick).toHaveBeenCalledWith('n0');
  });
});
