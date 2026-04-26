# 12. 페르소나 텍스트 7종 + Attribute 6종 — 샘플 / 길이 통계

> **출처:** `train-00000-of-00009.parquet` (n=111,112) DuckDB 측정. 측정 스크립트: `scripts/schema_probe.py`. 출력: `scripts/schema_probe_output.json`.

## 1) 길이 통계 (단위: char, shard 0 전수)

### 1-1) Persona 7종 (자유 서사)

| field | min | avg | p50 | p90 | max |
|-------|-----|-----|-----|-----|-----|
| `professional_persona` | 60 | **159.5** | 163 | 196 | 276 |
| `sports_persona`       | 56 | 133.7 | 137 | 165 | 248 |
| `arts_persona`         | 57 | 138.2 | 142 | 169 | 238 |
| `travel_persona`       | 55 | 135.1 | 139 | 166 | 232 |
| `culinary_persona`     | 64 | 142.0 | 146 | 175 | 252 |
| `family_persona`       | 60 | 143.9 | 149 | 176 | 240 |
| `persona` (concise)    | 44 | **81.5** | 81 | 95 | 164 |

### 1-2) Persona attribute 6종

| field | min | avg | p50 | p90 | max | 형식 |
|-------|-----|-----|-----|-----|-----|------|
| `cultural_background`         | 59 | 135.3 | 139 | 170 | 283 | 자유 서사 |
| `skills_and_expertise`        | 54 | 121.0 | 124 | 153 | 236 | 자유 서사 |
| `skills_and_expertise_list`   | 37 | 78.4 | 78 | 96 | 169 | **string repr of Python list** |
| `hobbies_and_interests`       | 57 | 128.9 | 133 | 164 | 305 | 자유 서사 |
| `hobbies_and_interests_list`  | 39 | 79.2 | 78 | 99 | 171 | **string repr of Python list** |
| `career_goals_and_ambitions`  | 51 | 118.3 | 121 | 151 | 213 | 자유 서사 |

### 1-3) 합계 (per row, 13개 텍스트 컬럼)

평균 char 합계 ≈ **1,694 chars/row** (한국어 기준 ~1,200~1,500 token). 1 M rows × ~1,700 token ≈ 1.7 B token (README 명시값과 일치).

## 2) `*_list` 컬럼 형식 주의 ⚠️

```
$ duckdb> SELECT skills_and_expertise_list, typeof(skills_and_expertise_list) FROM p LIMIT 1
"['적재물 무게 중심 파악 및 효율적 배치', '현장 자재 결속 및 고정 기술', ...]" | VARCHAR
```

- pyarrow schema: `string`
- DuckDB typeof: `VARCHAR`
- **실제 값은 Python list의 `repr()` 결과 (대괄호 + single-quote)**.
- 사용 시 `ast.literal_eval(s)` 또는 `json.loads(s.replace("'", '"'))`로 파싱 필요.
- KG 빌더/voter agent prompt에서 list로 다루려면 인제션 단계에서 변환 컬럼(`*_list_arr` LIST<VARCHAR>) 추가 권장 (DuckDB ingestion → `string_split` + parsing).

## 3) 샘플 1 — 광주 70대 남성 (uuid `03b4f36a18e6469386d0286dddd513c8`)

**Demographic:** age=74, sex=남자, province=광주, district=광주-서구, occupation=하역 및 적재 관련 단순 종사원.

