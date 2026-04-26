// 지역 클릭 시 뜨는 방사형 온톨로지 모달
function RegionModal({ region, onClose, signatures, categories, members }) {
  if (!region) return null;
  const r = window.KR_REGIONS.find(x => x.id === region);
  if (!r) return null;

  const personas = Math.round(r.pop * 1000 * 0.02);
  const sig = signatures[region];

  return (
    <div className="region-modal-backdrop" onClick={onClose}>
      <div className="region-modal" onClick={e => e.stopPropagation()}>
        <div className="region-modal-head">
          <div>
            <div className="region-modal-eyebrow">REGION ONTOLOGY · 방사형</div>
            <div className="region-modal-title">{r.name} <span className="region-modal-en">{r.en}</span></div>
            <div className="region-modal-meta">
              <span>{r.cluster}</span>
              <span className="dot">·</span>
              <span>{r.type === "metro" ? "광역시" : "도"}</span>
              <span className="dot">·</span>
              <span>{(r.pop / 1000).toFixed(2)}M residents</span>
              <span className="dot">·</span>
              <span>{personas.toLocaleString()} personas</span>
            </div>
          </div>
          <button className="region-modal-close" onClick={onClose} aria-label="close">×</button>
        </div>

        <div className="region-modal-body">
          <div className="region-modal-graph">
            <window.OntologyGraph
              regionFilter={region}
              signatures={signatures}
              categories={categories}
              members={members}
              dimensions={9}
              minWeight={1}
            />
          </div>

          <div className="region-modal-side">
            <div className="region-modal-section">
              <div className="region-modal-section-title">DOMINANT TRAITS</div>
              <div className="region-modal-tags">
                {(sig?.dominant || []).map(d => (
                  <span key={d} className="region-modal-tag">{d}</span>
                ))}
              </div>
            </div>
            {sig?.note && (
              <div className="region-modal-section">
                <div className="region-modal-section-title">SIGNATURE</div>
                <p className="region-modal-note">{sig.note}</p>
              </div>
            )}
            <div className="region-modal-section">
              <div className="region-modal-section-title">CATEGORIES</div>
              <div className="region-modal-cats">
                {categories.slice(0, 9).map(c => (
                  <div key={c.id} className="region-modal-cat">
                    <span className="region-modal-cat-mark" style={{ background: c.color }} />
                    <span>{c.label.toLowerCase()}</span>
                    <span className="region-modal-cat-n">{c.count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="region-modal-foot">
          <span>esc 또는 바깥 영역을 클릭하여 닫기</span>
          <span className="region-modal-foot-link">전체 화면으로 보기 →</span>
        </div>
      </div>
    </div>
  );
}

window.RegionModal = RegionModal;
