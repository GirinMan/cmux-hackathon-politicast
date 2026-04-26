// Election ontology data — synthetic but plausible 2026 서울시장 시나리오
// Node types: Candidate, Party, Election, Contest, District, NarrativeFrame,
//             PressConference, PollPublication, News, Person

const NODE_TYPES = [
  { id: "Candidate",       label: "후보",         color: "var(--c-candidate)", count: 0 },
  { id: "Party",           label: "정당",         color: "var(--c-party)",     count: 0 },
  { id: "Election",        label: "선거",         color: "var(--c-election)",  count: 0 },
  { id: "Contest",         label: "선거구",       color: "var(--c-contest)",   count: 0 },
  { id: "District",        label: "행정구역",     color: "var(--c-district)",  count: 0 },
  { id: "NarrativeFrame",  label: "내러티브",     color: "var(--c-narrative)", count: 0 },
  { id: "PressConference", label: "기자회견",     color: "var(--c-press)",     count: 0 },
  { id: "PollPublication", label: "여론조사",     color: "var(--c-poll)",      count: 0 },
  { id: "News",            label: "뉴스",         color: "var(--c-news)",      count: 0 },
  { id: "Person",          label: "인물",         color: "var(--c-person)",    count: 0 },
];

// Snapshot scaffolding — just used to flavor metadata
const SNAPSHOTS = [
  { id: "seoul_mayor",    name: "서울시장",         tag: "smoke", steps: 3, region: "seoul_mayor",
    cutoff: "2026-06-03T00:00:00", source: "_workspace/snapshots/kg_seoul_mayor_t3.json" },
  { id: "gwangju_mayor",  name: "광주시장",         tag: "mock",  steps: 1, region: "gwangju_mayor",
    cutoff: "2026-06-03T00:00:00", source: "_workspace/snapshots/kg_gwangju_mayor_t1.json" },
  { id: "daegu_mayor",    name: "대구시장",         tag: "mock",  steps: 1, region: "daegu_mayor",
    cutoff: "2026-06-03T00:00:00", source: "_workspace/snapshots/kg_daegu_mayor_t1.json" },
  { id: "busan_buk_gap",  name: "부산 북구 갑 (보궐)", tag: "mock",  steps: 1, region: "busan_buk_gap",
    cutoff: "2026-04-09T00:00:00", source: "_workspace/snapshots/kg_busan_buk_gap_t1.json" },
  { id: "daegu_dalseo_gap", name: "대구 달서구 갑 (보궐)", tag: "mock", steps: 1, region: "daegu_dalseo_gap",
    cutoff: "2026-04-09T00:00:00", source: "_workspace/snapshots/kg_daegu_dalseo_gap_t1.json" },
];

