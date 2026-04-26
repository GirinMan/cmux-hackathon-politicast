// Outline-style icons for each ontology node type.
// Each renders inside a centered group; pass `size` (final width/height) and `color`.
// All are stroke-only (hollow), 1.5 stroke width, rounded line caps.

const EOIcon = ({ kind, size = 18, color = "currentColor", strokeWidth = 1.5, opacity = 1 }) => {
  const s = size;
  const r = s / 2;
  const sw = strokeWidth;
  const props = {
    fill: "none",
    stroke: color,
    strokeWidth: sw,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    opacity,
  };

  // Each icon is drawn in a 24x24 viewBox centered, scaled to `s`
  const scale = s / 24;
  const g = (children) => (
    <g transform={`translate(${-12 * scale},${-12 * scale}) scale(${scale})`} {...props}>
      {children}
    </g>
  );

  switch (kind) {
    // 후보 — person bust inside circle
    case "Candidate":
      return g(<>
        <circle cx="12" cy="12" r="10" />
        <circle cx="12" cy="10" r="3" />
        <path d="M5.6 19c1.4-2.6 3.7-4 6.4-4s5 1.4 6.4 4" />
      </>);

    // 정당 — flag
    case "Party":
      return g(<>
        <path d="M6 3v18" />
        <path d="M6 4h11l-2.5 4 2.5 4H6" />
      </>);

    // 선거 — ballot box
    case "Election":
      return g(<>
        <rect x="3.5" y="9" width="17" height="11" rx="1.5" />
        <path d="M9 9V5.5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1V9" />
        <path d="M10 13.5h4" />
      </>);

    // 선거구 — pin with flag (winner-take-all marker)
    case "Contest":
      return g(<>
        <path d="M12 21s7-7.2 7-12a7 7 0 1 0-14 0c0 4.8 7 12 7 12z" />
        <path d="M10 8h5l-1.2 1.8L15 12h-5" />
      </>);

    // 행정구역 — map polygon
    case "District":
      return g(<>
        <path d="M3.5 6.5l5-2.2 7 2.2 5-2.2v13l-5 2.2-7-2.2-5 2.2v-13z" />
        <path d="M8.5 4.3v15" />
        <path d="M15.5 6.5v15" />
      </>);

    // 내러티브 — speech / frame
    case "NarrativeFrame":
      return g(<>
        <path d="M4 5h16v10H8l-4 4V5z" />
        <path d="M8 9.5h8" />
        <path d="M8 12h5" />
      </>);

    // 기자회견 — microphone
    case "PressConference":
      return g(<>
        <rect x="9" y="3" width="6" height="11" rx="3" />
        <path d="M5.5 11.5a6.5 6.5 0 0 0 13 0" />
        <path d="M12 18v3" />
        <path d="M9 21h6" />
      </>);

    // 여론조사 — bar chart inside frame
    case "PollPublication":
      return g(<>
        <rect x="3.5" y="3.5" width="17" height="17" rx="1.5" />
        <path d="M7.5 16.5V13" />
        <path d="M12 16.5V8.5" />
        <path d="M16.5 16.5v-5.5" />
      </>);

    // 뉴스 — newspaper
    case "News":
      return g(<>
        <path d="M3.5 5.5h13v13a1.5 1.5 0 0 0 1.5 1.5h0a1.5 1.5 0 0 0 1.5-1.5V8.5h-3" />
        <path d="M3.5 20h14.5" />
        <path d="M6.5 9h7" />
        <path d="M6.5 12h7" />
        <path d="M6.5 15h4" />
      </>);

    // 인물 — silhouette circle (different from candidate)
    case "Person":
      return g(<>
        <circle cx="12" cy="8.5" r="3.5" />
        <path d="M5 20c.8-3.6 3.6-6 7-6s6.2 2.4 7 6" />
      </>);

    default:
      return g(<circle cx="12" cy="12" r="9" />);
  }
};

window.EOIcon = EOIcon;
