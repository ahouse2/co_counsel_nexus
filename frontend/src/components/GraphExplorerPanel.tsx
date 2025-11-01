import { useEffect, useMemo, useState } from 'react';

interface GraphNode {
  id: string;
  label: string;
  cluster: string;
  weight: number;
}

const nodeSeed: GraphNode[] = [
  { id: 'witness-1', label: 'Witness 01', cluster: 'testimony', weight: 1 },
  { id: 'witness-2', label: 'Witness 02', cluster: 'testimony', weight: 0.9 },
  { id: 'contract-1', label: 'Acquisition Agreement', cluster: 'contract', weight: 0.7 },
  { id: 'email-42', label: 'Email Thread 42', cluster: 'communication', weight: 0.65 },
  { id: 'analysis-5', label: 'AI Finding 5', cluster: 'insight', weight: 0.8 },
  { id: 'analysis-6', label: 'AI Finding 6', cluster: 'insight', weight: 0.75 },
];

export function GraphExplorerPanel(): JSX.Element {
  const [focus, setFocus] = useState<string>('witness-1');
  const nodes = useMemo(() => nodeSeed, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setFocus((current) => {
        const index = nodes.findIndex((node) => node.id === current);
        const nextIndex = index >= 0 ? (index + 1) % nodes.length : 0;
        return nodes[nextIndex]?.id ?? nodes[0]?.id ?? 'witness-1';
      });
    }, 4200);
    return () => clearInterval(timer);
  }, [nodes]);

  return (
    <section className="graph-explorer" aria-labelledby="graph-explorer-title">
      <header className="graph-header">
        <div>
          <h2 id="graph-explorer-title">Graph Explorer</h2>
          <p>Neon-linked relationships show testimony, contracts, and AI findings orbiting the core theory.</p>
        </div>
        <div className="graph-controls">
          <button type="button" className="ghost">Focus orbit</button>
          <button type="button" className="ghost">Collapse cluster</button>
          <button type="button" className="accent">Export brief</button>
        </div>
      </header>
      <div className="graph-canvas" role="img" aria-label="Evidence relationship graph">
        <ul className="graph-node-list">
          {nodes.map((node) => (
            <li key={node.id}>
              <button
                type="button"
                className={`node ${focus === node.id ? 'active' : ''}`}
                onClick={() => setFocus(node.id)}
              >
                <span className="node-label">{node.label}</span>
                <span className="node-cluster">{node.cluster}</span>
              </button>
            </li>
          ))}
        </ul>
        <div className="graph-backdrop" aria-hidden>
          <div className="graph-stars" />
          <div className="graph-fog" />
        </div>
      </div>
    </section>
  );
}
