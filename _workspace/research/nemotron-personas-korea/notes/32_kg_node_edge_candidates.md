# 32 — KG Node / Edge 후보 도출

> Task #19 · owner: politikast-utility
> Source: Nemotron-Personas-Korea README (26 fields), `_workspace/contracts/api_contract.json`, `data_paths.json`
> Cross-ref: `30_prompt_field_mapping.md`, `31_political_signals.md`

본 노트는 PolitiKAST 의 정치 KG (Election + Event/Discourse) 가 페르소나 데이터와 어떻게 연결될지 — Nemotron-Personas-Korea 의 컬럼들을 KG 노드/엣지로 어떻게 흡수할지 — 를 정리한다. 실제 KG 빌드는 `kg-engineer` 가 networkx MultiDiGraph 로 수행하며, 본 노트는 노드 라벨 / 속성 / 관계 후보를 표기 `(:Label {prop})-[:REL]->(:Label)` 로 제안한다.

## 1. 노드 라벨 후보

| label | 출처 | 핵심 속성 | 카디널리티 (P0 region 5개 기준) | 비고 |
|---|---|---|---|---|
| `:Voter` | `persona_core` 1행 | uuid (PK), age, sex, age_group | 5 region × per-region n (50~500) | persona_block은 텍스트 별도 테이블 |
| `:PersonaText` | `persona_text` 1행 | uuid (FK), persona, professional_persona, family_persona, cultural_background, hobbies_and_interests | 1:1 with Voter | 토큰 비용 절약 위해 외부화 |
| `:Region` | `data_paths.regions[]` | id, type, province, district, label | 5 (P0) | seoul_mayor/gwangju_mayor/daegu_mayor/busan_buk_gap/daegu_dalseo_gap |
| `:Province` | KOSIS 17개 | name | 17 (전국 KG 시 기준) | 본 P0에서는 5개만 활성 |
| `:District` | KOSIS 252개 | name, province (FK) | 252 (전국) / 5 region 한정 시 ~10 | |
| `:Occupation` | KOSIS 직업 분류 | label, major_group (대분류) | ~30 (대분류 9개 + 빈출 세분류) | 자영/임금/공무원/은퇴 분류 가능 |
| `:EducationLevel` | enum | label, ordinal_rank | 8 (무학/초등/중/고/2-3년제/4년제/석사/박사) | ordinal |
| `:HousingType` | enum | label, owner_renter | ~5 | 자가/전세/월세/공공임대/기타 |
| `:FamilyType` | enum | label, household_role | ~10 | 부부+미혼자녀, 1인가구, 부부, 모/부+미혼자녀, 3세대 등 |
| `:AgeGroup` | derived from age | label (예: "19-29") | 7~9 | 페르소나-aggregate 시각화·breakdown용 |
| `:Election` | scenario 시드 | id, type (광역단체장/기초단체장/보궐), date | 5 (1 per region) | |
| `:Contest` | scenario 시드 | id, election (FK), region (FK) | 5 | 단일 region당 1 contest |
| `:Candidate` | scenario 시드 | id, name, party, contest (FK), withdrawn | 5 region × ~3 후보 = ~15 | |
| `:Party` | scenario 시드 | id, name, ideology_axis (≈ -1..+1) | ~5~7 | 더불어민주당/국민의힘/조국혁신당/개혁신당/정의당/무소속/기타 |
| `:Event` | curated political_event | id, type, date, summary, scope (national/regional) | ~30~80 | timestep 컷오프 적용 대상 |
| `:Frame` | curated discourse | id, label (예: "부동산", "안보", "복지", "공정") | ~10 | 이슈 프레임 |
| `:Poll` | raw_poll | id, pollster, date, sample_n, contest (FK) | 변동 (region당 5~20) | poll_consensus 노드 별도 |
| `:PollConsensus` | derived | date, contest (FK), winner_lead | timestep 수만큼 | 가중평균 결과 |
| `:CulturalBackgroundTag` | derived from cultural_background text | tag (예: "수도권 출신", "기독교 가정", "지방 농촌 성장") | ~30 (LLM extract) | optional, P1 feature |

