# 03. 한국어 페르소나 Grounding 자료 추적

- 작성일: 2026-04-26
- 데이터셋: `nvidia/Nemotron-Personas-Korea` v1.0
- 작성자: provenance-research

## 1. 그라운딩 소스 5종 — 공식 매핑

README.md (라인 192–207, 한·영 양면 기재)에 따르면 본 데이터셋은 다음 5개 source의 공공 통계로 그라운딩된다:

| # | 기관(KO) | 기관(EN) | 약어 | 라이선스 | 그라운딩 컬럼(추정) |
|---|---|---|---|---|---|
| 1 | 대한민국 통계청 국가통계포털 | Korean Statistical Information Service | **KOSIS** | 공공누리(추정) | `sex`, `age`, `district`, `province`, `occupation`, `bachelors_field`, 여행/여가, 학력 분포 |
| 2 | 대법원 | Supreme Court of Korea | — | 공공누리(추정) | 이름(미수록 컬럼이지만 PGM seed) — 출생연도 × 성별 분포 |
| 3 | 국민건강보험공단 | National Health Insurance Service | **NHIS** | 공공누리 제0유형 (출처 표시 시 자유 이용) [^1] | `family_type`, `housing_type`, 인구통계 보강 |
| 4 | 한국농촌경제연구원 | Korea Rural Economic Institute | **KREI** | 공공누리 제4유형 (출처 표시 + 비상업 / 변경금지) [^2] | `culinary_persona` 분포, 식품 소비 라이프스타일 |
| 5 | NAVER Cloud | NAVER Cloud | — | 명시 없음 (협력 제공) | seed data + domain expertise (설계 단계) |

> README L196: *"국민건강보험공단의 '국민건강보험공단_건강검진정보_20241231' (공공데이터포털에서 공공누리 제0유형으로 개방한 저작물로, '공공데이터포털'에서 무료로 다운받을 수 있습니다.)"*
> README L197: *"한국농촌경제연구원의 '2024년 식품소비행태조사 결과발표대회논문 자료집' (한국농촌경제연구원에서 공공누리 제4유형으로 개방한 저작물로, ...)"*

## 2. 각 그라운딩 소스 상세

### 2.1 KOSIS (국가통계포털)

- URL: https://kosis.kr [^3]
- 운영: 통계청 (현 국가데이터처)
- 제공 통계 약 7만 5천여 표 — JSON / SDMX / XML / XLS 다운로드, OpenAPI 제공 [^4]
- README가 명시한 활용 분야: **성별, 지역, 산업, 직업, 여행, 여가생활** 인구조사 데이터
- 추정 사용 통계표 (PolitiKAST 관점 중요한 것):
  - **인구총조사** — 17 시도 × 252 시군구 인구 분포 (행정구역 매핑의 기반)
  - **경제활동인구조사 / 지역별고용조사** — `occupation` PGM 학습용 (2025년 기준 제8차 한국표준직업분류 KSCO 적용 [^5])
  - **사회조사** — `marital_status`, `family_type`
  - **가계동향조사** — 가구 유형/소득 (Korea 판은 `housing_type`까지)
  - **여가활동조사 / 국민여행조사** — `travel_persona`, `sports_persona`, `arts_persona` 분포
- API 인증: 일반인도 OpenAPI 키 발급 가능 [^4]; 데이터 라이선스는 대부분 KOGL 제1유형(출처 표시) 또는 사용 자유

### 2.2 대법원 가족관계등록 통계

- URL: https://www.scourt.go.kr (전자가족관계등록시스템 통계 서비스: efamily.scourt.go.kr) [^6]
- 2014-05-26부터 가족관계등록 통계 인터넷 공개 [^7]
- README가 명시한 활용 분야: **출생연도 × 성별 × 이름** 데이터 → 118개 성씨 + 21,400개 이름의 PGM seed
- 데이터 시작 시점: 일부 시각화 서비스(NameChart 등)는 **2008년 이후** 출생자만 다룸 [^8]
- 한계: 1940–2007년대 이름은 외부 시각화 자료 [^9] (뉴스젤리)에서 보완 가능하나 대법원 직접 통계는 2008+
- → **PolitiKAST 함의:** Korea 판의 60+ 세대 페르소나 이름은 대법원 ≥2008 raw가 아닌 다른 보정 통계로 합성된 것으로 추정 (README L242에 "성별과 출생 연도에 따라 세대별 작명 경향을 반영" 명시; "영숙·정숙·순자" 등 고연령 이름이 나타남)

### 2.3 국민건강보험공단 (NHIS) — 건강검진 표본 100만명

