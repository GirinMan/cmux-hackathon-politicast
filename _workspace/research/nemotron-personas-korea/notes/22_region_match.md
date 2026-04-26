# 22. 5 Region 매칭 행수 (서울 / 광주 / 대구 / 부산 북구 갑 / 대구 달서구 갑)

> Task #13 — `eda-analyst`. 재현: `scripts/region_match.py`.
> 데이터: `eda_charts/_data/{region_match,province_breakdown,gyeonggi_districts}.csv`.

## 1. 컬럼 발견

`integrity_check.py` 결과 `province` + `district` 두 컬럼이 모든 행에 존재(결측 0). 따라서 **텍스트 LIKE 휴리스틱이 아니라 정확한 GROUP BY** 가능.

값 형식:
- `province` — **광역단위 약칭**(예: `서울`, `경기`, `광주`, `대구`, `경상남`, `충청북`). "특별시/광역시/도" 접미사 없음.
- `district` — **`<광역약칭>-<시군구>[ <구>]` 하이픈 구분**(예: `부산-북구`, `대구-달서구`, `서울-강남구`).

> ⚠ 휴리스틱 주의: `district LIKE '%북구%'`는 여러 광역시 북구를 섞을 수 있음 → `province`와 `district`를 함께 정확 매칭한다.

## 2. Province 분포 (전수, 17개)

| province (약칭) | n | % |
|---|---:|---:|
| 경기 | 262,154 | 26.22 |
| 서울 | 185,228 | 18.52 |
| 부산 | 65,285 | 6.53 |
| 경상남 | 62,416 | 6.24 |
| 인천 | 58,991 | 5.90 |
| 경상북 | 50,298 | 5.03 |
| 대구 | 46,934 | 4.69 |
| 충청남 | 41,456 | 4.15 |
| 전라남 | 34,391 | 3.44 |
| 전북 | 34,188 | 3.42 |
| 충청북 | 31,296 | 3.13 |
| 강원 | 30,200 | 3.02 |
| 대전 | 28,646 | 2.86 |
| 광주 | 27,594 | 2.76 |
| 울산 | 21,317 | 2.13 |
| 제주 | 12,673 | 1.27 |
| 세종 | 6,933 | 0.69 |

합계: 1,000,000. 한국 17개 광역 모두 커버 (전북=전라북, 전남=전라남 별표기 — 전북만 약칭형 `전북`이고 나머지는 `전라남`/`경상북` 식 풀네임 → **약칭 비일관성**, 매칭 시 주의).

## 3. PolitiKAST contract region 매칭 결과

![5 region row counts](./eda_charts/region_match_bar.png)

매칭 규칙은 `_workspace/contracts/data_paths.json`의 5개 region을 그대로 따른다. `daegu_dalseo_gap`은 `daegu_mayor`의 부분집합이므로 아래 count는 disjoint CASE가 아니라 region별 독립 COUNT이다.

```sql
SELECT 'seoul_mayor', COUNT(*) FROM persona_core WHERE province = '서울'
UNION ALL
SELECT 'gwangju_mayor', COUNT(*) FROM persona_core WHERE province = '광주'
UNION ALL
SELECT 'daegu_mayor', COUNT(*) FROM persona_core WHERE province = '대구'
UNION ALL
SELECT 'busan_buk_gap', COUNT(*) FROM persona_core
  WHERE province = '부산' AND district = '부산-북구'
UNION ALL
SELECT 'daegu_dalseo_gap', COUNT(*) FROM persona_core
  WHERE province = '대구' AND district = '대구-달서구'
```

| region | n | % | 매칭 키 |
|---|---:|---:|---|
| **seoul_mayor** | **185,228** | **18.52** | `province = '서울'` |
| **daegu_mayor** | **46,934** | **4.69** | `province = '대구'` |
| **gwangju_mayor** | **27,594** | **2.76** | `province = '광주'` |
| **daegu_dalseo_gap** | **10,617** | **1.06** | `province='대구' AND district='대구-달서구'` |
| **busan_buk_gap** | **5,421** | **0.54** | `province='부산' AND district='부산-북구'` |

### 핵심 인사이트

1. **서울 18.5만 명** — 가장 큰 페르소나 풀, 모든 다운스케일 사다리에서 sample size 여유.
2. **광주 27.6k, 대구 46.9k** — 광역시장 contest는 충분한 stratified down-sampling 가능.
3. **부산 북구 5.4k, 대구 달서구 10.6k** — 보궐 contest도 district-level sample 400명 기준으로 충분한 모집단 확보.
4. **중복 주의** — `daegu_dalseo_gap`은 `daegu_mayor`에 포함된다. contest별 sample frame은 독립으로 취급하고 5개 행수를 단순 합산해 전체 커버리지로 해석하면 안 된다.

## 4. 보궐선거 region 검증

보궐 region은 현재 계약에서 아래 2개로 확정됐다.

- `busan_buk_gap`: `district='부산-북구'` = 5,421명.
- `daegu_dalseo_gap`: `district='대구-달서구'` = 10,617명.

전체 부산/대구 district 분포는 `eda_charts/_data/by_election_districts.csv` 참조.

## 6. 다음 단계

- **utility 팀(#20)**: 위 region별 페르소나 N을 받아 region별 sample 전략(stratified vs full vs upsample) 수립.
- **data-engineer**: `politikast.duckdb` 인제션 시 위 5 region region 컬럼 derived view 미리 생성 (이 SQL 그대로).
- **paper-writer**: 표 3(데이터) 5 region row count 표를 위 매칭 결과로 채움.

---
재현: `python3 scripts/region_match.py`
