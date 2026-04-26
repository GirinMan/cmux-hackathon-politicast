# 31 — 정치 성향 Inferable Signals 분석

> Task #18 · owner: politikast-utility
> Source: Nemotron-Personas-Korea README, `_workspace/contracts/api_contract.json`
> Cross-ref: `30_prompt_field_mapping.md`, `13_categorical_enums.md` (예정), `12_demo_charts.md` (예정)

본 노트는 Nemotron-Personas-Korea 의 어떤 컬럼이 한국 유권자의 정치 성향을 어느 정도까지 합리적으로 추정할 수 있는 시그널을 제공하는지, 그리고 어떤 컬럼은 시그널이 약하거나 leakage 위험이 있는지를 정리한다. **데이터셋 자체에는 정치 성향·정당지지·투표이력 컬럼이 전혀 없다** (README 26 필드 전수 확인). 따라서 추정은 전적으로 인구통계·지역·직업·문화배경에서 LLM이 prior로 가져오는 패턴에 의존한다.

## 0. 출처: 한국 유권자 인구통계 vs. 이념의 통상 패턴

PolitiKAST 의 voter agent 가 합리적 prior를 가질 수 있도록, 아래 레퍼런스 패턴을 KG context 또는 system prompt 의 "한국 유권자 일반 추세" 블록으로 제공할 수 있다(논문 Limitations 절에 명시 필요).

- **연령**: 한국갤럽 매년 1~4월 통합치, 보수>진보 분기점이 2012년 47세 → 2020년 57세 → 2024년 56세로 이동. 50대 후반·60대 이상은 보수 우세, 18–55세는 진보 우세 [Chosun 2020-05-08, 2024-04-07].
- **성별×연령 교차**: 20·30대에서는 여성이 또래 남성보다 진보적, 60대 이상은 남녀 모두 보수 [Gallup 2024-09].
- **직업·계층**: 사무/관리/전문직, 판매/생산/노무/서비스, 학생 → 더불어민주당 우세. 가정주부, 농/임/어업, 무직/은퇴 → 국민의힘 우세 [Realmeter 2022-01 via eknews 2023-01-28].
- **지역**: 호남(광주) 진보 강세, 영남(특히 대구·경북) 보수 강세, 부산 보궐의 인물·당적 변수. `data_paths.regions` 의 5개 region 선정 자체가 이 사실을 반영(서울=baseline, 광주=진보, 대구=보수, 부산 북구 갑/대구 달서구 갑=보궐 이슈효과).

> **인용 링크**:
> - Gallup 2024-09 https://www.gallup.co.kr/gallupdb/reportContent.asp?seqNo=1509
> - Chosun 2020-05-08 https://www.chosun.com/site/data/html_dir/2020/05/08/2020050800012.html
> - Chosun 2024-04-07 https://www.chosun.com/politics/2024/04/07/XO3H5WT3DZAEVKTIDODGSBNRN4/
> - Realmeter via eknews 2023-01-28 https://www.eknews.net/xe/kr_politics/35057142
> - Gallup column 2021-02 https://www.gallup.co.kr/gallupdb/columnContents.asp?seqNo=126
> - 홍기혜·민인식 22대 총선 분석 http://kasr.skyd.co.kr/survey_SR/25_2_1

## 1. 컬럼별 시그널 강도 표

