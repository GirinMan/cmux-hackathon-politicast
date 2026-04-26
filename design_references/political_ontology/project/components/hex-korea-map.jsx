// Hex grid 한국 지도 + 모달 트리거
const { useMemo: useMHex, useState: useSHex } = React;

function HexKoreaMap({ regions, signatures, categories, members, selected, onSelect, hovered, onHover, density }) {
  const W = 1180, H = 760;
  const SIZE = 36;
  const HEX = window.KR_HEX;
  const JEJU_GAP = 28; // 본토 아래 제주까지 간격

  // 중앙 정렬 위해 bbox 계산
  const positioned = useMHex(() => {
    const pts = HEX.map(h => {
      const p = window.hexToPixel(h.q, h.r, SIZE);
      return { ...h, x: p.x, y: p.y + (h.gap ? JEJU_GAP : 0) };
    });
    const xs = pts.map(p => p.x), ys = pts.map(p => p.y);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const w = maxX - minX, h = maxY - minY;
    const ox = (W - w) / 2 - minX;
    const oy = (H - h) / 2 - minY;
    return pts.map(p => ({ ...p, x: p.x + ox, y: p.y + oy }));
  }, []);

  // 시·도 단위로 그룹핑 — 클릭/호버 강조용
  const byParent = useMHex(() => {
    const m = {};
    positioned.forEach(p => {
      if (!m[p.parent]) m[p.parent] = [];
      m[p.parent].push(p);
    });
    return m;
  }, [positioned]);

  // 시·도 중심 (라벨 위치)
  const provinceCenters = useMHex(() => {
    const out = {};
    Object.entries(byParent).forEach(([pid, cells]) => {
      const cx = cells.reduce((s,c) => s + c.x, 0) / cells.length;
      const cy = cells.reduce((s,c) => s + c.y, 0) / cells.length;
      out[pid] = { cx, cy };
    });
    return out;
  }, [byParent]);

  const colorFor = (parent) => {
    const r = regions.find(x => x.id === parent);
    if (!r) return "#1f2630";
    if (r.type === "metro") return "#2a3e3a";  // 광역시: 민트 톤
    return "#1d2630";                           // 도: 슬레이트
  };

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "100%", display: "block" }}>
      <defs>
        <radialGradient id="hex-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#7dd3c0" stopOpacity="0.18" />
          <stop offset="100%" stopColor="#7dd3c0" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* 클러스터 라벨 (수도권/관동/충청/영남/호남/제주) */}
      <g fontFamily="ui-monospace, monospace" fontSize="9.5" fill="#3a4450" letterSpacing="0.18em">
        <text x="60" y="80">SUDOGWON · 수도권</text>
        <text x="60" y="220">CHUNGCHEONG · 충청</text>
        <text x="60" y="380">HONAM · 호남</text>
        <text x={W - 60} y="80" textAnchor="end">GANGWON · 관동</text>
        <text x={W - 60} y="280" textAnchor="end">YEONGNAM · 영남</text>
        <text x={W - 60} y="640" textAnchor="end">JEJU · 제주</text>
      </g>

      {/* hex 셀 */}
      <g>
        {positioned.map(cell => {
          const isSelected = selected === cell.parent;
          const isHovered  = hovered === cell.parent;
          const region = regions.find(r => r.id === cell.parent);
          const fill = colorFor(cell.parent);
          const stroke = isSelected ? "#7dd3c0" : isHovered ? "#a5adb6" : "#2a3038";
          const strokeWidth = isSelected ? 1.6 : isHovered ? 1.1 : 0.8;
          const opacity = (selected && !isSelected) ? 0.42 : 1;
          const corners = window.hexCorners(cell.x, cell.y, SIZE - 2);
          const points = corners.map(([x,y]) => `${x},${y}`).join(" ");

          // 광역시 표시: 내부 작은 사각형 마커
          const isMetro = region?.type === "metro";

          return (
            <g key={cell.id}
               onClick={() => onSelect(cell.parent)}
               onMouseEnter={() => onHover(cell.parent)}
               onMouseLeave={() => onHover(null)}
               style={{ cursor: "pointer", opacity, transition: "opacity 200ms" }}>
              <polygon points={points} fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
              {isMetro && cell.solo && (
                <rect x={cell.x - 4} y={cell.y - 4} width="8" height="8"
                      fill={isSelected ? "#7dd3c0" : "#5fb3a3"} opacity="0.65" />
              )}
              {!isMetro && (
                <circle cx={cell.x} cy={cell.y} r="2" fill="#5b6470" opacity="0.6" />
              )}
            </g>
          );
        })}
      </g>

      {/* 시·도 라벨 (중심부) */}
      <g fontFamily="-apple-system, system-ui, sans-serif" pointerEvents="none">
        {Object.entries(provinceCenters).map(([pid, c]) => {
          const r = regions.find(x => x.id === pid);
          if (!r) return null;
          const isSel = selected === pid;
          return (
            <g key={pid} transform={`translate(${c.cx},${c.cy})`}>
              <text textAnchor="middle" fontSize={isSel ? 13 : 11} fontWeight={isSel ? 600 : 500}
                    fill={isSel ? "#e7e5dc" : "#a5adb6"} y="-2">
                {r.name}
              </text>
              <text textAnchor="middle" fontSize="8.5" fill="#5b6470" y="11"
                    fontFamily="ui-monospace, monospace" letterSpacing="0.05em">
                {(r.pop / 1000).toFixed(1)}M
              </text>
            </g>
          );
        })}
      </g>

      {/* 안내 */}
      <text x={W/2} y={H - 24} textAnchor="middle" fontSize="10.5" fill="#5b6470"
            fontFamily="ui-monospace, monospace" letterSpacing="0.12em">
        시·도를 클릭하면 해당 지역의 방사형 온톨로지가 모달로 열립니다
      </text>
    </svg>
  );
}

window.HexKoreaMap = HexKoreaMap;
