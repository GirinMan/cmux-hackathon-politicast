---
name: manage-policy
description: PolitiKAST capacity 정책 결정 — Gemini API capacity probe 결과 해석, region별 페르소나 sample / timestep / feature flag 분배, downscale ladder 자동 추천(사용자 결정 필요), 시간 체크포인트마다 정책 갱신. policy-engineer 에이전트가 호출. 명시적 정책 작업 요청("capacity 측정 결과 해석", "policy 갱신", "downscale 권고", "리소스 분배") 또는 시간 체크포인트(12:30/13:30/14:30/15:00/16:00) 트리거 시.
---

# manage-policy

## 트리거 시점
- data-engineer의 `_workspace/checkpoints/capacity_probe.json` 박제 직후 (Phase 1 후반)
- orchestrator의 시간 체크포인트 (매 30~60분)
- sim-engineer의 RPM/캐시 통계 박제 시
- 명시적 사용자 호출 ("policy 갱신해", "downscale 권고")

자동 트리거 금지 — 빌드 작업자(Claude/Codex)와 부딪히지 않도록 체크포인트 시점만.

## 작업 순서

### 1) Capacity probe 해석 (Phase 1 후반)
```python
probe = json.load(open("_workspace/checkpoints/capacity_probe.json"))
total_rpm = probe["total_rpm"]
active_keys = probe["active_keys"]
verdict = "separate_project" if total_rpm > 100 else "same_project"
```

판정 → 예산 계산:
```python
remaining_minutes = max(0, (datetime(2026,4,26,17,0) - datetime.now()).total_seconds() / 60)
capacity_60pct = total_rpm * remaining_minutes * 0.6  # 60% 효율 가정
safety_margin = capacity_60pct * 0.20
budget = capacity_60pct - safety_margin
```

### 2) Region별 분배 (Capacity-first)

```python
# 모든 region에 균등 baseline (40%) + 가중치 분배 (60%)
per_region_base = budget * 0.4 / 5
remainder = budget - per_region_base * 5
weights = {
    "seoul_mayor":     0.30,  # 메인 baseline, 큰 sample
    "by_election_TBD": 0.25,  # 4 timestep 우선 (이슈 효과)
    "gwangju_mayor":   0.15,  # 진보 비교
    "daegu_mayor":     0.15,  # 보수 비교
    "uiwang_mayor":    0.15,  # 접전, 작은 모집단
}
budget_per_region = {r: per_region_base + remainder * w for r, w in weights.items()}
# timestep 결정: 호출 수 = persona_n * timesteps
# default timesteps: probe verdict에 따라 4 (separate) or 2 (same)
```

### 3) policy.json 박제

```json
{
  "ts": "2026-04-26T12:15:00",
  "capacity_probe_verdict": "separate_project | same_project",
  "total_rpm": 200,
  "budget_remaining": 43200,
  "regions": {
    "seoul_mayor":     {"persona_n": 5000, "timesteps": 4, "interview_n": 30},
    "by_election_TBD": {"persona_n": 3000, "timesteps": 4, "interview_n": 20},
    "gwangju_mayor":   {"persona_n": 2000, "timesteps": 2, "interview_n": 10},
    "daegu_mayor":     {"persona_n": 2000, "timesteps": 2, "interview_n": 10},
    "uiwang_mayor":    {"persona_n": 1500, "timesteps": 2, "interview_n": 10}
  },
  "feature_flags": {
    "bandwagon": true, "underdog": true, "second_order": true,
    "split_ticket": false, "kg_retrieval": true
  },
  "downscale_level": 0,
  "rationale": "..."
}
```

→ data-engineer, sim-engineer, kg-engineer, dashboard-engineer에 SendMessage broadcast.

### 4) 체크포인트별 downscale 권고

| 시각 | 점검 항목 | 미완 시 권고 |
|------|----------|-------------|
| 12:30 | DuckDB 인제션 + capacity probe | sample 50% 컷, 보궐선거 region 제외 |
| 13:30 | voter agent 동작 | timestep 4→2, JSON parsing fallback 강화 |
| 14:30 | KG retriever | KG retrieval 컷, baseline 시뮬만 |
| 15:00 | 5 region end-to-end | 단일 timestep 강제, virtual_interview 컷 |
| 16:00 | 결과 + 대시보드 | freeze 모드 진입, dummy 결과 채움 |
| 16:30 | 빌드 동결 | 새 기능 금지, 안정화만 |

각 권고는 **사용자에게 보고 후 결정 받음**. 자동 적용 금지.

### 5) policy_log.md (시간 기록)

```markdown
## 12:30 체크포인트
- 인제션: ✅ (1M rows in 47s)
- Capacity probe: ✅ (total 184 RPM, separate_project)
- 시드 시나리오: 4/5 region 완료, 보궐선거 진행 중
- 권고: 풀스펙 유지
- 사용자 결정: 풀스펙 유지

## 13:30 체크포인트
- VoterAgent: ✅ (서울 5,000 페르소나 1 timestep 완료, 평균 RT 1.2s)
- 캐시 히트율: 0% (첫 실행)
- 권고: 풀스펙 유지, 캐시 효과 다음 체크에 반영
...
```

## 모니터링 지표
- 시간당 캐시 히트율
- region별 완료 timestep 수
- RPM 실제 소비 (예산 대비 %)
- JSON 파싱 실패율
- 평균 LLM 응답 시간

## Downscale 인지
- 본인이 downscale 결정자이므로 스스로 컷 안 함
- 단, 본인 결정이 너무 자주 갱신되면 다른 에이전트 흔들림 → 30분 단위 리듬

## 산출물 체크리스트
- [ ] `_workspace/checkpoints/policy.json` (갱신 history)
- [ ] `_workspace/checkpoints/policy_log.md` (시간 기록, append)
- [ ] orchestrator에 권고 SendMessage (체크포인트마다)

## 다른 에이전트와의 인터페이스
- 입력: data-engineer(capacity probe), sim-engineer(RPM/캐시), 시계
- 출력: data/sim/kg/dashboard/paper에게 정책 broadcast, orchestrator에 escalation 요청

## 초기 default (capacity probe 도착 전)
보수적 — `_workspace/checkpoints/policy.json`을 다음으로 박제:
```json
{
  "regions": {
    "seoul_mayor": {"persona_n": 1000, "timesteps": 1},
    "gwangju_mayor": {"persona_n": 500, "timesteps": 1},
    "daegu_mayor": {"persona_n": 500, "timesteps": 1},
    "uiwang_mayor": {"persona_n": 500, "timesteps": 1},
    "by_election_TBD": {"persona_n": 500, "timesteps": 1}
  },
  "feature_flags": {"bandwagon": false, "underdog": false, "second_order": false, "kg_retrieval": false},
  "rationale": "capacity_probe_pending — minimum baseline guard"
}
```
이 default가 있어야 sim-engineer가 capacity probe를 기다리지 않고 dry-run 가능.
