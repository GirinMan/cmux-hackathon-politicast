// 실제 한국 지도 형상 위에 온톨로지 오버레이
// 시·도 폴리곤이 본토 윤곽을 채우도록 viewBox + transform 조정

const { useMemo: useMmGM } = React;

function GeoMapOverlay({ regions, signatures, categories, members, selected, onSelect, hovered, onHover, density = "normal", expandedRegion = null }) {
  const W = 1180, H = 760;
  const mapPaths = window.KR_MAP_PATHS;

  // 지도를 캔버스 중앙쪽에 + 적절한 크기
  const mapTransform = "translate(360, 30) scale(1.0)";

  const cap = density === "low" ? 2 : density === "high" ? 5 : 3;

  const buildSatellites = (regionId, cx, cy, baseR) => {
    const sig = signatures[regionId];
    const dom = sig?.dominant || [];
    const sats = [];
    const n = Math.min(cap, dom.length);
    dom.slice(0, n).forEach((memberLabel, i) => {
      let cat = null;
      for (const c of categories) {
        const ms = members[c.id];
        if (ms && ms.includes(memberLabel)) { cat = c; break; }
      }
      if (!cat) return;
      const angle = -Math.PI / 2 + (i / Math.max(1, n)) * Math.PI * 2;
      sats.push({
        id: `${regionId}-${cat.id}-${i}`,
        x: cx + Math.cos(angle) * baseR,
        y: cy + Math.sin(angle) * baseR,
        cat, label: memberLabel, angle,
      });
    });
    return sats;
  };

  const maxPop = Math.max(...regions.map(r => r.pop));
  const popScale = (pop) => Math.sqrt(pop / maxPop);

  // 확장된 방사형 뷰
  const RadialDetail = ({ region }) => {
    const sig = signatures[region.id];
    const path = mapPaths.regions[region.id];
    if (!path) return null;
    const cx = path.cx, cy = path.cy;
    const detailR = 145;

    const allNodes = categories.map((cat, idx) => {
      const angle = -Math.PI / 2 + (idx / categories.length) * Math.PI * 2;
      const ms = members[cat.id] || [`${cat.label}-1`];
      const dom = sig?.dominant || [];
      const rep = ms.find(m => dom.includes(m)) || ms[0];
      return {
        cat, label: rep,
        x: cx + Math.cos(angle) * detailR,
        y: cy + Math.sin(angle) * detailR,
        angle,
      };
    });

    return (
      <g>
        <circle cx={cx} cy={cy} r={detailR + 30} fill="rgba(125,211,192,0.05)" />
        <circle cx={cx} cy={cy} r={detailR} fill="none" stroke="rgba(125,211,192,0.35)" strokeWidth="0.6" strokeDasharray="2 4" />
        <circle cx={cx} cy={cy} r={detailR * 0.6} fill="none" stroke="rgba(125,211,192,0.2)" strokeWidth="0.5" strokeDasharray="2 4" />

        {allNodes.map((n, i) => (
          <line key={i} x1={cx} y1={cy} x2={n.x} y2={n.y} stroke={n.cat.color} strokeWidth="0.9" opacity="0.6" />
        ))}

        {allNodes.map((n, i) => (
          <g key={`n-${i}`} transform={`translate(${n.x},${n.y})`}>
            <window.NodeSymbol shape={n.cat.shape} size={20} color={n.cat.color} />
            {(() => {
              const lx = Math.cos(n.angle) * 22;
              const ly = Math.sin(n.angle) * 22;
              const anchor = Math.cos(n.angle) > 0.3 ? "start" : Math.cos(n.angle) < -0.3 ? "end" : "middle";
              return (
                <text x={lx} y={ly + 3} fontSize="10" fill="#c0c8d0" textAnchor={anchor} style={{ pointerEvents: "none" }}>
                  {n.label}
                </text>
              );
            })()}
          </g>
        ))}

        <circle cx={cx} cy={cy} r="24" fill="#0a0e13" stroke="#7dd3c0" strokeWidth="1.4" />
        <circle cx={cx} cy={cy} r="19" fill="none" stroke="#7dd3c0" strokeWidth="0.5" opacity="0.5" />
        <text x={cx} y={cy + 3} textAnchor="middle" fontSize="11" fill="#e7e5dc" fontWeight="600" style={{ pointerEvents: "none" }}>
          {region.name}
        </text>
      </g>
    );
  };

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "100%", display: "block" }}>
      <defs>
        <pattern id="bg-dots-g" width="18" height="18" patternUnits="userSpaceOnUse">
          <circle cx="9" cy="9" r="0.4" fill="#1a2230" />
        </pattern>
        <pattern id="map-hatch-g" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="5" stroke="#1f2832" strokeWidth="0.4" />
        </pattern>
        <radialGradient id="region-glow-g" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#7dd3c0" stopOpacity="0.22" />
          <stop offset="100%" stopColor="#7dd3c0" stopOpacity="0" />
        </radialGradient>
      </defs>

      <rect x="0" y="0" width={W} height={H} fill="url(#bg-dots-g)" />

      {/* 좌표 라벨 */}
      <g fontFamily="ui-monospace, monospace" fontSize="9" fill="#2e3845" letterSpacing="0.1em">
        <text x="40" y="40">38°N ─</text>
        <text x="40" y="180">37°N ─</text>
        <text x="40" y="320">36°N ─</text>
        <text x="40" y="460">35°N ─</text>
        <text x="40" y="600">34°N ─</text>
        <text x="40" y="700">33°N ─</text>
        <text x="40" y="730" fill="#3a4452">REPUBLIC OF KOREA</text>
        <text x="40" y="745" fill="#3a4452">17 SIDO · 9 ONTOLOGY DIMS</text>
      </g>

      <g transform={mapTransform}>
        {/* 본토 outline + 해치 */}
        <path d={mapPaths.outline} fill="url(#map-hatch-g)" stroke="#3a4452" strokeWidth="1" opacity="0.55" strokeLinejoin="round" />
        {/* DMZ 점선 */}
        <path d={mapPaths.dmz} fill="none" stroke="#5a6470" strokeWidth="0.8" strokeDasharray="3 4" opacity="0.5" />

        {/* 시·도 영역 */}
        {regions.map(r => {
          const path = mapPaths.regions[r.id];
          if (!path) return null;
          const isSel = selected === r.id;
          const isHov = hovered === r.id;
          const isExp = expandedRegion === r.id;
          const dim = (selected || expandedRegion) && !isSel && !isExp;

          return (
            <g key={r.id} opacity={dim ? 0.32 : 1} style={{ transition: "opacity 250ms" }}>
              {(isSel || isExp) && (
                <circle cx={path.cx} cy={path.cy} r={isExp ? 175 : 60} fill="url(#region-glow-g)" />
              )}
              <path
                d={path.d}
                fill={isSel || isExp ? "rgba(125,211,192,0.09)" : isHov ? "rgba(232,229,220,0.05)" : "rgba(232,229,220,0.018)"}
                stroke={isSel || isExp ? "#7dd3c0" : isHov ? "#8a96a8" : "#3a4452"}
                strokeWidth={isSel || isExp ? 1.4 : isHov ? 1 : 0.7}
                strokeLinejoin="round"
                style={{ cursor: "pointer", transition: "all 200ms" }}
                onClick={() => onSelect && onSelect(r.id)}
                onMouseEnter={() => onHover && onHover(r.id)}
                onMouseLeave={() => onHover && onHover(null)}
              />
            </g>
          );
        })}

        {/* 위성 노드 (확장되지 않은 지역) */}
        {regions.map(r => {
          const path = mapPaths.regions[r.id];
          if (!path) return null;
          const isExp = expandedRegion === r.id;
          if (isExp) return null;
          const dim = (selected || expandedRegion) && selected !== r.id;
          if (dim) return null;

          const pSize = popScale(r.pop);
          const baseR = 22 + pSize * 16;
          const sats = buildSatellites(r.id, path.cx, path.cy, baseR);

          return (
            <g key={`sat-${r.id}`} style={{ pointerEvents: "none" }}>
              {sats.map(s => (
                <line key={`l-${s.id}`} x1={path.cx} y1={path.cy} x2={s.x} y2={s.y}
                  stroke={s.cat.color} strokeWidth="0.55" opacity="0.5" />
              ))}
              {sats.map(s => (
                <g key={s.id} transform={`translate(${s.x},${s.y})`}>
                  <window.NodeSymbol shape={s.cat.shape} size={9 + pSize * 4} color={s.cat.color} />
                </g>
              ))}
            </g>
          );
        })}

        {/* 시·도 허브 */}
        {regions.map(r => {
          const path = mapPaths.regions[r.id];
          if (!path) return null;
          const isExp = expandedRegion === r.id;
          if (isExp) return null;
          const isSel = selected === r.id;
          const isHov = hovered === r.id;

          return (
            <g key={`hub-${r.id}`}
               style={{ cursor: "pointer" }}
               onClick={() => onSelect && onSelect(r.id)}
               onMouseEnter={() => onHover && onHover(r.id)}
               onMouseLeave={() => onHover && onHover(null)}>
              {r.type === "metro" ? (
                <rect
                  x={path.cx - 6} y={path.cy - 6}
                  width="12" height="12"
                  rx="1.5"
                  fill={isSel ? "#7dd3c0" : "#0a0e13"}
                  stroke={isSel ? "#7dd3c0" : isHov ? "#e7e5dc" : "#9aa5a8"}
                  strokeWidth="1.2"
                />
              ) : (
                <circle
                  cx={path.cx} cy={path.cy} r="5"
                  fill={isSel ? "#7dd3c0" : "#0a0e13"}
                  stroke={isSel ? "#7dd3c0" : isHov ? "#e7e5dc" : "#9aa5a8"}
                  strokeWidth="1.2"
                />
              )}
              <text
                x={path.cx} y={path.cy - 11}
                textAnchor="middle"
                fontSize={isSel || isHov ? 11 : 10}
                fontWeight={isSel ? 600 : 500}
                fill={isSel ? "#7dd3c0" : isHov ? "#e7e5dc" : "#a5adb6"}
                style={{ pointerEvents: "none", letterSpacing: "0.02em" }}
                fontFamily="-apple-system, system-ui, sans-serif">
                {r.name}
              </text>
              {(isHov || isSel) && (
                <text x={path.cx} y={path.cy + 18} textAnchor="middle"
                  fontSize="9" fill="#6b7480"
                  fontFamily="ui-monospace, monospace"
                  style={{ pointerEvents: "none", letterSpacing: "0.04em" }}>
                  {(r.pop / 1000).toFixed(2)}M
                </text>
              )}
            </g>
          );
        })}

        {/* 확장된 지역 방사형 디테일 */}
        {expandedRegion && (() => {
          const r = regions.find(x => x.id === expandedRegion);
          return r ? <RadialDetail region={r} /> : null;
        })()}
      </g>

      {/* 우측 클러스터 라벨 */}
      <g fontFamily="-apple-system, system-ui, sans-serif" fontSize="10" fill="#3e4858" letterSpacing="0.18em" fontWeight="500">
        <text x="900" y="160">SUDOGWON · 수도권</text>
        <text x="900" y="220">GANGWON · 관동</text>
        <text x="900" y="320">CHUNGCHEONG · 충청</text>
        <text x="900" y="400">YEONGNAM · 영남</text>
        <text x="900" y="480">HONAM · 호남</text>
        <text x="900" y="690">JEJU · 제주</text>
      </g>

      {/* 안내 */}
      {!expandedRegion && (
        <g fontFamily="-apple-system, system-ui, sans-serif" fontSize="10" fill="#6b7480">
          <text x={W - 40} y={H - 20} textAnchor="end">시·도를 클릭하면 해당 지역의 방사형 온톨로지가 펼쳐집니다.</text>
        </g>
      )}
      {expandedRegion && (
        <g fontFamily="-apple-system, system-ui, sans-serif" fontSize="10" fill="#7dd3c0"
           style={{ cursor: "pointer" }}
           onClick={() => onSelect && onSelect("all")}>
          <text x={W - 40} y={H - 20} textAnchor="end">← 전체 지도로 돌아가기</text>
        </g>
      )}
    </svg>
  );
}

window.GeoMapOverlay = GeoMapOverlay;
