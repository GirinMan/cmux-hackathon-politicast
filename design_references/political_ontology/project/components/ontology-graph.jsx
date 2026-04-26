// 방사형 온톨로지 그래프 — outline + 새 심볼 시스템
const { useMemo: useMemoOG } = React;

function OntologyGraph({ regionFilter, signatures, categories, members, dimensions = 9, minWeight = 1 }) {
  const W = 900, H = 660;
  const cx = W / 2, cy = H / 2;

  const { nodes, edges, hubLabel } = useMemoOG(() => {
    const sig = signatures[regionFilter] || null;
    const dominantSet = new Set(sig?.dominant || []);
    const weightFor = (m) => dominantSet.has(m) ? 0.88 + Math.random() * 0.12 : 0.32 + Math.random() * 0.42;

    const visibleCats = categories.slice(0, dimensions);
    const N = visibleCats.length;
    const TWO_PI = Math.PI * 2;
    const allNodes = [];

    visibleCats.forEach((cat, idx) => {
      const baseAngle = -Math.PI / 2 + (idx / N) * TWO_PI;
      let radius = 220;
      if (cat.id === "region" || cat.id === "province") radius = 280;
      else if (cat.id === "district") radius = 250;
      else if (cat.id === "sex") radius = 130;
      const sweep = (TWO_PI / N) * 0.78;
      const ms = members[cat.id] || Array(cat.count).fill(0).map((_, i) => `${cat.label}-${i + 1}`);
      const adjSweep = ms.length <= 2 ? sweep * 0.3 : sweep;
      const startA = baseAngle - adjSweep / 2;

      ms.forEach((m, i) => {
        const t = ms.length === 1 ? 0.5 : i / (ms.length - 1);
        const a = startA + adjSweep * t;
        const w = weightFor(m);
        allNodes.push({
          id: `${cat.id}:${m}`, label: m, cat,
          x: cx + Math.cos(a) * radius,
          y: cy + Math.sin(a) * radius,
          angle: a, weight: w,
          size: 9 + w * 11,
        });
      });
    });

    const wT = 0.3 + (minWeight - 1) / 12 * 0.6;
    const visible = allNodes.filter(n => n.weight >= wT);
    const eds = visible.map(n => ({
      from: { x: cx, y: cy }, to: n,
      weight: n.weight, color: n.cat.color,
    }));

    const lbl = regionFilter === "all" ? "All Personas" : (window.KR_REGIONS.find(r => r.id === regionFilter)?.name || regionFilter);
    return { nodes: visible, edges: eds, hubLabel: lbl };
  }, [regionFilter, signatures, categories, members, dimensions, minWeight]);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "100%", display: "block" }}>
      <defs>
        <radialGradient id="hub-glow-og" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#7dd3c0" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#7dd3c0" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* 동심원 가이드 */}
      <g opacity="0.07" fill="none" stroke="#7dd3c0">
        <circle cx={cx} cy={cy} r={130} strokeDasharray="2 4" />
        <circle cx={cx} cy={cy} r={200} strokeDasharray="2 4" />
        <circle cx={cx} cy={cy} r={250} />
        <circle cx={cx} cy={cy} r={280} strokeDasharray="2 4" />
      </g>

      {/* 카테고리 섹터 라벨 */}
      {categories.slice(0, dimensions).map((cat, idx) => {
        const N = categories.slice(0, dimensions).length;
        const a = -Math.PI / 2 + (idx / N) * Math.PI * 2;
        const r = 320;
        const lx = cx + Math.cos(a) * r, ly = cy + Math.sin(a) * r;
        return (
          <text key={cat.id} x={lx} y={ly} fontSize="9.5" fontFamily="ui-monospace, monospace"
            textAnchor="middle" fill={cat.color} opacity="0.75" letterSpacing="0.1em" fontWeight="500">
            {cat.label.toUpperCase()}
          </text>
        );
      })}

      <circle cx={cx} cy={cy} r="80" fill="url(#hub-glow-og)" />

      {/* 엣지 */}
      <g fill="none">
        {edges.map((e, i) => {
          const mx = (e.from.x + e.to.x) / 2;
          const my = (e.from.y + e.to.y) / 2;
          return (
            <path key={i}
              d={`M${e.from.x},${e.from.y} Q${mx},${my} ${e.to.x},${e.to.y}`}
              stroke={e.color}
              strokeWidth={0.4 + e.weight * 1.2}
              opacity={0.18 + e.weight * 0.32}
            />
          );
        })}
      </g>

      {/* 노드 */}
      <g fontFamily="-apple-system, system-ui, sans-serif">
        {nodes.map(n => (
          <g key={n.id} transform={`translate(${n.x},${n.y})`}>
            <window.NodeSymbol shape={n.cat.shape} size={n.size} color={n.cat.color} />
            {n.weight > 0.55 && (() => {
              const d = n.size / 2 + 8;
              const lx = Math.cos(n.angle) * d;
              const ly = Math.sin(n.angle) * d;
              const anchor = Math.cos(n.angle) > 0.3 ? "start" : Math.cos(n.angle) < -0.3 ? "end" : "middle";
              return (
                <text x={lx} y={ly + 3} fontSize="9.5" fill="#a5adb6" textAnchor={anchor}
                  style={{ pointerEvents: "none" }}>{n.label}</text>
              );
            })()}
          </g>
        ))}
      </g>

      {/* 허브 */}
      <g transform={`translate(${cx},${cy})`}>
        <circle r="28" fill="#0a0e13" stroke="#7dd3c0" strokeWidth="1.2" />
        <circle r="22" fill="none" stroke="#7dd3c0" strokeWidth="0.5" opacity="0.45" />
        <circle r="3" fill="#7dd3c0" />
        <text textAnchor="middle" y="48" fontSize="11" fill="#e7e5dc" fontWeight="600">
          {hubLabel}
        </text>
      </g>
    </svg>
  );
}

window.OntologyGraph = OntologyGraph;
