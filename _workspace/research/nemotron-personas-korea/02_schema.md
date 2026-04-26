# 02. Nemotron-Personas-Korea — 스키마 풀스펙

> **버전:** 2026-04-26 (Phase 1)
> **작성:** `schema-doc` 에이전트 (nemotron-research 팀)
> **데이터 검증 범위:** `data/train-00000-of-00009.parquet` (1 / 9 shard, **n=111,112 rows**) — 전수 통계는 `eda-analyst` 담당.
> **세부 노트:**
> - `notes/10_schema_raw.md` — README features + DuckDB DESCRIBE
> - `notes/11_schema_ko_en_mapping.md` — KO/EN 다이어그램 매핑
> - `notes/12_persona_texts.md` — 페르소나 텍스트 7+6종 샘플·길이
> - `notes/13_categorical_enums.md` — 카테고리 enum 전수
> - `scripts/schema_probe.py` + `scripts/schema_probe_output.json` (재현)

---

## 1) Headline

| 항목 | 값 |
|------|---|
| 총 컬럼 | **26** (uuid 1 + persona 7 + persona attribute 6 + demographic·geo 12) |
| 총 row | 1,000,000 (9 shard × ~111,111) — 본 노트는 shard 0 검증 |
| 총 토큰 | 1.7 B (페르소나 1 B) |
| 라이선스 | CC BY 4.0 |
| 연령 제약 | **만 19세 이상 성인** |
| Null 비율 | 전 컬럼 0.000% (shard 0) |
| 합성 방식 | NeMo Data Designer + PGM + google/gemma-4-31B-it |

## 2) 컬럼 26개 — 한 표 요약

| # | column | dtype | distinct (n=111,112) | null% | 그룹 | 비고 |
|---|--------|-------|----------------------|-------|------|------|
| 1 | `uuid` | string | 111,112 | 0 | id | 32-char hex (UUID-v4 dashless) |
| 2 | `professional_persona` | string | 111,112 | 0 | persona-7 | 직업 서사, avg 160 char |
| 3 | `sports_persona` | string | 111,112 | 0 | persona-7 | 운동 서사, avg 134 char |
| 4 | `arts_persona` | string | 111,112 | 0 | persona-7 | 예술 서사, avg 138 char |
| 5 | `travel_persona` | string | 111,112 | 0 | persona-7 | 여행 서사, avg 135 char |
| 6 | `culinary_persona` | string | 111,112 | 0 | persona-7 | 식문화 서사, avg 142 char |
| 7 | `family_persona` | string | 111,112 | 0 | persona-7 | 가족 서사, avg 144 char |
| 8 | `persona` | string | 111,112 | 0 | persona-7 | concise 1~2문장 요약, avg 81 char |
| 9 | `cultural_background` | string | 111,112 | 0 | attr-6 | 지역·세대 배경 서사 |
| 10 | `skills_and_expertise` | string | 111,112 | 0 | attr-6 | 전문성 서사 |
| 11 | `skills_and_expertise_list` | string | 111,107 | 0 | attr-6 | **Python list `repr()` 문자열** ⚠ |
| 12 | `hobbies_and_interests` | string | 111,112 | 0 | attr-6 | 취미 서사 |
| 13 | `hobbies_and_interests_list` | string | 111,112 | 0 | attr-6 | **Python list `repr()` 문자열** ⚠ |
| 14 | `career_goals_and_ambitions` | string | 111,112 | 0 | attr-6 | 경력 목표 서사 |
| 15 | `sex` | string | 2 | 0 | demo-12 | `여자` 50.3% / `남자` 49.7% |
| 16 | `age` | int64 | 81 | 0 | demo-12 | 19~99, median 51 |
| 17 | `marital_status` | string | 4 | 0 | demo-12 | 배우자있음/미혼/사별/이혼 |
| 18 | `military_status` | string | 2 | 0 | demo-12 | 비현역 99.5% / 현역 0.5% |
| 19 | `family_type` | string | 39 | 0 | demo-12 | 가구 동거 구성 |
| 20 | `housing_type` | string | 6 | 0 | demo-12 | 아파트 62%/단독 17%/… |
| 21 | `education_level` | string | 7 | 0 | demo-12 | 무학~대학원 |
| 22 | `bachelors_field` | string | 11 | 0 | demo-12 | 해당없음 67% + 10 분야 |
| 23 | `occupation` | string | 1,632 | 0 | demo-12 | KSCO 세분류 + 무직 36.8% |
| 24 | `district` | string | 252 | 0 | demo-12 | `<province>-<시군구 [구]>` |
| 25 | `province` | string | 17 | 0 | demo-12 | 약식 표기 (경상남/충청북 등) ⚠ |
| 26 | `country` | string | 1 | 0 | demo-12 | 상수 `대한민국` |

