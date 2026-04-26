// 노드 심볼 — outline 위주, 복잡한 형태
// 카테고리별로 고유한 시그니처 심볼

const NodeSymbol = ({ shape, size, color, weight = 1, filled = false }) => {
  const r = size / 2;
  const sw = 1.2;
  const stroke = color;
  const fill = filled ? color : "none";
  const innerFill = filled ? "rgba(0,0,0,0.4)" : "none";

  switch (shape) {
    // Region: 다이아몬드 + 내부 십자 (방위)
    case "diamond": {
      return (
        <g>
          <polygon points={`0,${-r} ${r},0 0,${r} ${-r},0`} fill="none" stroke={stroke} strokeWidth={sw} />
          <polygon points={`0,${-r * 0.45} ${r * 0.45},0 0,${r * 0.45} ${-r * 0.45},0`} fill={stroke} opacity="0.55" />
        </g>
      );
    }
    // Province: 사각 격자 (4분할)
    case "square": {
      return (
        <g>
          <rect x={-r} y={-r} width={size} height={size} rx="1" fill="none" stroke={stroke} strokeWidth={sw} />
          <line x1={-r} y1="0" x2={r} y2="0" stroke={stroke} strokeWidth="0.5" opacity="0.5" />
          <line x1="0" y1={-r} x2="0" y2={r} stroke={stroke} strokeWidth="0.5" opacity="0.5" />
          <rect x={-r * 0.4} y={-r * 0.4} width={r * 0.8} height={r * 0.8} fill={stroke} opacity="0.7" />
        </g>
      );
    }
    // District: 동심원 + 점
    case "circle": {
      return (
        <g>
          <circle r={r} fill="none" stroke={stroke} strokeWidth={sw} />
          <circle r={r * 0.55} fill="none" stroke={stroke} strokeWidth="0.6" opacity="0.6" />
          <circle r={r * 0.22} fill={stroke} />
        </g>
      );
    }
    // AgeGroup: 호(arc) — 시간/세대 메타포
    case "circle-age": {
      return (
        <g>
          <circle r={r} fill="none" stroke={stroke} strokeWidth={sw} />
          <path d={`M 0 ${-r} A ${r} ${r} 0 0 1 ${r * 0.95} ${r * 0.31}`} fill="none" stroke={stroke} strokeWidth="1.6" />
          <circle r={r * 0.18} fill={stroke} />
        </g>
      );
    }
    // Sex: 위/아래 화살표 결합 (gender symbol abstraction)
    case "triangle": {
      return (
        <g>
          <polygon points={`0,${-r} ${r * 0.86},${r * 0.6} ${-r * 0.86},${r * 0.6}`} fill="none" stroke={stroke} strokeWidth={sw} />
          <line x1="0" y1={-r * 0.3} x2="0" y2={r * 0.4} stroke={stroke} strokeWidth="1.2" />
          <circle cy={r * 0.1} r={r * 0.18} fill={stroke} />
        </g>
      );
    }
    // EducationLevel: 단계형 사다리꼴 (학력 단계)
    case "edu": {
      return (
        <g>
          <polygon
            points={`${-r * 0.85},${r * 0.7} ${r * 0.85},${r * 0.7} ${r * 0.55},${-r * 0.7} ${-r * 0.55},${-r * 0.7}`}
            fill="none" stroke={stroke} strokeWidth={sw}
          />
          <line x1={-r * 0.7} y1={r * 0.2} x2={r * 0.7} y2={r * 0.2} stroke={stroke} strokeWidth="0.6" opacity="0.7" />
          <line x1={-r * 0.62} y1={-r * 0.25} x2={r * 0.62} y2={-r * 0.25} stroke={stroke} strokeWidth="0.6" opacity="0.7" />
        </g>
      );
    }
    // Occupation: 핀(pin) — 위치/직군 메타포
    case "pin": {
      return (
        <g>
          <path
            d={`M 0 ${r} L ${-r * 0.7} ${-r * 0.1} A ${r * 0.7} ${r * 0.7} 0 1 1 ${r * 0.7} ${-r * 0.1} Z`}
            fill="none" stroke={stroke} strokeWidth={sw}
          />
          <circle cx="0" cy={-r * 0.25} r={r * 0.28} fill={stroke} />
        </g>
      );
    }
    // FamilyType: 별-삼각 합성 (가족 군집)
    case "family": {
      return (
        <g>
          <polygon points={`0,${-r} ${r * 0.86},${r * 0.6} ${-r * 0.86},${r * 0.6}`} fill="none" stroke={stroke} strokeWidth={sw} />
          <polygon points={`0,${r * 0.85} ${r * 0.86},${-r * 0.45} ${-r * 0.86},${-r * 0.45}`} fill="none" stroke={stroke} strokeWidth={sw} opacity="0.65" />
          <circle r={r * 0.2} fill={stroke} />
        </g>
      );
    }
    // HousingType: 집 형태 (지붕 + 박스)
    case "house": {
      return (
        <g>
          <path
            d={`M ${-r} ${-r * 0.15} L 0 ${-r} L ${r} ${-r * 0.15} L ${r} ${r * 0.85} L ${-r} ${r * 0.85} Z`}
            fill="none" stroke={stroke} strokeWidth={sw}
          />
          <rect x={-r * 0.25} y={r * 0.2} width={r * 0.5} height={r * 0.65} fill={stroke} opacity="0.7" />
        </g>
      );
    }
    default:
      return <circle r={r} fill="none" stroke={stroke} strokeWidth={sw} />;
  }
};

window.NodeSymbol = NodeSymbol;
