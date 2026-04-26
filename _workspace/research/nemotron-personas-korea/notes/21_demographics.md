# 21. Demographics 분포 (age / sex / marital / education)

> Task #12 — `eda-analyst`. 재현: `scripts/demographics.py`. 데이터: `eda_charts/_data/{age_summary,age_hist,sex_pie,marital_bar,education_bar}.csv`.
> 한글 폰트 부재로 차트 라벨은 영문, 본 노트는 한글 병기.

## 1. Age (만나이)

![Age histogram](./eda_charts/age_hist.png)

| 통계 | 값 |
|---|---:|
| N | 1,000,000 |
| min | 19 |
| 5%ile | 23 |
| 25%ile | 36 |
| **median** | **51** |
| mean | 50.66 |
| 75%ile | 64 |
| 95%ile | 80 |
| max | 99 |
| std | 17.61 |

- **만 19세 이상만 포함** → 합성 단계에서 성인(투표권 보유)만 샘플링.
- 분포는 한국 통계청 추정과 비교해 **고연령 쪽으로 두꺼운 편**(median 51 vs 한국 중위연령 ≈ 45세, 2024). PolitiKAST에서 region별 가중을 줄 때 이 점 인지.
- **선거권 한계**: 한국 공직선거법 만 18세 이상이지만 데이터셋은 19+. 만 18세 유권자(2026년 시점 약 60만 명)는 미커버 → Limitations 섹션 명시 필요.

## 2. Sex

![Sex pie](./eda_charts/sex_pie.png)

| sex | n | % |
|---|---:|---:|
| 여자 (Female) | 504,442 | 50.44 |
| 남자 (Male) | 495,558 | 49.56 |

- 여성 비율 50.44 % — 사실상 균형(±0.5 pp).
- 단 2개 enum (`남자`/`여자`)만 등장. **3rd-gender / nonbinary 표현 없음** → Limitations.

## 3. Marital status

![Marital status](./eda_charts/marital_bar.png)

| marital_status | EN | n | % |
|---|---|---:|---:|
| 배우자있음 | Married | 592,538 | 59.25 |
| 미혼 | Never married | 256,962 | 25.70 |
| 사별 | Widowed | 87,888 | 8.79 |
| 이혼 | Divorced | 62,612 | 6.26 |

- 4-class enum, 결측 0. "기혼+동거" 분리 없음 → 한국 통계청 KOSIS 인구주택총조사 분류와 호환.
- **기혼(59 %)**이 다수 → 가족 효과(`family_persona`) 활용 가치 큼.

## 4. Education level

![Education level](./eda_charts/education_bar.png)

| education_level | EN | n | % |
|---|---|---:|---:|
| 고등학교 | High school | 331,377 | 33.14 |
| 4년제 대학교 | 4yr university | 271,256 | 27.13 |
| 2~3년제 전문대학 | 2-3yr college | 150,235 | 15.02 |
| 중학교 | Middle school | 85,255 | 8.53 |
| 초등학교 | Elementary | 81,239 | 8.12 |
| 대학원 | Graduate | 54,323 | 5.43 |
| 무학 | None | 26,315 | 2.63 |

- 7-class ordinal. 고졸 33 % + 4년제 대학 27 % = 60 % → 한국 평균 학력(고졸 이상 ≈ 88 %)과 정합.
- **대졸 이상(4년제+대학원) 32.6 %** — 한국 25–64세 고등교육 이수율(50 % 이상)에 비해 약간 낮음. 이는 19+ 전체(고령 포함)이기 때문일 가능성 큼. region별 비교 시 주의.

## 5. 인사이트

1. **합성 분포 ≈ 한국 인구통계 근사**: sex 균형, marital 4-class, education 7-class 모두 KOSIS 카테고리와 1:1 매핑 가능 — Voter agent 프롬프트에 그대로 주입 가능.
2. **연령 cutoff 19+**: 만 18세 유권자 미포함 → 시뮬레이션의 외적 타당성 한계로 paper Limitations에 명시.
3. **enum 표 안정**: 위 4개 필드 모두 닫힌 enum → KG node attribute / DuckDB ENUM dtype 적용 가능.
4. **gender binary**: nonbinary 미반영 → 사회적 representativeness 문제, paper Limitations.

---
재현: `python3 scripts/demographics.py`