// Node graph — synthetic, ~22 nodes / 32 edges to mirror screenshot counts
// Each node is fictional / illustrative.
const NODES = [
  // Election root
  { id: "el:seoul_2026", type: "Election", label: "2026 서울시장 선거",
    attrs: { date: "2026-06-03", level: "광역단체장", electorate: "8.42M", turnout_proj: "57.3%" },
    summary: "2026년 6월 3일 실시되는 제9회 전국동시지방선거 중 서울특별시장 선거." },

  // Contests (district sub-elections)
  { id: "ct:seoul_main", type: "Contest", label: "서울특별시장",
    attrs: { seats: 1, type: "단일선거구", registered: "8,420,118", precincts: 425 },
    summary: "서울특별시 전역을 단일 선거구로 하는 시장 경선." },
  { id: "ct:gangnam_council", type: "Contest", label: "강남구의회 비례",
    attrs: { seats: 4, type: "비례대표", registered: "452,114" },
    summary: "강남구 기초의회 비례대표 4석 경선." },

  // Districts
  { id: "ds:seoul", type: "District", label: "서울특별시",
    attrs: { code: "11", area: "605.2 km²", population: "9.41M", households: "4.21M" },
    summary: "대한민국 수도. 25개 자치구로 구성." },
  { id: "ds:gangnam", type: "District", label: "강남구",
    attrs: { code: "11680", population: "543K", households: "227K" },
    summary: "서울특별시 동남권 자치구. 보수 성향이 상대적으로 강한 지역." },
  { id: "ds:gwanak", type: "District", label: "관악구",
    attrs: { code: "11620", population: "493K", households: "231K" },
    summary: "1인 가구 비율이 가장 높은 자치구 중 하나. 진보 성향이 강함." },

  // Parties
  { id: "pt:dp", type: "Party", label: "민주평화당",
    attrs: { ideology: "중도진보", seats_assembly: 142, color: "#0a4da3", founded: "2017" },
    summary: "현 원내 1당. 시민자치·돌봄 의제를 중심에 두고 있음. (가상 정당)" },
  { id: "pt:rk", type: "Party", label: "국민통합당",
    attrs: { ideology: "중도보수", seats_assembly: 108, color: "#c8102e", founded: "2020" },
    summary: "원내 2당. 규제완화·치안 의제 중심. (가상 정당)" },
  { id: "pt:gp", type: "Party", label: "녹색미래당",
    attrs: { ideology: "생태진보", seats_assembly: 6, color: "#2f9e44", founded: "2014" },
    summary: "기후·세대 의제를 강조하는 원내 소수 정당. (가상 정당)" },

  // Candidates
  { id: "cd:lee_seoul", type: "Candidate", label: "이서연",
    attrs: { age: 52, gender: "여", party: "민주평화당", career: "前 여성가족부 장관",
             slogan: "돌보는 도시, 잇는 서울", poll_avg: "41.2%" },
    summary: "前 여성가족부 장관 출신. 돌봄·보육 정책을 중심에 두고 캠페인 전개." },
  { id: "cd:kang_seoul", type: "Candidate", label: "강민호",
    attrs: { age: 58, gender: "남", party: "국민통합당", career: "前 서울시 부시장",
             slogan: "다시 일하는 서울", poll_avg: "38.7%" },
    summary: "前 서울시 행정1부시장. 규제완화·재건축·교통망 확장 공약." },
  { id: "cd:park_seoul", type: "Candidate", label: "박지우",
    attrs: { age: 41, gender: "여", party: "녹색미래당", career: "환경운동연합 사무총장",
             slogan: "기후 1번지 서울", poll_avg: "9.8%" },
    summary: "환경운동연합 사무총장 출신의 시민사회계 후보. 30·40대 지지층 결집." },

  // Persons (관련 인물)
  { id: "pr:lee_chief", type: "Person", label: "정수영",
    attrs: { role: "캠프 총괄본부장", affiliation: "이서연 캠프", age: 49 },
    summary: "이서연 후보 캠프 총괄. 前 청와대 정무수석실 행정관." },
  { id: "pr:han_strategy", type: "Person", label: "한도현",
    attrs: { role: "전략기획실장", affiliation: "강민호 캠프", age: 45 },
    summary: "강민호 캠프 전략기획. 광고·여론 분야 컨설턴트." },
  { id: "pr:moon_advisor", type: "Person", label: "문지혜",
    attrs: { role: "정책자문단장", affiliation: "박지우 캠프", age: 38 },
    summary: "박지우 캠프 기후정책 자문. 서울대 환경대학원 부교수." },

  // Narrative frames
  { id: "nf:carecity", type: "NarrativeFrame", label: "돌봄도시",
    attrs: { sentiment: "+0.42", reach: "27.8%", peak: "T2" },
    summary: "보육·간병·고령자 통합돌봄을 도시 운영원리로 제시하는 프레임. 이서연 캠프 주도." },
  { id: "nf:rebuild", type: "NarrativeFrame", label: "재건축 정상화",
    attrs: { sentiment: "+0.28", reach: "33.1%", peak: "T1" },
    summary: "재건축 안전진단 완화·용적률 상향 등 공급정책을 묶은 프레임. 강민호 캠프 주도." },
  { id: "nf:climate1", type: "NarrativeFrame", label: "기후 1번지",
    attrs: { sentiment: "+0.51", reach: "11.4%", peak: "T3" },
    summary: "에너지자립·녹지·기후예산을 묶은 박지우 캠프 핵심 프레임." },

  // Press conferences
  { id: "pc:lee_kickoff", type: "PressConference", label: "이서연 출마 선언",
    attrs: { date: "2026-04-12", venue: "서울시의회 본관", attendees: 87, qa: 14 },
    summary: "이서연 후보 출마선언 및 1호 공약 발표. '서울 돌봄청' 신설 제안." },
  { id: "pc:kang_housing", type: "PressConference", label: "강민호 주택공약 발표",
    attrs: { date: "2026-04-21", venue: "여의도 캠프", attendees: 62, qa: 11 },
    summary: "30만호 공급 로드맵 및 재건축 안전진단 폐지 공약." },

  // Poll publications
  { id: "po:naver_w15", type: "PollPublication", label: "NAVER 트렌드 W15",
    attrs: { agency: "NAVER Cloud", method: "검색·뉴스 가중", n: "—", date: "2026-04-15" },
    summary: "검색량·뉴스 노출량 가중 트렌드 지수. 이서연 41.2 / 강민호 38.7 / 박지우 9.8." },
  { id: "po:realmeter_w16", type: "PollPublication", label: "리얼메타 4월 3주",
    attrs: { agency: "리얼메타", method: "ARS·전화면접 혼용", n: "1,012", date: "2026-04-22" },
    summary: "유선 ARS와 무선 전화면접 혼합. 응답률 8.4%, 표본오차 ±3.1%p." },

  // News
  { id: "nw:joongang_lee", type: "News", label: "이서연, 돌봄청 신설 공약",
    attrs: { outlet: "중앙일보", date: "2026-04-13", section: "정치", reads: "284K" },
    summary: "이서연 후보의 출마선언 및 1호 공약을 주요 보도. 사설은 비판적 톤." },
  { id: "nw:hani_climate", type: "News", label: "박지우, 기후 1번지 공약",
    attrs: { outlet: "한겨레", date: "2026-04-18", section: "정치", reads: "112K" },
    summary: "박지우 후보의 기후 정책 패키지를 주요 분석. 우호적 논조." },
  { id: "nw:chosun_kang", type: "News", label: "강민호 주택공약 첫 공개",
    attrs: { outlet: "조선일보", date: "2026-04-22", section: "정치", reads: "401K" },
    summary: "강민호 후보의 주택공약을 주요 보도. 1면 톱 다룸." },
];