| column | dtype | signal | inferred direction | confidence (★1~5) | 비고 |
|---|---|---|---|---|---|
| `age` | int64 | 세대효과·연령효과 | <56세 진보 경향 / ≥57세 보수 경향 | ★★★★★ | 가장 강한 단일 변수. 86세대(50대) 진보 유지가 예외 패턴. |
| `sex` | string | gender gap | 20·30대 여성 진보·남성 중도/보수 | ★★★★☆ | 단독 사용 약함. **age × sex 교차** 필수. |
| `province` | string | 지역주의 | 호남 진보 / 영남(특히 TK) 보수 / 수도권 경쟁 | ★★★★★ | 5 region 설계 자체가 이 시그널 활용. |
| `district` | string | 도시 vs 농촌, 도심 vs 외곽 | 도심·신도시 진보 / 농촌·구도심 보수 (편차 큼) | ★★★☆☆ | 강남 3구 등은 province 효과를 뒤집을 수 있음. |
| `education_level` | string | 학력 효과 | 4년제 대졸 이상 진보 경향 (특히 청년) / 무학·초등 고연령은 보수 | ★★★☆☆ | age 와 강한 confound. 단독 효과 약함. |
| `bachelors_field` | string | 전공 효과 | STEM/이공계 vs 인문사회 — 약한 시그널, 일관성 낮음 | ★★☆☆☆ | 미디어 노출·연령 confound. drop 권고 (P2). |
| `occupation` | string | 계층·고용형태 효과 | 자영업·농어업·가정주부·은퇴 → 보수 / 사무·전문·서비스·학생 → 진보 | ★★★★☆ | 연령·지역과 confound. 그러나 직업 카테고리 자체가 강한 prior. |
| `professional_persona` | text | 직업 디테일·고용 안정성 | 임금근로 vs 자영 vs 비정규 → 경제정책 sensitivity | ★★★☆☆ | 자유서술 → LLM이 nuance 추출 가능. |
| `marital_status` | string | 가족부양·세대 | 유배우 + 자녀 있음 → 교육·부동산 정책 sensitivity | ★★☆☆☆ | 단독 약함, age×family_type 결합 시 의미. |
| `family_type` | string | 가구구조 | 1인가구(청년)·핸한부모 → 복지·주거 sensitivity / 부부+미혼자녀 → 교육·부동산 | ★★★☆☆ | family_persona 와 결합하면 강해짐. |
| `housing_type` | string | 자산효과 | 자가 → 부동산 보수 / 전월세·공공임대 → 진보 경향 | ★★★★☆ | 한국 정치학에서 강한 변수(주택가격·부동산 소유). enum 확인 필요(`13_categorical_enums.md`). |
| `family_persona` | text | 가족 부양 부담·세대 갈등 | 돌봄 부담·다세대 → 복지/연금 sensitivity | ★★★☆☆ | 자유서술. 정치 키워드 leakage 모니터링. |
| `cultural_background` | text | 종교·지역정체성·가치관 | 종교(개신교 등)·전통가치 → 보수 경향 / 다문화·국제경험 → 진보 경향 | ★★★☆☆ | **종교 컬럼 부재**의 부분 보완. 정치 키워드 leakage 모니터링. |
| `military_status` | string | 안보·국방 sensitivity | 복무 완료 남성 → 안보 보수 가능성 | ★★☆☆☆ | 남성 한정. 단독 효과 약함. |
| `hobbies_and_interests` | text | 미디어 소비·라이프스타일 | 등산·종교활동 → 보수 경향 / 독서·문화예술 → 진보 경향 | ★★☆☆☆ | weak·noisy. virtual_interview 모드에서만 활용. |
| `career_goals_and_ambitions` | text | 미래지향 | 신호 약함 | ★☆☆☆☆ | drop. |
| `skills_and_expertise(_list)` | text/list | 전문성 | 신호 매우 약함 | ★☆☆☆☆ | drop. |
| `sports_persona` | text | 스포츠 선호 | 신호 거의 없음 | ★☆☆☆☆ | drop. |
| `arts_persona` | text | 예술 선호 | 신호 거의 없음 | ★☆☆☆☆ | drop. |
| `travel_persona` | text | 여행 선호 | 신호 거의 없음 | ★☆☆☆☆ | drop. |
| `culinary_persona` | text | 음식 선호 | 신호 거의 없음 | ★☆☆☆☆ | drop. |
| `persona` | text (concise) | 종합 요약 | (위 모든 시그널의 압축) | ★★★★☆ | system prompt L0 진입점. 가장 token-efficient. |
| `uuid` | string | 식별자 | 시그널 없음 | — | 메타 |
| `country` | string | 국적 | 모두 KR — 시그널 없음 | — | drop |

## 2. 권고: voter agent 의 "정치 prior" 주입 전략

1. **암시적 prior**: persona_block 의 P0 필드(age/sex/province/district/education/occupation)만으로도 LLM(`gemini-3-flash-preview`)은 한국 유권자 일반 추세에 대한 prior를 활성화한다. 추가 instruction 없이 동작.
2. **명시적 prior(선택)**: P0 region별 시뮬레이션 안정성을 위해, system prompt 끝에 다음 한 줄을 추가할 수 있다 — "한국 유권자 일반 통계상 연령·지역·직업이 정치 성향과 상관관계가 있음을 알고 있다. 그러나 본인의 구체적 판단은 본인의 배경과 KG 컨텍스트에 근거하라." (논문 Reproducibility appendix 에 명기 권고)
3. **금지**: persona_block에 "당신은 진보/보수다" 류의 직접 라벨을 절대 주입하지 않는다 — 이는 simulation의 핵심 outcome을 prompt에 leak 시키는 행위다.

## 3. Persona text의 정치 키워드 사전 점검 권고

eda-analyst 가 `15_text_stats.md` 에서 다음을 확인해 줄 것:

- `persona`, `professional_persona`, `family_persona`, `cultural_background` 텍스트 1만 샘플에서 정치 관련 키워드(예: "정치", "정당", "보수", "진보", "민주당", "국민의힘", "선거", "지지") 의 등장 비율.
- 등장 비율이 0.1% 이상이면 voter agent 응답이 합성 페르소나의 인공 라벨에 의해 편향될 수 있음 → Limitations 절에 명시.
- 0.01% 이하라면 leakage risk 무시 가능.

## 4. 잠재 편향 (sampling 노트 #33 으로 인계)

- **age × education confound**: 고연령은 무학·초등 비율이 매우 높음(80세 이상 73%) → 이중 효과(나이 + 학력)가 보수 시그널을 과대 추정할 수 있음.
- **gender × occupation confound**: PGM이 sex × major 결합 효과를 모델링하지 않음(README "Limitations" 명시) → 직업 분포가 실제 한국보다 gender-balanced 하게 합성되었을 가능성.
- **종교 부재**: cultural_background 텍스트만으로는 개신교(보수 시그널)·천주교·불교·무종교 식별이 어려움. 정확한 종교 컬럼이 없는 것은 큰 한계.
- **소득 부재**: housing_type이 부분 proxy 역할을 하지만 직접 소득 컬럼은 없음 → 계층 시그널이 weakened.
- **투표이력·정당지지 부재**: prior period 의 vote behavior 가 없으므로 first-mover preference가 LLM의 hallucination에 의존.
