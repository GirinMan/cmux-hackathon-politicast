# PolitiKAST — 셀프호스팅 가이드

> 본인의 노트북·서버에 PolitiKAST 를 직접 띄우고 싶으실 때 한 페이지로
> 끝내는 안내서입니다. 학술적 디테일은 [research-summary.md](research-summary.md) 를,
> 시스템 구조는 [architecture.md](architecture.md) 를 참고하세요.

## 1. 사전 준비

### 1.1 시스템 요구사항

| 항목 | 권장 사양 | 비고 |
|---|---|---|
| OS | macOS 14+ / Ubuntu 22.04+ | Windows 는 WSL2 필요 |
| Python | 3.12+ | `.venv` 사용 권장 |
| Docker | Docker Desktop 또는 Engine 20.10+ | `docker compose v2` |
| 디스크 | 5 GB | Postgres + Neo4j 볼륨 + 페르소나 캐시 |
| 메모리 | 8 GB+ | 5 region 동시 시뮬레이션 시 추천 16 GB |

### 1.2 LLM API 키 준비

PolitiKAST 는 **dev** (Gemini 무료 티어) / **prod** (OpenAI + Anthropic) 두
모드를 지원합니다.

- **무료로 살펴보기만** — Gemini 키 1개 (`gemini-3.1-flash-lite-preview` 무료 티어).
- **풀 시뮬레이션** — OpenAI + Anthropic 키. 비용 가드는
  `LLM_COST_THRESHOLD_*` 환경 변수에서 조정 가능.

### 1.3 데이터셋 (선택)

기본 시나리오 5종은 저장소에 포함되어 있습니다. **합성 페르소나 풀**
(NVIDIA Nemotron-Personas-Korea, ~5 GB) 은 별도로 받아 두시는 게 좋습니다.

```bash
# Hugging Face 에서 다운로드 (CC BY 4.0)
git clone https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea \
  ~/datasets/Nemotron-Personas-Korea

# .env 의 NEMOTRON_PARQUET_DIR 가 위 경로를 가리키는지 확인
```

데이터셋 없이도 backend / frontend 는 정상 동작하며, 시뮬레이션은 비어 있는
페르소나 풀로 fallback (인구 패널이 비게 됩니다).

## 2. 5분 셋업 (Docker Compose, 권장)

```bash
git clone https://github.com/<your-fork>/politikast
cd politikast

cp .env.example .env
# 에디터로 .env 열고 최소한 다음 항목 채우세요:
#   GEMINI_API_KEYS=AIzaSy...                 (또는 OPENAI/ANTHROPIC 키)
#   POSTGRES_PASSWORD=politikast              (변경 권장)
#   NEO4J_AUTH=neo4j/<your-strong-password>
#   POLITIKAST_API_INTERNAL_SERVICE_TOKEN=<random-32-chars>

make dev
```

`make dev` 가 자동으로 처리하는 일:

1. `postgres` + `neo4j` 컨테이너 기동 (`db-up`).
2. Alembic `upgrade head` (`make migrate-db`).
3. `backend` 컨테이너 (`uvicorn` reload 모드).
4. `frontend` 컨테이너 (`vite dev`, HMR).

기다리신 후 다음 URL 들이 응답하면 정상입니다:

- 프론트: <http://localhost:5173>
- 백엔드 Swagger: <http://localhost:8080/docs>
- Neo4j 브라우저: <http://localhost:7474> (계정은 `.env` 의 `NEO4J_AUTH`)
- Postgres: `localhost:5433` (psql 로 접근)

## 3. 로컬 dev (Docker 없이)

Python 만으로 백엔드를 띄우고, 프론트는 별도 터미널에서 vite dev:

```bash
# 1) Python 의존성 (uv 사용 — `.venv/`를 자동 생성)
uv sync

# 2) Postgres + Neo4j 만 컨테이너로
make db-up
make migrate-db

# 3) 백엔드
make api-dev          # uvicorn backend.app.main:app --reload :8080

# 4) 프론트 (다른 터미널)
cd frontend
npm install
npm run dev           # :5173
```

## 4. 데이터 인입 (선택)

기본 시나리오만으로도 SPA 가 동작합니다. 실제 NESDC 폴 / NEC 후보 등록 /
뉴스 / Perplexity 사실을 인입하려면:

```bash
# 전부 dry-run (스테이징까지만, 타깃 MERGE 없음)
make ingest-dryrun

# 운영 인입 (실제 MERGE)
make ingest

# 특정 어댑터만
make ingest ARGS="--source nesdc_poll"

# 인입 상태 확인
make ingest-status
```

