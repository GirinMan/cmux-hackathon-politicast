import { useMemo, useRef } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import type cytoscape from 'cytoscape';

import { KgEdgeDTO, KgNodeDTO } from '../lib/types';

interface Props {
  nodes: KgNodeDTO[];
  edges: KgEdgeDTO[];
  onNodeClick?: (node: KgNodeDTO) => void;
}

const NODE_KIND_COLOR: Record<string, string> = {
  Candidate: '#4f7cff',
  Person: '#34a853',
  Party: '#e53935',
  Issue: '#fdd835',
  Event: '#8e24aa',
  CohortPrior: '#fb8c00',
};

export default function KgGraph({ nodes, edges, onNodeClick }: Props) {
  const cyRef = useRef<cytoscape.Core | null>(null);
  const elements = useMemo(() => {
    return [
      ...nodes.map((n) => ({
        data: { id: n.id, label: n.label || n.id, kind: n.kind, ts: n.ts },
      })),
      ...edges.map((e, i) => ({
        data: {
          id: `e${i}`,
          source: e.source,
          target: e.target,
          predicate: e.predicate,
        },
      })),
    ];
  }, [nodes, edges]);

  return (
    <div className="card" style={{ padding: 0, height: 520 }}>
      <CytoscapeComponent
        elements={elements}
        cy={(cy) => {
          cyRef.current = cy;
          cy.removeListener('tap', 'node');
          cy.on('tap', 'node', (evt) => {
            const id = evt.target.id() as string;
            const n = nodes.find((x) => x.id === id);
            if (n && onNodeClick) onNodeClick(n);
          });
        }}
        layout={{ name: 'cose', animate: false, fit: true, padding: 30 }}
        stylesheet={[
          {
            selector: 'node',
            style: {
              'background-color': (ele: cytoscape.NodeSingular) =>
                NODE_KIND_COLOR[ele.data('kind') as string] ?? '#7c8190',
              label: 'data(label)',
              color: '#d6dae4',
              'font-size': 11,
              'text-valign': 'bottom',
              'text-halign': 'center',
              'text-margin-y': 6,
              width: 28,
              height: 28,
            },
          },
          {
            selector: 'edge',
            style: {
              'curve-style': 'bezier',
              'target-arrow-shape': 'triangle',
              'line-color': '#3a4150',
              'target-arrow-color': '#3a4150',
              width: 1.5,
              label: 'data(predicate)',
              'font-size': 9,
              color: '#7c8190',
              'text-rotation': 'autorotate',
            },
          },
        ]}
        style={{ width: '100%', height: '100%' }}
      />
    </div>
  );
}
