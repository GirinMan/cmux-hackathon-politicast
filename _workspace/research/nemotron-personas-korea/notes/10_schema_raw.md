# 10. README features 풀스펙 (Schema Raw)

> **출처:** `/Users/girinman/datasets/Nemotron-Personas-Korea/README.md` (HuggingFace dataset card) `dataset_info.features` 블록 + `train-00000-of-00009.parquet` shard 1개 검증.
> **검증 도구:** DuckDB 1.5.2 (`scripts/schema_probe.py`, 출력 `scripts/schema_probe_output.json`).
> **샘플 범위:** shard 0 (`train-00000-of-00009.parquet`) **111,112 rows** — 전체 1,000,000 rows의 약 11.11%. 9 shard 균등 분포 가정 시 1M/9 ≒ 111,111. 전수 통계는 eda-analyst 담당.

## 0) 헤드라인

| 항목 | 값 |
|------|---|
| 총 컬럼 수 | **26** (uuid 1 + persona 7 + persona-attribute 6 + demographic·geo 12) |
| README 표기 | "26 fields: 7 persona fields, 6 persona attribute fields, 12 demographic & geographic contextual fields, and 1 unique identifier" |
| 토큰 규모 | 1.7 B tokens (페르소나 1 B), 1 M records, 2.0 GB |
| 라이선스 | CC BY 4.0 |
| 연령 제약 | **만 19세 이상 성인만** (한국법상 성년) — 미성년자 미포함 |
| 한계(README 명시) | (1) 변수 간 독립성 가정 (예: 성별×전공 교호효과 미반영), (2) gender(사회적 성)는 데이터 부재로 미반영, biological sex만 포함, (3) 이름·성격 traits는 본 데이터셋에서 제외 (Data Designer extended 버전에만 포함) |

## 1) 컬럼 풀스펙 (26개)

shard 0 (n=111,112) 측정 결과. **전 컬럼 null 0%**.

### 1-1) 식별자 (1)

| name | dtype | null% | cardinality | min/avg/max len | 비고 |
|------|-------|-------|-------------|------------------|------|
| `uuid` | VARCHAR | 0.000 | 111,112 (=row count, 100% unique) | 32 / 32 / 32 | 32-char hex (UUID-v4 dashless). PK. |

### 1-2) Persona 텍스트 (7)

전 7종 모두 **per-row 고유 (자유 서사)**, null 0%, 한국어 자연어.

| name | dtype | null% | cardinality | char min/avg/p50/p90/max | 비고 |
|------|-------|-------|-------------|--------------------------|------|
| `professional_persona` | VARCHAR | 0.000 | 111,112 | 60 / 159.5 / 163 / 196 / 276 | 직업 관련 핵심 분야·스킬·행동 |
| `sports_persona`       | VARCHAR | 0.000 | 111,112 | 56 / 133.7 / 137 / 165 / 248 | 신체활동·피트니스 선호·습관 |
| `arts_persona`         | VARCHAR | 0.000 | 111,112 | 57 / 138.2 / 142 / 169 / 238 | 예술 향유·창작 활동 |
| `travel_persona`       | VARCHAR | 0.000 | 111,112 | 55 / 135.1 / 139 / 166 / 232 | 여행 선호 스타일 |
| `culinary_persona`     | VARCHAR | 0.000 | 111,112 | 64 / 142.0 / 146 / 175 / 252 | 식문화·외식 패턴 |
| `family_persona`       | VARCHAR | 0.000 | 111,112 | 60 / 143.9 / 149 / 176 / 240 | 가족 관계·역학 |
| `persona`              | VARCHAR | 0.000 | 111,112 | 44 / **81.5** / 81 / 95 / 164 | **요약(concise) 버전** — 1~2문장 |

### 1-3) Persona attribute (6)

| name | dtype | null% | cardinality | char min/avg/p50/p90/max | 비고 |
|------|-------|-------|-------------|--------------------------|------|
| `cultural_background`         | VARCHAR | 0.000 | 111,112 | 59 / 135.3 / 139 / 170 / 283 | 문화·세대·지역 배경 서사 |
| `skills_and_expertise`        | VARCHAR | 0.000 | 111,112 | 54 / 121.0 / 124 / 153 / 236 | 전문성·스킬 자유 서술 |
| `skills_and_expertise_list`   | VARCHAR | 0.000 | 111,107 (≈100%) | 37 / 78.4 / 78 / 96 / 169 | **콤마/리스트 형식** (실제 dtype은 string, 다섯 행만 동일 — 사실상 row-unique) |
| `hobbies_and_interests`       | VARCHAR | 0.000 | 111,112 | 57 / 128.9 / 133 / 164 / 305 | 취미 자유 서술 |
| `hobbies_and_interests_list`  | VARCHAR | 0.000 | 111,112 | 39 / 79.2 / 78 / 99 / 171 | 리스트 형식 |
| `career_goals_and_ambitions`  | VARCHAR | 0.000 | 111,112 | 51 / 118.3 / 121 / 151 / 213 | 경력 목표·포부 |

> 주의: `*_list` 컬럼은 `dtype: string` (배열 아님) — 콤마 구분 텍스트로 후처리 필요.

### 1-4) Demographic & Geographic context (12)

