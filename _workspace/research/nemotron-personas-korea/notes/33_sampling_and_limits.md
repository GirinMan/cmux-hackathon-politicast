# 33 — 5 Region 페르소나 추출 전략 + 한계/리스크

> Task #20 · owner: politikast-utility
> Source: `data_paths.json` (5 regions), `_workspace/research/nemotron-personas-korea/notes/20_integrity.md` (1M rows, 26 col, null=0, uuid 고유), `30/31/32` 노트
> 의존: `22_region_match.md` (eda-analyst, 실측 반영 완료).

본 노트는 PolitiKAST P0 5 region(서울/광주/대구/부산 북구 갑/대구 달서구 갑) 시뮬레이션을 위해 Nemotron-Personas-Korea 100만 페르소나에서 어떻게 페르소나를 추출할지 — 인구통계 대표성을 보존하면서 LLM 호출 예산(`llm_strategy.json`: 약 10.8k–43.2k 호출)에 맞추는 전략을 설계한다.

## 1. 전제 조건

- 데이터 무결성: 1,000,000 rows, 26 col, null=0, uuid 고유 (`20_integrity.md`).
- 모든 페르소나는 19세 이상 성인(README 명시). PolitiKAST는 이를 그대로 채택한다.
- region 매칭: `province` (광역) + `district` (시군구) 컬럼이 결측 없음 → 정확한 GROUP BY 가능.
- LLM capacity: capacity probe 미완 → 보수적 가정 `MAX_CALLS = 10800` (6h × 60% × 50 RPM).
- timestep 수: P0 4 timestep(scenario 시작 → 중간 → 결과 직전 → 투표일).

## 2. Region 별 모집단 (population in dataset) 실측치

Nemotron 100만 페르소나 전수에서 contract region별 정확 매칭으로 산출했다. `daegu_dalseo_gap`은 `daegu_mayor`의 부분집합이다.

| region_id | province | district | 실측 비중 (1M 기준) | 실측 행수 | 비고 |
|---|---|---|---|---|---|
| `seoul_mayor` | 서울 | (전체) | 18.52% | 185,228 | baseline |
| `gwangju_mayor` | 광주 | (전체) | 2.76% | 27,594 | 진보 baseline |
| `daegu_mayor` | 대구 | (전체) | 4.69% | 46,934 | 보수 baseline |
| `busan_buk_gap` | 부산 | 부산-북구 | 0.54% | 5,421 | 보궐 |
| `daegu_dalseo_gap` | 대구 | 대구-달서구 | 1.06% | 10,617 | 보궐, `daegu_mayor` subset |

## 3. 표본 크기 추천 (capacity 10.8k 호출, 4 timestep, 5 region)

총 호출 = `Σ_region (n_persona_r × T_timestep) + 가상 인터뷰 추가 호출`

- 단순 균등 분배: 10800 / (5 region × 4 timestep × 1.1 마진) ≈ **490 페르소나 / region**
- 가장 작은 `busan_buk_gap`도 5,421명으로 균등 490명 sample이 가능하다.

권고 분배 (P0 / capacity 10.8k):

| region | n_persona | timestep | LLM 호출 |
|---|---:|---:|---:|
| seoul_mayor | 600 | 4 | 2,400 |
| gwangju_mayor | 500 | 4 | 2,000 |
| daegu_mayor | 500 | 4 | 2,000 |
| busan_buk_gap | 400 | 4 | 1,600 |
| daegu_dalseo_gap | 400 | 4 | 1,600 |
| **subtotal** | **2,400** | — | **9,600** |
| 가상 인터뷰 (region당 30명 × 1회) | 150 | — | 150 |
| 캐시미스 마진 (~10%) | — | — | ~1,000 |
| **TOTAL** | — | — | **~10,750** |

**Downscale ladder** (capacity probe 결과에 따라 policy-engineer가 선택):

- L0: 위 권고 (n=400~600, T=4)
- L1: T=3 으로 단축 → 호출 25% 감소
- L2: 모든 region n=300, T=3 → 호출 ~5,400
- L3: secondary regions(busan_buk_gap/daegu_dalseo_gap) n=200, T=2 → 호출 ~3,000
- L4: 단일 region(seoul) demo만, n=200, T=2 → 호출 ~400

## 4. Stratified Sampling 의사코드

5 region 모두에서 인구통계 대표성을 보존하기 위해 **age_group × sex** 2축 stratification을 사용한다(추가 옵션: education_level 또는 housing_type 1축).

```python
# duckdb 또는 pandas 기반. 의사코드.

REGIONS = [
  {"id": "seoul_mayor",     "province": "서울", "district": None, "n": 600},
  {"id": "gwangju_mayor",   "province": "광주", "district": None, "n": 500},
  {"id": "daegu_mayor",     "province": "대구", "district": None, "n": 500},
  {"id": "busan_buk_gap",   "province": "부산", "district": "부산-북구", "n": 400},
  {"id": "daegu_dalseo_gap","province": "대구", "district": "대구-달서구", "n": 400},
]

AGE_BINS = [(19,29),(30,39),(40,49),(50,59),(60,69),(70,200)]
SEX_BINS = ["남","여"]

def stratified_sample(con, region, n_target, seed=42):
    # 1. region 모집단 SELECT
    where = f"province = '{region['province']}'"
    if region["district"] is not None:
        where += f" AND district = '{region['district']}'"

    # 2. stratum별 모집단 비율 산출
    pop = con.sql(f"""
        SELECT
          CASE WHEN age BETWEEN 19 AND 29 THEN '19-29'
               WHEN age BETWEEN 30 AND 39 THEN '30-39'
               WHEN age BETWEEN 40 AND 49 THEN '40-49'
               WHEN age BETWEEN 50 AND 59 THEN '50-59'
               WHEN age BETWEEN 60 AND 69 THEN '60-69'
               ELSE '70+' END AS age_group,
          sex,
          COUNT(*) AS pop_n
        FROM persona_core WHERE {where}
        GROUP BY 1,2
    """).df()

    pop_total = pop["pop_n"].sum()
    pop["target_n"] = (pop["pop_n"] / pop_total * n_target).round().astype(int)

    # 3. stratum별 random sample (seed 고정 — 재현성)
    sampled = []
    for _, row in pop.iterrows():
        q = f"""
            SELECT uuid FROM persona_core
            WHERE {where}
              AND sex = '{row['sex']}'
              AND age BETWEEN {age_lo(row['age_group'])} AND {age_hi(row['age_group'])}
            USING SAMPLE reservoir({row['target_n']} ROWS) REPEATABLE ({seed})
        """
        sampled.extend(con.sql(q).df()["uuid"].tolist())
    return sampled

# 4. 결과 적재
for r in REGIONS:
    uuids = stratified_sample(con, r, r["n"])
    con.execute("""
        INSERT INTO persona_sample (region_id, uuid)
        SELECT ?, unnest(?)
    """, [r["id"], uuids])
```

