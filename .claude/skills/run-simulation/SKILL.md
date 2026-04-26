---
name: run-simulation
description: PolitiKAST 시뮬레이션 엔진 빌드 — CAMEL ChatAgent 기반 VoterAgent, ElectionEnv timestep loop, Poll Consensus 가중평균, bandwagon/underdog/second-order 효과, 비밀투표 JSON 프롬프트, 5 region asyncio 병렬 실행, 결과 JSON 직렬화. sim-engineer가 Phase 2~3에서 호출. 명시적 시뮬레이션 작업 요청("시뮬 빌드", "voter agent", "시나리오 실행", "결과 생성") 시에만 트리거.
---

# run-simulation

## 트리거 시점
- orchestrator의 Phase 2 시작 신호 (data-engineer로부터 GeminiPool/DuckDB 준비 완료 수신 후)
- 명시적 호출 ("시뮬 돌려", "scenario run", "결과 생성")
- policy-engineer의 timestep/feature flag 갱신 요청

## 모델 수식 ↔ 코드 대응
$U_{i,b,k}(t) = U^{base}_{i,b,k} + \Delta U^{media}_{i,b,k}(t) + \Delta U^{poll}_{i,b,k}(t) + \Delta U^{gov}_{i,b,k}(t) + \varepsilon$

| 항 | 코드 위치 |
|----|----------|
| $U^{base}$ | `src/sim/utility.py::baseline_utility(persona, candidate)` |
| $\Delta U^{media}$ | `src/sim/utility.py::media_shock(events_subgraph, candidate, t)` (kg-engineer retriever 사용) |
| $\Delta U^{poll}$ | `src/sim/poll_consensus.py::bandwagon_underdog(p_hat, candidate, ranking)` |
| $\Delta U^{gov}$ | `src/sim/utility.py::second_order(gov_approval, candidate.party, position_type)` |
| $\varepsilon$ | LLM 응답에 내재 (logit noise) |

## 작업 순서

### 1) VoterAgent (12:30~13:30, 60분)

`src/sim/voter_agent.py` — `GeminiPool`을 사용해 페르소나 + 컨텍스트 → 투표 의사결정 JSON.

```python
class VoterAgent:
    def __init__(self, pool, persona_row, persona_text):
        self.pool = pool
        self.persona = persona_row  # core dict
        self.text = persona_text     # narrative
        self.system_prompt = self._build_system()

    def _build_system(self):
        return f"""당신은 한국 유권자입니다.
- 거주: {self.persona['province']} {self.persona['district']}
- 연령: {self.persona['age']}, 성별: {self.persona['sex']}
- 직업: {self.persona['occupation']}, 학력: {self.persona['education_level']}
- 가족: {self.persona['family_type']}, 주거: {self.persona['housing_type']}

서사: {self.text['persona']}
직업 배경: {self.text['professional_persona']}
가족 맥락: {self.text['family_persona']}
문화 배경: {self.text['cultural_background']}

규칙: 제공된 컨텍스트(이슈·여론조사·이벤트) 외 정보를 사용하지 마세요.
반드시 JSON으로만 응답하세요: {{"vote": "...", "turnout": true|false, "confidence": 0.0~1.0, "reason": "...", "key_factors": ["..."]}}
출마 포기한 후보는 선택할 수 없습니다.
"""

    async def vote(self, candidates, context_block, timestep, mode="secret_ballot"):
        cache_key = f"{self.persona['uuid']}|{hash(context_block)}|{timestep}"
        user = self._build_user(candidates, context_block, timestep, mode)
        return await self.pool.complete(self.system_prompt, user, cache_key)
```

### 2) ElectionEnv + Poll Consensus (13:30~14:30, 60분)

