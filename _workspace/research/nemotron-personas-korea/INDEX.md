# Nemotron-Personas-Korea — Research Index

> 작성: 2026-04-26 · 팀 `nemotron-research` (6명: provenance / schema / eda / utility / api / frontend) · 데이터셋 v1 (1M rows × 26 cols × 9 shards · 1.89 GB · CC BY 4.0)

이 디렉토리는 PolitiKAST 해커톤 빌더(`data-engineer`, `sim-engineer`, `kg-engineer`, `paper-writer`, `dashboard-engineer`, `policy-engineer`)가 **Nemotron-Personas-Korea를 안전하게 활용하기 위해 알아야 할 모든 것**을 정리한 단일 진실의 원천이다.

---

## 1. 메인 보고서 4종 (먼저 읽을 것)

| # | 파일 | 분량 | 누가 봐야 하나 |
|---|------|-----|----------------|
| 01 | [`01_overview.md`](./01_overview.md) | 2,308 단어 / 11+ 인용 | **all** — 데이터셋이 어디서 왔고, 어떻게 만들어졌고, 어떻게 인용해야 하는지 |
| 02 | [`02_schema.md`](./02_schema.md) | 26 컬럼 풀스펙 | `data-engineer`(인제션 스키마), `sim-engineer`(VoterAgent 필드 접근), `kg-engineer`(노드 attribute) |
| 03 | [`03_eda.md`](./03_eda.md) | 9 차트 + 통계 | `data-engineer`(전수 분포), `policy-engineer`(region 행수→sample 예산), `paper-writer`(figures) |
| 04 | [`04_politikast_utility.md`](./04_politikast_utility.md) | 프롬프트/KG/sampling/한계 | `sim-engineer`(prompt template), `kg-engineer`(노드·엣지·firewall), `paper-writer`(Limitations) |

각 보고서는 부속 노트(`./notes/`)와 차트/CSV(`./eda_charts/`)를 상대경로로 참조한다.

---

## 2. 부속 노트 (스트림별)

### 2.1 Provenance · Lineage · License (`provenance-research`)
- [`notes/01_provenance_huggingface.md`](./notes/01_provenance_huggingface.md) — HuggingFace 페이지, 영어 원본 `Nemotron-Personas`와의 관계
- [`notes/02_synthesis_pipeline.md`](./notes/02_synthesis_pipeline.md) — NeMo Data Designer 파이프라인 (PGM → OCEAN → Gemma-4-31B-IT 2-stage)
- [`notes/03_grounding_sources.md`](./notes/03_grounding_sources.md) — KOSIS / 대법원 / NHIS / KREI / NAVER Cloud
- [`notes/04_citation.md`](./notes/04_citation.md) — CC BY 4.0 의무사항 + **BibTeX 7종** + 권장 영문 1문단 + 한국어 footer
- [`notes/05_external_verification_20260426.md`](./notes/05_external_verification_20260426.md) — Perplexity 기반 외부 재확인: 확정/미확정 provenance 항목 구분

### 2.2 Schema · Field Dictionary (`schema-doc`)
- [`notes/10_schema_raw.md`](./notes/10_schema_raw.md) — 26 컬럼 dtype + null 0% + per-column 카디널리티 (shard 0)
- [`notes/11_schema_ko_en_mapping.md`](./notes/11_schema_ko_en_mapping.md) — KO/EN 매핑 (이미지 멀티모달 확인)
- [`notes/12_persona_texts.md`](./notes/12_persona_texts.md) — 페르소나 7종 + attribute 6종 길이 + 샘플 2건
- [`notes/13_categorical_enums.md`](./notes/13_categorical_enums.md) — 9 enum 컬럼 전수 + district/occupation top30

### 2.3 EDA (`eda-analyst`)
- [`notes/20_integrity.md`](./notes/20_integrity.md) — 9 shards / 1M rows / schema 동일 / uuid unique / null 0%
- [`notes/21_demographics.md`](./notes/21_demographics.md) — age/sex/marital/education 전수
- [`notes/22_region_match.md`](./notes/22_region_match.md) — **5 region 실측 행수**
- [`notes/23_occupation_skills.md`](./notes/23_occupation_skills.md) — 직업·스킬·취미 (1.45M skills unique)
- [`notes/24_persona_length.md`](./notes/24_persona_length.md) — 7 페르소나 텍스트 길이 (median 합 957자 ≈ 2k token)

### 2.4 PolitiKAST Utility (`politikast-utility`)
- [`notes/30_prompt_field_mapping.md`](./notes/30_prompt_field_mapping.md) — 26 필드 → VoterAgent prompt slot (P0~P3)
- [`notes/31_political_signals.md`](./notes/31_political_signals.md) — 컬럼별 정치 시그널 ★표
- [`notes/32_kg_node_edge_candidates.md`](./notes/32_kg_node_edge_candidates.md) — KG 17 노드 라벨 + Cypher 의사코드 + Temporal Firewall
- [`notes/33_sampling_and_limits.md`](./notes/33_sampling_and_limits.md) — 5 region sampling 권고 + downscale ladder L0~L4

---

## 3. 차트 인덱스 (`./eda_charts/*.png`)

| 파일 | 출처 노트 | 용도 |
|------|-----------|------|
| `age_hist.png` | 21_demographics | paper Figure 후보 |
| `sex_pie.png` | 21_demographics | dashboard 카드 |
| `marital_bar.png` | 21_demographics | dashboard 카드 |
| `education_bar.png` | 21_demographics | paper Figure 후보 |
| `region_match_bar.png` | 22_region_match | **5 region sample 예산 시각화** |
| `occupation_top.png` | 23_occupation_skills | dashboard 카드 |
| `skills_top.png` | 23_occupation_skills | 부록 |
| `hobbies_top.png` | 23_occupation_skills | 부록 |
| `persona_length.png` | 24_persona_length | 프롬프트 토큰 예산 검증 |