> **재현성**: `REPEATABLE(seed)` 와 stratum 정렬 순서를 고정. paper Reproducibility appendix 에 seed 명기.
> **검증**: 샘플 후 `age_group × sex` 분포가 region 모집단 비율 ±2% 이내인지 chi-square 또는 단순 percent diff 로 자동 확인.

## 5. 한계 / 리스크 (필수 5항목)

### ① 19세 미만 페르소나 부재 (README 명시)
- Nemotron-Personas-Korea는 만 19세 이상 성인만 수록한다.
- 한국 공직선거법상 선거권 연령(만 18세, 2020년 이후) 과 1년 차이가 있어, **18세 유권자는 시뮬레이션에서 완전히 누락**된다.
- 영향: 18세 인구는 전체 유권자의 ~1.3% 수준이지만, 첫 투표 세대의 정치 참여 패턴은 Z세대 시그널로 중요하다.
- 완화: paper Limitations 절에 명기. 5 region별 결과를 "19세 이상 인구 시뮬레이션"으로 표기.

### ② 종교 / 소득 / 투표이력 컬럼 부재
- 종교: 한국 정치성향과 강한 상관(개신교 보수 경향 등)이 있으나 데이터셋에 없음. `cultural_background` 텍스트가 부분 보완할 수 있으나 일관성 낮다.
- 소득: 직접 컬럼 없음. `housing_type` 과 `occupation` 이 부분 proxy 이지만 ordinal 정보 손실.
- 투표이력: 과거 vote behavior 가 없어 voter agent 의 first-mover preference 가 LLM hallucination 에 의존.
- 영향: KG context_block 만으로 결정해야 하므로 simulation outcome 의 noise 가 커짐.
- 완화: `:Frame` 노드로 이슈 sensitivity 를 보강(부동산/안보/복지/공정), 이를 occupation/housing/age 기반 휴리스틱으로 연결.

### ③ 합성 데이터의 대표성 (PGM 한계)
- README 가 명시: PGM이 변수 간 독립성을 가정하여 sex × major 등 교호작용을 모델링하지 않는다.
- 영향: 직업 분포가 실제 한국 분포보다 gender-balanced 하게 나올 수 있어 gender × occupation 결합 효과(예: 여성 자영업자) 의 정치 시그널이 attenuated 된다.
- 완화: 결과 해석 시 "합성 페르소나 기반" 으로 표기. 원본 KOSIS 분포와의 cross-tab 비교를 paper 부록에 첨부 권고.

### ④ Gender Bias (sex vs gender 구분 부재)
- README 가 명시: 한국 공공 데이터에 포괄적 gender 통계가 없어 생물학적 sex(남/여) 만 포함, 사회적 gender 정체성 미반영.
- 영향: 성소수자·논바이너리 유권자 시뮬레이션 불가. 20·30대 여성 진보 시그널이 sex 단독 변수로 환원되며, 청년 남성 보수화의 다른 축(예: 안티페미니즘 담론) 시그널이 sex 변수로만 표현된다.
- 완화: paper Limitations 절에 explicit하게 명기. 결과 해석 시 "sex-based" 로 한정.

### ⑤ 페르소나 텍스트의 정치 언급 부재 (또는 잠재적 leakage)
- 7종 페르소나 텍스트(`professional/sports/arts/travel/culinary/family/persona`)는 정치 키워드를 의도적으로 배제한 것으로 추정되나, eda-analyst `15_text_stats.md` 결과 미확정.
- 양면 리스크:
  - **부재 시**: voter agent 의 정치 prior 는 인구통계 + LLM 일반 지식에만 의존 → 시뮬레이션이 "교과서적 패턴" 으로 단조로워질 수 있음.
  - **존재 시 (leakage)**: 합성 시점 LLM(gemma-4-31B-it)의 정치 편향이 페르소나에 인쇄되어 결과를 오염시킬 수 있음.
- 완화: eda-analyst 가 1만 샘플에서 정치 키워드 빈도 측정. 0.1% 이상이면 해당 텍스트 컬럼을 P0 prompt에서 제외.

## 6. 후속 / Open Items

- eda-analyst `22_region_match.md` 실측 행수 → 본 노트 §2 표 갱신.
- policy-engineer 가 capacity probe 결과로 §3 Downscale ladder 의 어느 레벨로 갈지 결정.
- 보궐 region province/district 확정 → ✅ `busan_buk_gap`, `daegu_dalseo_gap` 반영 완료.
- schema-doc `13_categorical_enums.md` 결과로 stratification 축에 education 또는 housing 추가 여부 검토.