| field | text |
|-------|------|
| `persona` | 전기태 씨는 광주 서구에서 평생 하역 일을 하며 살아온 70대 가장으로, 투박한 손마디에 삶의 흔적이 배어 있는 성실하고 사교적인 인물입니다. |
| `professional_persona` | 전기태 씨는 광주 서구의 하역 현장에서 수십 년간 짐을 쌓아 올리며, 지렛대 원리를 이용해 무거운 자재를 효율적으로 옮기는 베테랑의 면모를 보입니다. 동료들 사이에서 가장 빠르고 정확하게 무게 중심을 잡는다는 평을 듣지만, 가끔은 고집스럽게 본인의 옛 방식만을 고수하며 젊은 일꾼들과 투닥거리기도 합니다. |
| `sports_persona` | 주말마다 무등산 자락을 느릿느릿 걸으며 땀을 흘리고, 내려오는 길에 단골 목욕탕에서 친구들과 엉켜 앉아 정치 이야기를 나누는 것으로 일주일을 마무리합니다. … |
| `arts_persona` | 거실 소파에 깊숙이 파묻혀 텔레비전에서 나오는 옛날 가요 프로그램을 보며 젊은 시절의 추억에 젖어드는 시간을 가장 좋아합니다. … |
| `travel_persona` | 아내와 함께 전국의 역사 유적지를 찾아다니며 옛 조상들의 발취를 느끼는 여행을 즐깁니다. 화려한 관광지보다는 경주나 부여처럼 조용하고 고즈넉한 곳을 걸으며, 아내의 손을 꼭 잡고 천천히 시간을 보내는 것을 소중히 여깁니다. |
| `culinary_persona` | 일주일에 한 번 배달 짜장면과 탕수육을 시켜 먹는 날을 손꼽아 기다리며, 2주에 한 번은 아내와 함께 동네 고깃집에서 지글지글 구운 삼겹살에 소주 한 잔을 곁들입니다. … |
| `family_persona` | 전·월세 아파트에서 평생의 동반자인 아내와 단출하게 살아가며, 투박한 전라도 사투리로 서로를 챙기는 소박한 애정을 나눕니다. … |
| `cultural_background` | 광주 서구에서 평생을 보내며 투박하지만 정겨운 전라도 사투리가 몸에 배어 있고, 시장통 사람들과 어울려 왁자지껄하게 이야기 나누는 것을 즐깁니다. 초등학교 졸업 후 곧바로 현장 일에 뛰어들어 몸으로 부딪치며 살아온 세월이 있어, 격식보다는 사람 사이의 의리와 눈치 빠른 태도를 더 중요하게 생각합니다. |
| `skills_and_expertise` | 수십 년간 하역 현장에서 다져진 감각으로 짐의 무게 중심을 한눈에 파악해 가장 효율적으로 쌓아 올리는 요령이 탁월합니다. … |
| `skills_and_expertise_list` | `['적재물 무게 중심 파악 및 효율적 배치', '현장 자재 결속 및 고정 기술', '하역 작업 동선 최적화', '현장 인력 간의 갈등 중재 및 분위기 주도']` |
| `hobbies_and_interests` | 주말이면 무등산 자락을 천천히 걸으며 땀을 빼고, 내려오는 길에 단골 목욕탕에서 뜨거운 물에 몸을 담그며 동네 친구들과 정치 이야기를 나누는 시간을 가장 아낍니다. … |
| `hobbies_and_interests_list` | `['무등산 둘레길 산책', '동네 대중사우나 이용', '전통시장 맛집 탐방', '트로트 프로그램 시청', '가족과 함께하는 경주나 부여 역사 유적지 여행']` |
| `career_goals_and_ambitions` | 큰 욕심 없이 지금처럼 매일 아침 정해진 시간에 출근해 땀 흘려 일하며 건강을 유지하는 것에 만족합니다. 무리하지 않는 선에서 하역 일을 계속하며 아내와 함께 소박하게 생활할 수 있는 생활비를 꾸준히 마련하는 것이 현재의 가장 큰 목표입니다. |

## 4) 샘플 2 — 서울 70대 여성 (uuid `73f75d42a3934626b0d9a4bff062715a`)

**Demographic:** age=71, sex=여자, province=서울, district=서울-서초구, occupation=회계 사무원.

| field | text |
|-------|------|
| `persona` | 최은지 씨는 서초구에서 부동산 회계 사무원으로 일하며 경제적 자립과 사교적인 삶을 동시에 누리는 당찬 70대 여성입니다. |
| `professional_persona` | 서초동 부동산 사무실에서 장부를 잡으며 복잡한 취득세나 양도세 계산을 암산 수준으로 빠르게 처리하는 베테랑 회계 사무원입니다. … |
| `cultural_background` | 최은지는 서초구의 오래된 다세대 주택가에서 나고 자라며 체면과 질서를 중시하는 분위기에 익숙합니다. 수학을 전공한 이성적인 사고방식을 가졌지만, 동네 문화센터나 모임에서는 누구보다 목소리가 크고 활기차게 분위기를 주도하는 외향적인 면모를 보입니다. |
| `skills_and_expertise_list` | `['부동산 취득세 및 보유세 산출', '복식부기 기반의 회계 장부 작성', '빠른 암산을 통한 수치 검증', '사무실 내 대인 관계 조율 및 분위기 주도']` |
| `hobbies_and_interests_list` | `['경복궁과 창덕궁 고궁 산책', '트로트 경연 프로그램 시청', '동네 공원 나무 그늘 아래서 낮잠 자기', '청국장이나 나물 비빔밥 같은 담백한 한식집 탐방']` |
| `career_goals_and_ambitions` | 지금처럼 규칙적으로 출근하며 동료들과 어울리는 일상을 유지하는 것에 만족하며, 본인이 가진 실무 노하우를 후배들에게 전수하며 인정받기를 원합니다. … |

> 본 샘플 2건은 **shard 0의 첫 두 행**으로, 임의 선택. 전수 길이 분포 차트는 eda-analyst (#15)가 9 shard 통합 후 작성.

## 5) PolitiKAST 활용 가이드

- **VoterAgent 시스템 프롬프트 코어**: `persona`(81 char) + `cultural_background`(135 char) + `professional_persona`(160 char) + `family_persona`(144 char) ≈ 520 char ≈ **약 400 token 영역** — 4 키 풀 RPM 안에서 1 페르소나당 컨텍스트 최소화 가능.
- **정치성향 직접 시그널 부재**: `political_persona` 같은 필드 없음. 추론은 `cultural_background`(지역·세대) + `family_persona` + `hobbies_and_interests`(예: "정치 이야기를 나누는") + occupation에서 간접 도출. 한계 = 정치성향 ground-truth 없음 → 시뮬 결과는 hypothesis-generative.
- **샘플 1 같은 페르소나 텍스트 내 "광주 서구" 직접 언급** → KG 노드 매칭 시 텍스트 substring 매칭 가능하나, occupation/region 필드를 우선 사용 권장 (LLM 환각 방지).
- **샘플 1의 `hobbies_and_interests`에 "정치 이야기를 나누는"** 명시 → political-engagement signal 컬럼으로 텍스트 마이닝 가능. utility 분석에서 활용 (#18).