원본 집계 CSV/JSON은 [`eda_charts/_data/`](./eda_charts/_data/)에 모두 보존.

---

## 4. 재현 스크립트 (`./scripts/`, **모두 `uv run` 표준**)

```bash
cd _workspace/research/nemotron-personas-korea
uv run scripts/integrity_check.py    # 9 shards 무결성
uv run scripts/demographics.py       # age/sex/marital/education + 차트
uv run scripts/region_match.py       # 5 region 행수
uv run scripts/occupation_skills.py  # 직업·스킬·취미 top30
uv run scripts/persona_length.py     # 7 페르소나 텍스트 길이
uv run scripts/schema_probe.py       # 컬럼 26 + 카디널리티 (shard 0)
```

각 스크립트는 PEP 723 inline metadata로 의존성을 자기완결.

---

## 5. PolitiKAST 빌더용 빠른 참조 (Cheat Sheet)

| 빌더 스킬 | 첫 번째로 읽기 | 참조 SQL/스크립트 |
|-----------|----------------|--------------------|
| `data-ingest` (`data-engineer`) | `02_schema.md` § 컬럼 사전 + `notes/20_integrity.md` | `scripts/schema_probe.py` (DDL 후보) |
| `run-simulation` (`sim-engineer`) | `04_politikast_utility.md` §3 prompt template + `notes/30_prompt_field_mapping.md` | persona 7종 합산 ≈ 2k token |
| `build-kg` (`kg-engineer`) | `notes/32_kg_node_edge_candidates.md` + `01_overview.md` §시점(2024-12 → 2026 보궐, **1.5년 시차**) | Temporal Firewall 의사코드 |
| `manage-policy` (`policy-engineer`) | `notes/22_region_match.md` + `notes/33_sampling_and_limits.md` | downscale ladder L0~L4 |
| `update-paper` (`paper-writer`) | `notes/04_citation.md` (BibTeX) + `04_politikast_utility.md` §6 (Limitations) | 모든 차트 `eda_charts/*.png` |
| `launch-dashboard` (`dashboard-engineer`) | `ui/eda-explorer/` (별도 EDA 인터랙티브 앱, port 8234) | FastAPI :8235 endpoints |

### 5.1 Contract region 행수 (확정)
- 서울시장 **185,228** / 광주시장 **27,594** / 대구시장 **46,934** / 부산 북구 갑 **5,421** / 대구 달서구 갑 **10,617**
- 기준은 `_workspace/contracts/data_paths.json`. `daegu_dalseo_gap`은 `daegu_mayor`의 부분집합이므로 5개 행수 합계는 disjoint population이 아니다.

### 5.2 라이선스 한 줄 (CC BY 4.0)
> Built with NVIDIA `Nemotron-Personas-Korea` (CC BY 4.0). https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea

`notes/04_citation.md`에 BibTeX 7종 + 한국어 dashboard footer 박제됨.

---

## 6. 알려진 한계 (paper Limitations 절 골격)

1. **age 19+ cutoff** — 만 18세 유권자(2026 지방선거 신규 유권자) 미커버
2. **gender binary only** — `sex` 2-class, nonbinary 미반영
3. **변수 독립성 가정** — PGM 단변량 분포 product-sample. 성별×전공, 직업×지역 결합 효과 부재
4. **시점 단일 (2024-12)** — KG `Temporal Firewall` 필수. 2026 사건은 KG에서만 보강
5. **표면형 중복** — occupation 2,120 unique / skills 1.45M unique. 임베딩 클러스터링 또는 KSCO 11그룹 롤업 권장
6. **정치성향 직접 컬럼 부재** — `04_politikast_utility.md` §3 정치 시그널 ★표 + KG 외부 보강 의존

---

## 7. 후속 작업 / 미확인

- **보궐 region 확정** → ✅ `busan_buk_gap`, `daegu_dalseo_gap` 반영 완료 (`region_match.csv`, `04_politikast_utility.md` §5)
- README features 광고(40+) vs 실제(26 컬럼) 차이 — 2026-04-26 외부 재확인 후에도 train split 26 컬럼을 repo-local truth로 유지
- PGM 정확한 구조, OCEAN 한국 보정 여부, `military_status` grounding 출처 — 2026-04-26 Perplexity 재확인에서도 미확정. 확인된 것처럼 쓰지 말 것
- `*_list` 컬럼: DuckDB는 string으로 보고하나 실제는 Python list repr → 인제션 시 `ast.literal_eval` + DuckDB LIST 변환 권장

---

## 8. 별도 산출물 — EDA 인터랙티브 대시보드

리서치 결과를 인터랙티브로 탐색할 수 있도록 별도 frontend가 동시 빌드 중 (팀원 `eda-api-builder` + `eda-frontend-builder`).

- 위치: `/Users/girinman/repos/cmux-hackathon-politicast/ui/eda-explorer/`
- 백엔드: FastAPI on `:8235` (DuckDB 공유 — `_workspace/db/politikast.duckdb` 우선, parquet fallback)
- 프론트엔드: Vite + React + TS + Tailwind + ECharts on `:8234`
- 메인 PolitiKAST FastAPI/React 앱과 호환: HTTP API 호출 또는 iframe 임베드

빌드 완료 후 이 INDEX 갱신.

---

*이 INDEX는 lead가 모든 스트림 종료 후 1회 작성. 변경 시 lead 또는 paper-writer에게 알릴 것.*