| name | dtype | null% | cardinality | example | 비고 |
|------|-------|-------|-------------|---------|------|
| `sex`             | VARCHAR | 0.000 | **2** | `여자`(50.3%) / `남자`(49.7%) | biological sex only (gender 미반영) |
| `age`             | BIGINT  | 0.000 | **81** | min 19 / median 51 / max 99 (avg 50.6) | 19세 미만 0건, 100+ 0건 (shard 0 기준) |
| `marital_status`  | VARCHAR | 0.000 | **4** | `배우자있음`(59.1%) / `미혼`(25.9%) / `사별`(8.7%) / `이혼`(6.3%) | |
| `military_status` | VARCHAR | 0.000 | **2** | `비현역`(99.5%) / `현역`(0.5%) | "현역" = 군 복무 중 |
| `family_type`     | VARCHAR | 0.000 | **39** | `배우자·자녀와 거주`(27.0%) / `배우자와 거주`(20.6%) / `혼자 거주`(14.0%) … | 가구 유형, 다단계 동거 형태 |
| `housing_type`    | VARCHAR | 0.000 | **6** | `아파트`(62.1%) / `단독주택`(17.0%) / `다세대주택`(11.5%) / `주택 이외의 거처`(5.9%) / `연립주택`(2.5%) / `비주거용 건물 내 주택`(1.0%) | |
| `education_level` | VARCHAR | 0.000 | **7** | `고등학교`(33.3%) / `4년제 대학교`(27.1%) / `2~3년제 전문대학`(14.9%) / `중학교`(8.3%) / `초등학교`(8.1%) / `대학원`(5.5%) / `무학`(2.6%) | |
| `bachelors_field` | VARCHAR | 0.000 | **11** | `해당없음`(67.3%) / `공학·제조·건설`(6.8%) / `경영·행정·법`(5.5%) / `예술·인문`(4.8%) / `보건·복지` / `교육` / `정보통신기술` / `서비스` / `사회과학·언론` / `자연과학·수학` / `농림어업·수의학` | "해당없음" = 비대졸 |
| `occupation`      | VARCHAR | 0.000 | **1,632** | `무직`(36.8%) / `건물 청소원` / `건물 경비원` / `경리 사무원` / `사무 보조원` / `일반 비서` … | KSCO(한국표준직업분류) 세분류 수준 |
| `district`        | VARCHAR | 0.000 | **252** | `경기-화성시` / `서울-송파구` / `서울-강서구` / `인천-서구` / `경기-평택시` … | `<province>-<시군구>` 또는 `<province>-<시 구>` 포맷, "-" 단일 구분자 |
| `province`        | VARCHAR | 0.000 | **17** | `경기`(26.2%) / `서울`(18.6%) / `부산`(6.5%) / `경상남`(6.2%) / `인천`(5.9%) / `경상북` / `대구` / `충청남` / `전라남` / `전북` / `충청북` / `강원` / `대전` / `광주` / `울산` / `제주` / `세종`(0.7%) | **약식 표기**: "경상남"(경상남도), "충청북"(충청북도), "전북"(전라북도). 5 region 매칭 시 정규화 필요 |
| `country`         | VARCHAR | 0.000 | **1** | `대한민국`(100%) | 상수 |

## 2) 토큰 통계 추정 (단일 shard 기준)

페르소나 7종 + attribute 5종 (list 2종은 짧음) ≒ 평균 char 합계 ≈ 1,694 chars/row.
한국어 char-token 비 ~0.7~0.9 적용 시 row당 ~1,200~1,500 tokens. README "1.7 B tokens / 1 M rows" ≒ 1,700 tokens/row와 일치.

## 3) Schema 신뢰성 평가

- **장점:** PGM 기반으로 marginal 분포(나이·지역·교육·직업)는 KOSIS 등 공공통계와 정합 (README 분석 인용). null/타입 일관성 100%.
- **약점/리스크 (PolitiKAST 사용 관점):**
  - **Adult-only(19+)** — 청년 유권자 18세 정확 매칭 불가 (대선·지선 모두 18세부터 투표 가능). 한계 명시 필요.
  - **gender 미반영** — voter agent 정치성향 inference에 sex(생물학적)만 사용 가능, gender identity는 추정 불가.
  - **PGM 독립성 가정** — 직업×성별×전공 교호효과 부재. 페르소나 텍스트(LLM 생성)에서 일부 보정되나 ground-truth 아님.
  - **이름·성격 traits 미수록** — voter agent 호명 시 텍스트 내 "전기태 씨", "최은지 씨" 등 페르소나 내부 호칭만 사용 가능.
  - **time-stamp 부재** — 시점 기준 freezing 위해 dataset 자체 타임스탬프(2026-04-20 release) 사용 필요. Temporal Information Firewall 설계 시 모든 행을 단일 timestamp로 취급.

## 4) 후속 작업 핸드오프

- **#7 (KO↔EN 매핑):** 26개 컬럼 모두 `name: dtype: string` 동일, 의미 매핑은 `nemotron_personas_korea_schema_{ko,en}.png` 시각 확인 → `notes/11_schema_ko_en_mapping.md`.
- **#8 (페르소나 텍스트 샘플):** sample 2건은 본 노트 측정에 포함 (uuid `03b4f36a18e6469386d0286dddd513c8` 광주 70대 남, `73f75d42a3934626b0d9a4bff062715a` 서울 70대 여). 자유 서사 7종 길이 통계 → `notes/12_persona_texts.md`.
- **#9 (categorical enums 전수):** `enum_categorical` 9개 컬럼 (sex, marital_status, military_status, family_type, housing_type, education_level, bachelors_field, country, province) + occupation/district top30 → `notes/13_categorical_enums.md`.
- **#10 (통합 02_schema.md):** 위 4개 노트 통합.
