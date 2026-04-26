# 04. CC BY 4.0 인용 의무 + BibTeX 후보

- 작성일: 2026-04-26
- 데이터셋: `nvidia/Nemotron-Personas-Korea` v1.0 (2026-04-20)
- 작성자: provenance-research
- 활용처: PolitiKAST 논문 `paper/elex-kg-final.tex`

## 1. CC BY 4.0 라이선스 의무 요약

데이터셋은 **Creative Commons Attribution 4.0 International (CC BY 4.0)** [^1] 으로 배포된다. PolitiKAST가 이를 활용·재배포·상업 사용·수정할 때 다음 4가지 의무를 만족해야 한다 [^2][^3]:

| # | 의무 | PolitiKAST 이행 방법 |
|---|---|---|
| 1 | **출처 표시(Attribution)** — 저작자명 | 논문 본문/Reference + 코드 README + 대시보드 footer에 "NVIDIA Corporation" 명시 |
| 2 | **출처 URL/원본 링크** | https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea |
| 3 | **라이선스 표기** | "Released under CC BY 4.0" 명시 |
| 4 | **변경 사항 명시(Indicate changes)** | "We extract a 5-contest subsample (서울시장/광주시장/대구시장/부산 북구 갑/대구 달서구 갑) and re-condition for adult-19+ voter agents" 등 변경 내용 기재 |

CC BY 4.0은 **카피레프트가 아니므로** PolitiKAST 자체 코드/논문 라이선스를 자유롭게 선택 가능 (CC BY 4.0 의무는 페르소나 데이터 부분에만 적용).

## 2. NVIDIA 공식 BibTeX (README.md 라인 400–406, 그대로)

```bibtex
@software{nvidia/Nemotron-Personas-Korea,
  author = {Kim, Hyunwoo and Ryu, Jihyeon and Lee, Jinho and Ryu, Hyungon and Praveen, Kiran and Prayaga, Shyamala and Thadaka, Kirit and Jennings, Will and Sadeghi, Bardiya and Sharabiani, Ashton and Choi, Yejin and Meyer, Yev},
  title = {Nemotron-Personas-Korea: Synthetic Personas Aligned to Real-World Distributions for Korea},
  month = {April},
  year = {2026},
  url = {https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea}
}
```

> **주의:** 이 BibTeX은 README에 그대로 기재된 형태이지만 BibTeX 문법상 다음 두 가지 이슈가 있다:
> 1. citation key `nvidia/Nemotron-Personas-Korea` 의 슬래시(`/`) — LaTeX/BibTeX은 허용하지만 일부 백엔드(biber/biblatex)에서 파싱 오류 가능.
> 2. `month = {April}` — `month = apr` (BibTeX macro)이 더 호환성 좋음.

## 3. PolitiKAST 권장 BibTeX (호환성 보강 버전)

