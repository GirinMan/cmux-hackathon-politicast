# 30 — Voter Agent 프롬프트 필드 매핑

> Task #17 · owner: politikast-utility
> Source: `Nemotron-Personas-Korea/README.md` (26 fields), `_workspace/contracts/api_contract.json` (`voter_request_schema`)
> Linked: `../notes/13_categorical_enums.md` (schema-doc, 진행 중), `../notes/22_region_match.md` (eda-analyst, 진행 중)

본 노트는 Nemotron-Personas-Korea 의 26개 필드를 PolitiKAST `VoterAgent` 의 system / user prompt 슬롯에 어떻게 주입할지 매핑한다. 매핑 원칙은 다음 세 가지다.

1. **api_contract 준수** — `voter_request_schema.persona_block` 정의("concise + professional + family + cultural_background")를 기본으로 삼되, 정치 의사결정에 결정적인 인구통계 컨텍스트(`age`, `sex`, `province`, `district`, `education_level`, `occupation`, `marital_status`, `housing_type`, `family_type`)를 별도 라인으로 노출한다.
2. **토큰 절약** — 7종 페르소나 텍스트(`professional / sports / arts / travel / culinary / family / persona`)를 모두 넣으면 토큰 비용·rate-limit이 폭주한다. region별 timestep×persona 수가 수천 단위이므로(`llm_strategy.json` 참조: 6h × 60% × 50 RPM 기준 ≈ 10.8k 호출), persona당 1.0–1.5k char 이내로 압축한다.
3. **정치성향 leakage 차단** — 합성 페르소나에 정치 키워드가 거의 없으므로(README "정치" 언급 없음), KG-derived `context_block`이 정치 정보의 단일 출처가 되도록 한다. persona text는 인구통계·생활양식·관심사만 노출한다.

## 1. 26 필드 → prompt slot 매핑 표

| 필드 (Nemotron) | dtype | prompt slot | 위치 | 우선순위 | 비고 |
|---|---|---|---|---|---|
| `uuid` | string | `persona_id` (메타) | request 메타 | P0 | 캐시 키 / interview log 식별 |
| `age` | int64 | demographics 헤더 | persona_block L1 | P0 | 세대 효과(20대/60대 vs)에 핵심 |
| `sex` | string | demographics 헤더 | persona_block L1 | P0 | gender gap 분석 |
| `province` | string | location 헤더 | persona_block L2 | P0 | region filter — request에서 region_id로 매핑 |
| `district` | string | location 헤더 | persona_block L2 | P0 | 도시/농촌 구분 (서울 강남 vs 강북 등) |
| `country` | string | — | (drop) | P3 | 모두 "대한민국" — 정보량 0 |
| `marital_status` | string | demographics 헤더 | persona_block L1 | P1 | 가족부양 정책 sensitivity |
| `military_status` | string | demographics 헤더 | persona_block L1 | P2 | 안보·국방 이슈 시그널 (남성 한정) |
| `family_type` | string | family slot | persona_block L3 | P1 | 가족정책·돌봄·보육 sensitivity |
| `housing_type` | string | family slot | persona_block L3 | P1 | 부동산·전월세·LTV 정책 sensitivity |
| `education_level` | string | demographics 헤더 | persona_block L1 | P0 | 교육·이념 상관 (KOSIS 통상 패턴) |
| `bachelors_field` | string | professional slot | persona_block L4 | P2 | STEM/인문 차이 — 이슈 priming |
| `occupation` | string | professional slot | persona_block L4 | P0 | 자영업/임금근로/공무원 → 경제정책 sensitivity 핵심 |
| `professional_persona` | string (text) | professional slot | persona_block L4 | P0 | 자유서술 — 직업 디테일 |
| `family_persona` | string (text) | family slot | persona_block L3 | P0 | 가족·세대 갈등·부양 부담 표현 |
| `cultural_background` | string (text) | cultural slot | persona_block L5 | P0 | 종교/지역정체성 일부 — 정치성향 시그널 잠재 |
| `persona` | string (text) | concise slot | persona_block L0 (요약) | P0 | 한 줄 요약 — system prompt 진입점 |
| `skills_and_expertise` | string (text) | (drop in P0) | — | P3 | 정치 결정에 약함 |
| `skills_and_expertise_list` | string | (drop in P0) | — | P3 | 토큰 비용 |
| `hobbies_and_interests` | string (text) | lifestyle slot | persona_block L6 (선택) | P2 | 미디어 소비 추정 (스포츠팬·등산·독서 등) |
| `hobbies_and_interests_list` | string | (drop) | — | P3 | 자유서술이 있으면 충분 |
| `career_goals_and_ambitions` | string (text) | (drop in P0) | — | P3 | 미래지향 — vote choice 약함 |
| `sports_persona` | string (text) | (drop) | — | P3 | 정치 비관련 |
| `arts_persona` | string (text) | (drop) | — | P3 | 정치 비관련 |
| `travel_persona` | string (text) | (drop) | — | P3 | 정치 비관련 |
| `culinary_persona` | string (text) | (drop) | — | P3 | 정치 비관련 |

