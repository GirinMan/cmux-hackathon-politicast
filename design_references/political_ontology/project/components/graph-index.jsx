// Graph Index 사이드 패널

const GraphIndexPanel = ({ categories, topNodes, regionFilter, regionName }) => {
  const totalNodes = categories.reduce((s, c) => s + c.count, 0);

  return (
    <div className="gi-panel">
      <div className="gi-section">
        <div className="gi-title">Graph Index</div>
        <div className="gi-sub">node categories · {totalNodes} total</div>
        <div className="gi-cats">
          {categories.map(c => (
            <div key={c.id} className="gi-cat">
              <span className="gi-cat-dot" style={{ background: c.color }} />
              <span className="gi-cat-label">{c.label}</span>
              <span className="gi-cat-count">{c.count}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="gi-divider" />

      <div className="gi-section">
        <div className="gi-title">Top nodes</div>
        <div className="gi-sub">
          {regionFilter === "all" ? "across all personas" : `in ${regionName}`}
        </div>
        <div className="gi-tops">
          {topNodes.map((n, i) => {
            const cat = categories.find(c => c.id === n.category);
            return (
              <div key={i} className="gi-top">
                <div className="gi-top-row">
                  <span className="gi-top-label">{n.label}</span>
                  <span className="gi-top-pct">{n.pct.toFixed(1)}%</span>
                </div>
                <div className="gi-top-bar">
                  <div
                    className="gi-top-fill"
                    style={{
                      width: `${n.pct}%`,
                      background: cat?.color || "#7dd3c0",
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

window.GraphIndexPanel = GraphIndexPanel;