## 3) 그룹별 핵심 enum

### sex / marital / military

```
sex            : 여자(50.3%) | 남자(49.7%)
marital_status : 배우자있음(59.1%) | 미혼(25.9%) | 사별(8.7%) | 이혼(6.3%)
military_status: 비현역(99.5%) | 현역(0.5%)
```

### education / bachelors_field

```
education_level: 무학(2.6%) → 초등학교(8.1%) → 중학교(8.3%) → 고등학교(33.3%)
                → 2~3년제 전문대학(14.9%) → 4년제 대학교(27.1%) → 대학원(5.5%)
bachelors_field: 해당없음(67.3%) | 공학·제조·건설(6.8%) | 경영·행정·법(5.5%)
                | 예술·인문(4.8%) | 보건·복지(3.6%) | 교육(3.1%) | 정보통신기술(2.9%)
                | 서비스(1.9%) | 사회과학·언론(1.7%) | 자연과학·수학(1.6%)
                | 농림어업·수의학(0.6%)
```

### housing_type / family_type

```
housing_type   : 아파트(62.1%) | 단독주택(17.0%) | 다세대주택(11.5%)
                | 주택 이외의 거처(5.9%) | 연립주택(2.5%) | 비주거용 건물 내 주택(1.0%)
family_type    : 39종 (top: 배우자·자녀와 거주 27.0% / 배우자와 거주 20.7%
                / 혼자 거주 14.0% / 부모와 동거 9.3% / …)
                ⇒ 시뮬 시 7~8 그룹으로 축약 권장
```

### province (17, 약식 표기)

| province | shard0 % | 5 region |
|----------|----------|----------|
| 경기 | 26.23% | (의왕 포함) |
| 서울 | 18.57% | ★ |
| 부산 | 6.52% |  |
| 경상남 | 6.22% |  |
| 인천 | 5.89% |  |
| 경상북 | 4.99% |  |
| 대구 | 4.70% | ★ |
| 충청남 | 4.20% |  |
| 전라남 | 3.47% |  |
| 전북 | 3.39% |  |
| 충청북 | 3.08% |  |
| 강원 | 3.00% |  |
| 대전 | 2.90% |  |
| 광주 | 2.73% | ★ |
| 울산 | 2.10% |  |
| 제주 | 1.31% |  |
| 세종 | 0.70% |  |

> **약식 표기 비표준화 ⚠:** "경상남/경상북/충청남/충청북/전라남"은 도(道) 생략, 그러나 "전북"은 줄임형. KOSIS 표준("경상남도") join 시 매핑 사전 필요.

## 4) PolitiKAST 5 region 매칭 시안

| Region | 기준 query | shard 0 측정 추정 | 1 M 추정 |
|--------|-----------|-------------------|----------|
| seoul_mayor | `province = '서울'` | 20,638 | 185,228 |
| gwangju_mayor | `province = '광주'` | 3,031 | 27,594 |
| daegu_mayor | `province = '대구'` | 5,220 | 46,934 |
| busan_buk_gap | `province = '부산' AND district = '부산-북구'` | (전수 측정) | 5,421 |
| daegu_dalseo_gap | `province = '대구' AND district = '대구-달서구'` | (전수 측정) | 10,617 |

> `daegu_dalseo_gap`은 `daegu_mayor`의 부분집합이다. 표본 추출/집계는 contest별 scope로 처리한다.

## 5) 페르소나 텍스트 길이 (char, shard 0)