> 우선순위 정의: **P0 = 항상 포함**, **P1 = persona_block 압축 후 여유 시 포함**, **P2 = `instruction_mode == "virtual_interview"` 시에만 포함**, **P3 = drop**.

토큰 budget 예상치 (UTF-8 한글 1자 ≈ 1.7 토큰 가정):
- P0만: 약 350~600 토큰/페르소나
- P0+P1: 약 600~900 토큰/페르소나
- P0+P1+P2 (인터뷰 모드): 약 900~1500 토큰/페르소나

## 2. `persona_block` 직렬화 형식 (권고)

```
[L0] {persona}                                      # concise 요약 1~2문장
[L1] {age}세 {sex} · 학력: {education_level} · 혼인: {marital_status} · 군 복무: {military_status}
[L2] 거주: {province} {district}
[L3] 가족: {family_type} · 주거: {housing_type}
     {family_persona}                               # 자유서술
[L4] 직업: {occupation} (전공: {bachelors_field})
     {professional_persona}                         # 자유서술
[L5] 문화 배경: {cultural_background}
[L6] 관심사: {hobbies_and_interests}                # virtual_interview 모드에만
```

## 3. VoterAgent system prompt 템플릿 (P0)

```text
당신은 한국 시민이다. 아래 인구통계·생활 배경을 가진 한 사람으로서 사고하고 답한다.
- 당신의 정치 성향, 지지 정당, 과거 투표 이력은 데이터에 명시되지 않았다. 따라서
  배경(연령·지역·직업·가족·문화)에서 합리적으로 추정한다.
- 외부에서 학습한 실제 정치인 정보, 2024년 이후 사건은 사용하지 않는다.
- 답변은 반드시 JSON 한 객체로 출력한다. 부가 텍스트 금지.

[페르소나]
{persona_block}

[선거 컨텍스트 (시점 t={timestep})]
- 지역/선거: {region_id} · {contest_id}
- 후보 목록:
{candidates_bullets}      # 형식: "- {id}: {name} ({party})  withdrawn={bool}"

[최근 사건·여론·담론 (KG 기반, 시점 t 이전만)]
{context_block}

[지시]
모드: {instruction_mode}
- secret_ballot: 비밀투표. `vote`/`turnout`/`confidence`/`key_factors`만 응답. `reason` 빈 문자열.
- poll_response: 여론조사 응답. 위 + 짧은 `reason` (<=120자).
- virtual_interview: 인터뷰. 위 + 상세 `reason` (<=200자).

[응답 스키마 (반드시 준수)]
{
  "vote": "<candidate_id 또는 null>",
  "turnout": <true|false>,
  "confidence": <0.0~1.0>,
  "reason": "<문자열>",
  "key_factors": ["<요인1>", "<요인2>", "<요인3>"]   # 0~3개
}
```

## 4. 다른 contract 슬롯과의 정합

| api_contract 필드 | 본 매핑에서의 출처 | 검증 포인트 |
|---|---|---|
| `persona_id` | `uuid` 1:1 | `persona_core.uuid` PK |
| `persona_block` | 위 L0~L6 직렬화 | `persona_text` 테이블에 미리 캐시 권고 |
| `region_id` | `province` + `district` → `data_paths.regions[].id` 매핑 | sampling 단계에서 join |
| `contest_id` | scenario 시드(curated) | 페르소나 외부 |
| `candidates` | scenario 시드 | 페르소나 외부 |
| `context_block` | KG retrieval (kg-engineer) | Temporal Firewall t≤T 강제 |
| `timestep` | env loop | — |
| `instruction_mode` | env policy | P2 필드 포함 여부 결정 |

## 5. 미해결 / 후속

- README의 가구유형(`family_type`) enum 값 전수가 아직 없음 → schema-doc `13_categorical_enums.md` 결과 반영 후, "부부+미혼자녀 / 1인가구 / 부부 / 모+미혼자녀 / 부+미혼자녀 / 3세대 …" 등을 한국어 표기 그대로 둘지 영문 정규화할지 확정.
- `persona` 필드 평균 길이 미확정 → eda-analyst `15` 결과 반영 시 토큰 budget 재계산.
- `instruction_mode == "virtual_interview"` 표본 비율은 sampling 노트(#33)에서 결정.
