// Node detail modal — hero section with portrait for people, emblem for parties,
// glyph for districts. Outline icon for everything else.

const { useEffect: useE_m, useMemo: useM_m } = React;

function ElectionModal({ node, onClose, nodes, edges, types, onJump }) {
  useE_m(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const t = types.find(x => x.id === node.type);
  const color = t ? t.color : "var(--fg-2)";

  const rels = useM_m(() => {
    const out = [];
    edges.forEach(e => {
      if (e.from === node.id) {
        const target = nodes.find(n => n.id === e.to);
        if (target) out.push({ dir: "→", node: target, predicate: e.predicate });
      } else if (e.to === node.id) {
        const target = nodes.find(n => n.id === e.from);
        if (target) out.push({ dir: "←", node: target, predicate: e.predicate });
      }
    });
    return out;
  }, [node, edges, nodes]);

  const lead = node.summary;
  const attrEntries = Object.entries(node.attrs || {});
  const isPeople = node.type === "Candidate" || node.type === "Person";
  const isParty = node.type === "Party";
  const isDistrict = node.type === "District";
  const hasHeroVisual = isPeople || isParty || isDistrict;

  const renderHero = () => {
    if (node.photo) {
      return (
        <img src={node.photo} alt={node.label}
          style={{ width: 140, height: 140, borderRadius: "50%", objectFit: "cover",
                   border: `1px solid ${color}`, boxShadow: `0 0 0 3px rgba(0,0,0,0.4)` }} />
      );
    }
    if (isPeople) {
      return <window.PersonPortrait
        name={node.label}
        gender={node.attrs?.gender}
        age={node.attrs?.age}
        size={140} />;
    }
    if (isParty) {
      return <window.PartyEmblem name={node.label} color={node.attrs?.color || color} size={140} />;
    }
    if (isDistrict) {
      return <window.DistrictGlyph name={node.label} color={color} size={140} />;
    }
    return null;
  };

  return (
    <div className="eo-modal-bd" onClick={onClose}>
      <div className="eo-modal" onClick={e => e.stopPropagation()}>

        {/* Hero band */}
        <div className="eo-hero" style={{
          background: `linear-gradient(135deg, color-mix(in oklab, ${color} 18%, transparent) 0%, transparent 60%), var(--bg-1)`,
          borderBottom: `1px solid var(--line)`,
        }}>
          <button className="eo-modal-close eo-hero-close" onClick={onClose}>×</button>

          {hasHeroVisual ? (
            <div className="eo-hero-grid">
              <div className="eo-hero-portrait" style={{ boxShadow: `0 0 0 1px ${color}33, 0 14px 34px rgba(0,0,0,0.45)` }}>
                {renderHero()}
              </div>
              <div className="eo-hero-info">
                <span className="eo-modal-eyebrow"
                  style={{ color, background: `color-mix(in oklab, ${color} 12%, transparent)`,
                           border: `1px solid color-mix(in oklab, ${color} 30%, transparent)` }}>
                  <window.EOIcon kind={node.type} size={11} color={color} strokeWidth={1.6} />
                  <span>{t ? t.label : node.type}</span>
                </span>
                <div className="eo-hero-title">{node.label}</div>
                {(() => {
                  const items = [];
                  if (isPeople) {
                    if (node.attrs?.party) items.push(node.attrs.party);
                    if (node.attrs?.role) items.push(node.attrs.role);
                    if (node.attrs?.career) items.push(node.attrs.career);
                    if (node.attrs?.affiliation) items.push(node.attrs.affiliation);
                    if (node.attrs?.age) items.push(`${node.attrs.age}세`);
                  } else if (isParty) {
                    if (node.attrs?.ideology) items.push(node.attrs.ideology);
                    if (node.attrs?.seats_assembly) items.push(`의석 ${node.attrs.seats_assembly}석`);
                    if (node.attrs?.founded) items.push(`창당 ${node.attrs.founded}`);
                  } else if (isDistrict) {
                    if (node.attrs?.code) items.push(`코드 ${node.attrs.code}`);
                    if (node.attrs?.population) items.push(`인구 ${node.attrs.population}`);
                    if (node.attrs?.households) items.push(`세대 ${node.attrs.households}`);
                  }
                  if (!items.length) return null;
                  return (
                    <div className="eo-hero-meta">
                      {items.map((it, i) => (
                        <React.Fragment key={i}>
                          {i > 0 && <span className="sep">·</span>}
                          <span>{it}</span>
                        </React.Fragment>
                      ))}
                    </div>
                  );
                })()}
                <div className="eo-hero-id">{node.id}</div>
                {isPeople && node.attrs?.slogan && (
                  <div className="eo-hero-slogan" style={{ borderColor: color }}>
                    "{node.attrs.slogan}"
                  </div>
                )}
                {isPeople && node.attrs?.poll_avg && (
                  <div className="eo-hero-poll">
                    <span className="lbl">현재 지지율</span>
                    <span className="val" style={{ color }}>{node.attrs.poll_avg}</span>
                  </div>
                )}
              </div>
            </div>
          ) : (
            // Compact head for non-people types
            <div className="eo-modal-head" style={{ borderBottom: 0, paddingTop: 22 }}>
              <div className="eo-modal-icon" style={{ color, background: `color-mix(in oklab, ${color} 8%, var(--bg-2))`, borderColor: `color-mix(in oklab, ${color} 35%, var(--line-2))` }}>
                <svg width="32" height="32" viewBox="-16 -16 32 32">
                  <window.EOIcon kind={node.type} size={28} color={color} strokeWidth={1.5} />
                </svg>
              </div>
              <div className="eo-modal-titles">
                <span className="eo-modal-eyebrow"
                  style={{ color, background: `color-mix(in oklab, ${color} 12%, transparent)`,
                           border: `1px solid color-mix(in oklab, ${color} 30%, transparent)` }}>
                  <window.EOIcon kind={node.type} size={11} color={color} strokeWidth={1.6} />
                  <span>{t ? t.label : node.type}</span>
                </span>
                <div className="eo-modal-title">
                  <span>{node.label}</span>
                  <span className="eo-modal-id">{node.id}</span>
                </div>
                <div className="eo-modal-sub">{lead}</div>
              </div>
            </div>
          )}
        </div>

        <div className="eo-modal-body">
          <div>
            <div className="eo-modal-section">
              <div className="eo-modal-section-h">속성 / Attributes</div>
              <div className="eo-attrs">
                {attrEntries.length === 0 && (
                  <div className="eo-empty">기록된 속성이 없습니다.</div>
                )}
                {attrEntries.map(([k, v]) => (
                  <div key={k} className="eo-attr-row">
                    <div className="k">{k}</div>
                    <div className="v"><span className="mono">{String(v)}</span></div>
                  </div>
                ))}
              </div>
            </div>

            <div className="eo-modal-section">
              <div className="eo-modal-section-h">메타 / Provenance</div>
              <div className="eo-attrs">
                <div className="eo-attr-row">
                  <div className="k">node_id</div>
                  <div className="v"><span className="mono">{node.id}</span></div>
                </div>
                <div className="eo-attr-row">
                  <div className="k">type</div>
                  <div className="v"><span className="mono" style={{ color }}>{node.type}</span></div>
                </div>
                <div className="eo-attr-row">
                  <div className="k">snapshot</div>
                  <div className="v"><span className="mono">kg_seoul_mayor_t3.json</span></div>
                </div>
                <div className="eo-attr-row">
                  <div className="k">cutoff</div>
                  <div className="v"><span className="mono">2026-06-03T00:00:00</span></div>
                </div>
              </div>
            </div>
          </div>

          <div>
            <div className="eo-modal-section">
              <div className="eo-modal-section-h">요약 / Summary</div>
              <blockquote className="eo-quote" style={{ borderLeftColor: color }}>
                {lead}
              </blockquote>
            </div>

            <div className="eo-modal-section">
              <div className="eo-modal-section-h">관계 / Relations · {rels.length}</div>
              <div className="eo-rels">
                {rels.length === 0 && (
                  <div className="eo-empty">연결된 노드가 없습니다.</div>
                )}
                {rels.map((r, i) => {
                  const rt = types.find(x => x.id === r.node.type);
                  return (
                    <div key={i} className="eo-rel" onClick={() => onJump && onJump(r.node)}>
                      <div className="ic">
                        <svg width="20" height="20" viewBox="-10 -10 20 20">
                          <window.EOIcon kind={r.node.type} size={16}
                            color={rt ? rt.color : "var(--fg-2)"} strokeWidth={1.4} />
                        </svg>
                      </div>
                      <div>
                        <div className="lbl">{r.node.label}</div>
                        <div className="pred">{r.dir} {r.predicate} · {rt ? rt.label : r.node.type}</div>
                      </div>
                      <div style={{
                        fontFamily: "var(--font-mono)", fontSize: 10,
                        color: "var(--fg-3)", letterSpacing: "0.06em"
                      }}>OPEN ›</div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="eo-modal-section">
              <div className="eo-modal-section-h">태그</div>
              <div className="eo-tags">
                <span className="eo-tag">snapshot:t3</span>
                <span className="eo-tag">region:seoul_mayor</span>
                <span className="eo-tag">type:{node.type}</span>
                <span className="eo-tag">{rels.length} edges</span>
              </div>
            </div>
          </div>
        </div>

        <div className="eo-modal-foot">
          <span>esc — 닫기 · click backdrop — 닫기</span>
          <span className="eo-foot-id">{node.id}</span>
        </div>
      </div>
    </div>
  );
}

window.ElectionModal = ElectionModal;