- 데이터셋 ID: **`국민건강보험공단_건강검진정보_20241231`** (공공데이터포털 제공) [^1][^10]
- 라이선스: **공공누리 제0유형** (출처 표시 의무 없음, 자유 이용; CC0 유사) — 본 README가 명시
- 표본: 직장가입자 + 20세 이상 피부양자/지역가입자 중 일반건강검진 수검자 무작위 100만 명 [^1]
- 항목: 시도코드, 성별, 연령대(5세 단위), 신장/체중/혈압/혈당/콜레스테롤/혈색소 등 [^1][^11]
- → README의 그라운딩 사용처 추정:
  - 시도 단위 인구분포 보강 (KOSIS와 cross-check)
  - `age × sex × province` 결합 분포 (NHIS는 5세 연령대 단위 → Korea 판이 1세 단위 정수 `age`로 후처리)
- 데이터 코드 정의 (NHIS 데이터셋 변수정보 [^11]): 시도 11(서울)~50(제주), 시군구 3~5자리 행정구역코드 — Korea 판 `province`/`district` 컬럼이 이 코드 체계를 한글명으로 디코드한 것일 가능성 높음

### 2.4 KREI 식품소비행태조사

- 정확한 출처 (README 명시): **"2024년 식품소비행태조사 결과발표대회논문 자료집"** [^12][^13]
- 발표대회 일정: 2024-12-13 서울 양재 aT센터 [^14]
- 통계보고서: 2025-05-22 KREI 발간 [^12]
- 표본: 통계청 집계구 활용 가구명부 기반, 가구원 식품소비행태 (성인편 + 청소년편 + 가구 내 주 구입자편)
- 라이선스: **공공누리 제4유형** (출처 표시 + 비상업 + 변경금지)
- → **주의:** 제4유형은 **상업적 이용 시 별도 협의 필요**. 그러나 NVIDIA는 KREI 데이터를 *PGM/LLM의 학습/seed로* 사용하고 그 결과물(페르소나 narrative)만 배포하므로 직접 KREI 자료를 재배포하지 않음 → CC BY 4.0 배포가 가능. PolitiKAST가 *Korea 판 페르소나*만 사용하면 KREI 라이선스를 직접 상속받지 않는다.
- 그라운딩 컬럼: `culinary_persona`(7가지 페르소나 중 1개), `hobbies_and_interests`의 식품/외식 관련 부분

### 2.5 NAVER Cloud

- 역할 (README L197): *"네이버 클라우드는 설계 단계에서 초기 데이터와 해당 분야 전문 지식을 제공"*
- 추정 기여:
  - 한국어 라이팅 스타일/문체 (특히 한국어 narrative의 자연스러움)
  - 한국 문화 컨텍스트 도메인 지식
  - 일부 기업/엔터프라이즈 도메인 지식 (BUT enterprise 페르소나는 본 데이터셋에서 제외됨, README L111)
- 라이선스 표시 의무: 없음 (NAVER Cloud 명칭만 README에 등재)

## 3. 그라운딩 시점(Vintage)

| 소스 | 시점 | 비고 |
|---|---|---|
| KOSIS | 미명시 (최신 활용 추정) | 인구총조사 2020 또는 2025; 직업분류는 2024 기준 KSCO 8차 [^5] |
| 대법원 가족관계 | 미명시 | 시각화 서비스 기준 2008+ 데이터 (60+ 세대 이름은 외부 보정) |
| NHIS | **2024-12-31** (명시) | 가장 최신·가장 명확 |
| KREI | **2024년 조사** (명시) | 발표 2024-12, 보고서 2025-05 |
| NAVER Cloud | 2025–2026 설계기 | 데이터셋 release 2026-04-20 |

→ **PolitiKAST 함의:** 페르소나 데이터는 **2024년 시점의 한국 인구·생활 상태**를 반영한다고 보는 것이 가장 안전. 2026년 4월 보궐선거 시뮬레이션에는 1.5년 시차가 존재하지만, 인구통계 자체는 단기 변동 적음. 다만 **여론·정치 이벤트는 본 데이터셋에 없음** — KG 빌더가 별도로 보강해야 함.

## 4. 그라운딩 ↔ 컬럼 매핑 (확신도 표기)

| 컬럼 | 1차 source | 2차 source | 확신도 |
|---|---|---|---|
| `sex` | KOSIS 인구총조사 | NHIS | **확실** |
| `age` (1세 단위 int64) | KOSIS 주민등록인구 | NHIS (5세대 → 보간) | **확실** |
| `marital_status` | KOSIS 사회조사 | — | **확실** |
| `military_status` | KOSIS / 병무청 (미언급) | — | 추정 (한국 특수 컬럼) |
| `family_type` | KOSIS 인구총조사 | NHIS | **확실** |
| `housing_type` | KOSIS 주택총조사 | NHIS | **확실** |
| `education_level` | KOSIS 사회조사 / 인구총조사 | — | **확실** |
| `bachelors_field` | KOSIS 교육통계 (학과별) | — | 추정 |
| `occupation` | KOSIS 직업별 취업자 (KSCO 8차) | — | **확실** |
| `district` (시군구) | KOSIS 행정구역 | NHIS 행정구역코드 | **확실** |
| `province` (시도) | KOSIS | NHIS | **확실** |
| `country` | 모두 "대한민국" 고정 | — | **확실** |
| 이름(컬럼 없음, 페르소나 텍스트 안에만 등장) | 대법원 가족관계 | — | **확실** |
| `cultural_background`, `skills_and_expertise(_list)`, `career_goals_and_ambitions`, `hobbies_and_interests(_list)` | LLM A 생성 (Gemma-4-31B-IT) | OCEAN seed | LLM 합성 |
| 7개 `*_persona` (직업/스포츠/예술/여행/음식/가족/요약) | LLM B 생성 | + KREI(culinary), KOSIS 여가/여행조사 | LLM 합성 |

