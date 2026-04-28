# PolitiKAST Ingest Adapters — 패턴 노트

## 개요

`src/ingest/` 는 모든 외부 데이터 흐름을 단일 인터페이스(`SourceAdapter`)
로 정규화한다. 어댑터는 **fetch (외부 → raw payload)** 와 **parse (raw →
staging row)** 두 단계만 책임지고, MERGE / staging insert / 결과 로깅은
`PipelineRunner` 가 처리한다.

```
외부 시스템                src/ingest/                 DuckDB
(NESDC, NEC, 뉴스 …) ──▶  Adapter.fetch()       FetchPayload(items=[…])
                          Adapter.parse()  ──▶ ParseResult(table="stg_*", rows=[…])
                          PipelineRunner   ──▶ MERGE → 본 테이블
```

## SourceAdapter Protocol

`src/ingest/base.py` 에 정의됨.

```python
class SourceAdapter(Protocol):
    source_id: str        # registry 의 unique id
    kind: SourceKind      # "structured" | "llm"
    target_kind: TargetKind  # "raw_poll" | "candidate" | "kg_triple" | "issue" | "person"

    def fetch(self, ctx: IngestRunContext) -> FetchPayload: ...
    def parse(self, payload: FetchPayload, ctx: IngestRunContext) -> ParseResult: ...
```

각 어댑터 모듈은 `get_adapter() -> SourceAdapter` factory 를 반드시
export 한다 (`importlib` 동적 로드용).

## 정형 어댑터 (structured)

### NESDC 여론조사 — `src/ingest/adapters/nesdc_poll.py`

- 입력: NESDC 등록부 리스트 페이지 (VT026 + VT039) 또는 캐시된
  `_workspace/snapshots/validation/nesdc_list_raw.json`.
- 출력: `stg_raw_poll` row (legacy `raw_poll` 컬럼과 동일 shape).
- per-region cap: default 25, `ctx.config["per_region_cap"]` 로 override.
- CI/회귀 모드: `fetch_details=False` (default) — 외부 HTTP 없이 list snapshot
  만으로 결정적 결과 재현.
- 회귀 baseline: 5 region cap=25 적용 시 정확히 77 row (Seoul 25 / Gwangju
  25 / Daegu 25 / Busan-buk-gap 2 / Daegu-dalseo-gap 0).

**검증 게이트**: `tests/ingest/test_adapter_nesdc.py` — row count, region 분포,
PK 유일성, 멱등성 (동일 입력 → 동일 row 시퀀스) 모두 핀.

### NEC 후보 등록부 — `src/ingest/adapters/nec_candidate.py`

- 입력: `_workspace/data/registries/candidates.json` (default `mode="registry"`)
  또는 `_workspace/data/scenarios/*.json` (`mode="scenarios"` fallback).
- 출력: `stg_kg_triple` row. predicate ∈ {`hasName`, `memberOfParty`,
  `runsInContest`, `hasAlias`}.
- ts: `ctx.config["registered_at"]` 또는 default `2026-01-01T00:00:00+09:00`
  (election cycle 시작) — KG firewall 통과 위해 모든 row 가 ts 박힘.

## 어댑터 추가 패턴

새 정형 소스를 붙일 때:

1. **registry 등록** — `_workspace/data/registries/data_sources.json`
   에 `id`, `kind`, `target_kind`, `fetcher_module` 추가.
2. **모듈 작성** — `src/ingest/adapters/<source>.py` 에 dataclass 어댑터
   + `get_adapter()` factory. 외부 의존성은 lazy import (테스트 시 mock 가능).
3. **테스트** — `tests/ingest/test_adapter_<source>.py` 에 fetch/parse
   결정성, row shape, idempotency 핀.
4. **회귀 baseline** — 캐시 가능한 raw fixture 를 `_workspace/snapshots/`
   에 저장하고 `ctx.config["...path"]` 로 lookup.
5. **deprecation** — 기존 `scripts/data/*.py` 가 같은 일을 하던 경우
   docstring 첫 줄에 `[DEPRECATED ... — Phase 3 ...]` 헤더 추가.

## ParseResult.table 명명 규칙

- `stg_raw_poll`            — NESDC 여론조사
- `stg_raw_poll_result`     — share 결과 (별도 어댑터 또는 LLM 추출)
- `stg_kg_triple`           — KG 트리플 (구조화/LLM 공통)
- `stg_issue` / `stg_person`— 이슈/인물 enrichment

표 컬럼 사양은 `src/ingest/staging.py` (eval-extender 가 박제) 의 DDL 과
일치해야 한다. 어댑터가 누락 컬럼을 보내면 staging insert 가 NULL 로 채우거나
명시적 reject 한다 (resolver 단계 이전).

## 회귀 게이트 — make ingest 흐름

```
make ingest SOURCE=nesdc_poll       # 첫 실행: n_loaded > 0
make ingest SOURCE=nesdc_poll       # 두 번째: n_loaded == 0 (멱등)
```

`PipelineRunner` 가 `IngestRun` row 를 박제하고 어댑터의 결정적 row 출력 +
staging MERGE 의 PK 충돌 fence 로 멱등성을 보장한다.
