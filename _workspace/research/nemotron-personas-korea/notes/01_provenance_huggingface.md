# 01. HuggingFace + Nemotron Personas Lineage

- 작성일: 2026-04-26
- 데이터셋: `nvidia/Nemotron-Personas-Korea`
- 데이터셋 버전: 1.0 (2026-04-20)
- 라이선스: CC BY 4.0
- 작성자: provenance-research

## 1. HuggingFace 공개 정보

| 항목 | 값 | 출처 |
|---|---|---|
| Repo URL | https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea | README.md (line 128) [^1] |
| Release date | 2026-04-20 (HF), 블로그 발표 2026-04-21 | README.md, TheAgentTimes [^2] |
| Splits | `train` 단일 split (1,000,000 records) | README.md `dataset_info` |
| File layout | 9 shards × ~210MB Parquet (`data/train-0000{0..8}-of-00009.parquet`) | 로컬 디렉토리 확인 |
| Compressed download size | 1,982,395,106 bytes (≈1.98 GB) | README.md `download_size` |
| Uncompressed dataset size | 4,195,142,595 bytes (≈4.19 GB) | README.md `dataset_size` |
| Tokens | 1.7B 전체 / 1B persona 토큰 | README.md "Field & Token Counts" |
| 컬럼 수 | 26 (uuid 포함) — 필드 분류: 7 persona + 6 attribute + 12 demographic/geo + 1 uuid | README.md "Dataset Details" |
| 페르소나 수 | 7M (1M 레코드 × 7 persona 변종) | README.md, TheAgentTimes [^2] |
| Tags | `synthetic, personas, NVIDIA, Korean, datadesigner` | README.md frontmatter |

## 2. 데이터셋 저자(Author) 명단 — 공식 BibTeX 기준

README.md 라인 401–406에 등재된 저자 13인 (소속 기재 없음, 모두 NVIDIA 또는 협력 파트너로 추정):

1. Hyunwoo Kim
2. Jihyeon Ryu
3. Jinho Lee
4. Hyungon Ryu
5. Kiran Praveen
6. Shyamala Prayaga
7. Kirit Thadaka
8. Will Jennings
9. Bardiya Sadeghi
10. Ashton Sharabiani
11. Yejin Choi
12. Yev Meyer (← Nemotron-Personas 원본의 1저자, 아래 참조)

(영문 표기는 README BibTeX 그대로)

## 3. Nemotron Personas Collection 계보 (Cross-Country Lineage)

NVIDIA의 **Sovereign AI 데이터** 시리즈로 다국가 확장 중인 컬렉션의 한국어 판이다.

| 국가 | HF Repo | 발표 | 협력기관 | 비고 |
|---|---|---|---|---|
| 🇺🇸 USA (원본) | `nvidia/Nemotron-Personas` | 2025-06 | Gretel(인수합병) | 100K records, 22 fields, US Census 그라운딩 [^3][^4] |
| 🇺🇸 USA (확장) | `nvidia/Nemotron-Personas-USA` | 2026 (≤4월) | NVIDIA | 1M+ records, CC BY 4.0 [^5] |
| 🇯🇵 Japan | `nvidia/Nemotron-Personas-Japan` | 2025–2026 | (NVIDIA, 일본 통계) | 1M records × 6 persona = 6M, 22 fields, 1.4B 토큰. Fujita et al. (2025) [^6] |
| 🇮🇳 India | `nvidia/Nemotron-Personas-India` | 2025 | (NVIDIA) | NVIDIA 개발자 페이지 컬렉션 [^7] |
| 🇸🇬 Singapore | (HF) | 2025 | AI Singapore | NVIDIA 블로그 [^2] |
| 🇧🇷 Brazil | `nvidia/Nemotron-Personas-Brazil` | 2026-02 | WideLabs (IBGE 데이터) | 6M personas, CC BY 4.0 [^8] |
| 🇫🇷 France | (HF) | 2026 | Pleias | NVIDIA 블로그 [^2] |
| 🇰🇷 **Korea** | `nvidia/Nemotron-Personas-Korea` | **2026-04-20** | NAVER Cloud (seed/expertise) | **본 분석 대상.** 1M × 7 persona = 7M, 26 fields, 1.7B 토큰 [^1][^2] |

**한국 판의 차별점:**
- 영어/일본/인도/브라질 판 대비 **컬럼 수 26개로 최대** (페르소나 7종 — 직업/스포츠/예술/여행/음식/가족/요약 — 으로 1개 늘어남: 영어 원본은 6종)
- 토큰 수 1.7B로 일본판(1.4B)보다 큼
- 그라운딩 소스가 가장 다양 (KOSIS + 대법원 + NHIS + KREI + NAVER Cloud)
- 19세 이상 성인 페르소나만 포함 (한국 법정 성년 기준) — 영어 판은 18+ 추정 (US 18세 성년)

## 4. 영어 원본(Nemotron-Personas) 계보 추적

