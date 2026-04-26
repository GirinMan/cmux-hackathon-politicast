---
name: politikast-hackathon
description: PolitiKAST 12시간 해커톤 오케스트레이션 (validation-first rolling-origin gate). 6명 팀(data/sim/kg/dashboard/paper/policy) TeamCreate, Phase A~D 진행, 시간 체크포인트(14:40/15:25/16:05/16:30/17:00) 평가, 다운스케일 권고를 사용자에게 escalate. 명시적 호출("PolitiKAST 시작/진행", "다음 phase", "체크포인트", "다운스케일", "재실행", "발표 준비") 또는 시간 체크포인트 도달 시에만 트리거. 일반 코딩 질문에는 트리거되지 않음.
---

# politikast-hackathon (Orchestrator) — Validation-First v2

## 변경 이력 (canonical)

- **2026-04-26 14:20 KST 재설계 v2**: zero-shot 5-region prediction phase(P1~P5)을 폐기하고 **validation-first rolling-origin gate**로 전면 교체.
  - canonical handoff: `scratchpad.md` "Main Agent Reference: Validation-First Redesign" + `_workspace/validation/official_poll_validation_targets.md`
  - 폐기 사유: zero-shot prediction이 calibration 없이 진행되면 ground-truth 부재. v1.4 fire (5 region, 1340 personas, T=4) 결과는 model-determinism artifact (Gemini lite 단일 후보 sweep)로 invalidated → `_workspace/snapshots/_archived/v14_run_20260426T050040Z/`로 archive.
  - 새 P0: 공식 등록 사전 여론조사(NESDC `여론조사결과 보기`, 2025-12-03~선거전, 1,487건) 기반 rolling-origin validation gate 통과 시에만 시뮬을 forecast으로 인용.

## 트리거 (보수적, v2도 동일)

- 명시적 슬래시/호출: "PolitiKAST 시작", "다음 phase", "체크포인트", "다운스케일", "재실행", "발표 준비"
- 시계 기반 — 사용자가 시간 진행을 요청할 때 (예: "14:40 됐어 점검해")
- **트리거 안 함**: 코드 한 줄 수정, 단순 파일 읽기, 일반 질문

## Phase 0: 컨텍스트 확인 (호출마다 반드시 첫 단계)

```python
import json, os
from datetime import datetime

now = datetime.now()
deadline = datetime(2026, 4, 26, 17, 0)
remaining_min = (deadline - now).total_seconds() / 60

workspace = "_workspace"
state = {
    "policy": os.path.exists(f"{workspace}/checkpoints/policy.json"),
    "validation_targets": os.path.exists(f"{workspace}/validation/official_poll_validation_targets.md"),
    "raw_poll": os.path.exists(f"{workspace}/db/politikast.duckdb"),
    "archived_v14": os.path.exists(f"{workspace}/snapshots/_archived/v14_run_20260426T050040Z/"),
    "results_index": os.path.exists(f"{workspace}/snapshots/results_index.json"),
}
```

분기:
- `now < 16:30` → 빌드 모드, 현재 phase 판정 후 작업 분배
- `16:30 <= now < 17:00` → freeze 모드, 빌드 동결 + paper 컴파일 + dashboard 안정화
- `now >= 17:00` → 제출 준비 모드 (사용자 직접)

## Phase A (~14:40~15:25) — NESDC fetch + DuckDB 계약 ingest

목표: 5 region subset (서울/광주/대구/부산북갑/대구달서갑) 사전 여론조사 데이터를 NESDC `pollGubuncd=VT026` registry에서 fetch + `raw_poll`/`raw_poll_result`/`poll_consensus_daily` DuckDB 계약 ingest.

작업 분배 (TaskCreate, blockedBy로 의존성):
- **V1 [data]**: NESDC HTML fetch (각 region 3~5 poll, 2026-04 위주). `raw_poll` (poll_id, contest_id, region_id, field_start, field_end, publish_ts, pollster, sample_size, ...) 박제. `_workspace/validation/official_poll_validation_targets.md`의 "Initial Direct Validation Labels" 표를 시드로 사용.
- **V2 [data, blockedBy: V1]**: `raw_poll_result` (poll_id, candidate_id, share, undecided_share) 박제. candidate_id 매핑은 `_workspace/data/scenarios/`의 region별 candidate 정의와 정합.
- **V3 [data, blockedBy: V2]**: `poll_consensus_daily` (contest_id, region_id, as_of_date, candidate_id, p_hat, variance, n_polls, method_version="weighted_v1", source_poll_ids) 박제. as_of_date grid는 5 region별 fieldwork 윈도우.
- **V4 [paper, parallel]**: validation results section (영문/국문) 표 슬롯 + LaTeX 컴파일 검증. Codex 13:59 완료 narrative와 정합.
- **V5 [policy, parallel]**: validation budget 박제 (origin × candidate × poll-day grid). v1.4 incident → v2.0 spec entry. paper Limitations에 NESDC caveat ("registered, not certified") 박제.

**체크포인트 15:25**:
- 점검: V1, V3 완료? (DuckDB raw_poll, raw_poll_result, poll_consensus_daily 모두 row 박제됨)
- 미완 시: V1 fetch range 축소 — 5 region 중 핵심 2개 (seoul, busan_buk_gap)만 박제 → policy 권고 #A1 escalate.
- 완료 시: Phase B 자동 진입.

## Phase B (~15:25~16:05) — sim rolling-origin output + 1 region 검증 fire