| field | min | avg | p50 | p90 | max |
|-------|-----|-----|-----|-----|-----|
| `professional_persona` | 60 | 159.5 | 163 | 196 | 276 |
| `sports_persona` | 56 | 133.7 | 137 | 165 | 248 |
| `arts_persona` | 57 | 138.2 | 142 | 169 | 238 |
| `travel_persona` | 55 | 135.1 | 139 | 166 | 232 |
| `culinary_persona` | 64 | 142.0 | 146 | 175 | 252 |
| `family_persona` | 60 | 143.9 | 149 | 176 | 240 |
| `persona` (concise) | 44 | **81.5** | 81 | 95 | 164 |
| `cultural_background` | 59 | 135.3 | 139 | 170 | 283 |
| `skills_and_expertise` | 54 | 121.0 | 124 | 153 | 236 |
| `skills_and_expertise_list` | 37 | 78.4 | 78 | 96 | 169 |
| `hobbies_and_interests` | 57 | 128.9 | 133 | 164 | 305 |
| `hobbies_and_interests_list` | 39 | 79.2 | 78 | 99 | 171 |
| `career_goals_and_ambitions` | 51 | 118.3 | 121 | 151 | 213 |

> 13 컬럼 합산 평균 ≈ 1,694 char/row → ~1.2~1.5 K token. README 1.7 B token / 1 M row와 일치.

## 6) 알려진 함정 & 인제션 권장사항

1. **`*_list` 컬럼 = string repr of Python list** — `ast.literal_eval()` 또는 정규식 파싱 필요. DuckDB 인제션 시 `LIST<VARCHAR>` 변환 컬럼 추가 권장.
2. **`province` 약식 표기** — 외부 join 전 `province_normalize.json` 매핑 사전 적용. 5 region 추출 시 직접 enum 비교만 사용해도 OK.
3. **`district`** — 단일 하이픈 + 공백 구분(예: `경기-고양시 덕양구`). split 시 `'-'` 1회만 split, 뒷부분은 raw로.
4. **`occupation` 1,632 distinct** — 시뮬 단순화 위해 KSCO 대분류(11그룹)로 롤업 권장. 매핑 사전은 데이터 인제션 단계에서 큐레이션 필요.
5. **이름·성격 traits 미수록** — voter agent 호명 시 persona 텍스트 내부 호칭(예: "전기태 씨")만 사용. 필드 없음.
6. **연령 19+** — 18세 청년 유권자 매칭 시 19세 페르소나로 근사 + Limitations에 명시.
7. **gender 부재** — `sex`만 있고 gender identity 없음. paper Limitations 섹션에 명시.
8. **timestamp 부재** — 단일 시점(2026-04-20) 가정. Temporal Information Firewall은 데이터셋 외부(KG 이벤트)에 적용.

## 7) 후속 작업 의존성

| 후속 노트 | 사용 정보 |
|-----------|-----------|
| `03_eda.md` (eda-analyst) | shard 0~8 무결성, 5 region 전수 매칭 (#13), 분포 차트 |
| `04_politikast_utility.md` (politikast-utility) | voter agent 입력 컬럼 (`persona`/`cultural_background`/`occupation`/`age`/`sex`/`region`), KG 노드 후보 (occupation, district, family_type, education_level) |
| `01_overview.md` (provenance-research) | 라이선스, BibTeX, KOSIS/대법원/NHIS/KREI/NAVER 시드 인용 |
| paper `Limitations` (paper-writer) | 19+ adult-only / PGM 독립성 / gender 부재 / 약식 province 표기 |

## 8) 재현

```bash
# uv 사용 (시스템 python/pip 금지). PEP 723 inline metadata가 의존성 자동 해결.
cd /Users/girinman/repos/cmux-hackathon-politicast/_workspace/research/nemotron-personas-korea
uv run scripts/schema_probe.py
# → scripts/schema_probe_output.json
```

ad-hoc DuckDB 쿼리:

```bash
uv run --with duckdb --with pyarrow python -c "
import duckdb
print(duckdb.sql(\"DESCRIBE SELECT * FROM read_parquet('/Users/girinman/datasets/Nemotron-Personas-Korea/data/train-00000-of-00009.parquet')\"))
"
# 또는 DuckDB CLI: uvx duckdb -c "..."
```
