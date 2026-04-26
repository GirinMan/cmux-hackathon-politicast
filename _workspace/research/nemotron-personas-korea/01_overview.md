# 01_overview.md — Nemotron-Personas-Korea Provenance 종합 보고서

- 작성일: 2026-04-26
- 데이터셋: `nvidia/Nemotron-Personas-Korea` v1.0 (HF 공개 2026-04-20)
- 라이선스: CC BY 4.0
- 작성자: provenance-research (PolitiKAST 해커톤 nemotron-research 팀)
- 부속 노트: [`./notes/01_provenance_huggingface.md`](./notes/01_provenance_huggingface.md) · [`./notes/02_synthesis_pipeline.md`](./notes/02_synthesis_pipeline.md) · [`./notes/03_grounding_sources.md`](./notes/03_grounding_sources.md) · [`./notes/04_citation.md`](./notes/04_citation.md)

---

## 0. TL;DR (PolitiKAST 의사결정자용 1쪽 요약)

| 질문 | 답 | 출처 |
|---|---|---|
| 무슨 데이터셋인가? | 한국 인구통계 분포에 정합되는 합성 페르소나 1M 레코드 / 7M 페르소나 / 1.7B 토큰 / 26 컬럼 | README.md L170–183, [§1](#1-데이터셋-정체성) |
| 누가 만들었나? | NVIDIA Corporation (저자 13인, NAVER Cloud가 seed 기여) | README BibTeX, [§1.2](#12-저자-및-개발자) |
| 언제 어떻게 공개됐나? | 2026-04-20 HuggingFace, CC BY 4.0 | README.md L127–138 |
| 어떻게 만들어졌나? | NeMo Data Designer (Apache-2.0, OSS) → PGM + OCEAN → Gemma-4-31B-IT 두 차례 호출 | README L96, approach.png 다이어그램, [§2](#2-합성-파이프라인) |
| 무엇으로 그라운딩됐나? | KOSIS · 대법원 가족관계등록 · NHIS 건강검진(공공누리 0유형) · KREI 식품소비행태조사(공공누리 4유형) · NAVER Cloud | README L191–207, [§3](#3-한국-그라운딩-소스) |
| 인용은? | NVIDIA 공식 `@software` BibTeX 또는 PolitiKAST 호환 `@misc` 버전 | README L400–406, [§4](#4-인용-및-license-attribution) |
| **PolitiKAST가 자유롭게 쓸 수 있나?** | **YES** — CC BY 4.0; KREI 4유형(상업 제한)이지만 NVIDIA가 PGM seed로 변환했으므로 상속되지 않음. Attribution(NVIDIA + URL + license)만 만족하면 끝 | [§4.5](#45-라이선스-호환성-결론) |
| **알아야 할 한계** | (1) 19세 이상만, (2) 변수 간 독립성 가정(예: 성별×전공 무모델), (3) 생물학적 sex만(gender 없음), (4) 정치 관련 컬럼 부재 (별도 KG 필요) | README L154–164, [§5](#5-한계와-pol리스크) |

---

## 1. 데이터셋 정체성

### 1.1 기본 사양

| 항목 | 값 |
|---|---|
| Repo | https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea |
| 버전 | 1.0 (2026-04-20) |
| 데이터 생성일 | 2026-04-20 |
| 라이선스 | CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/legalcode) |
| Splits | `train` 단독, 1,000,000 레코드 |
| 파일 | 9 shards × ~210MB Parquet (train-0000{0..8}-of-00009.parquet) |
| 총 압축 다운로드 | 1.98 GB |
| 총 비압축 | 4.19 GB |
| 토큰 수 | 1.7B 전체 / 1B 페르소나 토큰 |
| 컬럼 수 | 26 (= 7 persona + 6 attribute + 12 demographic/geo + 1 uuid) |
| 페르소나 수 | 7,000,000 (각 레코드의 7가지 narrative variant) |
| 지리 커버리지 | 17 시도 × 252+ 시군구 |
| 이름 다양성 | 118 성씨 × 21,400 이름 → 209,167 unique full-name combinations |
| 연령 범위 | **만 19세 이상** (한국 법정 성년) |
| 데이터 수집 방법 | Hybrid (Human + Synthetic + Automated), README L367 |
| Tags | synthetic, personas, NVIDIA, Korean, datadesigner |

### 1.2 저자 및 개발자

- 개발자: **NVIDIA Corporation** (README L124)
- 저자(BibTeX): Hyunwoo Kim, Jihyeon Ryu, Jinho Lee, Hyungon Ryu, Kiran Praveen, Shyamala Prayaga, Kirit Thadaka, Will Jennings, Bardiya Sadeghi, Ashton Sharabiani, Yejin Choi, **Yev Meyer** (← 영어 원본 Nemotron-Personas의 1저자)
- 협력: **NAVER Cloud** (설계 단계의 seed data + 한국 도메인 전문성)

### 1.3 Nemotron-Personas Collection 내 위치 (계보)

| 국가 | 발표 | 협력기관 | 비고 |
|---|---|---|---|
| 🇺🇸 USA (원본) | 2025-06 | Gretel(NVIDIA 인수) | 100K records, 22 fields, US Census 그라운딩 |
| 🇺🇸 USA-Extended | 2026 | NVIDIA | 1M+ records |
| 🇯🇵 Japan | 2025–2026 | (NVIDIA) | 1M × 6 = 6M, 22 fields |
| 🇮🇳 India | 2025 | (NVIDIA) | NVIDIA Developer 페이지 |
| 🇸🇬 Singapore | 2025 | AI Singapore | Sovereign AI 협력 |
| 🇧🇷 Brazil | 2026-02 | WideLabs (IBGE) | 6M personas |
| 🇫🇷 France | 2026 | Pleias | NVIDIA 블로그 |
| **🇰🇷 Korea** | **2026-04-20** | **NAVER Cloud** | **1M × 7 = 7M, 26 fields, 1.7B tokens (현재까지 컬렉션 중 최대 컬럼/토큰)** |

→ Korea 판은 컬렉션 내에서 **컬럼/토큰 모두 가장 큰 사이즈**이며, 페르소나 종류도 7가지(영어 원본 6 + `family_persona` 추가 또는 변종)로 가장 풍부하다.

### 1.4 영어 원본과의 스키마 차이

Korea 판에 신설/한국 특수 필드:
- `military_status` (한국 병역 컨텍스트)
- `bachelors_field` (학사 전공)
- `family_type` / `housing_type` (한국 인구조사 분류 그대로)
- `province`/`district` ← (영어 원본의 `state` 대체)
- `country` 고정값 = "대한민국" (영어 판은 "USA")

→ 자세한 스키마 분석은 schema-doc 팀의 `02_schema.md` 참조.

---

## 2. 합성 파이프라인

### 2.1 사용 도구

| 도구 | 라이선스 | 역할 |
|---|---|---|
| **NeMo Data Designer** (`github.com/NVIDIA-NeMo/DataDesigner`) | Apache-2.0 (2025-12 OSS화) | 오케스트레이션 프레임워크 — sampler + LLM column + 검증 |
| **PGM** (Probabilistic Generative Model) | Apache-2.0 (Gretel/NVIDIA 자체) | 인구통계 컬럼 12종 합성 |
| **OCEAN (Big-5) 모형** | 학계 일반 | 성격 latent 점수 → LLM A 컨텍스트 |
| **`google/gemma-4-31B-it`** | **Apache 2.0** (2026-04-02 출시) | LLM A (속성 narrative) + LLM B (페르소나 narrative) |

### 2.2 파이프라인 다이어그램 (`approach.png` 해석)

```
[KOSIS+대법원+NHIS+KREI 통계] ──► [PGM 샘플러] ──┐
                                                   ├──► [LLM A: Gemma-4-31B-IT] ──► [4개 attribute narrative]
[Big-5 인구분포]              ──► [OCEAN 샘플러] ──┘                                    └─► [LLM B: Gemma-4-31B-IT] ──► [7개 persona narrative]
                                                                                              (직업/스포츠/예술/여행/음식/가족/요약)
```

자세한 단계별 컬럼 매핑은 [`./notes/02_synthesis_pipeline.md`](./notes/02_synthesis_pipeline.md)의 §3.1 참조.

### 2.3 출시 시점 정합성

- Gemma 4 31B-IT 출시: **2026-04-02** (Apache-2.0)
- Korea 판 데이터 생성: **2026-04-20**
→ 신규 모델 출시 18일 만에 1M 레코드 batch 생성 → NeMo Data Designer의 효율성 입증.

---

## 3. 한국 그라운딩 소스

### 3.1 5개 source 요약

| # | 기관 | 라이선스 | 그라운딩 컬럼 |
|---|---|---|---|
| 1 | **KOSIS** (통계청 국가통계포털) | KOGL 1유형 (대부분) | sex, age, marital, military, family/housing, education, bachelors_field, occupation(KSCO 8차), district/province |
| 2 | **대법원 전자가족관계등록** | KOGL 1유형 (추정) | 이름 PGM seed (출생연도×성별×이름) |
| 3 | **NHIS** (`건강검진정보_20241231`, 100만명 표본) | **KOGL 0유형 (자유 이용)** | 시도 단위 분포 보강, age×sex×province cross-check |
| 4 | **KREI** (`2024년 식품소비행태조사 결과발표대회 자료집`) | KOGL 4유형 (출처+비상업+변경금지) | culinary_persona, hobbies(식품 부분) |
| 5 | **NAVER Cloud** | 명시 없음 (협력) | 한국어 문체, 도메인 지식 |

### 3.2 데이터 시점

- NHIS: 2024-12-31 (가장 명확)
- KREI: 2024년 조사
- KOSIS: 미명시 (직업분류 기준 KSCO 8차 = 2024 기준)
- 대법원: 미명시 (외부 시각화 서비스는 2008+ raw, 60+ 세대는 보정)
→ **유효 시점은 2024년 한국 인구**로 가정. 2026년 4월 보궐선거와 1.5년 시차 존재.

### 3.3 5 region 매칭 가능성 (PolitiKAST P0)

| region | KOSIS coverage | NHIS coverage | 페르소나 표본 충분성 |
|---|---|---|---|
| 서울시장 | 풍부 | 풍부 | ✅ 185,228명 |
| 광주시장 | 충분 | 충분 | ✅ 27,594명 |
| 대구시장 | 충분 | 충분 | ✅ 46,934명 |
| **부산 북구 갑** (보궐) | district 단위 | 시군구 단위 | ✅ 5,421명 |
| **대구 달서구 갑** (보궐) | district 단위 | 시군구 단위 | ✅ 10,617명 |

→ 매칭 가능 row count 산출은 eda-analyst의 task #13 참조. `daegu_dalseo_gap`은 `daegu_mayor`의 부분집합이므로 contest별 sample frame으로 관리한다.

---

## 4. 인용 및 License Attribution

### 4.1 NVIDIA 공식 BibTeX (README 그대로)

```bibtex
@software{nvidia/Nemotron-Personas-Korea,
  author = {Kim, Hyunwoo and Ryu, Jihyeon and Lee, Jinho and Ryu, Hyungon and Praveen, Kiran and Prayaga, Shyamala and Thadaka, Kirit and Jennings, Will and Sadeghi, Bardiya and Sharabiani, Ashton and Choi, Yejin and Meyer, Yev},
  title = {Nemotron-Personas-Korea: Synthetic Personas Aligned to Real-World Distributions for Korea},
  month = {April},
  year = {2026},
  url = {https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea}
}
```

### 4.2 PolitiKAST 권장 BibTeX (LaTeX/biblatex 호환)

```bibtex
@misc{nvidia2026nemotronpersonaskorea,
  author       = {Kim, Hyunwoo and Ryu, Jihyeon and Lee, Jinho and Ryu, Hyungon and
                  Praveen, Kiran and Prayaga, Shyamala and Thadaka, Kirit and
                  Jennings, Will and Sadeghi, Bardiya and Sharabiani, Ashton and
                  Choi, Yejin and Meyer, Yev},
  title        = {{Nemotron-Personas-Korea}: Synthetic Personas Aligned to
                  Real-World Distributions for Korea},
  howpublished = {Hugging Face Datasets},
  publisher    = {NVIDIA Corporation},
  year         = {2026},
  month        = apr,
  version      = {1.0},
  note         = {Licensed under CC BY 4.0; 1M records, 7M personas;
                  grounded in KOSIS, Supreme Court of Korea, NHIS, KREI},
  url          = {https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea}
}
```

→ 추가 BibTeX 후보(NeMo Data Designer, Gemma 4, 영어 원본 Nemotron-Personas, KOSIS, NHIS, KREI)는 [`./notes/04_citation.md`](./notes/04_citation.md) §4 참조.

### 4.3 권장 1문단 (논문 Data 섹션)

> We build voter agent populations from **Nemotron-Personas-Korea** (\cite{nvidia2026nemotronpersonaskorea}; CC BY 4.0), an open synthetic persona dataset of 1,000,000 records spanning 7,000,000 narrative personas (1.7B tokens) across 26 fields. The dataset was generated with NVIDIA's NeMo Data Designer using a probabilistic graphical model fit to official Korean statistics (KOSIS, Supreme Court of Korea, NHIS, KREI; with seed contributions from NAVER Cloud) and the Apache-2.0 licensed `google/gemma-4-31B-it` language model. Coverage spans 17 provinces and 252 districts and includes only adult personas (≥19, the South Korean legal age of adulthood). For PolitiKAST, we filter five focal regions (Seoul, Gwangju, Daegu, Uiwang-si, and Ganghwa-gun) and use the 12 demographic/geographic fields together with the 6 attribute fields and 7 narrative persona fields to condition CAMEL voter agents.

### 4.4 한국어 attribution (대시보드 footer)

```
본 시뮬레이션은 NVIDIA의 Nemotron-Personas-Korea v1.0 (CC BY 4.0)을 사용합니다.
원본 데이터셋은 KOSIS·대법원·NHIS·KREI·NAVER Cloud의 자료를 기반으로 합성되었습니다.
출처: https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea
```

### 4.5 라이선스 호환성 결론

- ✅ **Korea 페르소나 = CC BY 4.0** → 자유 사용·재배포·상업·수정 모두 가능
- ✅ KOSIS / NHIS / 대법원: 모두 KOGL ≤1유형 (NVIDIA가 흡수 처리 완료)
- ✅ KREI(4유형 = 상업 제한)도 NVIDIA가 PGM/LLM seed로 변환 → **PolitiKAST는 직접 KREI를 재배포하지 않으므로 4유형 의무가 상속되지 않음**
- ✅ Gemma 4 = Apache 2.0 (출력물 권리 제한 없음)
- → **Attribution 4종 (저자 + URL + 라이선스 + 변경 사항)만 만족하면 PolitiKAST의 모든 사용 사례(논문, 코드, 대시보드, 상업 데모)에서 안전.**

---

## 5. 한계와 PolitiKAST 리스크

### 5.1 데이터셋 자체의 한계 (README + Docs 명시)

| # | 한계 | 영향 | PolitiKAST 대응 |
|---|---|---|---|
| L1 | **변수 간 독립성 가정** (e.g., `sex × bachelors_field` 결합 분포 부재) | 교차분석 편향 | marginal 분포만 사용; 결합 추정은 KG에서 별도 검증 |
| L2 | **19세 이상만** 포함 (한국 법정 성년) | 18세 유권자 없음 | Limitations 섹션 명시 |
| L3 | **gender 없음** (sex만, 한국 공공 통계에 gender 부재) | 성소수자 표현 불가 | Limitations 명시; Gender-aware 분석 불가 표시 |
| L4 | **시점 ambiguity** (KOSIS는 미명시, NHIS/KREI는 2024) | 2026년 정치 컨텍스트와 시차 | KG 노드에 timestamp 부여; Temporal Information Firewall ($\mathcal{D}_{\le t}$) 적용 |
| L5 | enterprise(금융/헬스케어) 페르소나 제외 | 직업 분포 일부 결측 | KOSIS 직업 분포로 보완 |
| L6 | 페르소나에 직접 정치성향/투표이력 컬럼 없음 | voter agent 정치 prompt 외부 보강 필요 | KG에서 후보·이벤트 정보 주입 (kg-engineer 작업) |

### 5.2 PolitiKAST 시뮬레이션 사용 시 추가 리스크

| 리스크 | 설명 | 완화책 |
|---|---|---|
| **Temporal Leakage** | 페르소나가 2024 기반인데 2026 보궐 시뮬에 사용 → 2025–2026 신생 정치 사건이 이미 페르소나에 반영되었을 가능성 (특히 LLM 생성 narrative) | KG에서 timestamp 기반 사실 차단; sim-engineer가 voter prompt에 cutoff 명시 |
| **5 region 표본 불균형** | 광역시는 풍부, 보궐 district는 수천~1만 명 규모 | 다운스케일 ladder에서 region별 sample size 차등 (policy-engineer) |
| **PGM 학습 데이터 PII 위험** | NHIS는 100만 명 무작위 추출이지만 합성 단계에서 실명 reconstruct 가능성 이론적으로 존재 | NVIDIA 공식 입장 "zero PII" + PIPA 고려 설계 — PolitiKAST는 이를 신뢰; 추가 audit 시간 부족 |
| **Gemma 4 학습 데이터 bias 전파** | 한국어 narrative가 Gemma 4의 학습 분포에 의존 | 다중 페르소나 cross-check + KG 사실 검증 |
| **저자 명단의 한자/한글 표기** | BibTeX 영문만 제공 | 논문은 영문 그대로; 부록에 한글 병기 (선택) |

---

## 6. 후속 작업 (다른 팀에 인계할 사항)

| 팀 | 인계 사항 | 본 문서 참조 위치 |
|---|---|---|
| **schema-doc** | 26 컬럼 dtype/enum 정확히 추출, KO↔EN 매핑 | §1.4, §3.3 |
| **eda-analyst** | 5 region row 수, age/edu 분포, 페르소나 텍스트 길이 통계 | §3.3 (보궐 district 표본 및 overlap 확인) |
| **politikast-utility** | 정치성향 추론 가능 컬럼 도출, KG 노드/엣지 후보 | §5.2 (페르소나에 정치 컬럼 없음 → 외부 KG 필수) |
| **paper-writer** | BibTeX 삽입, Limitations 19+/PGM/gender 추가, 1문단 description 사용 | §4.2, §4.3, §5.1 |
| **kg-engineer** | Temporal Firewall($\mathcal{D}_{\le t}$) — KG에 사실의 시점 메타 부여 | §5.2 (Temporal Leakage 리스크) |
| **policy-engineer** | 보궐 district row 수 확인 후 다운스케일 ladder 분배 | §3.3 |

---

## 7. 미확인 / 후속 조사 권장

1. **PGM 정확한 구조** (Bayesian Network vs HMM vs Markov Random Field) — NVIDIA OSS 코드 확인 필요
2. **OCEAN 분포의 한국화 여부** — Korean population에 맞춘 Big-5 통계 사용했는지, US 분포 차용했는지
3. **`military_status` 컬럼 grounding source** — 병무청 통계연보 추정, 미명시
4. **LLM A/B prompt 템플릿** — Data Designer 코드 분석으로 추정 가능 (해커톤 시간 외)
5. **검증 단계의 LLM-as-judge 사용 여부** — Hacker News [^A]에서 Van Segbroeck가 옵션이라 했으나 Korea 판 적용 여부 미공개

[^A]: https://news.ycombinator.com/item?id=46136055

---

## 8. 통계: 본 문서 + 부속 노트

| 파일 | 주요 내용 | 인용 수 |
|---|---|---|
| [`./notes/01_provenance_huggingface.md`](./notes/01_provenance_huggingface.md) | HF 사양, 저자, 컬렉션 계보, 영어 원본 관계 | 11 |
| [`./notes/02_synthesis_pipeline.md`](./notes/02_synthesis_pipeline.md) | NeMo Data Designer + PGM + Gemma 4 31B-IT, 다이어그램 해석 | 12 |
| [`./notes/03_grounding_sources.md`](./notes/03_grounding_sources.md) | KOSIS/대법원/NHIS/KREI/NAVER Cloud, 컬럼 매핑, 라이선스 호환성 | 14 |
| [`./notes/04_citation.md`](./notes/04_citation.md) | CC BY 4.0 의무, BibTeX 권장 후보 7종, 한국어 attribution | 4 |
| **`01_overview.md` (본 문서)** | **5 노트 통합** | **약 30 (참조 통합)** |

**총 unique 외부 인용 URL ≈ 40+** — Perplexity 검색 9회, WebFetch 1회, 로컬 README/이미지 직접 분석 다회.