// Edges — predicate-typed
// Each edge: { from, to, predicate, weight }
const EDGES = [
  // Election ↔ contest ↔ district
  { from: "el:seoul_2026", to: "ct:seoul_main", predicate: "hasContest" },
  { from: "el:seoul_2026", to: "ct:gangnam_council", predicate: "hasContest" },
  { from: "ct:seoul_main", to: "ds:seoul", predicate: "inDistrict" },
  { from: "ct:gangnam_council", to: "ds:gangnam", predicate: "inDistrict" },
  { from: "ds:gangnam", to: "ds:seoul", predicate: "partOf" },
  { from: "ds:gwanak", to: "ds:seoul", predicate: "partOf" },

  // Candidate ↔ party / contest
  { from: "cd:lee_seoul", to: "pt:dp", predicate: "memberOf" },
  { from: "cd:kang_seoul", to: "pt:rk", predicate: "memberOf" },
  { from: "cd:park_seoul", to: "pt:gp", predicate: "memberOf" },
  { from: "cd:lee_seoul", to: "ct:seoul_main", predicate: "runsIn" },
  { from: "cd:kang_seoul", to: "ct:seoul_main", predicate: "runsIn" },
  { from: "cd:park_seoul", to: "ct:seoul_main", predicate: "runsIn" },

  // Person ↔ candidate (캠프 인물)
  { from: "pr:lee_chief", to: "cd:lee_seoul", predicate: "advises" },
  { from: "pr:han_strategy", to: "cd:kang_seoul", predicate: "advises" },
  { from: "pr:moon_advisor", to: "cd:park_seoul", predicate: "advises" },

  // Narrative ↔ candidate
  { from: "nf:carecity", to: "cd:lee_seoul", predicate: "promotedBy" },
  { from: "nf:rebuild", to: "cd:kang_seoul", predicate: "promotedBy" },
  { from: "nf:climate1", to: "cd:park_seoul", predicate: "promotedBy" },

  // Press conferences
  { from: "pc:lee_kickoff", to: "cd:lee_seoul", predicate: "heldBy" },
  { from: "pc:kang_housing", to: "cd:kang_seoul", predicate: "heldBy" },
  { from: "pc:lee_kickoff", to: "nf:carecity", predicate: "frames" },
  { from: "pc:kang_housing", to: "nf:rebuild", predicate: "frames" },

  // News ↔ press / candidate / narrative
  { from: "nw:joongang_lee", to: "pc:lee_kickoff", predicate: "covers" },
  { from: "nw:joongang_lee", to: "nf:carecity", predicate: "frames" },
  { from: "nw:hani_climate", to: "cd:park_seoul", predicate: "covers" },
  { from: "nw:hani_climate", to: "nf:climate1", predicate: "frames" },
  { from: "nw:chosun_kang", to: "pc:kang_housing", predicate: "covers" },
  { from: "nw:chosun_kang", to: "nf:rebuild", predicate: "frames" },

  // Polls ↔ candidates / election
  { from: "po:naver_w15", to: "el:seoul_2026", predicate: "measures" },
  { from: "po:realmeter_w16", to: "el:seoul_2026", predicate: "measures" },
  { from: "po:naver_w15", to: "cd:lee_seoul", predicate: "ranks" },
  { from: "po:realmeter_w16", to: "cd:kang_seoul", predicate: "ranks" },
];

// Compute counts per type
NODE_TYPES.forEach(t => { t.count = NODES.filter(n => n.type === t.id).length; });

window.NODE_TYPES = NODE_TYPES;
window.NODES = NODES;
window.EDGES = EDGES;
window.SNAPSHOTS = SNAPSHOTS;

// Snapshot index list (sidebar) — synthetic
window.SNAPSHOT_INDEX = [
  { region: "busan_buk_gap",   step: "T0", path: "_workspace/snapshots/kg_busan_buk_gap_t0.json" },
  { region: "busan_buk_gap",   step: "T1", path: "_workspace/snapshots/kg_busan_buk_gap_t1.json" },
  { region: "busan_buk_gap",   step: "T2", path: "_workspace/snapshots/kg_busan_buk_gap_t2.json" },
  { region: "busan_buk_gap",   step: "T3", path: "_workspace/snapshots/kg_busan_buk_gap_t3.json" },
  { region: "seoul_mayor",     step: "T0", path: "_workspace/snapshots/kg_seoul_mayor_t0.json" },
  { region: "seoul_mayor",     step: "T1", path: "_workspace/snapshots/kg_seoul_mayor_t1.json" },
  { region: "seoul_mayor",     step: "T2", path: "_workspace/snapshots/kg_seoul_mayor_t2.json" },
  { region: "seoul_mayor",     step: "T3", path: "_workspace/snapshots/kg_seoul_mayor_t3.json" },
  { region: "global",          step: "T—", path: "_workspace/snapshots/kg_coverage_stats.json" },
];
