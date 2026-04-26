# 23. Occupation / Skills / Hobbies 분포 (전수)

> Task #14 — `eda-analyst`. 재현: `scripts/occupation_skills.py`.
> 데이터: `eda_charts/_data/{occupation,skills,hobbies}_top.csv` (top 100), `{skills,hobbies}_token_count.json`.

## 1. Occupation

![Occupation top 30](./eda_charts/occupation_top.png)

| 항목 | 값 |
|---|---|
| unique occupations | **2,120** |
| 1위 `무직` | 367,349 (36.7 %) |
| 2위 `건물 청소원` | 18,253 (1.83 %) |
| 3위 `건물 경비원` | 17,473 |

상위 15:

| rank | occupation | n |
|---:|---|---:|
| 1 | 무직 | 367,349 |
| 2 | 건물 청소원 | 18,253 |
| 3 | 건물 경비원 | 17,473 |
| 4 | 경리 사무원 | 16,146 |
| 5 | 사무 보조원 | 13,630 |
| 6 | 전화 상담원 | 11,211 |
| 7 | 시설 경비원 | 10,897 |
| 8 | 일반 비서 | 10,895 |
| 9 | 하역 및 적재 관련 단순 종사원 | 9,160 |
| 10 | 한식 조리사 | 8,566 |
| 11 | 그 외 일반 영업원 | 8,199 |
| 12 | 주방 보조원 | 7,542 |
| 13 | 지게차 운전원 | 7,382 |
| 14 | 회계 사무원 | 7,250 |
| 15 | 마케팅 전문가 | 7,226 |

### 인사이트
- **`무직` 비중 36.7 %** — 19+ 합성 분포에서 은퇴/주부/실업이 대거 포함된 결과(median age 51, 95%ile 80과 정합).
- 한국통계청 직업분류(KSCO 7차) 기반 어휘로 보임 (`경리 사무원`, `하역 및 적재 관련 단순 종사원` 등 표준 명칭). schema-doc과 cross-check 가치 있음.
- **2,120개 unique** → KG occupation 노드로 그대로 쓰기엔 sparse. KSCO 대분류(10개)로 roll-up 후 attribute로 사용 권장.

## 2. Skills & Expertise

![Skills top 30](./eda_charts/skills_top.png)

| 항목 | 값 |
|---|---|
| 행당 항목 수 (mean / median / min / max) | 4.09 / 4 / 3 / 5 |
| 전수 unique skills | **1,453,619** |
| 전수 skill mentions | 4,089,132 |
| zero-item rows | 0 |

상위 15:

| rank | skill | n |
|---:|---|---:|
| 1 | 제철 나물 무침 | 16,413 |
| 2 | 효율적인 가계 지출 관리 | 9,038 |
| 3 | 베란다 텃밭 작물 재배 | 5,737 |
| 4 | 텃밭 작물 재배 및 관리 | 5,315 |
| 5 | 베란다 텃밭 가꾸기 | 4,920 |
| 6 | 대인 관계 갈등 중재 | 4,232 |
| 7 | 입주민 민원 응대 및 갈등 중재 | 3,713 |
| 8 | 효율적인 주거 공간 정리 정돈 | 3,562 |
| 9 | 텃밭 작물 재배 | 3,501 |
| 10 | 효율적인 집안 정리 정돈 | 3,435 |
| 11 | 제철 식재료를 활용한 한식 상차림 | 3,374 |
| 12 | 지역 사회 인적 네트워크 관리 | 3,121 |
| 13 | 지역 커뮤니티 갈등 중재 | 2,872 |
| 14 | 마을 공동체 갈등 중재 | 2,815 |
| 15 | 제철 나물 요리 | 2,716 |

