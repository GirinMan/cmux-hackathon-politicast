// Top-level app — election ontology graph

const { useState: useS_a, useEffect: useE_a, useMemo: useM_a } = React;

function App() {
  const [snap, setSnap] = useS_a("seoul_mayor");
  const [step, setStep] = useS_a("T3");
  const [selectedNode, setSelectedNode] = useS_a(null);
  const [dimmedTypes, setDimmedTypes] = useS_a(new Set());

  const snapMeta = useM_a(
    () => window.SNAPSHOTS.find(s => s.id === snap) || window.SNAPSHOTS[0],
    [snap]
  );

  const nodeCount = window.NODES.length;
  const edgeCount = window.EDGES.length;
  const snapshotCount = window.SNAPSHOT_INDEX.length;

  const tabs = [
    { id: "summary",   label: "개요" },
    { id: "result",    label: "결과" },
    { id: "ontology",  label: "온톨로지", active: true },
    { id: "ops",       label: "운영" },
    { id: "data",      label: "데이터" },
  ];

  const toggleType = (id) => {
    setDimmedTypes(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const chips = [
    { id: "all",                name: "전체",                 num: 185228, active: true },
    { id: "seoul_mayor",        name: "서울시장",             num: 27694 },
    { id: "gwangju_mayor",      name: "광주시장",             num: 66906 },
    { id: "daegu_mayor",        name: "대구시장",             num: 5421 },
    { id: "busan_buk_gap",      name: "부산 북구 갑 (보궐)",  num: 5421 },
    { id: "daegu_dalseo_gap",   name: "대구 달서구 갑 (보궐)", num: 10617 },
  ];

  return (
    <div>
      <header className="eo-header">
        <div className="eo-brand">
          <span className="eo-brand-mark" />
          <span className="eo-brand-name">PolitiKAST</span>
          <span className="eo-brand-sub">Election Simulation Frontend</span>
        </div>
        <nav className="eo-tabs">
          {tabs.map(t => (
            <div key={t.id} className={`eo-tab ${t.active ? "active" : ""}`}>{t.label}</div>
          ))}
        </nav>
        <div className="eo-header-right">
          <span className="eo-pill"><span className="dot" /> ok</span>
          <span>라이트</span>
        </div>
      </header>

      <div className="eo-region-bar">
        <span className="eo-region-label">Region</span>
        {chips.map(c => (
          <div key={c.id} className={`eo-chip ${c.active ? "active" : ""}`}>
            <span>{c.name}</span>
            <span className="eo-chip-num">{c.num.toLocaleString()}</span>
          </div>
        ))}
      </div>

      <div className="eo-title-bar">
        <div>
          <div className="eo-eyebrow">Temporal Ontology</div>
          <h1>온톨로지</h1>
          <p>region·timestep별 ontology snapshot과 result artifact가 실제로 참조한 event trail을 함께 확인합니다.</p>
        </div>
        <div className="eo-stat-row">
          <div className="eo-stat">
            <div className="eo-stat-label">Nodes</div>
            <div className="eo-stat-val">{nodeCount}</div>
          </div>
          <div className="eo-stat">
            <div className="eo-stat-label">Edges</div>
            <div className="eo-stat-val">{edgeCount}</div>
          </div>
          <div className="eo-stat">
            <div className="eo-stat-label">Snapshots</div>
            <div className="eo-stat-val">{snapshotCount}</div>
          </div>
        </div>
      </div>

      <div className="eo-snap">
        <div className="eo-snap-h">
          <div>
            <div className="t">Region and timestep</div>
            <div className="s" style={{ marginTop: 2 }}>freshest ontology snapshot selector</div>
          </div>
        </div>
        <div className="eo-snap-row">
          {window.SNAPSHOTS.map(s => (
            <button key={s.id}
              className={`eo-snap-btn ${snap === s.id ? "active" : ""}`}
              onClick={() => setSnap(s.id)}>
              <div className="name">{s.name}</div>
              <span className="tag">{s.tag} · {s.steps}T</span>
            </button>
          ))}
        </div>
        <div className="eo-step-row">
          <span className="eo-step-label">timestep</span>
          {["T0","T1","T2","T3"].map(t => (
            <button key={t}
              className={`eo-step-btn ${step === t ? "active" : ""}`}
              onClick={() => setStep(t)}>{t}</button>
          ))}
        </div>
      </div>

      <div className="eo-grid">
        <div className="eo-canvas" data-screen-label="ontology-canvas">
          <div className="eo-canvas-head">
            <div>
              <div className="eo-canvas-title">Ontology snapshot graph</div>
              <div className="eo-canvas-sub">{snapMeta.source}</div>
            </div>
            <span className="eo-live"><span className="dot" /> live</span>
          </div>

          <div className="eo-legend">
            {window.NODE_TYPES.map(t => (
              <span key={t.id}
                className={`eo-legend-item ${dimmedTypes.has(t.id) ? "dimmed" : ""}`}
                onClick={() => toggleType(t.id)}
                title="클릭하여 그룹 강조 / 흐림">
                <span className="icon" style={{ color: t.color }}>
                  <svg width="18" height="18" viewBox="-9 -9 18 18">
                    <window.EOIcon kind={t.id} size={16} color={t.color} strokeWidth={1.5} />
                  </svg>
                </span>
                <span>{t.label}</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, color: "var(--fg-3)", marginLeft: 2 }}>
                  {t.count}
                </span>
              </span>
            ))}
          </div>

          <div className="eo-canvas-body">
            <window.ElectionGraph
              nodes={window.NODES}
              edges={window.EDGES}
              types={window.NODE_TYPES}
              onSelect={setSelectedNode}
              selectedId={selectedNode?.id}
              dimmedTypes={dimmedTypes}
            />
          </div>
        </div>

        <aside className="eo-side">
          <div className="eo-card">
            <div className="eo-card-h">Snapshot metadata</div>
            <div className="eo-card-sub">{snapMeta.id}_2026</div>
            <div className="eo-meta-row"><span className="k">Region</span>   <span className="v">{snapMeta.region}</span></div>
            <div className="eo-meta-row"><span className="k">Timestep</span> <span className="v">{step}</span></div>
            <div className="eo-meta-row"><span className="k">Cutoff</span>   <span className="v">{snapMeta.cutoff}</span></div>
            <div className="eo-meta-row"><span className="k">Source</span>   <span className="v" style={{ wordBreak: "break-all", textAlign: "right" }}>{snapMeta.source}</span></div>
          </div>

          <div className="eo-card">
            <div className="eo-card-h">Events used by simulation</div>
            <div className="eo-card-sub">result.kg_events_used</div>
            <div className="eo-empty">이 result artifact에 기록된 ontology event가 없습니다.</div>
          </div>

          <div className="eo-card">
            <div className="eo-card-h">Available snapshots</div>
            <div className="eo-card-sub">all indexed ontology exports</div>
            <div className="eo-snap-list">
              {window.SNAPSHOT_INDEX.map((s, i) => (
                <div key={i} className="eo-snap-item">
                  <div className="n">
                    <span>{s.region}</span>
                    <span className="t">{s.step}</span>
                  </div>
                  <div className="p">{s.path}</div>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>

      <footer className="eo-foot">
        PolitiKAST frontend는 simulation result, temporal ontology, capacity policy를 함께 표시합니다. 원본 데이터셋은 KOSIS·대법원·NHIS·KREI·NAVER Cloud 자료를 기반으로 합성되었습니다.
      </footer>

      {selectedNode && (
        <window.ElectionModal
          node={selectedNode}
          nodes={window.NODES}
          edges={window.EDGES}
          types={window.NODE_TYPES}
          onClose={() => setSelectedNode(null)}
          onJump={(n) => setSelectedNode(n)}
        />
      )}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
