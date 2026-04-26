# EDA Explorer — Frontend (React + Vite + TS + Tailwind 4)

Nemotron-Personas-Korea EDA + PolitiKAST ontology frontend.

- **포트:** `8234` (strict)
- **백엔드:** FastAPI on `http://127.0.0.1:8235`, Vite proxy `/api` → 8235
- **차트:** Apache ECharts (`echarts-for-react`)
- **상태:** React Query (서버) + URL-backed Filter context (클라이언트)
- **테마:** 다크 기본 + 토글 (`localStorage: eda-theme`)

## 페이지

| 경로 | 설명 |
|------|------|
| `/overview` | 시스템 상태 · contract region 요약 · 스키마 · 출처/라이선스 |
| `/demographics` | age hist · sex pie · marital bar · education bar |
| `/regions` | contract region 카드 · 17 시도 막대 · region별 직업 Top 20 |
| `/regions/compare` | 5 contract region 모집단·연령·demographic matrix 비교 |
| `/personas` | 텍스트 길이 통계 (p50/p90) · 24개 샘플 카드 · UUID 모달 (전체 26 필드) |
| `/ontology` | categorical ontology / cluster graph |

## 개발

```bash
cd ui/eda-explorer/frontend
npm install
npm run dev   # http://127.0.0.1:8234
```

백엔드는 `ui/eda-explorer/backend`에서 별도로 띄운다 (FastAPI on 8235).

## 환경변수

| 변수 | 기본 | 설명 |
|------|------|------|
| `VITE_API_BASE` | `/api` | 다른 호스트의 백엔드를 가리킬 때 (예: `http://api.example.com/api`). 비워두면 Vite proxy 사용. |
| `VITE_USE_MOCK` | `0` | (예약) mock 데이터 토글 — 백엔드가 늦을 경우 격리된 fixture 사용. |

## 디렉토리 구조

```
src/
├── api/         # axios 클라이언트 + 엔드포인트 함수
├── charts/      # ECharts 래퍼
├── components/  # Card / StatGrid / States / RegionFilterBar
├── hooks/       # React Query hooks
├── layout/      # AppShell (nav + footer)
├── pages/       # 라우트 페이지
├── state/       # ThemeProvider, FilterProvider (URL 동기화)
├── types/       # backend models 미러
└── main.tsx     # provider 트리
```

## API 계약

`backend/models.py` 와 `src/types/api.ts` 를 일치시킨다. 변경 시 양쪽을 함께 수정.
