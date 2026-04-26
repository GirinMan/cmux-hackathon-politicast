// 한국 시·도 추상화 데이터
// 격자 좌표 (col, row) — 실제 지리적 위치를 단순화한 도트맵 형태
// 인구는 2026 추정 기반 목업 (단위: 천명)

const KR_REGIONS = [
  // sido = 광역시·도, 위치는 12x10 격자
  { id: "seoul",      name: "서울",     en: "Seoul",       col: 5, row: 3, pop: 9411,  type: "metro",    cluster: "수도권" },
  { id: "incheon",    name: "인천",     en: "Incheon",     col: 4, row: 3, pop: 2954,  type: "metro",    cluster: "수도권" },
  { id: "gyeonggi",   name: "경기",     en: "Gyeonggi",    col: 5, row: 2, pop: 13630, type: "province", cluster: "수도권" },
  { id: "gangwon",    name: "강원",     en: "Gangwon",     col: 7, row: 2, pop: 1536,  type: "province", cluster: "관동" },
  { id: "chungbuk",   name: "충북",     en: "Chungbuk",    col: 6, row: 4, pop: 1592,  type: "province", cluster: "충청" },
  { id: "chungnam",   name: "충남",     en: "Chungnam",    col: 4, row: 4, pop: 2123,  type: "province", cluster: "충청" },
  { id: "sejong",     name: "세종",     en: "Sejong",      col: 5, row: 4, pop: 386,   type: "metro",    cluster: "충청" },
  { id: "daejeon",    name: "대전",     en: "Daejeon",     col: 5, row: 5, pop: 1442,  type: "metro",    cluster: "충청" },
  { id: "jeonbuk",    name: "전북",     en: "Jeonbuk",     col: 4, row: 6, pop: 1751,  type: "province", cluster: "호남" },
  { id: "jeonnam",    name: "전남",     en: "Jeonnam",     col: 4, row: 7, pop: 1804,  type: "province", cluster: "호남" },
  { id: "gwangju",    name: "광주",     en: "Gwangju",     col: 3, row: 7, pop: 1418,  type: "metro",    cluster: "호남" },
  { id: "gyeongbuk",  name: "경북",     en: "Gyeongbuk",   col: 7, row: 4, pop: 2569,  type: "province", cluster: "영남" },
  { id: "daegu",      name: "대구",     en: "Daegu",       col: 7, row: 5, pop: 2360,  type: "metro",    cluster: "영남" },
  { id: "ulsan",      name: "울산",     en: "Ulsan",       col: 8, row: 6, pop: 1099,  type: "metro",    cluster: "영남" },
  { id: "gyeongnam",  name: "경남",     en: "Gyeongnam",   col: 6, row: 6, pop: 3261,  type: "province", cluster: "영남" },
  { id: "busan",      name: "부산",     en: "Busan",       col: 7, row: 7, pop: 3293,  type: "metro",    cluster: "영남" },
  { id: "jeju",       name: "제주",     en: "Jeju",        col: 3, row: 9, pop: 678,   type: "province", cluster: "제주" },
];

// 강조될 샘플 지역 (스크린샷에서 보이던 것들)
const FEATURED_REGIONS = [
  { id: "all",            name: "전체",                 personas: 1000000 },
  { id: "seoul-market",   name: "서울시장",             personas: 185228, parent: "seoul" },
  { id: "gwangju-market", name: "광주시장",             personas: 27594,  parent: "gwangju" },
  { id: "daegu-market",   name: "대구시장",             personas: 46934,  parent: "daegu" },
  { id: "busan-buk-bo",   name: "부산 북구 갑 (보궐)",  personas: 5421,   parent: "busan" },
  { id: "daegu-dalseo-bo",name: "대구 달서구 갑 (보궐)",personas: 10617,  parent: "daegu" },
];

// region 간 인접/연결 (지도 위 엣지 — 시각적 단서용)
const REGION_ADJ = [
  ["seoul","incheon"],["seoul","gyeonggi"],["incheon","gyeonggi"],
  ["gyeonggi","gangwon"],["gyeonggi","chungbuk"],["gyeonggi","chungnam"],
  ["chungnam","sejong"],["sejong","chungbuk"],["sejong","daejeon"],
  ["daejeon","chungbuk"],["daejeon","chungnam"],["daejeon","jeonbuk"],
  ["chungbuk","gyeongbuk"],["chungbuk","gangwon"],
  ["jeonbuk","jeonnam"],["jeonnam","gwangju"],["jeonnam","gyeongnam"],
  ["jeonbuk","gyeongbuk"],["jeonbuk","gyeongnam"],
  ["gyeongbuk","daegu"],["gyeongbuk","gangwon"],["gyeongbuk","ulsan"],
  ["daegu","gyeongnam"],["daegu","gyeongbuk"],
  ["gyeongnam","busan"],["gyeongnam","ulsan"],["busan","ulsan"],
];

window.KR_REGIONS = KR_REGIONS;
window.FEATURED_REGIONS = FEATURED_REGIONS;
window.REGION_ADJ = REGION_ADJ;
