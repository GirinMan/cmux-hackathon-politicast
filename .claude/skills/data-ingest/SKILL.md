---
name: data-ingest
description: PolitiKAST 데이터 인프라 빌드 — Nemotron-Personas-Korea parquet을 DuckDB에 인제션, 5 region(서울/광주/대구/의왕/보궐) 페르소나 추출, 후보·여론조사·이벤트 시드 시나리오 큐레이션, GeminiPool LLM 클라이언트 구현, capacity probe 실행. data-engineer 에이전트가 Phase 1에서 호출. 명시적 데이터 작업 요청("데이터 인제션", "duckdb 빌드", "capacity probe", "시나리오 시드") 시에만 트리거.
---

# data-ingest

## 트리거 시점
- orchestrator의 Phase 1 시작 신호
- 사용자의 명시적 호출 ("데이터 빌드", "DB 만들어", "capacity 측정")
- policy-engineer의 region별 sample 갱신 요청

자동 트리거 금지 — 사용자가 Claude/Codex로 직접 코드 작업 중일 때 끼어들지 말 것.

## 작업 순서 (15:00까지 P0, 이후는 P1)

### 1) DuckDB 인제션 (10:30~11:00, 30분)

`/Users/girinman/datasets/Nemotron-Personas-Korea/data/*.parquet` 9개 파일 → `_workspace/db/politikast.duckdb`.

```python
import duckdb
con = duckdb.connect("_workspace/db/politikast.duckdb")
con.execute("""
  CREATE OR REPLACE TABLE persona_raw AS
  SELECT * FROM read_parquet('/Users/girinman/datasets/Nemotron-Personas-Korea/data/*.parquet')
""")
# 분리: persona_core (인덱스 가능 컬럼) + persona_text (텍스트 컬럼)
con.execute("""
  CREATE TABLE persona_core AS
  SELECT uuid, sex, age, marital_status, military_status, family_type,
         housing_type, education_level, bachelors_field, occupation,
         district, province
  FROM persona_raw
""")
con.execute("CREATE INDEX idx_region ON persona_core(province, district)")
con.execute("CREATE INDEX idx_demo ON persona_core(age, sex, occupation)")
con.execute("""
  CREATE TABLE persona_text AS
  SELECT uuid, persona, professional_persona, family_persona,
         travel_persona, culinary_persona, arts_persona, sports_persona,
         cultural_background, skills_and_expertise, hobbies_and_interests,
         career_goals_and_ambitions
  FROM persona_raw
""")
```

### 2) 선거·후보·여론조사 스키마 + 시드 (11:00~12:00, 60분)

```sql
CREATE TABLE election (election_id TEXT PRIMARY KEY, name TEXT, election_date DATE, type TEXT);
CREATE TABLE contest (contest_id TEXT PRIMARY KEY, election_id TEXT, region_id TEXT, position_type TEXT, name TEXT);
CREATE TABLE candidate (candidate_id TEXT PRIMARY KEY, contest_id TEXT, name TEXT, party TEXT, withdrawn BOOLEAN DEFAULT FALSE);
CREATE TABLE raw_poll (poll_id BIGINT PRIMARY KEY, contest_id TEXT, org TEXT, mode TEXT, field_start DATE, field_end DATE, sample_size INT, response_rate REAL, moe REAL, published_at TIMESTAMP);
CREATE TABLE raw_poll_result (poll_id BIGINT, candidate_id TEXT, support REAL);
CREATE TABLE political_event (event_id TEXT PRIMARY KEY, type TEXT, target_candidate_id TEXT, target_party TEXT, region_id TEXT, ts TIMESTAMP, severity REAL, frame TEXT, source_text TEXT);
```

5 region 시드 시나리오를 `_workspace/data/scenarios/{region_id}.json`로 박제. 후보 2~4명 + 1~2개 핵심 이슈/이벤트 + 1~3개 가상 여론조사. **출처 표기 있으면 좋고, 없으면 placeholder + paper-writer에 보강 플래그**.

