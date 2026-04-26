# Handoff — Nemotron Research + EDA Explorer

> 작성: 2026-04-26 11:30 KST · 작성자: Claude Code `team-lead` (nemotron-research 팀)
> 업데이트: 2026-04-26 12:09 KST · Codex `frontend-bff` — contract region/ontology graph 반영.
> 다음 작업자(Codex 등)를 위한 single source of truth.

---

## 0. TL;DR

PolitiKAST 해커톤 컨텍스트에서, **NVIDIA Nemotron-Personas-Korea** 데이터셋(1M 행, 9 parquet shards, CC BY 4.0)에 대한 종합 리서치를 수행했고, 결과를 인터랙티브하게 탐색할 수 있는 별도 frontend(`ui/eda-explorer/`, FastAPI :8235 + Vite/React :8234)를 빌드했다. 6명 agent team(`nemotron-research`)이 34개 task로 분담 완료. 두 dev 서버는 background로 라이브 가동 중.

---

## 1. 현재 가동 상태 (LIVE)

| 포트 | 서비스 | 프로세스 | 상태 | 헬스체크 |
|---|---|---|---|---|
| 8234 | Vite dev (frontend) | node, PID 62991 | LISTEN | `curl http://127.0.0.1:8234/` → 200 |
| 8235 | FastAPI (backend) | uvicorn --reload | LISTEN | `curl http://127.0.0.1:8235/api/health` → `{"status":"ok"}` |

**중요:** 두 서버 모두 다른 Bash background task로 띄워져 있다. 재시작 시 아래 §6 명령 참조.

```bash
lsof -nP -iTCP:8234 -sTCP:LISTEN
lsof -nP -iTCP:8235 -sTCP:LISTEN
```

---

## 2. 산출물 위치

### 2.1 리서치 (`_workspace/research/nemotron-personas-korea/`)

```
INDEX.md                   ← 먼저 읽기. 모든 산출물 인덱스 + 다른 빌더용 cheat sheet
01_overview.md             ← provenance / lineage / 합성 파이프라인 / 라이선스
02_schema.md               ← 26 컬럼 풀스펙 + KO/EN 매핑 + enum
03_eda.md                  ← 1M 전수 EDA + 9 차트
04_politikast_utility.md   ← 프롬프트 매핑 / 정치 시그널 / KG 후보 / 한계
notes/                     ← 17개 부속 노트
  01~04 provenance, 10~13 schema, 20~24 eda, 30~33 utility
eda_charts/                ← 9 PNG + _data/ (21 CSV/JSON)
scripts/                   ← 6 재현 스크립트 (모두 PEP 723 + uv run)
```

### 2.2 EDA Explorer 앱 (`ui/eda-explorer/`)

```
backend/
  pyproject.toml           ← uv 관리. fastapi/uvicorn/duckdb/pydantic
  app.py                   ← lifespan, CORS allow=8234
  db.py                    ← DuckDB conn (영속 우선 → parquet fallback, *_list ast.literal_eval)
  models.py                ← Pydantic 응답 모델 (모든 엔드포인트)
  routers/{health,demographics,regions,personas}.py
  tests/test_smoke.py      ← 18 tests, 모두 pass
  README.md
  uv.lock

frontend/
  package.json             ← React 19 + Vite 8 + TS 6 + Tailwind 4 + ECharts 6
  vite.config.ts           ← server :8234, proxy /api → :8235
  src/
    main.tsx, App.tsx
    api/{client.ts,endpoints.ts}
    hooks/queries.ts       ← React Query
    state/{theme.tsx,filter.tsx}  ← URL 쿼리스트링 동기화 필터
    layout/AppShell.tsx
    components/{Card,RegionFilterBar,StatGrid,States}.tsx
    charts/EChart.tsx
    pages/{OverviewPage,DemographicsPage,RegionsPage,PersonasPage}.tsx
    types/api.ts
  README.md
```

---

## 3. 데이터 / 인프라

### 3.1 데이터셋
- **파일:** `/Users/girinman/datasets/Nemotron-Personas-Korea/data/train-{00000..00008}-of-00009.parquet` (9 shards × 210MB ≈ 1.89GB)
- **행수:** 1,000,000 (9 × 111,111 + 1)
- **컬럼:** 26 (BIGINT 1, VARCHAR 25). README는 40+ 광고하지만 실제는 26.
- **null:** 0% 모든 컬럼
- **uuid:** unique
- **라이선스:** CC BY 4.0 (NVIDIA) — `notes/04_citation.md`에 BibTeX 7종

### 3.2 영속 DuckDB (다른 PolitiKAST 팀이 만든 것)
- **경로:** `_workspace/db/politikast.duckdb`
- **테이블 발견:** `persona_core` (1M), `persona_text` (1M), `personas_seoul_mayor`, `personas_gwangju_mayor`, `personas_daegu_mayor`, `personas_busan_buk_gap`, `personas_daegu_dalseo_gap` 등
- **시사점:** EDA backend는 `_workspace/contracts/data_paths.json` 기반 region resolver를 사용한다. 과거 `uiwang/byelection` 키는 더 이상 frontend/API 기준이 아니다.
- 우리 backend는 이 DB를 read-only로 우선 사용하고, 부재 시 parquet glob fallback.