> P0(시간 우선) 라벨: `:Voter`, `:Region`, `:District`, `:Province`, `:Election`, `:Contest`, `:Candidate`, `:Party`, `:Event`, `:Frame`, `:Poll`, `:PollConsensus`, `:Occupation`, `:EducationLevel`, `:HousingType`, `:FamilyType`, `:AgeGroup`.
> P1(여유 시): `:PersonaText`, `:CulturalBackgroundTag`.

## 2. 엣지(관계) 후보 — 페르소나 ↔ 정치 연결

### 2.1 페르소나 자체의 구조 엣지

```
(:Voter {uuid})-[:LIVES_IN]->(:District {name})
(:District {name})-[:PART_OF]->(:Province {name})
(:Voter {uuid})-[:IN_REGION]->(:Region {id})           # data_paths.regions와 매칭된 경우만
(:Voter {uuid})-[:HAS_SEX {value: "남|여"}]            # 또는 속성으로 인라인
(:Voter {uuid})-[:IN_AGE_GROUP]->(:AgeGroup {label})
(:Voter {uuid})-[:HAS_EDUCATION]->(:EducationLevel {label})
(:Voter {uuid})-[:HAS_OCCUPATION]->(:Occupation {label})
(:Voter {uuid})-[:LIVES_AS]->(:HousingType {label})
(:Voter {uuid})-[:FAMILY_OF]->(:FamilyType {label})
(:Voter {uuid})-[:DESCRIBED_BY]->(:PersonaText {uuid})  # P1
```

### 2.2 정치 컨텍스트 엣지

```
(:Election {id})-[:HELD_IN]->(:Region {id})
(:Contest {id})-[:PART_OF]->(:Election {id})
(:Candidate {id})-[:RUNS_IN]->(:Contest {id})
(:Candidate {id})-[:MEMBER_OF]->(:Party {id})
(:Poll {id})-[:MEASURES]->(:Contest {id})
(:Poll {id})-[:REPORTS_SUPPORT {share: float}]->(:Candidate {id})
(:PollConsensus {date})-[:SUMMARIZES]->(:Contest {id})
(:Event {id})-[:OCCURS_AT {date}]->(:Date)
(:Event {id})-[:AFFECTS]->(:Candidate {id})
(:Event {id})-[:AFFECTS]->(:Party {id})
(:Event {id})-[:FRAMED_AS]->(:Frame {label})
(:Frame {label})-[:RELATES_TO]->(:Contest {id})
```

### 2.3 페르소나 ↔ 정치 연결 (GraphRAG retrieval 핵심)

```
(:Voter {uuid})-[:ELIGIBLE_IN]->(:Contest {id})
       # 조건: voter.region == contest.region AND age >= 19 (Nemotron은 19+만)

(:Voter {uuid})-[:EXPOSED_TO {timestep, weight}]->(:Event {id})
       # weight = scope match (national=1.0, regional=2.0 if same region)

(:Voter {uuid})-[:AWARE_OF]->(:Frame {label})
       # 추정: occupation·age·family_type 기반 휴리스틱 또는 LLM 분류

(:Occupation {label})-[:SENSITIVE_TO {weight}]->(:Frame {label})
(:HousingType {label})-[:SENSITIVE_TO {weight}]->(:Frame {label})
(:AgeGroup {label})-[:SENSITIVE_TO {weight}]->(:Frame {label})
       # 예: (:HousingType {label:"전월세"})-[:SENSITIVE_TO {weight:0.8}]->(:Frame {label:"부동산"})

# 시뮬레이션 산출 (sim-engineer가 timestep마다 write)
(:Voter {uuid})-[:VOTED_FOR {timestep, confidence}]->(:Candidate {id})
(:Voter {uuid})-[:ABSTAINED {timestep}]
```

### 2.4 Temporal Information Firewall ($\mathcal{D}_{\le t}$)

KG retrieval 시 모든 `:Event`, `:Poll`, `:PollConsensus` 노드는 `date <= timestep_date` 필터를 강제한다. 페르소나 노드(`:Voter`, `:PersonaText`)는 시점 무관(인구통계는 변하지 않음으로 가정).