`paper/elex-kg-final.tex`에 삽입할 수 있도록 키 슬래시를 underscore로 치환하고 month macro 사용한 버전:

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
  note         = {Licensed under CC BY 4.0; 1M records, 7M personas,
                  grounded in KOSIS, Supreme Court of Korea, NHIS, KREI},
  url          = {https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea}
}
```

논문 본문 인용 권장 형태 (LaTeX):
```latex
We use the Nemotron-Personas-Korea dataset~\cite{nvidia2026nemotronpersonaskorea}, an
open synthetic persona dataset of 1M records (7M personas) released by NVIDIA under CC BY 4.0
and grounded in official Korean statistics (KOSIS, NHIS, KREI, Supreme Court of Korea).
```

## 4. 수반 인용 권장 후보 (Secondary citations)

PolitiKAST 논문에서 데이터셋의 *기술적 맥락*을 논의할 때 함께 인용하면 좋은 자료:

### 4.1 NeMo Data Designer (생성 도구)

```bibtex
@software{nvidia2025nemodatadesigner,
  author       = {{NVIDIA Corporation}},
  title        = {{NeMo Data Designer}: An Enterprise-Grade Compound AI System
                  for Synthetic Data Generation},
  year         = {2025},
  publisher    = {NVIDIA},
  note         = {Open-sourced December 2025; Apache-2.0},
  url          = {https://github.com/NVIDIA-NeMo/DataDesigner}
}
```

### 4.2 Gemma 4 31B-IT (생성에 사용된 LLM)

```bibtex
@misc{google2026gemma4,
  author       = {{Google DeepMind}},
  title        = {{Gemma 4}: Open Models from Google},
  year         = {2026},
  month        = apr,
  note         = {Apache-2.0; the 31B Instruction-Tuned variant
                  was used by Nemotron-Personas-Korea},
  url          = {https://ai.google.dev/gemma}
}
```

### 4.3 Nemotron-Personas (영어 원본; 계보)

```bibtex
@misc{meyer2025nemotronpersonas,
  author       = {Meyer, Yev and Corneil, Dane},
  title        = {{Nemotron-Personas}: Synthetic Personas Aligned to
                  Real-World Distributions},
  year         = {2025},
  publisher    = {NVIDIA},
  url          = {https://huggingface.co/datasets/nvidia/Nemotron-Personas}
}
```

### 4.4 Nemotron-Personas-Japan (자매 데이터셋, 외부 인용 사례)

```bibtex
@misc{fujita2025nemotronpersonasjapan,
  author       = {Fujita, A. and Gong, V. and Ogushi, M. and Yamamoto, K. and
                  Suhara, Y. and Corneil, D. and Meyer, Y.},
  title        = {{Nemotron-Personas-Japan}: Synthetic Personas Aligned to
                  Real-World Distributions},
  year         = {2025},
  publisher    = {NVIDIA},
  url          = {https://huggingface.co/datasets/nvidia/Nemotron-Personas-Japan}
}
```

### 4.5 KOSIS (1차 grounding source)

```bibtex
@misc{kosis2026,
  author       = {{Statistics Korea / National Data Office}},
  title        = {{KOSIS}: Korean Statistical Information Service},
  howpublished = {\url{https://kosis.kr}},
  note         = {Census, employment (KSCO 8th classification),
                  social survey, and household statistics},
  year         = {2026}
}
```

### 4.6 NHIS 표본 데이터

```bibtex
@misc{nhis2024healthcheckup,
  author       = {{National Health Insurance Service}},
  title        = {NHIS Health Checkup Information (as of 2024-12-31)},
  howpublished = {Korea Public Data Portal},
  year         = {2025},
  note         = {KOGL Type 0 license; sample of 1M Korean adults},
  url          = {https://www.data.go.kr/data/15007122/fileData.do}
}
```

### 4.7 KREI 식품소비행태조사

```bibtex
@techreport{krei2024foodconsumption,
  author       = {Lee, Kyeiim and others},
  title        = {2024 Food Consumption Behavior Survey: Statistical Report},
  institution  = {Korea Rural Economic Institute (KREI)},
  year         = {2025},
  month        = may,
  note         = {KOGL Type 4 license},
  url          = {https://www.krei.re.kr/krei/page/53?cmd=view&biblioId=543024}
}
```

## 5. 한국어 텍스트 attribution 예시 (대시보드/README용)

```
본 시뮬레이션은 NVIDIA의 Nemotron-Personas-Korea v1.0 (2026-04-20)을 사용합니다.
원본 데이터셋은 CC BY 4.0 라이선스로 공개되어 있으며, 출처는 다음과 같습니다:

  Kim, H., Ryu, J., Lee, J., Ryu, H., Praveen, K., Prayaga, S.,
  Thadaka, K., Jennings, W., Sadeghi, B., Sharabiani, A.,
  Choi, Y., & Meyer, Y. (2026). Nemotron-Personas-Korea:
  Synthetic Personas Aligned to Real-World Distributions for Korea.
  NVIDIA Corporation. https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea

원본 데이터셋은 KOSIS, 대법원, 국민건강보험공단(NHIS), 한국농촌경제연구원(KREI),
NAVER Cloud의 자료를 기반으로 합성되었습니다.

PolitiKAST 시스템은 본 데이터셋에서 5개 선거구/행정구역(서울시장/광주시장/대구시장/부산 북구 갑/대구 달서구 갑)의
페르소나 부분 집합을 추출하여 정치 시뮬레이션 용도로 재가공하였습니다.
```

## 6. 잠재적 리스크 및 대응

| 리스크 | 설명 | 대응 |
|---|---|---|
| 저자 명단의 한자/한글 표기 일관성 | BibTeX이 영문 표기만 제공 | 논문에서 영문 그대로 사용; 한글 부록 필요시 별도 표 |
| Korea 판이 향후 v2.0으로 업데이트될 가능성 | 1.0 필드 셋이 변경될 수 있음 | `version = {1.0}` 명시 + 다운로드 timestamp 코드 commit hash로 고정 |
| Gemma 4의 학습 데이터 출처 우려 (간접) | Gemma 4가 학습한 텍스트의 라이선스가 페르소나 narrative에 어떻게 영향? | Gemma 4는 Apache-2.0 출력물 권리 제한 없음 [^4] → 안전 |
| 페르소나에 실명과 유사한 이름 출현 | 대법원 통계 기반이므로 실재 인물과 동명이인 가능 | README L113 명시 *"전적으로 우연"* — PolitiKAST 대시보드에서 fictional disclaimer 표시 |

## 7. 요약 — 논문 1줄 인용 + 1문단 description

**1줄 (Reference 섹션):**
> Kim, H. et al. (2026). *Nemotron-Personas-Korea: Synthetic Personas Aligned to Real-World Distributions for Korea*. NVIDIA Corporation. https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea (CC BY 4.0)

**1문단 (Data 섹션):**
> We build voter agent populations from **Nemotron-Personas-Korea** ([Kim et al., 2026]; CC BY 4.0), an open synthetic persona dataset of 1,000,000 records spanning 7,000,000 narrative personas (1.7B tokens) across 26 fields. The dataset was generated with NVIDIA's NeMo Data Designer using a probabilistic graphical model fit to official Korean statistics (KOSIS, Supreme Court of Korea, NHIS, KREI; with seed contributions from NAVER Cloud) and the Apache-2.0 licensed `google/gemma-4-31B-it` language model. Coverage spans 17 provinces and 252 districts and includes only adult personas (≥19, the South Korean legal age of adulthood). For PolitiKAST, we filter five focal regions (Seoul, Gwangju, Daegu, Uiwang-si, and Ganghwa-gun) and use the 12 demographic/geographic fields together with the 6 attribute fields and 7 narrative persona fields to condition CAMEL voter agents.

## 각주

[^1]: Creative Commons. *Attribution 4.0 International (CC BY 4.0) — Legal Code*. https://creativecommons.org/licenses/by/4.0/legalcode
[^2]: Creative Commons. *Attribution 4.0 International (CC BY 4.0) — Deed*. https://creativecommons.org/licenses/by/4.0/deed.en
[^3]: Creative Commons Wiki. "Best practices for attribution." https://wiki.creativecommons.org/wiki/Best_practices_for_attribution
[^4]: Implicator. "Google Releases Gemma 4 Open Models Under Apache 2.0." 2026-04-02. https://www.implicator.ai/google-releases-gemma-4-under-apache-2-0-dropping-its-custom-ai-license/