## 5. 라이선스 호환성 분석 (PolitiKAST 관점)

| 자원 | 라이선스 | PolitiKAST 활용 시 | 의무 |
|---|---|---|---|
| Korea 페르소나 데이터셋 | CC BY 4.0 | **자유 사용·재배포·상업 가능** | 출처 표시 (NVIDIA + URL + BibTeX) |
| 원천 KOSIS 통계 | KOGL 1유형 (대부분) | 직접 재배포 시만 영향 | NVIDIA가 처리 완료 |
| 원천 NHIS 데이터 | KOGL 0유형 | 직접 재배포 시도 자유 | — |
| 원천 KREI 자료 | KOGL 4유형 | **직접 재배포 금지** (단, NVIDIA가 PGM/LLM seed로 변환했으므로 상속되지 않음) | NVIDIA가 처리 완료 |
| Gemma 4 31B-IT (생성에 사용) | Apache 2.0 | OK | — |

**결론:** PolitiKAST는 Nemotron-Personas-Korea를 통해 위 모든 source를 *간접적으로* 활용하며, **CC BY 4.0 attribution만 만족하면 모든 리스크가 해소**된다.

## 6. 미확인 / 후속 조사 필요

- **`military_status` 컬럼의 grounding source**: README에 명시 없음. 병무청 통계연보일 가능성이 높음 (NVIDIA 미언급).
- **OCEAN(Big-5) 통계 분포의 Korean 보정**: 한국인 대상 Big-5 분포 데이터를 사용했는지, US 분포를 그대로 옮겼는지 미확인. 후자라면 한국 정치성향 추정에 영향.
- **5 region 매칭 가능성** (eda-analyst 작업과 연동):
  - 서울/광주/대구 광역 contest: 충분.
  - 부산 북구 갑: `province='부산' AND district='부산-북구'` = 5,421명.
  - 대구 달서구 갑: `province='대구' AND district='대구-달서구'` = 10,617명 (`daegu_mayor` subset).

## 각주

[^1]: 공공데이터포털. *국민건강보험공단_건강검진정보_20241231*. https://www.data.go.kr/data/15007122/fileData.do (제공일 2025-08-04)
[^2]: 한국농촌경제연구원. *식품소비행태조사 안내*. https://www.krei.re.kr/foodSurvey/index.do
[^3]: KOSIS 국가통계포털. https://kosis.kr (운영주체: 국가데이터처)
[^4]: KOSIS. *공유서비스(OpenAPI) 안내*. https://kosis.kr/serviceInfo/openAPIGuide.do
[^5]: 통계청 고시 제2025-219호. *KOSIS 통계표 — 제8차 한국표준직업분류 적용*. https://kostat.go.kr/boardDownload.es?bid=107&list_no=436053&seq=2
[^6]: 대법원 전자가족관계등록시스템. https://efamily.scourt.go.kr (대법원 https://scourt.go.kr)
[^7]: 대법원 보도자료. *출생·개명 시 가장 선호하는 이름 순위 등 가족관계등록 통계 인터넷 제공*. 2014-05-26. https://www.scourt.go.kr/supreme/news/NewsViewAction2.work?seqnum=193&gubun=702
[^8]: NameChart. *한국인 아기 이름 인기 순위와 연도별 통계*. https://www.namechart.kr (2008+ 데이터)
[^9]: NewsJelly. *데이터로 보는 시대별 이름 트렌드*. 2022-07-18. https://newsjel.ly/archives/newsjelly-report/data-storytelling/14345
[^10]: 보건복지부 데이터링크. *NHIS 데이터셋 변수정보 (테이블 BFC, G1E_OBJ, G1EQ, INST 등)*. https://datalink.mohw.go.kr/nhis.xlsx
[^11]: 같은 자료 [^10] — 시도/시군구 행정구역 코드 (11=서울, 11110=종로구, …)
[^12]: KREI. *2024 식품소비행태조사 통계보고서*. 2025-05-22. https://www.krei.re.kr/krei/page/53?cmd=view&biblioId=543024&pageIndex=1
[^13]: KDI 경제정보센터. *2024 식품소비행태조사 통계보고서 소개*. 2026-02-23. https://eiec.kdi.re.kr/policy/domesticView.do?ac=0000196212
[^14]: BusyNews. *KREI 2024년 식품소비행태조사 결과발표대회 개최*. 2024-12-13. http://www.busynews.net/m/page/detail.html?no=21015
