# 04 — PolitiKAST 활용 가능성 (Utility Synthesis)

> Owner: `politikast-utility` agent
> Tasks: #17 (prompt mapping) · #18 (정치 시그널) · #19 (KG 스키마) · #20 (sampling/한계)
> Sub-notes: [`30_prompt_field_mapping.md`](notes/30_prompt_field_mapping.md), [`31_political_signals.md`](notes/31_political_signals.md), [`32_kg_node_edge_candidates.md`](notes/32_kg_node_edge_candidates.md), [`33_sampling_and_limits.md`](notes/33_sampling_and_limits.md)
> 의존: [`20_integrity.md`](notes/20_integrity.md) (eda — 무결성 확인 ✅), `13_categorical_enums.md` / `15_text_stats.md` / `22_region_match.md` (미작성, 추후 본 문서 갱신 권고)

본 문서는 Nemotron-Personas-Korea 데이터셋이 PolitiKAST(2026 한국 지방선거 KG 증강 다중 에이전트 시뮬레이션) 빌드에서 어떻게 활용될지를 4개 축(prompt 매핑 · 정치 시그널 · KG 통합 · sampling/한계)으로 통합 정리한다. 각 절의 상세는 `notes/3x.md` 를 참조.

---

## §1. 한 눈에 보는 결론

| 축 | 핵심 결론 |
|---|---|
| **Prompt 매핑** | 26 컬럼 중 P0 필수 9개(uuid, age, sex, province, district, education_level, occupation, persona, professional_persona)와 P1 4개(family_persona, cultural_background, family_type, housing_type)만 voter agent system prompt 에 주입. token budget 페르소나당 350~900 토큰. |
| **정치 시그널** | 데이터셋에 정치 라벨/투표이력 컬럼이 **0개**. 시그널은 인구통계(age × sex × region × occupation × housing) 와 자유서술 텍스트의 LLM prior 에 의존. age, province, occupation 이 ★★★★ 이상의 강한 시그널. |
| **KG 통합** | networkx MultiDiGraph. P0 라벨 17종, persona ↔ 정치 연결 핵심 엣지 `[:LIVES_IN]` `[:HAS_OCCUPATION]` `[:LIVES_AS]` `[:ELIGIBLE_IN]` `[:EXPOSED_TO]`. Temporal Firewall 은 dated 노드 (`:Event`, `:Poll`, `:PollConsensus`) 에 적용. |
| **Sampling** | P0 권고 분배: seoul_mayor=600, gwangju_mayor=500, daegu_mayor=500, busan_buk_gap=400, daegu_dalseo_gap=400 (총 2,400 페르소나 × 4 timestep = ~10.7k LLM 호출, capacity 10.8k 가정). age_group × sex stratified sampling, seed 고정. |
| **한계 (필수 5)** | ① 19+ 만 ② 종교/소득/투표이력 부재 ③ 합성 PGM 독립성 가정 ④ sex만(gender ✗) ⑤ 페르소나 텍스트 정치 키워드 미확인 |

---

## §2. Prompt 매핑 (Task #17)

`api_contract.json` 의 `voter_request_schema.persona_block` 정의("concise + professional + family + cultural_background")를 기본으로, 정치 의사결정에 결정적인 인구통계 컨텍스트를 별도 라인으로 노출한다.

