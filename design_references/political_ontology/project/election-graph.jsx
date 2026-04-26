// Free-floating force-directed graph.
// - No central hub; type clusters seed initial positions but nodes float freely.
// - Velocity Verlet-ish loop: type cohesion + same-type repulsion + global repulsion + edge springs + light damping.
// - Drag any node to pin & drag; release to resume floating.

const { useMemo: useM_g, useState: useS_g, useRef: useR_g, useEffect: useE_g } = React;

function ElectionGraph({ nodes, edges, types, onSelect, selectedId, dimmedTypes }) {
  const W = 1100, H = 720;
  const cx = W / 2, cy = H / 2;

  // Refs hold the live simulation state (mutated each frame, not rendered through React).
  const stateRef = useR_g(null);
  const svgRef = useR_g(null);
  const [, setTick] = useS_g(0); // request re-render

  // Initialize once when the node set changes
  useE_g(() => {
    const visibleTypes = types.filter(t => nodes.some(n => n.type === t.id));
    const T = Math.max(1, visibleTypes.length);
    const TWO_PI = Math.PI * 2;
    const clusterR = 240;

    const typeAnchor = {};
    visibleTypes.forEach((t, i) => {
      const a = -Math.PI / 2 + (i / T) * TWO_PI;
      typeAnchor[t.id] = { x: cx + Math.cos(a) * clusterR, y: cy + Math.sin(a) * clusterR };
    });

    const sim = {};
    nodes.forEach((n) => {
      const a = typeAnchor[n.type] || { x: cx, y: cy };
      // jittered start near cluster anchor
      const jitter = 50;
      sim[n.id] = {
        x: a.x + (Math.random() - 0.5) * jitter,
        y: a.y + (Math.random() - 0.5) * jitter,
        vx: 0, vy: 0,
        pinned: false,
      };
    });

    stateRef.current = { sim, typeAnchor, visibleTypes };
    setTick(t => t + 1);
  }, [nodes, types]);

  // Physics tick
  useE_g(() => {
    let raf;
    const tick = () => {
      const st = stateRef.current;
      if (st) {
        const { sim, typeAnchor } = st;
        const ids = Object.keys(sim);

        // Reset accel
        const ax = {}, ay = {};
        ids.forEach(id => { ax[id] = 0; ay[id] = 0; });

        // 1. Anchor pull (each node lightly toward its type cluster anchor)
        nodes.forEach(n => {
          const p = sim[n.id];
          const a = typeAnchor[n.type];
          if (!p || !a) return;
          const dx = a.x - p.x, dy = a.y - p.y;
          ax[n.id] += dx * 0.0009;
          ay[n.id] += dy * 0.0009;
        });

        // 2. Pairwise repulsion (Coulomb-like). Same-type a bit stronger to avoid overlap.
        const typeOf = {};
        nodes.forEach(n => { typeOf[n.id] = n.type; });
        for (let i = 0; i < ids.length; i++) {
          for (let j = i + 1; j < ids.length; j++) {
            const a = sim[ids[i]], b = sim[ids[j]];
            let dx = a.x - b.x, dy = a.y - b.y;
            let d2 = dx * dx + dy * dy;
            if (d2 < 1) { dx = (Math.random() - 0.5); dy = (Math.random() - 0.5); d2 = 1; }
            const sameType = typeOf[ids[i]] === typeOf[ids[j]];
            const k = sameType ? 1100 : 850;
            const f = k / d2;
            const d = Math.sqrt(d2);
            ax[ids[i]] += (dx / d) * f;
            ay[ids[i]] += (dy / d) * f;
            ax[ids[j]] -= (dx / d) * f;
            ay[ids[j]] -= (dy / d) * f;
          }
        }

        // 3. Edge springs — stiffer so the web tugs as a whole
        const restLen = 130;
        edges.forEach(e => {
          const a = sim[e.from], b = sim[e.to];
          if (!a || !b) return;
          const dx = b.x - a.x, dy = b.y - a.y;
          const d = Math.max(0.1, Math.sqrt(dx * dx + dy * dy));
          const stretch = (d - restLen);
          const k = 0.06;
          const fx = (dx / d) * stretch * k;
          const fy = (dy / d) * stretch * k;
          ax[e.from] += fx; ay[e.from] += fy;
          ax[e.to]   -= fx; ay[e.to]   -= fy;
        });

        // 3b. Cursor spring — drag pulls via a spring instead of teleporting,
        //    so connected nodes feel an immediate reaction through the web.
        if (dragRef.current && dragRef.current.target) {
          const id = dragRef.current.id;
          const p = sim[id];
          const tgt = dragRef.current.target;
          if (p) {
            const dx = tgt.x - p.x, dy = tgt.y - p.y;
            const k = 0.45;
            ax[id] += dx * k;
            ay[id] += dy * k;
          }
        }

        // 4. Gentle centering force (keep cloud near canvas center)
        ids.forEach(id => {
          const p = sim[id];
          ax[id] += (cx - p.x) * 0.00015;
          ay[id] += (cy - p.y) * 0.00015;
        });

        // Integrate
        const damping = 0.82;
        ids.forEach(id => {
          const p = sim[id];
          p.vx = (p.vx + ax[id]) * damping;
          p.vy = (p.vy + ay[id]) * damping;
          // clamp velocity
          const maxV = 6;
          if (p.vx > maxV) p.vx = maxV; else if (p.vx < -maxV) p.vx = -maxV;
          if (p.vy > maxV) p.vy = maxV; else if (p.vy < -maxV) p.vy = -maxV;
          p.x += p.vx;
          p.y += p.vy;
          // soft bounds
          const m = 40;
          if (p.x < m) { p.x = m; p.vx *= -0.4; }
          if (p.x > W - m) { p.x = W - m; p.vx *= -0.4; }
          if (p.y < m) { p.y = m; p.vy *= -0.4; }
          if (p.y > H - m) { p.y = H - m; p.vy *= -0.4; }
        });

        setTick(t => (t + 1) % 1e9);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [nodes, edges]);

  // Pan / zoom
  const [view, setView] = useS_g({ x: 0, y: 0, k: 1 });
  const panRef = useR_g(null);

  // Convert client-space delta to svg-space (account for zoom & svg→pixel scale)
  const clientToSvg = (clientX, clientY) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const rect = svg.getBoundingClientRect();
    const sx = W / rect.width, sy = H / rect.height;
    const px = (clientX - rect.left) * sx;
    const py = (clientY - rect.top) * sy;
    return { x: (px - view.x) / view.k, y: (py - view.y) / view.k };
  };

  const onSvgMouseDown = (e) => {
    // background pan only — node drag handled per-node
    panRef.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y };
  };
  const onSvgMouseMove = (e) => {
    if (dragRef.current) {
      const p = clientToSvg(e.clientX, e.clientY);
      // Update spring target — physics loop pulls the node toward this point,
      // and connected nodes feel the tug through the edge springs.
      dragRef.current.target = p;
      const last = dragRef.current.lastClient;
      if (last && (Math.abs(e.clientX - last.x) + Math.abs(e.clientY - last.y) > 2)) {
        dragRef.current.moved = true;
      }
      dragRef.current.lastClient = { x: e.clientX, y: e.clientY };
      return;
    }
    if (panRef.current) {
      const dx = e.clientX - panRef.current.x;
      const dy = e.clientY - panRef.current.y;
      setView(v => ({ ...v, x: panRef.current.vx + dx, y: panRef.current.vy + dy }));
    }
  };
  const onSvgMouseUp = (e) => {
    if (dragRef.current) {
      const wasMoved = dragRef.current.moved;
      const nodeRef = dragRef.current.node;
      dragRef.current = null;
      // if no movement, treat as click-to-select
      if (!wasMoved && nodeRef) onSelect && onSelect(nodeRef);
    }
    panRef.current = null;
  };

  const dragRef = useR_g(null);
  const startNodeDrag = (e, n) => {
    e.stopPropagation();
    const st = stateRef.current;
    if (!st || !st.sim[n.id]) return;
    const p = clientToSvg(e.clientX, e.clientY);
    dragRef.current = {
      id: n.id, node: n, moved: false,
      target: { x: p.x, y: p.y },
      lastClient: { x: e.clientX, y: e.clientY },
    };
  };

  const onWheel = (e) => {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 0.92 : 1.08;
    setView(v => ({ ...v, k: Math.max(0.5, Math.min(2.4, v.k * factor)) }));
  };

  useE_g(() => {
    const el = svgRef.current;
    if (!el) return;
    const handler = (e) => onWheel(e);
    el.addEventListener("wheel", handler, { passive: false });
    return () => el.removeEventListener("wheel", handler);
  }, []);

  const zoomBy = (f) => setView(v => ({ ...v, k: Math.max(0.5, Math.min(2.4, v.k * f)) }));
  const reset = () => setView({ x: 0, y: 0, k: 1 });

  const [hover, setHover] = useS_g(null);

  const isDim = (typeId) => dimmedTypes && dimmedTypes.has(typeId);

  const st = stateRef.current;
  const getPos = (id) => (st && st.sim[id]) ? st.sim[id] : null;

  return (
    <div style={{ position: "absolute", inset: 0 }}>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="eo-graph-svg"
        preserveAspectRatio="xMidYMid meet"
        onMouseDown={onSvgMouseDown}
        onMouseMove={onSvgMouseMove}
        onMouseUp={onSvgMouseUp}
        onMouseLeave={onSvgMouseUp}
      >
        <defs>
          <pattern id="eo-grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1a2230" strokeWidth="0.5" opacity="0.5" />
          </pattern>
        </defs>

        <rect width={W} height={H} fill="url(#eo-grid)" />

        <g transform={`translate(${view.x},${view.y}) scale(${view.k})`}>
          {/* edges */}
          <g fill="none">
            {edges.map((e, i) => {
              const f = getPos(e.from), t = getPos(e.to);
              if (!f || !t) return null;
              const fromNode = nodes.find(n => n.id === e.from);
              const toNode = nodes.find(n => n.id === e.to);
              if (!fromNode || !toNode) return null;
              const dim = isDim(fromNode.type) || isDim(toNode.type);
              const isSel = selectedId && (e.from === selectedId || e.to === selectedId);
              return (
                <path key={i}
                  d={`M${f.x},${f.y} L${t.x},${t.y}`}
                  stroke={isSel ? "#7dd3c0" : "#3a4450"}
                  strokeWidth={isSel ? 1.4 : 0.9}
                  opacity={dim ? 0.06 : (isSel ? 0.85 : 0.42)}
                />
              );
            })}
          </g>

          {/* nodes */}
          <g>
            {nodes.map(n => {
              const p = getPos(n.id);
              if (!p) return null;
              const t = types.find(x => x.id === n.type);
              const dim = isDim(n.type);
              const sel = selectedId === n.id;
              const hov = hover && hover.id === n.id;
              const r = sel ? 21 : (hov ? 19 : 17);
              return (
                <g key={n.id}
                   className={`eo-node-g ${sel ? "selected" : ""} ${dim ? "dim" : ""}`}
                   transform={`translate(${p.x},${p.y})`}
                   onMouseDown={(ev) => startNodeDrag(ev, n)}
                   onMouseEnter={() => setHover(n)}
                   onMouseLeave={() => setHover(h => h && h.id === n.id ? null : h)}
                   style={{ color: t.color, cursor: "grab" }}
                >
                  <circle r={r} fill="#0a0e13" stroke={t.color}
                    strokeWidth={sel ? 1.6 : 1.1}
                    opacity={sel ? 1 : 0.85} />
                  <circle r={r - 4} fill="none" stroke={t.color}
                    strokeWidth="0.5" opacity={sel ? 0.6 : 0.35} />
                  <g className="eo-node-icon">
                    <window.EOIcon kind={n.type} size={r * 1.05} color={t.color} strokeWidth={1.4} />
                  </g>
                  <text className="eo-node-label"
                    y={r + 13}
                    textAnchor="middle"
                    fill={sel || hov ? "#e7e5dc" : "#7a8590"}
                    fontWeight={sel ? 600 : 400}
                  >
                    {n.label}
                  </text>
                </g>
              );
            })}
          </g>
        </g>
      </svg>

      {hover && (() => {
        const p = getPos(hover.id);
        if (!p) return null;
        const svg = svgRef.current;
        if (!svg) return null;
        const rect = svg.getBoundingClientRect();
        const sx = rect.width / W;
        const sy = rect.height / H;
        const px = (p.x * view.k + view.x) * sx;
        const py = (p.y * view.k + view.y) * sy;
        const t = types.find(x => x.id === hover.type);
        return (
          <div className="eo-tip" style={{ left: px, top: py }}>
            <div className="name">{hover.label}</div>
            <div className="meta">{t.label} · drag · click to inspect</div>
          </div>
        );
      })()}

      <div className="eo-graph-controls">
        <button className="eo-zoom-btn" onClick={() => zoomBy(1.15)} title="확대">+</button>
        <button className="eo-zoom-btn" onClick={() => zoomBy(0.85)} title="축소">−</button>
        <button className="eo-zoom-btn" onClick={reset} title="초기화" style={{ fontSize: 11 }}>⟲</button>
      </div>
    </div>
  );
}

window.ElectionGraph = ElectionGraph;