```python
# src/sim/poll_consensus.py
def consensus(raw_polls: list[dict], house_effect: dict, mode_effect: dict):
    """
    p_tilde = y - delta_house - delta_mode
    p_hat = sum(w_j * p_tilde_j) / sum(w_j)
    w_j = n_j^alpha * exp(-lambda * delta_t) * quality_score
    """
    ...

# src/sim/election_env.py
class ElectionEnv:
    def __init__(self, region_id, candidates, timesteps, kg_retriever):
        ...
    async def run(self, voters: list[VoterAgent]):
        results = {"poll_trajectory": [], "final_outcome": None, "virtual_interviews": []}
        for t in range(self.timesteps):
            context_blocks = {v.persona['uuid']: self.kg.subgraph_at(v.persona['uuid'], t, region_id=self.region_id) for v in voters}
            tasks = [v.vote(self.candidates, context_blocks[v.persona['uuid']], t, mode="poll_response") for v in voters]
            responses = await asyncio.gather(*tasks)
            poll = self._aggregate(responses)
            results["poll_trajectory"].append({"timestep": t, **poll})
        # final timestep — secret_ballot
        final_tasks = [v.vote(self.candidates, context_blocks[v.persona['uuid']], self.timesteps, mode="secret_ballot") for v in voters]
        final_responses = await asyncio.gather(*final_tasks)
        results["final_outcome"] = self._tally(final_responses)
        # 5~50 페르소나에 대해 virtual_interview 추가 호출
        ...
        return results
```

### 3) 5 region 실행 + 결과 직렬화 (14:30~15:30, 60분)

```python
# src/sim/run_scenario.py
async def main():
    pool = GeminiPool(os.environ["GEMINI_API_KEYS"].split(","))
    policy = json.load(open("_workspace/checkpoints/policy.json"))
    regions = policy["p0_regions"]
    for region_id in regions:
        scenario = json.load(open(f"_workspace/data/scenarios/{region_id}.json"))
        personas = get_personas_for_region(region_id, n=policy["per_region_persona_n"])
        kg = build_kg_for_scenario(scenario)
        retriever = KGRetriever(kg)
        env = ElectionEnv(region_id, scenario["candidates"], policy["timesteps"], retriever)
        voters = [VoterAgent(pool, p, p_text) for p, p_text in personas]
        result = await env.run(voters)
        json.dump(result, open(f"_workspace/snapshots/results/{region_id}__{scenario_id}.json","w"), ensure_ascii=False, indent=2)
        # results_index.json에 append
    ...
```

### 4) Feature flag 토글 (14:30 이후 P1)

환경변수로:
- `POLITIKAST_TIMESTEPS=4`
- `POLITIKAST_FEATURES=bandwagon,underdog,second_order,kg_retrieval` (comma-separated, off하려면 빼기)
- `POLITIKAST_SPLIT_TICKET=1` (광역+기초 동시)

policy-engineer가 `policy.json`에 박제하면 sim-engineer가 읽음.

## Downscale 트리거
- 13:30 voter agent 미동작 → CAMEL fallback chain (Plan B → Plan C: google-genai 직접) — `llm_strategy.json` 갱신 후 paper-writer 알림
- 14:30 KG retriever 미준비 → 빈 컨텍스트로 baseline 시뮬, degraded mode 명시
- 15:00 5 region 미완 → policy 권고에 따라 region 줄이거나 timestep 1로
- 16:00 결과 미완 → 부분 결과 + dummy 채움 (paper-writer가 정직하게 표시)

## 산출물 체크리스트
- [ ] `src/sim/voter_agent.py`
- [ ] `src/sim/election_env.py`
- [ ] `src/sim/poll_consensus.py`
- [ ] `src/sim/utility.py` (ΔU 계산)
- [ ] `src/sim/run_scenario.py` (CLI: `python -m src.sim.run_scenario --region all`)
- [ ] `_workspace/snapshots/results/*.json` (region별)
- [ ] `_workspace/snapshots/results_index.json`
- [ ] dashboard-engineer에 SendMessage("first result ready: seoul_mayor")

## 결과 메타 보고 (paper-writer/policy-engineer로)
- 캐시 히트율, 실제 RPM 소비, 평균 응답 시간, JSON 파싱 실패율
- 가능하면 region별 calibration metric (predicted vs latest poll consensus)
