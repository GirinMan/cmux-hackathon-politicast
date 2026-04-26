# 11. KO ↔ EN 필드 매핑 (Schema Bilingual)

> **출처:** `images/nemotron_personas_korea_schema_ko.png` + `images/nemotron_personas_korea_schema_en.png` (멀티모달 시각 확인) + README 본문.
> **요점:** 컬럼명은 26개 모두 **ASCII 영문**(`uuid`, `professional_persona`, `sex`, `province`...). 값(value)과 자연어 서술은 **한국어**(예: `여자`, `대한민국`, `4년제 대학교`, persona 텍스트). 별도 컬럼명 i18n 없음.

## 1) 컬럼 의미 매핑

| # | column (key) | KO 의미 (KO 스키마 다이어그램) | EN 의미 (EN 스키마 다이어그램) | 값 언어 |
|---|--------------|------------------------------|------------------------------|--------|
| 1 | `uuid` | 고유 식별자 | Globally unique identifier | hex |
| 2 | `professional_persona` | 직업·전문 분야의 핵심 업무, 핵심 직업 기술, 특성 및 행동 묘사 | Professional persona capturing primary field of work, key professional skills, traits and behavior | 한국어 |
| 3 | `sports_persona` | 스포츠 관련 신체활동, 운동 습관, 피트니스 선호 | Sports persona including physical interests, athletic activities, fitness preferences and habits | 한국어 |
| 4 | `arts_persona` | 예술·창작 표현 활동과 정체성에 미치는 영향 | Arts persona characterizing engagement with creative expression and how the arts shape their identity | 한국어 |
| 5 | `travel_persona` | 여행 관심사·스타일·선호 패턴 | Travel persona capturing travel interests and style | 한국어 |
| 6 | `culinary_persona` | 식문화·음식 선호·외식 패턴 | Culinary persona describing dining experiences, food preferences, and habits | 한국어 |
| 7 | `family_persona` | 가족 관계, 라이프스타일, 가족 내 역학 | Family persona describing family relationships, lifestyle, and personality traits | 한국어 |
| 8 | `persona` | 위 6개를 통합한 1~2문장 요약 (concise) | Concise persona description summarizing the overall character | 한국어 |
| 9 | `cultural_background` | 문화·세대·지역적 배경 서사 | Description of person's regional and generational cultural background | 한국어 |
| 10 | `skills_and_expertise` | 전문성·기술 자유 서술 | Professional aptitudes and long-term career objectives | 한국어 |
| 11 | `skills_and_expertise_list` | 같은 내용을 콤마/리스트 형식으로 정리 | List of skills and areas of expertise | 한국어 (콤마 구분) |
| 12 | `hobbies_and_interests` | 취미·관심사 자유 서술 | Natural, interests and recreational activities in narrative format | 한국어 |
| 13 | `hobbies_and_interests_list` | 동일 내용 리스트 형식 | List of hobbies and interests | 한국어 (콤마 구분) |
| 14 | `career_goals_and_ambitions` | 경력 목표·포부 서술 | Professional aspirations and long-term career objectives | 한국어 |
| 15 | `sex` | 생물학적 성 (남자/여자) | Biological sex (male/female) | 한국어 enum |
| 16 | `age` | 만 나이 | Age in years | int |
| 17 | `marital_status` | 혼인 상태 (미혼/배우자있음/이혼/사별) | Marital status (e.g. 미혼, 배우자있음, 이혼, 사별) | 한국어 enum |
| 18 | `education_level` | 최종 학력 (무학/초등학교/중학교/고등학교/2~3년제 전문대학/4년제 대학교/대학원) | Highest level of education completed (e.g. 4년제 대학교, 대학원) | 한국어 enum |
| 19 | `bachelors_field` | 학사 전공 분야 (해당없음 또는 11분야) | Field of study for bachelor's degree, if applicable | 한국어 enum |
| 20 | `occupation` | 세부 직업 (KSCO 세분류 수준) | Detailed occupation (e.g. 보육교사, 한식 조리사) | 한국어 (1,632 distinct) |
| 21 | `military_status` | 군 복무 상태 (현역/비현역) | Active duty status (현역/비현역) | 한국어 enum |
| 22 | `family_type` | 가구 유형 (39종, 동거 구성) | Type of household (e.g. 혼자 거주, 부모와 동거) | 한국어 enum |
| 23 | `housing_type` | 주거 형태 (아파트/단독주택/다세대주택/연립주택/주택 이외의 거처/비주거용 건물 내 주택) | Type of housing (e.g. 아파트, 단독주택) | 한국어 enum |
| 24 | `province` | 광역 시·도 (17종) | Province-level administrative division (시도) | 한국어 enum (약식) |
| 25 | `district` | 시·군·구 (252종, `province-시군구` 형식) | District-level administrative division (시군구) | 한국어 |
| 26 | `country` | 국가 (상수: 대한민국) | Country of residence (constant: 대한민국) | 한국어 (상수) |

## 2) Persona 7종 vs Attribute 6종 vs Demographic 12 — 그룹별 매핑

```
───────── 1 unique identifier ─────────
uuid

───────── 7 persona narratives ─────────
professional_persona / sports_persona / arts_persona /
travel_persona / culinary_persona / family_persona / persona(=concise)

───────── 6 persona attributes ─────────
cultural_background / skills_and_expertise / skills_and_expertise_list /
hobbies_and_interests / hobbies_and_interests_list / career_goals_and_ambitions

───────── 12 demographic & geo ─────────
sex / age / marital_status / military_status / family_type / housing_type /
education_level / bachelors_field / occupation /
district / province / country
```

## 3) 값(enum) KO/EN 표기

- 모든 enum 값은 **한국어 표기** (`여자`/`남자`, `미혼`/`배우자있음`/`이혼`/`사별`, `현역`/`비현역`, `대한민국` 등).
- 영문 키워드(`male`/`female` 등)는 데이터 내 등장하지 않음. 시뮬레이션·KG 라벨링 시 **한국어 그대로** 사용 권장 (또는 lookup table을 별도 정의).

## 4) 다이어그램 캡션 인용 (이미지 메타)

- KO 이미지: `Nemotron-Personas-Korea` 제목, 좌측 `column: type`, 우측 한국어 한 줄 설명.
- EN 이미지: 동일 레이아웃, 영문 한 줄 설명. 컬럼 키와 dtype은 두 이미지가 정확히 일치 (검증: 이미지 텍스트 vs README features 26개 — 1:1 매칭 확인).

## 5) PolitiKAST 사용 시 주의

- **컬럼 키는 영문**이라 코드 베이스에서 i18n 처리 불필요.
- **enum 값은 한국어**라 LLM 프롬프트에 그대로 사용 가능 (Gemini 한국어 처리 무관). 단 KG 노드 라벨 사용 시 namespace 충돌 주의 (예: 가구유형 `혼자 거주` vs region 라벨 충돌 가능 — prefix 부여 권장: `family_type:혼자 거주`).
- province 약식 표기(`경상남` 등)는 KOSIS 공식 표기(`경상남도`)와 다르므로 외부 데이터 join 시 정규화 매핑 필요. → `eda-analyst` 5 region 매칭 작업에서 처리.