목표: sim 결과 JSON에 `official_poll_validation` 필드 (per-as-of-date) 추가 + LLMPool 3-key bug fix (`.env LITELLM_MODEL=gemini/...` 1줄) + 1 region 검증 fire (seoul mayor) → rolling-origin metric 산출.

작업 분배:
- **V6 [sim]**: result JSON 확장 — `official_poll_validation = {target_series, as_of_date, method_version, cutoff_ts, source_poll_ids, metrics{mae, rmse, margin_error, leader_match}, by_candidate}` 박제. `election_env._inject_validation_metrics(poll_consensus_daily)` 함수 추가.
- **V7 [sim, blockedBy: V6]**: LLMPool 3-key bug Fix A 적용 (`.env LITELLM_MODEL=gemini/gemini-3.1-flash-lite-preview` 1줄, 코드 0줄). actual_keys=3 검증.
- **V8 [sim, blockedBy: V7]**: 1 region 검증 fire (seoul mayor, n=200, T=2, dev=Gemini, 캐시 무효화). 결과 JSON에 official_poll_validation 박제 + paper에 forward.
- **V9 [dashboard, parallel]**: Validation Gate 페이지 (#8) 데이터 슬롯 채우기 — `_workspace/snapshots/validation/{backtest_*,rolling_*}.json` 폴링 + threshold 표. 이미 placeholder 박제됨.
- **V10 [paper, parallel]**: 영문/국문 validation results table 행 채움 (V8 결과 도착 시).

**체크포인트 16:05**:
- 점검: V8 결과 박제? metrics.mae 산출됨? (정량 미달이어도 박제 자체가 시연 핵심)
- 미완 → 권고 #B1: seoul fire 다운스케일 (n=100, T=1) 또는 v1.4 baseline + Limitations 박제만.
- 완료 → Phase C 자동 진입.

## Phase C (~16:05~16:30) — paper numerics + dashboard 안정화

목표: V8 결과를 paper validation results에 numerics로 박제 + dashboard Validation Gate 시연 동선 검증 + freeze 직전 안정화.

작업 분배:
- **V11 [paper, blockedBy: V8]**: 영문/국문 numerics 채움 + figure 캡션 갱신 + xelatex 컴파일 검증.
- **V12 [dashboard, blockedBy: V8, V9]**: Validation Gate 페이지에 V8 결과 자동 폴링 + 시연 시뮬레이션 (5 region 카드 + threshold gate criteria 표).
- **V13 [policy, blockedBy: V8]**: validation budget actual usage 박제 + paper에 budget summary 인용.

**체크포인트 16:30 (HARD FREEZE)**:
- 새 기능 금지 broadcast.
- sim/dashboard/paper-writer는 안정화/컴파일/시연 동선 검증만.

## Phase D (16:30~17:00) — Freeze + 컴파일 + 제출 준비

- 영문/국문 paper 최종 xelatex+bibtex 빌드 검증.
- dashboard HTTP 200 검증, 시연 동선 (8 페이지) 시연 시뮬레이션.
- v1.4 archive evidence pointer (paper §Limitations, dashboard provenance) 정합 확인.

## Phase E (17:00 이후) — 제출 준비 모드

사용자 직접:
- 스크린샷 캡처 (대시보드 8 페이지 + Validation Gate)
- 발표 자료 슬라이드
- arXiv 업로드 검토

orchestrator는 idle, 사용자 호출 시만 응답:
- "발표 준비" → paper-writer outline + 30초 elevator pitch (validation-first narrative)
- "스크린샷 가이드" → dashboard-engineer page-by-page 캡처 가이드 (Validation Gate 강조)
- "future work" → V1.4 baseline → V2.0 validation gate → V3.0 election-day forecast 로드맵

## 다운스케일 escalation 절차 (모든 체크포인트 공통)

1. policy-engineer에게 SendMessage("status_check_at_HH:MM_v2")
2. policy-engineer 권고 수신 → 사용자에게 다음 형식으로 보고:
   ```
   [체크포인트 HH:MM]
   ✅ 완료: V<N>...
   ❌ 미완: V<N>...
   📊 메트릭: NESDC fetch 진행 X/5 region, MAE Y, dashboard live Z, freeze 마진 ±N min
   💡 policy 권고 #<N>: <다운스케일 내용>
   ⚠️  영향: <기능 손실 / region 축소 등>

   결정 필요:
   A) 권고 수용
   B) 풀스펙 유지 (시간 부족 위험)
   C) 사용자 지정 옵션
   ```
3. 사용자 결정 → policy-engineer에 broadcast → policy.json 갱신.

## 사용자 후속 작업 키워드 (description에도 포함, 트리거)

"PolitiKAST 시작/진행", "다음 phase", "체크포인트", "다운스케일", "재실행", "발표 준비",
"validation 결과", "policy 갱신", "freeze", "결과 다시", "rolling-origin gate"

## 컨텍스트 확인 후 재진입 (세션 끊김 시)

1. `_workspace/checkpoints/policy.json` mtime → 마지막 갱신 시각.
2. `_workspace/validation/official_poll_validation_targets.md` 존재 → P-A부터 진입.
3. `_workspace/snapshots/results_index.json` 박제 entry 중 `official_poll_validation` 필드 존재 → P-B 결과 박제 검증.
4. `_workspace/snapshots/_archived/v14_run_*` → v1.4 invalidation evidence (paper Limitations only).
5. 사용자에게 "현재 상태: ... 다음 행동: ..." 보고 후 진행 동의.
