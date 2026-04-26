// Portraits & visual decorations for modal hero.
// Person/Candidate: deterministic SVG avatar built from initials + attribute hash
// Party: simple emblem with party color
// District: minimap silhouette
// (Stylized — no real photos used.)

const eoHash = (s) => {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0;
  return Math.abs(h);
};

const PORTRAIT_PALETTES = [
  { bg: "#2a3340", skin: "#e8c39e", hair: "#1f2832", accent: "#7dd3c0" },
  { bg: "#2d2733", skin: "#d8a86b", hair: "#0f0a14", accent: "#c87f9e" },
  { bg: "#1f3340", skin: "#e6b08a", hair: "#1a1410", accent: "#6fc4d9" },
  { bg: "#33282a", skin: "#dca48a", hair: "#2a1410", accent: "#f0a868" },
  { bg: "#283328", skin: "#dcb898", hair: "#1a1f10", accent: "#9bd06a" },
  { bg: "#2a2840", skin: "#e8c8a8", hair: "#101428", accent: "#b48cd9" },
];

function PersonPortrait({ name, gender, age, size = 140 }) {
  const seed = eoHash(name || "person");
  const pal = PORTRAIT_PALETTES[seed % PORTRAIT_PALETTES.length];
  const female = gender === "여" || (seed % 2 === 1 && gender !== "남");
  const initial = (name || "?").trim().charAt(0);
  const senior = (age || 0) >= 55;

  const id = `pp-${seed}`;
  const hairLen = female ? 1 : 0; // 0=short, 1=longer

  return (
    <svg width={size} height={size} viewBox="0 0 120 120" style={{ display: "block" }}>
      <defs>
        <clipPath id={`clip-${id}`}><circle cx="60" cy="60" r="58" /></clipPath>
        <linearGradient id={`bg-${id}`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={pal.bg} stopOpacity="1" />
          <stop offset="100%" stopColor="#0a0e13" stopOpacity="1" />
        </linearGradient>
      </defs>

      <circle cx="60" cy="60" r="58" fill={`url(#bg-${id})`} stroke="#2a3340" strokeWidth="1" />

      <g clipPath={`url(#clip-${id})`}>
        {/* shoulders */}
        <path d={`M 8 120 Q 30 ${senior ? 92 : 88} 60 ${senior ? 90 : 86} Q 90 ${senior ? 92 : 88} 112 120 Z`}
              fill={pal.accent} opacity="0.18" />
        <path d={`M 14 120 Q 32 ${senior ? 96 : 92} 60 ${senior ? 94 : 90} Q 88 ${senior ? 96 : 92} 106 120 Z`}
              fill={pal.accent} opacity="0.32" />

        {/* neck */}
        <rect x="52" y="78" width="16" height="14" rx="3" fill={pal.skin} />

        {/* face */}
        <ellipse cx="60" cy="58" rx="22" ry="26" fill={pal.skin} />

        {/* hair */}
        {hairLen === 1 ? (
          <path d={`M 35 56 Q 32 30 60 28 Q 88 30 85 56 L 84 78 L 78 70 Q 76 48 60 48 Q 44 48 42 70 L 36 78 Z`}
                fill={pal.hair} />
        ) : (
          <path d={`M 38 50 Q 36 28 60 28 Q 84 28 82 50 Q 78 42 60 42 Q 42 42 38 50 Z`}
                fill={pal.hair} />
        )}

        {/* eyes */}
        <circle cx="51" cy="58" r="1.6" fill="#0a0e13" />
        <circle cx="69" cy="58" r="1.6" fill="#0a0e13" />
        {/* brows */}
        <path d="M 47 53 L 55 52" stroke="#0a0e13" strokeWidth="1.4" strokeLinecap="round" fill="none" />
        <path d="M 65 52 L 73 53" stroke="#0a0e13" strokeWidth="1.4" strokeLinecap="round" fill="none" />
        {/* nose */}
        <path d="M 60 60 L 58 67 L 61 68" stroke={pal.skin} strokeWidth="1" fill="none"
              opacity="0.6" />
        {/* mouth */}
        <path d="M 55 73 Q 60 76 65 73" stroke="#0a0e13" strokeWidth="1.2" fill="none" strokeLinecap="round" />

        {/* age lines */}
        {senior && (
          <>
            <path d="M 44 64 Q 47 65 49 63" stroke="#0a0e13" strokeWidth="0.5" fill="none" opacity="0.4" />
            <path d="M 71 63 Q 73 65 76 64" stroke="#0a0e13" strokeWidth="0.5" fill="none" opacity="0.4" />
          </>
        )}
      </g>

      {/* outer ring */}
      <circle cx="60" cy="60" r="58" fill="none" stroke={pal.accent} strokeWidth="0.8" opacity="0.4" />

      {/* initial badge */}
      <g transform="translate(96, 96)">
        <circle r="14" fill="#0a0e13" stroke={pal.accent} strokeWidth="1" />
        <text textAnchor="middle" y="4.5" fontSize="13" fontWeight="600"
          fontFamily="-apple-system, system-ui, sans-serif"
          fill={pal.accent}>{initial}</text>
      </g>
    </svg>
  );
}

function PartyEmblem({ name, color = "#7dd3c0", size = 140 }) {
  const seed = eoHash(name || "party");
  const initial = (name || "?").trim().charAt(0);
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" style={{ display: "block" }}>
      <defs>
        <linearGradient id={`pe-${seed}`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.32" />
          <stop offset="100%" stopColor={color} stopOpacity="0.04" />
        </linearGradient>
      </defs>
      <circle cx="60" cy="60" r="58" fill={`url(#pe-${seed})`} stroke={color} strokeWidth="1" opacity="0.85" />
      <circle cx="60" cy="60" r="44" fill="none" stroke={color} strokeWidth="0.6" opacity="0.4" strokeDasharray="2 4" />
      <g transform="translate(60,60)">
        <path d="M -22 8 L 0 -22 L 22 8 L 13 8 L 13 22 L -13 22 L -13 8 Z"
              fill="none" stroke={color} strokeWidth="1.6" strokeLinejoin="round" />
        <text textAnchor="middle" y="4" fontSize="12" fontWeight="700"
          letterSpacing="0.04em"
          fontFamily="-apple-system, system-ui, sans-serif"
          fill={color}>{initial}</text>
      </g>
    </svg>
  );
}

function DistrictGlyph({ name, color = "#7dd3c0", size = 140 }) {
  const seed = eoHash(name || "district");
  // procedural blob path
  const pts = [];
  const N = 9;
  for (let i = 0; i < N; i++) {
    const a = (i / N) * Math.PI * 2;
    const r = 38 + ((seed >> (i * 2)) % 14);
    pts.push([60 + Math.cos(a) * r, 60 + Math.sin(a) * r]);
  }
  const d = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ") + " Z";
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" style={{ display: "block" }}>
      <circle cx="60" cy="60" r="58" fill="#0a0e13" stroke="#2a3340" strokeWidth="1" />
      <path d={d} fill={color} opacity="0.16" stroke={color} strokeWidth="1.2" />
      {/* internal grid */}
      <path d="M 24 60 H 96" stroke={color} strokeWidth="0.4" opacity="0.3" />
      <path d="M 60 24 V 96" stroke={color} strokeWidth="0.4" opacity="0.3" />
      <circle cx="60" cy="60" r="3" fill={color} />
    </svg>
  );
}

window.PersonPortrait = PersonPortrait;
window.PartyEmblem = PartyEmblem;
window.DistrictGlyph = DistrictGlyph;
