# 20. Integrity & Schema Consistency (9 Parquet Shards 전수)

> Task #11 — `eda-analyst`. 재현 스크립트: `scripts/integrity_check.py`. 데이터: `eda_charts/_data/integrity_*.csv`, `integrity_uuid.json`.

## 1. Shard 행수 / 파일 사이즈

| shard | rows | size (MB) |
|---|---:|---:|
| train-00000-of-00009.parquet | 111,112 | 220.3 |
| train-00001-of-00009.parquet | 111,111 | 220.2 |
| train-00002-of-00009.parquet | 111,111 | 220.3 |
| train-00003-of-00009.parquet | 111,111 | 220.3 |
| train-00004-of-00009.parquet | 111,111 | 220.3 |
| train-00005-of-00009.parquet | 111,111 | 220.2 |
| train-00006-of-00009.parquet | 111,111 | 220.4 |
| train-00007-of-00009.parquet | 111,111 | 220.3 |
| train-00008-of-00009.parquet | 111,111 | 220.3 |
| **TOTAL** | **1,000,000** | **1,983** |

- 9개 shard 합계 정확히 **1,000,000행**(00번 shard만 +1).
- 각 shard ≈ 220 MB, 총 ≈ 1.98 GB. 메모리 8 GB 이내에서 DuckDB streaming SQL로 풀스캔 가능.

## 2. Schema 동일성

- 컬럼 수: **26** (모든 shard 동일).
- 컬럼 이름·타입·순서 9 shards 전수 일치 → `all_match=True`.
- 타입 분포: `BIGINT` 1개(`age`), 나머지 25개 `VARCHAR`.

레퍼런스 schema (column order 그대로):

```
uuid, professional_persona, sports_persona, arts_persona, travel_persona,
culinary_persona, family_persona, persona, cultural_background,
skills_and_expertise, skills_and_expertise_list,
hobbies_and_interests, hobbies_and_interests_list,
career_goals_and_ambitions, sex, age, marital_status, military_status,
family_type, housing_type, education_level, bachelors_field,
occupation, district, province, country
```

→ schema-doc 의 README 추출 결과(40+ 컬럼) 대비 실제 parquet은 **26 컬럼**으로 더 슬림. README의 일부 enriched 필드(예: 정치/경제 라벨)가 공개 train split에 포함되지 않을 수 있음. 추후 schema-doc과 cross-check 권장.

## 3. UUID Uniqueness (전수)

| 항목 | 값 |
|---|---|
| id column | `uuid` (VARCHAR) |
| total rows | 1,000,000 |
| distinct uuid | 1,000,000 |
| null uuid | 0 |
| **unique?** | ✅ True |

→ `uuid`를 1차 키로 안전하게 사용 가능. KG persona 노드 식별자로 채택 권장.

## 4. 결측(NULL) 비율 — 전수

26 컬럼 전수 `null_count = 0`. 즉 **결측 없음**(0.000 %).

> 합성 데이터 특성상 모든 셀이 채워져 있음. 단, 일부 텍스트 필드는 빈 문자열/placeholder일 가능성이 있어 Task #15(페르소나 텍스트 길이)에서 추가 점검.

## 5. 인사이트 / 다음 단계

1. **데이터 무결성 양호**: shard 결측 0, schema 9 shards 동일, uuid 고유 → DuckDB `read_parquet('.../*.parquet')` glob으로 안전하게 통합 적재 가능.
2. **컬럼 부족 감지**: README가 40+ 필드를 광고하는 반면 train split은 26 컬럼만 노출. provenance/ schema-doc 팀과 합동 검증 필요(README 광고 vs 실제 split 차이).
3. **PolitiKAST 활용**: `province` + `district`가 모든 행에 존재 → Task #13의 5 region 매칭은 텍스트 LIKE 휴리스틱이 아니라 정확한 GROUP BY 가능 (false positive 위험 거의 0).
4. **persona 텍스트 7종**: `professional_persona / sports_persona / arts_persona / travel_persona / culinary_persona / family_persona / persona` — Task #15에서 길이 통계.

---
재현: `python3 scripts/integrity_check.py` (DuckDB 1.5+, pandas 2.0+).
