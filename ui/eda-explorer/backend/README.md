# EDA Explorer — Backend (FastAPI)

Nemotron-Personas-Korea (1M personas) 인터랙티브 EDA + PolitiKAST contract region 필터를 제공하는 FastAPI 백엔드.

## 데이터 소스

우선순위:
1. `_workspace/db/politikast.duckdb` — `persona_core` (1M, demographics) + `persona_text` (1M, 6 long text) + `personas_{region_id}` contract tables.
2. `_workspace/contracts/data_paths.json`의 `nemotron_parquet_dir` — DB 가 없거나 테이블이 비어 있으면 in-memory view 로 fallback.

`/api/health` 가 현재 모드를 반환한다.

## 실행

```bash
# uv 사용 (시스템 python/pip 금지)
uv run --project /Users/girinman/repos/cmux-hackathon-politicast/ui/eda-explorer/backend \
  uvicorn app:app --reload --port 8235 --host 127.0.0.1
```

OpenAPI: http://127.0.0.1:8235/docs · http://127.0.0.1:8235/openapi.json

## 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/health` | 데이터 모드·테이블 row count |
| GET | `/api/schema` | 모든 테이블 schema |
| GET | `/api/demographics?region=` | age/sex/marital/education 분포 |
| GET | `/api/regions` | 17 시도 분포 |
| GET | `/api/regions/five` | PolitiKAST contract regions |
| GET | `/api/occupations?region=&limit=` | 직업 top-N |
| GET | `/api/occupations/major?region=` | KSCO-style 11-group heuristic rollup |
| GET | `/api/ontology/graph?region=&cluster_limit=&occupation_limit=&min_count=` | categorical ontology graph |
| GET | `/api/personas/sample?region=&limit=&seed=` | 랜덤 N 페르소나 |
| GET | `/api/personas/{uuid}` | 단일 페르소나 상세 (core+text join, *_list 파싱) |
| GET | `/api/personas/text-stats?region=&sample_size=` | 텍스트 9종 길이 통계 |

`region` 파라미터는 `_workspace/contracts/data_paths.json`의 region id를 사용한다:
`seoul_mayor / gwangju_mayor / daegu_mayor / busan_buk_gap / daegu_dalseo_gap`.

## 테스트

```bash
uv run --project /Users/girinman/repos/cmux-hackathon-politicast/ui/eda-explorer/backend \
  --extra test pytest -q
```

## 코드 컨벤션

- 모든 SQL 은 `db.query(sql, params)` prepared statement.
- 응답 모델은 `models.py` Pydantic — frontend 가 OpenAPI 로 자동 검증.
- CORS 는 `http://localhost:8234`, `http://127.0.0.1:8234` 만 허용.
- `province` 약식 표기(`서울`/`경기`/`경상남` 등) 보존 — 외부 join 시 별도 매핑 필요.
- `*_list` 컬럼은 Python `repr()` 문자열 → `db.parse_list_field()` 로 파싱.