보궐선거 region 결정: Perplexity로 "2026년 4월 진행 중인 한국 국회의원 보궐선거" 검색 → 1곳 선정 → `data_paths.json`의 `by_election_TBD` 항목 갱신.

### 3) GeminiPool 구현 (12:00~12:30, 30분)

`src/llm/gemini_pool.py` — CAMEL `ChatAgent` factory + 4 키 라운드로빈 + 429 backoff + sqlite cache.

```python
import os, hashlib, json, sqlite3, asyncio, itertools
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import GeminiConfig

class GeminiPool:
    def __init__(self, keys, cache_path="_workspace/db/llm_cache.sqlite"):
        self.keys = itertools.cycle(keys)
        self.cache = sqlite3.connect(cache_path)
        self.cache.execute("CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, v TEXT)")

    def _agent(self, system_prompt: str):
        os.environ["GEMINI_API_KEY"] = next(self.keys)
        model = ModelFactory.create(
            model_platform=ModelPlatformType.GEMINI,
            model_type=ModelType.GEMINI_3_FLASH,
            model_config_dict=GeminiConfig(response_format={"type":"json_object"}, temperature=0.7).as_dict()
        )
        return ChatAgent(system_message=system_prompt, model=model)

    async def complete(self, system_prompt, user_prompt, cache_key):
        h = hashlib.sha256(cache_key.encode()).hexdigest()
        row = self.cache.execute("SELECT v FROM cache WHERE k=?", (h,)).fetchone()
        if row: return json.loads(row[0])
        agent = self._agent(system_prompt)
        # retry with key rotation on 429
        for _ in range(len(list(self.keys)) + 1):
            try:
                resp = await asyncio.to_thread(agent.step, user_prompt)
                txt = resp.msgs[0].content
                parsed = json.loads(txt)
                self.cache.execute("INSERT OR REPLACE INTO cache VALUES (?,?)", (h, txt))
                self.cache.commit()
                return parsed
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower(): continue
                raise
        return {"error": "rate_limit_exhausted"}
```

### 4) Capacity probe (12:00~12:15, 병렬)

```python
# 4 키 각각에 1초당 1회씩 30초간 ping → RPM 합산 측정
# 결과: _workspace/checkpoints/capacity_probe.json
{
  "ts": "2026-04-26T12:00:00",
  "active_keys": 4,
  "per_key_rpm_observed": [12, 11, 12, 11],
  "total_rpm": 46,
  "verdict": "same_project_assumed (~50 RPM)"
}
```

→ policy-engineer에게 SendMessage 즉시.

### 5) Region별 페르소나 추출 (policy-engineer 권고 후)

```python
def sample_personas(region_id: str, n: int) -> list[dict]:
    # province/district 매칭, 1만~5만 한도
    ...
```

## Downscale 트리거
- 12:30 인제션 미완 → policy-engineer 권고 #1 수신, region당 sample을 절반으로
- 시드 큐레이션 시간 부족 → 보궐선거 region을 P1으로 미루고 4 region 우선

## 산출물 체크리스트
- [ ] `_workspace/db/politikast.duckdb` (persona_core, persona_text, election*, candidate, raw_poll*, political_event)
- [ ] `_workspace/data/scenarios/{seoul_mayor,gwangju_mayor,daegu_mayor,uiwang_mayor,by_election_*}.json` (5개)
- [ ] `_workspace/checkpoints/capacity_probe.json`
- [ ] `src/llm/gemini_pool.py`
- [ ] `src/data/queries.py` (`get_personas_for_region`, `get_scenario`)
- [ ] `_workspace/contracts/data_paths.json` 갱신 (status=filled)

## 다른 에이전트와의 인터페이스
- sim-engineer: `from src.llm.gemini_pool import GeminiPool` + `from src.data.queries import get_personas_for_region`
- kg-engineer: `_workspace/data/scenarios/*.json` 읽기
- dashboard-engineer: `from src.data.queries import ...` + DuckDB 직접 조회
- paper-writer: 데이터 통계 (총 페르소나 수, region별 n 등) SendMessage로 전달