### 3.3 5 region 실측 행수 (확정)
- 서울시장 **185,228** / 광주시장 **27,594** / 대구시장 **46,934** / 부산 북구 갑 **5,421** / 대구 달서구 갑 **10,617**
- `daegu_dalseo_gap`은 `daegu_mayor`의 부분집합이다. contest별 sample frame으로 해석하고 단순 합산 coverage로 쓰지 않는다.

---

## 4. 핵심 발견사항 (skip 시 함정)

1. **`*_list` 컬럼 함정:** parquet 스키마는 string이지만 실제 값은 Python list의 `repr()` 문자열(`['a','b',...]`). DuckDB로 그냥 select하면 string. backend/db.py에서 `ast.literal_eval()` 변환됨. 새로 쿼리 짤 때 주의.
2. **`province` 약식 표기:** `경상남`, `충청북`, `전북` 같은 짧은 이름 사용. KOSIS 표준명과 매핑 사전 필요.
3. **age cutoff 19+:** 만 18세 유권자 부재 → paper Limitations.
4. **gender binary only:** `sex` 2-class. 별도 gender 컬럼 없음.
5. **occupation 표면형 중복:** 2,120 unique 중 무직 36.7%. KSCO 11그룹 롤업 권장.
6. **시점 1.5년 시차:** grounding 통계는 2024-12 (NHIS). PolitiKAST 시뮬레이션 대상은 2026 보궐 → KG `Temporal Firewall` 필수.

---

## 5. Open items / 미완

| 항목 | 어디서 | 영향 |
|---|---|---|
| 보궐 region 결정 | data-engineer 또는 사용자 | ✅ `busan_buk_gap`, `daegu_dalseo_gap` 반영 완료. API `/regions/five`, INDEX/04_utility/22_region_match 갱신 |
| README 광고 40+ vs 실제 26 컬럼 | NVIDIA HF 페이지 재확인 | ✅ Perplexity 재확인 note 추가. repo-local truth는 26 parquet columns 유지 |
| PGM 정확한 구조 | NVIDIA 문서 | 재확인했으나 미확인 유지. 확인된 것처럼 쓰지 말 것 |
| OCEAN 한국 보정 여부 | NVIDIA 문서 | 재확인했으나 미확인 유지. 확인된 것처럼 쓰지 말 것 |
| `military_status` grounding | NVIDIA 문서 | 재확인했으나 미확인 유지. 확인된 것처럼 쓰지 말 것 |
| Streamlit 메인 앱과 통합 | dashboard-engineer 팀 | ✅ 새 페이지 `ui/dashboard/pages/7_EDA_Explorer.py` 추가. `:8234` iframe + `:8235` health |
| `/api/regions/five` 라벨 다국어 | frontend | i18n 필요 시 |
| 5 region 비교 뷰 | frontend | ✅ `/regions/compare` 추가 |

---

## 6. 명령 cheat sheet (재시작 / 확장)

### 6.1 Backend 재시작
```bash
# Kill if needed
lsof -nP -iTCP:8235 -sTCP:LISTEN | awk 'NR>1{print $2}' | xargs -r kill

# Start (foreground 또는 background)
uv run --project /Users/girinman/repos/cmux-hackathon-politicast/ui/eda-explorer/backend \
  uvicorn app:app --host 127.0.0.1 --port 8235 --reload

# Smoke test
uv run --project /Users/girinman/repos/cmux-hackathon-politicast/ui/eda-explorer/backend \
  --extra test pytest -q
```

### 6.2 Frontend 재시작
```bash
cd /Users/girinman/repos/cmux-hackathon-politicast/ui/eda-explorer/frontend
npm install         # 첫 실행 시만
npm run dev -- --host 127.0.0.1 --port 8234
# tsc check
npx tsc -b
```

### 6.3 데이터 분석 스크립트 재실행 (uv 표준)
```bash
cd /Users/girinman/repos/cmux-hackathon-politicast/_workspace/research/nemotron-personas-korea
uv run scripts/integrity_check.py
uv run scripts/demographics.py
uv run scripts/region_match.py
uv run scripts/occupation_skills.py
uv run scripts/persona_length.py
uv run scripts/schema_probe.py
```

### 6.4 백엔드 API 빠른 확인
```bash
curl -sS http://127.0.0.1:8235/api/health | jq .
curl -sS http://127.0.0.1:8235/api/schema | jq .
curl -sS http://127.0.0.1:8235/api/regions/five | jq .
curl -sS 'http://127.0.0.1:8235/api/demographics?region=seoul_mayor' | jq .
curl -sS 'http://127.0.0.1:8235/api/personas/sample?region=busan_buk_gap&limit=5&seed=42' | jq .
curl -sS 'http://127.0.0.1:8235/api/ontology/graph?region=seoul_mayor' | jq .
open http://127.0.0.1:8235/docs    # Swagger UI
```

---

## 7. 다음 작업자(Codex)에게 권장 작업 후보