```python
# 의사코드 (kg-engineer 참고용)
def retrieve_voter_subgraph(voter_uuid: str, t: date, contest_id: str):
    voter = G.nodes[voter_uuid]
    region = G[voter_uuid]["IN_REGION"]
    contest = G.nodes[contest_id]
    candidates = G[contest_id]["RUNS_IN"]
    # Temporal Firewall
    events = [e for e in G[contest_id]["~AFFECTS"]  # reverse edge
              if G.nodes[e]["date"] <= t]
    polls = [p for p in G[contest_id]["~MEASURES"]
             if G.nodes[p]["date"] <= t]
    frames = [G[occ]["SENSITIVE_TO"] for occ in voter["HAS_OCCUPATION"]]
    return assemble_context_block(voter, region, candidates, events, polls, frames)
```

## 3. Nemotron 컬럼 → KG 매핑 요약 표

| Nemotron column | 매핑 위치 | 노드/속성 |
|---|---|---|
| `uuid` | `:Voter.uuid` (PK) | — |
| `age` | `:Voter.age` + `:AgeGroup` 노드 연결 | `[:IN_AGE_GROUP]` |
| `sex` | `:Voter.sex` 속성 | (인라인) |
| `province` | `:Province` 노드 | `[:LIVES_IN]->[:PART_OF]` |
| `district` | `:District` 노드 | `[:LIVES_IN]` |
| `country` | drop | — |
| `marital_status` | `:Voter.marital_status` 속성 | (인라인) |
| `military_status` | `:Voter.military_status` 속성 | (인라인, gender prior와 결합) |
| `family_type` | `:FamilyType` 노드 | `[:FAMILY_OF]` |
| `housing_type` | `:HousingType` 노드 | `[:LIVES_AS]` |
| `education_level` | `:EducationLevel` 노드 | `[:HAS_EDUCATION]` |
| `bachelors_field` | `:Voter.bachelors_field` 속성 (P2) | — |
| `occupation` | `:Occupation` 노드 | `[:HAS_OCCUPATION]` |
| `professional_persona` | `:PersonaText.professional` (P1 외부 테이블) | — |
| `family_persona` | `:PersonaText.family` | — |
| `cultural_background` | `:PersonaText.cultural_background` (+ `:CulturalBackgroundTag` P1) | `[:HAS_TAG]` |
| `persona` (concise) | `:PersonaText.concise` | system prompt L0 진입 |
| `skills_and_expertise(_list)` | drop (P0) | — |
| `hobbies_and_interests(_list)` | `:PersonaText.hobbies` (P1) | virtual_interview only |
| `career_goals_and_ambitions` | drop | — |
| `sports/arts/travel/culinary_persona` | drop | — |

## 4. networkx 빌드 hint (kg-engineer 인계용)

- 단일 `MultiDiGraph` G. 노드 키는 (label, id) tuple 권고 (예: `("Voter", uuid)`).
- 속성 인라인 vs 노드 분리 기준: **카디널리티가 작고 다른 정치 노드와 연결되는 것**(occupation/education/housing/family_type) → 노드 분리. **인스턴스 고유 값**(sex/age/marital_status/military_status) → 속성 인라인.
- `GraphRAG retriever` 는 voter node 에서 BFS 깊이 2~3까지 탐색 → context_block 직렬화. 토큰 예산 800~1500자.
- Temporal Firewall 은 retriever 함수 인자로 `t: date` 받고 모든 dated 노드에 필터 적용.

## 5. 후속 / 미해결

- `family_type` enum 한국어 표기를 KG 노드 라벨로 그대로 둘지 영문 정규화할지 — `13_categorical_enums.md` 결과 반영.
- `:Event` 큐레이션 가이드(scope/type 분류)는 `data-engineer` 의 scenario 시드와 동기화 필요.
- `:CulturalBackgroundTag` 추출은 LLM 호출 비용이 추가되므로 capacity probe 결과 따라 P0 포함 여부 결정.