- 원본은 NVIDIA가 **인수합병한 Gretel**의 합성 데이터 기술을 기반으로 NeMo Data Designer (오픈소스)에 통합되어 출시되었다 [^4][^9].
- 원본 인용은 **Meyer & Corneil (2025) — "Nemotron Persona"** 로 SCOPE 논문 등 외부 연구가 인용 [^10].
- 원본 데이터셋(`nvidia/Nemotron-Personas`)은 100K records, 22 fields, ~54M tokens, 약 600K 페르소나 (미국 인구조사 기반) [^3].
- Korea 판은 원본 스키마(7 persona + 6 attribute + demographic/geo + uuid)를 **상속**하되, 한국 컨텍스트에 맞게 다음을 추가/조정:
  - 추가 필드: `military_status` (한국 특수), `bachelors_field` (전공), `family_type`/`housing_type` (한국 인구조사 분류)
  - 변경: `state` → `province`/`district` (시도/시군구 행정구역)
  - 한국어 화자만 대상이므로 모든 텍스트 필드는 한국어 (영어 원본 → 한글)

## 5. NVIDIA Nemotron Datasets 패밀리 내 위치

NVIDIA Developer 페이지 [^11]에 등재된 Nemotron Datasets 7대 카테고리 중 **"Nemotron Personas Datasets"** 카테고리에 속한다:
- Pre-/Post-Training Datasets (10T+ tokens)
- **Personas Datasets** ← Korea 포함
- Llama Nemotron VLM Dataset
- Safety Datasets
- RL Datasets
- RAG Datasets

PolitiKAST 관점에서 중요한 점: 같은 "Personas" 카테고리 안에서 **Sovereign AI** 라는 키워드로 묶여 있다 — 즉 NVIDIA는 명시적으로 "각 국가의 모델 개발자가 자국 인구통계 기반 모델을 만들도록" 지원하기 위한 데이터로 포지셔닝한다 (README.md 영문 단락 102–104).

## 6. Privacy/PII 상태

- README.md 영문 119: "All data, while mirroring real-world distributions, is **completely artificially generated**. Any similarity in names or persona descriptions to actual persons, living or dead, is purely coincidental."
- TheAgentTimes 보도 [^2]: "every persona is demographically accurate but contains **zero personally identifiable information**" — 한국 PIPA(개인정보 보호법)을 염두에 두고 설계.
- 단, 이름은 대법원 실제 출생연도-성별 분포로부터 합성되므로 동명이인이 다수 존재할 수 있다 (README 244: "Kim Young-sook" 빈도가 한국 실제 조사와 일치).

## 7. 미확인 항목

- arXiv 또는 동료심사 논문 부재: Korea 판은 현재 공식 BibTeX가 **`@software`** 형식으로 dataset card에만 존재 (논문 미공개). Japan 판은 외부 인용에서 `@misc{Fujita2025}` 형태로 사용되지만 arXiv 등재는 미확인. PolitiKAST 논문에서는 README BibTeX 그대로 사용해야 안전.
- HF 다운로드/star 수: Korea 판 specific 통계 미확인 (Nerq 등 분석은 USA 판 기준만 존재).
- Korea 판 발표 블로그(Hugging Face Blog `nvidia/nemotron-personas-korea` 추정 URL): 직접 fetch 미시도 (Task #4에서 시도).

## 각주(References)

[^1]: NVIDIA Corporation. *Nemotron-Personas-Korea README.md*. 로컬 사본: `/Users/girinman/datasets/Nemotron-Personas-Korea/README.md`. HF: https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea
[^2]: TheAgentTimes. "NVIDIA Ships 7 Million Synthetic Korean Personas to Ground Our..." 2026-04-21. https://theagenttimes.com/articles/nvidia-ships-7-million-synthetic-korean-personas-to-ground-o-5a257af0
[^3]: HyperAI. "Nemotron-Personas Character Dataset." 2025-06-12. https://beta.hyper.ai/en/datasets/40514
[^4]: Hacker News (Van Segbroeck). "NVIDIA open sources the synthetic data framework used to build Nemotron datasets." 2025-12-03. https://news.ycombinator.com/item?id=46136055
[^5]: Nerq. "Nemotron-Personas-USA Dataset Trust Analysis 2026." https://nerq.ai/dataset/nemotron-personas-usa
[^6]: Macnica. "Trying out AI persona marketing with NVIDIA DGX Spark: Part 2." 2026-03-24. https://www.macnica.co.jp/en/business/semiconductor/articles/nvidia/149439/ — Fujita, A., Gong, V., Ogushi, M., Yamamoto, K., Suhara, Y., Corneil, D., & Meyer, Y. (2025). *Nemotron-Personas-Japan: Synthetic Personas Aligned to Real-World Distributions*.
[^7]: NVIDIA Developer. "NVIDIA Nemotron AI Models." https://developer.nvidia.com/nemotron
[^8]: HyperAI. "NVIDIA Launches Nemotron-Personas-Brazil." 2026-02-04. https://hyper.ai/en/stories/7d0bdfd7adc69f7660bdf800ed0b305e
[^9]: Chris (YouTube). "Exploring the NVIDIA Personas Dataset - 600K Synthetic Personas." 2025-06-13. https://www.youtube.com/watch?v=47IayEsgtLQ
[^10]: arXiv 2601.07110 (SCOPE). "The Need for a Socially-Grounded Persona Framework for User..." 2026. https://arxiv.org/html/2601.07110v1 — citing Meyer & Corneil (2025) Nemotron Persona.
[^11]: NVIDIA Developer. "NVIDIA Nemotron Datasets." https://developer.nvidia.com/nemotron