1. **보궐 region 결정 → 종단 반영**
   - ✅ 완료: backend `db.py` contract resolver, `/api/regions/five`, `/api/ontology/graph`, frontend region chips, `04_politikast_utility.md`, `INDEX.md`, `22_region_match.md`
2. **5 region 비교 뷰 추가 (frontend)**
   - ✅ 완료: `/regions/compare`. demographics 5번 fetch + React Query 병렬, population/age/stacked-age/table 비교
3. **메인 PolitiKAST Streamlit 앱과 통합**
   - ✅ 완료: `ui/dashboard/pages/7_EDA_Explorer.py`에서 `:8234` iframe + `:8235` health status
4. **paper figures 채우기**
   - `eda_charts/*.png` 9개를 `elex-kg-final.tex`의 결과 placeholder에 끼우기
   - `/update-paper` 스킬 또는 paper-writer 에이전트 호출
5. **지도 시각화**
   - 17 시도 GeoJSON 받아서 ECharts map으로 province별 행수 colored choropleth
6. **occupation KSCO 롤업**
   - ✅ 완료: backend `/api/occupations/major` + frontend Regions page 대분류 chart
7. **테스트 강화**
   - frontend Vitest/Playwright (현재 0)
   - backend pytest 18 → 응답 schema 더 엄격하게

---

## 8. 팀 / agent team 구성

`nemotron-research` 팀 (TeamCreate, `~/.claude/teams/nemotron-research/config.json`):

| 이름 | 역할 | 산출 |
|---|---|---|
| team-lead | 작업 분배 + INDEX | 본 핸드오프, INDEX.md |
| provenance-research | HF/NVIDIA/grounding/citation | 01_overview + notes/01~04 |
| schema-doc | 컬럼 사전 + enum + 페르소나 텍스트 | 02_schema + notes/10~13 |
| eda-analyst | 1M 전수 EDA + 9 차트 | 03_eda + notes/20~24 |
| politikast-utility | prompt/KG/sampling/한계 | 04_politikast_utility + notes/30~33 |
| eda-api-builder | FastAPI :8235 | ui/eda-explorer/backend/ |
| eda-frontend-builder | Vite/React :8234 | ui/eda-explorer/frontend/ |

모든 팀원 idle 상태. 필요 시 SendMessage로 깨워서 재사용 가능. 새 팀 만들기 전에 기존 팀 정리(TeamDelete)할지 결정해야 함 — 현재는 보존 중.

---

## 9. 환경 표준

- **Python:** 무조건 `uv` 사용. `pip install --user` / 시스템 python 직접 호출 금지.
  - 스크립트 자기완결: PEP 723 inline metadata
    ```python
    # /// script
    # requires-python = ">=3.11"
    # dependencies = ["duckdb", "pyarrow", "pandas"]
    # ///
    ```
  - 프로젝트: `pyproject.toml` + `uv.lock` (backend/)
- **Node:** npm 또는 pnpm. 현재 `npm install`로 설치됨, `node_modules/` 보존.
- **포트 약속:** :8234(frontend) / :8235(backend). 변경 시 `vite.config.ts` proxy + backend CORS 동시 갱신.

---

## 10. 외부 컨텍스트 링크

- 프로젝트 CLAUDE.md (또는 동일 내용 AGENTS.md 심볼릭링크): `/Users/girinman/repos/cmux-hackathon-politicast/CLAUDE.md`
- 컨트랙트 4종: `_workspace/contracts/` (data_paths, api_contract, result_schema, llm_strategy)
- 다른 PolitiKAST 빌드 스킬: `.claude/skills/{data-ingest,run-simulation,build-kg,launch-dashboard,update-paper,manage-policy,politikast-hackathon}/`
- 해커톤 데드라인: 17:00 KST (2026-04-26) 빌드 동결, 16:30 hard freeze.

---

## 부록 A — 응답 schema 예시 (backend OpenAPI 그대로)

```json
GET /api/health
{
  "status": "ok",
  "mode": "duckdb",
  "source": "_workspace/db/politikast.duckdb",
  "persona_core_rows": 1000000,
  "persona_text_rows": 1000000,
  "region_tables": ["personas_daegu_mayor", "personas_gwangju_mayor",
                    "personas_seoul_mayor", "personas_busan_buk_gap",
                    "personas_daegu_dalseo_gap"]
}

GET /api/regions/five
{
  "regions": [
    {"key":"seoul_mayor",      "label_ko":"서울시장",              "count":185228, "available":true},
    {"key":"gwangju_mayor",    "label_ko":"광주시장",              "count":27594,  "available":true},
    {"key":"daegu_mayor",      "label_ko":"대구시장",              "count":46934,  "available":true},
    {"key":"busan_buk_gap",    "label_ko":"부산 북구 갑 (보궐)",   "count":5421,   "available":true},
    {"key":"daegu_dalseo_gap", "label_ko":"대구 달서구 갑 (보궐)", "count":10617,  "available":true}
  ]
}
```

전체 spec: http://127.0.0.1:8235/openapi.json

---

*다음 작업자: 위 §1 살아있는 서버 먼저 확인 → §2 산출물 둘러보기 → §5 Open items 또는 §7 권장 작업 중 선택 → 시작.*