### 인사이트
- **카운트 분포 long-tail**: 1.45M unique skills, 1위도 16.4k(전체 mention의 0.4 %)에 불과 → 거의 free-form text. KG의 명시적 노드보다는 voter agent 프롬프트에 raw injection이 효율적.
- 상위 항목이 **생활/가사·지역 공동체** 중심(텃밭, 가계 관리, 갈등 중재) → 무직/은퇴 비중 큰 결과와 정합. 정치 시뮬에서 후보 정책 매핑 시 "지역 커뮤니티 갈등 중재" 등은 지방의제 친화 신호로 활용 가능.
- 표준화 필요: "베란다 텃밭 작물 재배"/"텃밭 작물 재배 및 관리"/"베란다 텃밭 가꾸기" 등 동일 의미 변종 다수 → embedding clustering 후보(시뮬레이션 시 페르소나 다양성 유지하면서 KG 매핑은 클러스터 단위로).

## 3. Hobbies & Interests

![Hobbies top 30](./eda_charts/hobbies_top.png)

| 항목 | 값 |
|---|---|
| 행당 항목 수 (mean / median / min / max) | 4.41 / 4 / 1 / 6 |
| 전수 unique hobbies | **959,221** |
| 전수 hobby mentions | 4,411,896 |
| zero-item rows | 0 |

상위 15:

| rank | hobby | n |
|---:|---|---:|
| 1 | 지역 배드민턴 동호회 활동 | 21,205 |
| 2 | 임영웅 노래 감상 | 16,062 |
| 3 | 유튜브 트로트 영상 시청 | 15,931 |
| 4 | 베란다 텃밭 가꾸기 | 14,237 |
| 5 | 네이버 웹툰 정주행 | 11,609 |
| 6 | 모바일 퍼즐 게임 | 10,206 |
| 7 | 동네 목욕탕 사우나 | 8,938 |
| 8 | 리그 오브 레전드 게임 | 8,449 |
| 9 | 지역 배드민턴 클럽 활동 | 8,331 |
| 10 | 동네 사우나에서 반신욕 하기 | 8,157 |
| 11 | 동네 배드민턴 클럽 활동 | 8,057 |
| 12 | 동네 사우나 이용 | 7,509 |
| 13 | 북한산 둘레길 산책 | 7,079 |
| 14 | 동네 사우나 방문 | 7,035 |
| 15 | 동네 사우나 단골 방문 | 6,512 |

### 인사이트
- **임영웅 / 트로트 / 텃밭 / 사우나**가 상위에 다수 등장 — 합성 데이터지만 한국 중장년 라이프스타일 키워드를 강하게 반영. (한국 통계청 KOSIS 라이프스타일 카테고리와 비교 가치 있음)
- "리그 오브 레전드", "네이버 웹툰" 등 청년층 키워드도 포함 → 연령 분포가 19+ 전체임을 감안하면 inter-generational diversity 일부 확보.
- "동네 사우나 *" 5종 등장 → 표면형 중복 다수(skills와 동일 패턴). embedding clustering 권장.
- 정치 신호 활용: "지역 배드민턴 동호회 활동"(1위) 등 **지역 사회 참여형 hobby**가 voting/ civic engagement signal proxy로 사용 가능.

## 4. PolitiKAST 활용 권고

| 필드 | 활용 |
|---|---|
| `occupation` (2,120 unique) | KSCO 대분류 roll-up → KG attribute, 정책 매핑 시 표준화 |
| `skills_and_expertise_list` (1.45M unique, 4 항목/행) | 페르소나 텍스트에 raw injection. 클러스터 단위 KG edge |
| `hobbies_and_interests_list` (959k unique, 4 항목/행) | civic engagement / consumption signal. 클러스터 단위 group 통계 |

> 행당 항목 수가 3–6로 짧아 voter agent 프롬프트에 부담 없이 그대로 삽입 가능 (합산 ≈ 8 항목 × 평균 ≈ 12자 = 100자 이내).

---
재현: `python3 scripts/occupation_skills.py` (전수 1M 행 파싱, ~1분).
