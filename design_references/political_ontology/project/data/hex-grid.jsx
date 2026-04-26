// 한국 시·도 hex grid 좌표
// 축좌표(axial) (q, r): col=q + (r - (r&1))/2, 실제 지리적 위치 반영
// 본토는 q 0~5, r 0~7 / 제주는 r=8

// 실제 지리 ↔ hex 매핑:
//  - 강원이 동쪽 위, 인천/경기 서쪽 위
//  - 경북·대구·울산이 동쪽 중간, 충청이 서쪽 중간
//  - 호남이 서쪽 하단, 경남·부산이 동쪽 하단
//  - 제주는 분리

const KR_HEX = [
  // r=0 (북부) — DMZ 인근
  { id: "gyeonggi-n",  parent: "gyeonggi",  q: 2, r: 0, label: "경기북부" },
  { id: "gangwon-n",   parent: "gangwon",   q: 3, r: 0, label: "강원북부" },
  { id: "gangwon-e",   parent: "gangwon",   q: 4, r: 0, label: "강원동해" },

  // r=1
  { id: "incheon",     parent: "incheon",   q: 0, r: 1, label: "인천", solo: true },
  { id: "seoul",       parent: "seoul",     q: 1, r: 1, label: "서울", solo: true },
  { id: "gyeonggi",    parent: "gyeonggi",  q: 2, r: 1, label: "경기" },
  { id: "gangwon",     parent: "gangwon",   q: 3, r: 1, label: "강원" },
  { id: "gangwon-s",   parent: "gangwon",   q: 4, r: 1, label: "강원남부" },

  // r=2
  { id: "chungnam-n",  parent: "chungnam",  q: 0, r: 2, label: "충남서해" },
  { id: "chungnam",    parent: "chungnam",  q: 1, r: 2, label: "충남" },
  { id: "sejong",      parent: "sejong",    q: 2, r: 2, label: "세종", solo: true },
  { id: "chungbuk",    parent: "chungbuk",  q: 3, r: 2, label: "충북" },
  { id: "gyeongbuk-n", parent: "gyeongbuk", q: 4, r: 2, label: "경북북부" },

  // r=3
  { id: "chungnam-s",  parent: "chungnam",  q: 0, r: 3, label: "충남남부" },
  { id: "daejeon",     parent: "daejeon",   q: 1, r: 3, label: "대전", solo: true },
  { id: "chungbuk-s",  parent: "chungbuk",  q: 2, r: 3, label: "충북남부" },
  { id: "gyeongbuk",   parent: "gyeongbuk", q: 3, r: 3, label: "경북" },
  { id: "gyeongbuk-e", parent: "gyeongbuk", q: 4, r: 3, label: "경북동해" },

  // r=4
  { id: "jeonbuk-n",   parent: "jeonbuk",   q: 0, r: 4, label: "전북서해" },
  { id: "jeonbuk",     parent: "jeonbuk",   q: 1, r: 4, label: "전북" },
  { id: "jeonbuk-e",   parent: "jeonbuk",   q: 2, r: 4, label: "전북동부" },
  { id: "daegu",       parent: "daegu",     q: 3, r: 4, label: "대구", solo: true },
  { id: "gyeongbuk-s", parent: "gyeongbuk", q: 4, r: 4, label: "경북남부" },

  // r=5
  { id: "gwangju",     parent: "gwangju",   q: 0, r: 5, label: "광주", solo: true },
  { id: "jeonnam",     parent: "jeonnam",   q: 1, r: 5, label: "전남" },
  { id: "gyeongnam-w", parent: "gyeongnam", q: 2, r: 5, label: "경남서부" },
  { id: "gyeongnam",   parent: "gyeongnam", q: 3, r: 5, label: "경남" },
  { id: "ulsan",       parent: "ulsan",     q: 4, r: 5, label: "울산", solo: true },

  // r=6 (남해안)
  { id: "jeonnam-s",   parent: "jeonnam",   q: 1, r: 6, label: "전남남해" },
  { id: "gyeongnam-s", parent: "gyeongnam", q: 2, r: 6, label: "경남남해" },
  { id: "busan",       parent: "busan",     q: 3, r: 6, label: "부산", solo: true },

  // r=7.5 (제주 — 분리, 본토 아래쪽)
  { id: "jeju",        parent: "jeju",      q: 1, r: 7, label: "제주", solo: true, gap: true },
  { id: "jeju-e",      parent: "jeju",      q: 2, r: 7, label: "제주동부", gap: true },
];

// hex axial → pixel
// flat-top hex: x = size * 3/2 * q, y = size * sqrt(3) * (r + q/2)
// pointy-top hex: x = size * sqrt(3) * (q + r/2), y = size * 3/2 * r
function hexToPixel(q, r, size) {
  const x = size * Math.sqrt(3) * (q + r / 2);
  const y = size * 1.5 * r;
  return { x, y };
}

// flat-top hex 6점
function hexCorners(cx, cy, size) {
  const pts = [];
  for (let i = 0; i < 6; i++) {
    const a = (Math.PI / 3) * i + Math.PI / 6; // pointy-top
    pts.push([cx + size * Math.cos(a), cy + size * Math.sin(a)]);
  }
  return pts;
}

window.KR_HEX = KR_HEX;
window.hexToPixel = hexToPixel;
window.hexCorners = hexCorners;
