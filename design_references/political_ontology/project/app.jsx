// 메인 앱
const { useState: useS, useEffect: useE, useMemo: useM } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "viewMode": "hex",
  "showLabels": true,
  "accent": "#7dd3c0"
}/*EDITMODE-END*/;

function App() {
  const [tweaks, setTweak] = (window.useTweaks ? window.useTweaks(TWEAK_DEFAULTS) : [TWEAK_DEFAULTS, () => {}]);
  const [selectedRegion, setSelectedRegion] = useS("all");
  const [modalRegion, setModalRegion] = useS(null);
  const [hoveredRegion, setHoveredRegion] = useS(null);
  const [activeTab, setActiveTab] = useS("ontology");
  const [categoryDim, setCategoryDim] = useS(9);
  const [occupationDim, setOccupationDim] = useS(12);
  const [minWeight, setMinWeight] = useS(1);

  useE(() => {
    document.documentElement.style.setProperty("--accent", tweaks.accent);
    document.documentElement.style.setProperty("--ok", tweaks.accent);
  }, [tweaks.accent]);

  // ESC로 모달 닫기
  useE(() => {
    const onKey = (e) => { if (e.key === "Escape") setModalRegion(null); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const handleMapRegionSelect = (id) => {
    if (!id || id === "all") return;
    setSelectedRegion(id);
    setModalRegion(id);
  };

  const regionInfo = useM(() => {
    if (selectedRegion === "all") return { name: "전체", personas: 1000000, raw: null };
    const feat = window.FEATURED_REGIONS.find(f => f.id === selectedRegion);
    if (feat) return { name: feat.name, personas: feat.personas, raw: feat };
    const r = window.KR_REGIONS.find(x => x.id === selectedRegion);
    if (r) return { name: r.name, personas: Math.round(r.pop * 1000 * 0.02), raw: r };
    return { name: "전체", personas: 1000000, raw: null };
  }, [selectedRegion]);

  const totalCats = window.ONTOLOGY_CATEGORIES.length;
  const nodeCount = window.ONTOLOGY_CATEGORIES.reduce((s,c) => s + c.count, 0);
  const edgeCount = Math.round(nodeCount * 2.1);

  const chips = [
    { id: "all", name: "전체", num: 1000000 },
    ...window.FEATURED_REGIONS.filter(f => f.id !== "all").map(f => ({ id: f.id, name: f.name, num: f.personas })),
  ];

  const tabs = ["개요", "인구통계", "지역", "비교", "페르소나", "온톨로지"];

  const handleChipSelect = (id) => {
    setSelectedRegion(id);
    if (id === "all") return;
    const feat = window.FEATURED_REGIONS.find(f => f.id === id);
    const target = feat?.parent || id;
    if (window.KR_REGIONS.find(r => r.id === target)) setModalRegion(target);
  };

  const mapRegionId = selectedRegion === "all" ? null : (regionInfo.raw?.parent || selectedRegion);

  return (
    <div>
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark" />
          <span className="brand-name">Nemotron-Personas-Korea</span>
          <span className="brand-sub">EDA Explorer</span>
        </div>
        <nav className="tabs">
          {tabs.map(t => (
            <div key={t} className={`tab ${t === "온톨로지" ? "active" : ""}`} onClick={() => setActiveTab(t)}>
              {t}
            </div>
          ))}
        </nav>
        <div className="header-right">
          <span className="health-pill"><span className="health-dot" /> ok</span>
          <span style={{ color: "var(--fg-2)" }}>라이트</span>
        </div>
      </header>

      <div className="region-bar">
        <span className="region-bar-label">Region</span>
        {chips.map(c => (
          <div key={c.id}
               className={`region-chip ${selectedRegion === c.id ? "active" : ""}`}
               onClick={() => handleChipSelect(c.id)}>
            <span>{c.name}</span>
            <span className="region-chip-num">{c.num.toLocaleString()}</span>
          </div>
        ))}
      </div>

      <div className="title-bar">
        <div className="title-block">
          <h1>온톨로지</h1>
          <p>region · 행정구역 · 연령 · 성별 · 학력 · 직업 · 가족·주거 유형의 SQL aggregate graph</p>
        </div>
        <div className="controls">
          <div className="control">
            <div className="control-label"><span>범주</span><span className="control-val">{categoryDim}</span></div>
            <input type="range" min="3" max="9" value={categoryDim} onChange={e => setCategoryDim(+e.target.value)} />
          </div>
          <div className="control">
            <div className="control-label"><span>최소</span><span className="control-val">{minWeight}</span></div>
            <input type="range" min="1" max="12" value={minWeight} onChange={e => setMinWeight(+e.target.value)} />
          </div>
        </div>
      </div>

      <div className="kpis">
        <div className="kpi">
          <div className="kpi-label">Region</div>
          <div className="kpi-val">{regionInfo.name}</div>
          <div className="kpi-sub">{selectedRegion === "all" ? "all" : selectedRegion}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Personas</div>
          <div className="kpi-val">{regionInfo.personas.toLocaleString()}</div>
          <div className="kpi-sub">synthetic agents</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Nodes</div>
          <div className="kpi-val">{nodeCount}</div>
          <div className="kpi-sub">{totalCats} categories</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Edges</div>
          <div className="kpi-val">{edgeCount}</div>
          <div className="kpi-sub">aggregate links</div>
        </div>
      </div>

      <div className="main-grid">
        <div className="canvas" data-screen-label="ontology-canvas">
          <div className="canvas-head">
            <div>
              <div className="canvas-title">
                {tweaks.viewMode === "hex" && "Korea · Hex Grid Map"}
                {tweaks.viewMode === "graph" && "Ontology / Radial Graph"}
              </div>
              <div className="canvas-sub">
                raw_categorical_sql · {totalCats} dimensions · 17 regions
              </div>
            </div>
            <div className="view-toggle">
              <button className={tweaks.viewMode === "hex" ? "active" : ""}
                      onClick={() => setTweak("viewMode", "hex")}>지도형</button>
              <button className={tweaks.viewMode === "graph" ? "active" : ""}
                      onClick={() => setTweak("viewMode", "graph")}>방사형</button>
            </div>
          </div>

          <div className="canvas-body">
            {tweaks.viewMode === "hex" && (
              <window.HexKoreaMap
                regions={window.KR_REGIONS}
                signatures={window.REGION_SIGNATURES}
                categories={window.ONTOLOGY_CATEGORIES}
                members={window.CATEGORY_MEMBERS}
                selected={mapRegionId}
                onSelect={handleMapRegionSelect}
                hovered={hoveredRegion}
                onHover={setHoveredRegion}
              />
            )}
            {tweaks.viewMode === "graph" && (
              <window.OntologyGraph
                regionFilter={mapRegionId || "all"}
                signatures={window.REGION_SIGNATURES}
                categories={window.ONTOLOGY_CATEGORIES}
                members={window.CATEGORY_MEMBERS}
                dimensions={Math.min(categoryDim, 9)}
                minWeight={minWeight}
              />
            )}
          </div>

          <div className="canvas-legend">
            {window.ONTOLOGY_CATEGORIES.map(c => (
              <span key={c.id} className="legend-item">
                <svg width="14" height="14" className="legend-mark" style={{ overflow: "visible" }}>
                  <g transform="translate(7,7)">
                    <window.NodeSymbol shape={c.shape} size={11} color={c.color} />
                  </g>
                </svg>
                {c.label.toLowerCase()}
              </span>
            ))}
          </div>
        </div>

        <window.GraphIndexPanel
          categories={window.ONTOLOGY_CATEGORIES}
          topNodes={window.TOP_NODES}
          regionFilter={selectedRegion}
          regionName={regionInfo.name}
        />
      </div>

      <footer className="app-footer">
        본 대시보드는 NVIDIA의 <a href="#">Nemotron-Personas-Korea v1.0 (CC BY 4.0)</a>를 사용합니다. 원본은 KOSIS·대법원·NHIS·KREI·NAVER Cloud 자료를 기반으로 합성되었습니다.
      </footer>

      {modalRegion && window.RegionModal && (
        <window.RegionModal
          region={modalRegion}
          onClose={() => setModalRegion(null)}
          signatures={window.REGION_SIGNATURES}
          categories={window.ONTOLOGY_CATEGORIES}
          members={window.CATEGORY_MEMBERS}
        />
      )}

      {window.TweaksPanel && (
        <window.TweaksPanel title="Tweaks">
          <window.TweakSection title="레이아웃 모드">
            <window.TweakRadio value={tweaks.viewMode} onChange={v => setTweak("viewMode", v)}
              options={[
                { value: "hex", label: "지도형" },
                { value: "graph", label: "방사형" },
              ]} />
          </window.TweakSection>
          <window.TweakSection title="액센트 색">
            <window.TweakColor value={tweaks.accent} onChange={v => setTweak("accent", v)} />
          </window.TweakSection>
        </window.TweaksPanel>
      )}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