세부 어댑터 동작은 [adapters.md](adapters.md) 참조.

## 5. 운영 점검 명령

| 명령 | 의미 |
|---|---|
| `make help` | 전체 타깃 목록 |
| `make test` | 전체 pytest (LLM 호출 없음, 약 1~2초) |
| `make test-fast` | data + sim + eval + kg 빠른 부분 |
| `make schema-export` | Pydantic → JSON Schema export |
| `make validate-scenarios` | 5 region 시나리오 시드 strict 검증 |
| `make openapi-export` | OpenAPI 3.x JSON export (frontend codegen 입력) |
| `make migrate-db` | Alembic upgrade head |
| `make migrate-duckdb-to-pg` | 기존 DuckDB → Postgres 멱등 이전 |
| `make db-up` / `make db-down` | Postgres + Neo4j 컨테이너 제어 |
| `make db-reset` | **DESTRUCTIVE** — DB 볼륨 삭제 후 재생성 |
| `make llm-determinism` | LLM 캐시 hit ≥ 0.9 + sha256 결정성 게이트 |

## 6. KG (Neo4j) 미러링

기본은 `networkx` 인-프로세스 그래프이며, Neo4j 컨테이너가 떠 있으면 명시적
미러 명령으로 이전합니다:

```bash
# scenario-only 미러
PYTHONPATH=. .venv/bin/python -m tools.migrate_networkx_to_neo4j --dry-run
PYTHONPATH=. .venv/bin/python -m tools.migrate_networkx_to_neo4j

# staging 합성 후 미러
POLITIKAST_KG_USE_STAGING=1 \
  .venv/bin/python -m tools.migrate_networkx_to_neo4j
```

종료 코드:

| Code | 의미 |
|---|---|
| 0 | 성공 |
| 1 | 드라이버 미설치 / `NEO4J_URI` 미설정 |
| 2 | Firewall 위반 (미래 사건 미러 시도) |
| 3 | 런타임 오류 |

## 7. 백업 / 복구

```bash
# Postgres dump
docker compose exec postgres \
  pg_dump -U politikast -d politikast --format=custom \
  > backups/pg-$(date +%F).dump

# Neo4j dump (컨테이너 정지 후)
docker compose stop neo4j
docker run --rm -v politikast-neo4j-data:/data -v $(pwd)/backups:/backups \
  neo4j:5 neo4j-admin database dump neo4j --to-path=/backups
docker compose start neo4j
```

## 8. 자주 만나는 이슈

| 증상 | 원인 / 해결 |
|---|---|
| `make dev` 가 backend 에서 502 | `make migrate-db` 가 끝나기 전에 backend 가 떴습니다 — `docker compose logs backend` 확인 후 재기동. |
| `pytest` 가 `ModuleNotFoundError: sqlalchemy` | `uv sync` 재실행. Docker 모드에서는 발생하지 않습니다. |
| Frontend 에서 401 | `.env` 의 `POLITIKAST_API_INTERNAL_SERVICE_TOKEN` 이 비어 있거나 backend 와 다릅니다. |
| Neo4j 미러 후 firewall LEAK 경고 | KG 시나리오 시드 또는 staging triple 에 미래 ts 가 들어왔습니다 — `_workspace/snapshots/...` 의 audit 결과 확인. |
| LLM 호출 비용 폭주 | `LLM_COST_THRESHOLD_*` 환경 변수 + `POLITIKAST_LLM_CACHE=1` 로 캐시 사용. 검증 게이트 실행은 반드시 `=0` 으로. |

## 9. 본격 운영 시 권장사항

- TLS 종단: nginx 또는 caddy 로 프론트 / 백엔드 reverse proxy.
- 인증 secret 회전: `POLITIKAST_API_ADMIN_JWT_SECRET`,
  `POLITIKAST_API_INTERNAL_SERVICE_TOKEN` 정기 변경.
- Postgres / Neo4j 볼륨 외부 마운트 + 정기 백업.
- 블랙아웃 기간(공직선거법 §108) — `BlackoutBanner` 활성화 + 정치 발언 일시
  제한 정책을 운영 측에서 검토.
- Validation Gate 가 통과되지 않은 결과는 화면에 `prediction-only` 라벨이
  자동으로 붙습니다 — 라벨을 수동으로 떼지 말아 주세요.

## 10. 도움 요청

- GitHub Issues / Discussions
- 메일: `sjlee@bhsn.ai`
- 보안 취약점 보고: 동일 메일로 비공개 메시지 부탁드립니다.
