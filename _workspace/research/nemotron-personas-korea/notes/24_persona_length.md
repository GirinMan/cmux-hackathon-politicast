# 24. Persona 텍스트 길이 / 결측 통계 (전수)

> Task #15 — `eda-analyst`. 재현: `scripts/persona_length.py`.
> 데이터: `eda_charts/_data/persona_length_summary.csv`, `persona_length_missing.csv`.

분석 대상 텍스트 필드 9종:
- 7 페르소나: `professional_persona / sports_persona / arts_persona / travel_persona / culinary_persona / family_persona / persona`
- 2 보조: `cultural_background`, `career_goals_and_ambitions`

## 1. 결측 (NULL + 빈 문자열) 전수

| field | NULL | empty | missing_total | missing_ratio |
|---|---:|---:|---:|---:|
| professional_persona | 0 | 0 | 0 | 0.0000 |
| sports_persona | 0 | 0 | 0 | 0.0000 |
| arts_persona | 0 | 0 | 0 | 0.0000 |
| travel_persona | 0 | 0 | 0 | 0.0000 |
| culinary_persona | 0 | 0 | 0 | 0.0000 |
| family_persona | 0 | 0 | 0 | 0.0000 |
| persona | 0 | 0 | 0 | 0.0000 |
| cultural_background | 0 | 0 | 0 | 0.0000 |
| career_goals_and_ambitions | 0 | 0 | 0 | 0.0000 |

→ **결측·빈 문자열 0** (1M 전수). 모든 페르소나 필드를 항상 사용 가능. (합성 데이터 특성상 placeholder 가능성도 있어 길이 분포로 cross-check.)

## 2. 길이 통계 (chars, 전수 1M)

| field | min | p05 | p25 | p50 | p75 | p95 | max | mean | std |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| professional_persona | 60 | 105 | 140 | 163 | 181 | 206 | 306 | 159.5 | 30.3 |
| culinary_persona | 59 | 93 | 124 | 146 | 162 | 183 | 277 | 142.0 | 27.9 |
| family_persona | 58 | 93 | 126 | 149 | 164 | 183 | 252 | 144.0 | 27.9 |
| arts_persona | 54 | 91 | 121 | 142 | 157 | 177 | 260 | 138.2 | 26.3 |
| travel_persona | 51 | 87 | 119 | 139 | 153 | 174 | 248 | 135.1 | 26.4 |
| sports_persona | 51 | 87 | 116 | 137 | 152 | 173 | 293 | 133.7 | 26.2 |
| cultural_background | 55 | 87 | 112 | 139 | 156 | 179 | 299 | 135.3 | 28.8 |
| career_goals_and_ambitions | 47 | 80 | 95 | 121 | 138 | 158 | 243 | 118.3 | 25.5 |
| **persona** (요약) | **42** | **65** | **74** | **81** | **88** | **100** | **174** | **81.5** | **10.6** |

![Persona length boxplot](./eda_charts/persona_length.png)

> Boxplot은 10k reservoir sample(seed=42), 표는 전수 1M.

## 3. 인사이트

1. **`persona`는 짧은 한 줄 요약** (median 81자, max 174). 다른 6개 도메인 페르소나는 **3–4줄 단락**(median 137–163자). schema-doc의 페르소나 텍스트 7종 분류와 정합.
2. **professional_persona가 가장 김** (median 163자, max 306) — 직업 정보가 가장 풍부. voter agent 프롬프트 토큰 예산 산정 시 이 필드를 우선.
3. **분포 안정**: std 10–30자, p05–p95 폭 100–130자 → 동일 템플릿에서 합성된 흔적(생성 분포의 일관성). 페르소나 다양성은 텍스트 길이가 아니라 어휘에서 확인 필요(Task #14에서 unique skills/hobbies 95만~145만 확인됨).
4. **결측 0**: 모든 9 필드 1M행에서 NULL/빈 문자열 0 → 페르소나 텍스트 모두 안전하게 voter agent 프롬프트에 inject 가능.

## 4. PolitiKAST 토큰 예산 추정

- 한국어 1자 ≈ 1.5–2 BPE token. 평균 페르소나 텍스트 7종 합산:
  - sum(median) = 163+137+142+139+146+149+81 = **957 chars** ≈ **1.4–1.9 k tokens**
  - + cultural_background(139) + career_goals(121) = **1,217 chars** ≈ **1.8–2.5 k tokens**
- skills(4 항목 × 평균 12자 = 48) + hobbies(4 × 12 = 48) ≈ 추가 100 chars (~150 token).
- → **페르소나 fully injected 시 voter agent 시스템 prompt ≈ 2 k token 정도** (Gemini 컨텍스트 한도 상 매우 여유).

## 5. 권고

- voter agent 프롬프트에 **professional + family + persona** 핵심 3종은 항상 inject. 나머지(sports/arts/travel/culinary)는 시나리오 토픽에 맞춰 선택적 inject.
- `career_goals_and_ambitions`(median 121자)는 정치 정책 매핑 시 가장 유용 — 단독 필드로 KG에 저장 가치.
- 결측 핸들링 코드는 불필요(0 결측). 단 **하루 더 늘어난 split**(예: HuggingFace v2)을 가져올 경우 재검증 필요.

---
재현: `python3 scripts/persona_length.py` (DuckDB 풀스캔 + 10k reservoir sample, ~25s).