**필드 우선순위 요약** ([상세표](notes/30_prompt_field_mapping.md#1-26-필드--prompt-slot-매핑-표)):

- **P0 (항상 포함)**: `uuid`, `age`, `sex`, `province`, `district`, `education_level`, `occupation`, `persona` (concise), `professional_persona`, `family_persona`, `cultural_background`
- **P1 (여유 시)**: `marital_status`, `military_status`, `family_type`, `housing_type`, `bachelors_field`
- **P2 (virtual_interview 한정)**: `hobbies_and_interests`
- **P3 (drop)**: `country`, `skills_and_expertise(_list)`, `career_goals_and_ambitions`, `sports/arts/travel/culinary_persona`, `hobbies_list`

**`persona_block` 직렬화** (P0):
```
[L0] {persona}
[L1] {age}세 {sex} · 학력: {education_level} · 혼인: {marital_status} · 군 복무: {military_status}
[L2] 거주: {province} {district}
[L3] 가족: {family_type} · 주거: {housing_type}
     {family_persona}
[L4] 직업: {occupation} (전공: {bachelors_field})
     {professional_persona}
[L5] 문화 배경: {cultural_background}
```

**VoterAgent system prompt 템플릿** ([전체 템플릿](notes/30_prompt_field_mapping.md#3-voteragent-system-prompt-템플릿-p0)) — 한국 시민 1인칭 + 외부 정치 정보 차단 + JSON 단일 객체 응답 + `instruction_mode` (secret_ballot / poll_response / virtual_interview) 분기.

---

## §3. 정치 성향 Inferable Signals (Task #18)

**전제**: 데이터셋의 26 컬럼 어디에도 정치 성향, 정당 지지, 투표 이력이 없다 (`20_integrity.md` 전수 확인). voter agent 의 prior 는 (a) 인구통계 변수, (b) 자유서술 텍스트의 LLM 일반 지식, (c) KG context_block 에서만 온다.

**한국 유권자 인구통계 vs. 이념 통상 패턴** (Perplexity 인용):
- 보수>진보 분기점 연령: 2012년 47세 → 2020년 57세 → 2024년 56세 ([Chosun](https://www.chosun.com/site/data/html_dir/2020/05/08/2020050800012.html), [Chosun 2024](https://www.chosun.com/politics/2024/04/07/XO3H5WT3DZAEVKTIDODGSBNRN4/))
- 20·30대 여성 진보 / 60대 이상 남녀 보수 ([Gallup 2024-09](https://www.gallup.co.kr/gallupdb/reportContent.asp?seqNo=1509))
- 사무·전문·서비스·학생 → 민주당 / 가정주부·농어업·은퇴 → 국힘 ([eknews 2023](https://www.eknews.net/xe/kr_politics/35057142))
- 호남 진보, 영남(특히 TK) 보수, 수도권 경쟁 — 5 region 선정 자체가 이 사실을 활용

**시그널 강도** (★1~5, [상세표](notes/31_political_signals.md#1-컬럼별-시그널-강도-표)):
- ★★★★★: `age`, `province`
- ★★★★☆: `sex`, `occupation`, `housing_type`
- ★★★☆☆: `district`, `education_level`, `family_type`, `professional_persona`, `family_persona`, `cultural_background`
- ★★☆☆☆ 이하: `bachelors_field`, `marital_status`, `military_status`, `hobbies_*`
- 시그널 0 / drop: `country`, `skills_*`, `career_*`, `sports/arts/travel/culinary_persona`

**Occupation 카디널리티 처리**: eda 실측 결과 `occupation` 의 distinct value가 **2,120종**(무직 36.7% 단일 최빈값) — 그대로 prompt/KG 노드로 사용하면 sparse·noisy. **KSCO(한국표준직업분류) 대분류 11그룹** (관리자 / 전문가 및 관련 종사자 / 사무 종사자 / 서비스 종사자 / 판매 종사자 / 농림어업 숙련 종사자 / 기능원 및 관련 기능 종사자 / 장치·기계조작 및 조립 종사자 / 단순노무 종사자 / 군인 / 무직·은퇴·기타) 으로 **롤업한 `occupation_major` 컬럼을 derive** 하여 voter prompt L4 와 KG `:Occupation` 노드 라벨로 사용 권고. raw `occupation` 은 `:Voter.occupation_raw` 속성에 보존 (paper 부록 / virtual_interview 모드에서 디테일 노출).

**텍스트 길이 / 토큰 예산 재계산**: eda 실측 페르소나 7종 합산 median ≈ 957자 ≈ **2k token / 페르소나** (`notes/24_persona_length.md`). P0(concise + professional + family + cultural)만 직렬화 시 ~600~900 토큰으로 충분 — token budget 여유 있음, P1 필드 포함도 capacity 내 수용 가능.

**금지 사항**: persona_block 에 "당신은 진보/보수다" 류 직접 라벨 주입 금지. 정치 prior 는 인구통계와 KG 에서만 흘러야 한다.

---

## §4. KG 노드 / 엣지 후보 (Task #19)

**P0 노드 라벨** (17종): `:Voter`, `:Region`, `:District`, `:Province`, `:Election`, `:Contest`, `:Candidate`, `:Party`, `:Event`, `:Frame`, `:Poll`, `:PollConsensus`, `:Occupation`, `:EducationLevel`, `:HousingType`, `:FamilyType`, `:AgeGroup`. P1: `:PersonaText`, `:CulturalBackgroundTag`.

**핵심 엣지 패턴** ([전체](notes/32_kg_node_edge_candidates.md#2-엣지관계-후보--페르소나--정치-연결)):

```
# 페르소나 구조
(:Voter {uuid})-[:LIVES_IN]->(:District {name})-[:PART_OF]->(:Province {name})
(:Voter {uuid})-[:HAS_OCCUPATION]->(:Occupation {label})
(:Voter {uuid})-[:LIVES_AS]->(:HousingType {label})
(:Voter {uuid})-[:FAMILY_OF]->(:FamilyType {label})
(:Voter {uuid})-[:HAS_EDUCATION]->(:EducationLevel {label})
(:Voter {uuid})-[:IN_AGE_GROUP]->(:AgeGroup {label})

# 정치 컨텍스트
(:Candidate {id})-[:RUNS_IN]->(:Contest {id})-[:PART_OF]->(:Election {id})-[:HELD_IN]->(:Region {id})
(:Candidate {id})-[:MEMBER_OF]->(:Party {id})
(:Event {id})-[:AFFECTS]->(:Candidate {id})
(:Event {id})-[:FRAMED_AS]->(:Frame {label})
(:Poll {id})-[:MEASURES]->(:Contest {id})
(:Poll {id})-[:REPORTS_SUPPORT {share}]->(:Candidate {id})

# 페르소나 ↔ 정치 (GraphRAG 핵심)
(:Voter {uuid})-[:ELIGIBLE_IN]->(:Contest {id})
(:Voter {uuid})-[:EXPOSED_TO {timestep, weight}]->(:Event {id})
(:Occupation {label})-[:SENSITIVE_TO {weight}]->(:Frame {label})
(:HousingType {label})-[:SENSITIVE_TO {weight}]->(:Frame {label})

# 시뮬 산출
(:Voter {uuid})-[:VOTED_FOR {timestep, confidence}]->(:Candidate {id})
```

**Temporal Information Firewall**: retriever 함수에서 `t: date` 인자로 모든 dated 노드(`:Event`, `:Poll`, `:PollConsensus`) 를 `date <= t` 필터. 페르소나 노드는 시점 무관.

**컬럼 → KG 매핑 요약** ([표](notes/32_kg_node_edge_candidates.md#3-nemotron-컬럼--kg-매핑-요약-표)): 카디널리티가 작고 정치 노드와 연결 가능한 enum 컬럼(`occupation/education_level/housing_type/family_type`)은 별도 노드로, 인스턴스 고유 값(`sex/age/marital_status`)은 `:Voter` 속성으로 인라인.

---

## §5. 5 Region Sampling 전략 (Task #20)

**모집단 실측치** (eda `notes/22_region_match.md`, DuckDB 정확 매칭):

| region_id | 매칭 키 | 실측 행수 (1M 기준) | 권고 표본 | timestep | LLM 호출 |
|---|---|---:|---:|---:|---:|
| seoul_mayor | `province='서울'` | **185,228** | 600 | 4 | 2,400 |
| gwangju_mayor | `province='광주'` | **27,594** | 500 | 4 | 2,000 |
| daegu_mayor | `province='대구'` | **46,934** | 500 | 4 | 2,000 |
| busan_buk_gap | `province='부산' AND district='부산-북구'` | **5,421** | 400 | 4 | 1,600 |
| daegu_dalseo_gap | `province='대구' AND district='대구-달서구'` | **10,617** † | 400 | 4 | 1,600 |
| **subtotal** | — | — | **2,400** | — | **9,600** |
| 가상 인터뷰 + 캐시미스 마진 | — | — | — | — | ~1,150 |
| **TOTAL** | — | — | — | — | **~10,750** (capacity 10,800 가정 내) |

> † `daegu_dalseo_gap`은 `daegu_mayor`의 부분집합이다. contest별 sample table을 분리하거나 `(region_id, uuid)` 복합키로 관리해 같은 persona가 다른 contest에서 중복 사용될 수 있음을 명시한다.

**Stratified Sampling**: `age_group (6 bins) × sex (2 bins)` 2축, region 모집단 비율 유지 ([의사코드](notes/33_sampling_and_limits.md#4-stratified-sampling-의사코드) — DuckDB `USING SAMPLE reservoir(N) REPEATABLE(seed)`).

**Downscale ladder** (capacity probe → policy-engineer 가 선택):
- L0: 권고대로 (n=400~600, T=4, 호출 ~10.7k)
- L1: T=3 (호출 ~8k)
- L2: n=300, T=3 (호출 ~5.4k)
- L3: secondary regions n=200, T=2 (호출 ~3k)
- L4: seoul demo only, n=200, T=2 (호출 ~400)

---

## §6. 한계 / 리스크 (필수 5항목 + eda 보강)

1. **19세 미만 부재** — 만 19세 이상만 수록(README 명시, eda 전수 확인). **공직선거법 만 18세 이상 선거권자 약 1.3% 누락** → 첫 투표 세대(Gen Z 진입층)의 정치 참여 패턴 시뮬 불가. paper Limitations 절에 "19+ 시뮬레이션" 으로 명기.
2. **종교/소득/투표이력 부재** — 정치 성향 강한 변수들이 없음. `cultural_background` / `housing_type` / `occupation` 으로 부분 보완. KG 의 `:Frame` 이슈 노드와 `[:SENSITIVE_TO]` 휴리스틱으로 정치 sensitivity 보강.
3. **합성 데이터의 PGM 독립성 가정 + 표면형 중복** — sex × major 등 교호작용 미반영(README 명시). gender × occupation 결합 정치 시그널이 attenuated. 또한 eda 실측 결과 `occupation` distinct 2,120종, `skills_and_expertise_list` / `hobbies_and_interests_list` 등도 표면형이 sparse·중복(같은 의미를 다른 표기로) → KSCO 대분류 등 **외부 분류체계로 롤업**해야 KG 노드와 stratification이 의미 있어짐. KOSIS 원본과의 cross-tab 비교를 paper appendix 권고.
4. **Sex 만, Gender 미반영 (binary only)** — 사회적 gender 정체성 통계 부재(README 명시). 청년 남성 보수화의 안티페미니즘 축, 성소수자 정치 행동 시뮬레이션 불가. paper Limitations 명기.
5. **페르소나 텍스트의 정치 키워드 부재 / leakage 모두 리스크** — eda-analyst `15_text_stats.md` 결과 미확정. 부재 시 시뮬이 교과서적 단조성, 존재 시 합성 LLM(gemma-4-31B-it) 의 정치 편향 인쇄 가능성. 1만 샘플에서 정치 키워드 비율 측정 → 0.1% 이상이면 P0 prompt에서 해당 텍스트 제외.

**추가 (시나리오 한계)**: **region scope overlap** — 5개 contest region 중 `daegu_dalseo_gap`은 `daegu_mayor`의 부분집합이다. 결과 집계에서 5 region 행수 합계를 전체 유권자 수처럼 해석하지 말고, contest별 independent sampling frame으로 처리한다.

---

## §7. 후속 / Open Items

| 항목 | 의존 | 상태 / 처리 |
|---|---|---|
| §5 region 행수 실측치 갱신 | eda-analyst `22_region_match.md` | ✅ 반영 완료 (seoul 185k / daegu 47k / gwangju 28k / busan_buk 5.4k / daegu_dalseo 10.6k) |
| occupation 카디널리티(2,120) → KSCO 대분류 11그룹 롤업 | eda-analyst `notes/24_*.md` | ✅ §3 권고 추가 — data-engineer/kg-engineer 가 derive |
| 페르소나 텍스트 길이 / 토큰 예산 | eda-analyst `notes/24_persona_length.md` | ✅ §3 token budget 재계산 (median 957자 ≈ 2k token) |
| `family_type` 등 enum 한국어/영문 정규화 결정 | schema-doc `13_categorical_enums.md` (✅ 완료) | KG 노드 라벨 표기 정정 — `notes/32` small patch 대기 |
| 페르소나 텍스트 정치 키워드 비율 (leakage) | eda-analyst (text 통계 노트) | 미반영 — 결과 도착 시 §6 #5 한 줄 보강 |
| 보궐 region province/district 확정 | data-engineer scenario 큐레이션 | ✅ `busan_buk_gap`, `daegu_dalseo_gap` 반영 완료 |
| capacity probe 결과 → downscale level 선택 | policy-engineer | sim-engineer 에 broadcast |
| paper Limitations 절 5+1 항목 반영 | paper-writer | `update-paper` 스킬 호출 시 본 문서 §6 인용 |
