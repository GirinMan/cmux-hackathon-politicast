# PolitiKAST 해커톤 (12시간, 2026-04-26)

**프로젝트:** PolitiKAST — Political Knowledge-Augmented Multi-Agent Simulation of Voter Trajectories for Korean Local Elections
**저자:** Seongjin Lee (BHSN)
**산출물:** arXiv 논문(`paper/elex-kg-final.tex`) + 동작 엔진(CAMEL+Gemini+DuckDB) + Streamlit 대시보드
**제출 데드라인:** 17:00 KST 빌드 동결, 이후 제출 준비

**Jira:** 현재 프로젝트는 해커톤 로컬 프로젝트이므로 Jira 티켓을 고려하지 않는다.

## 하네스: PolitiKAST

**목표:** 6명 에이전트 팀으로 5 region(서울/광주/대구/의왕/보궐) 시뮬레이션 풀스펙을 17:00까지 완성. capacity probe 결과에 따라 동적 다운스케일.

**트리거:** PolitiKAST 관련 작업 요청 시 `politikast-hackathon` 스킬을 사용한다. 단순 코드 질문/한 줄 수정은 직접 응답. 다음 표현이면 트리거:
- "PolitiKAST 시작 / 진행 / 다음 phase / 체크포인트 / 다운스케일 / 재실행 / 발표 준비"
- "capacity 측정 결과 해석 / policy 갱신 / freeze 모드"
- 시간 체크포인트 도달 알림 (사용자가 "12:30 됐어" 등으로 알림 시)

**런타임 LLM:** Gemini API (`gemini-3-flash-preview`), 4 키 풀.
- 환경변수: `GEMINI_API_KEYS=key1,key2,key3,key4` (comma-separated, before 빌드 시작)
- CAMEL 0.2.90+ native 지원 (`ModelType.GEMINI_3_FLASH`) — 우회 불필요
- 진짜 병목: rate limit (preview tier RPM). `data-engineer`의 capacity probe로 측정.

**데이터셋:** `/Users/girinman/datasets/Nemotron-Personas-Korea/data/*.parquet` (9 files, 1M records, 7M personas, CC BY 4.0). 인용 의무 — `update-paper` 스킬 참조.

**개발 도구:** Claude Code + Codex (사용자 본인이 직접 코딩). 에이전트 팀은 빌드 분담·정책 결정·시간 관리 담당. 사용자 코딩 흐름을 끊지 않도록 자동 트리거 보수적.

## 공용 Scratchpad 프로토콜

모든 Claude/Codex 세션과 에이전트 팀은 루트 `scratchpad.md`를 단일 공유 상태판으로 사용한다.

**필수 규칙:**
- 작업 시작 전: 반드시 `scratchpad.md`의 `1. Main Project Purpose`, `2. Status per Agent/Team`, `3. Arguments`를 읽고 중복 작업이나 충돌 가능성을 확인한다.
- 작업 시작 시: `2. Status per Agent/Team`에 본인/팀 이름, 담당 범위, 시작 시각, 현재 상태, 건드릴 파일/디렉토리를 기록한다.
- 작업 중: 범위 변경, blocker, 다른 팀과 겹치는 파일, 결정 대기 사항이 생기면 즉시 `scratchpad.md`를 갱신한다.
- 작업 후: 완료/중단 여부, 변경 파일, 검증 결과, 남은 TODO를 기록하고 상태를 `done`, `blocked`, `handoff` 중 하나로 바꾼다.
- 논쟁/의사결정: 설계 이견, 우선순위 충돌, 다운스케일 판단, 미확정 가정은 `3. Arguments`에 근거와 함께 남긴다.
- `scratchpad.md`를 최신으로 유지하지 않은 상태에서 새 작업을 시작하지 않는다.

**충돌 방지 원칙:**
- 다른 에이전트가 같은 파일을 `in-progress`로 표시한 경우, 먼저 `scratchpad.md`에 handoff 요청을 남기고 해당 범위 편집을 피한다.
- 긴급 수정이 필요해 겹치는 파일을 수정해야 하면 `Arguments`에 사유와 예상 영향 범위를 먼저 기록한다.
- 사용자 지시가 기존 scratchpad 상태와 충돌하면 사용자 지시를 우선하되, 충돌 내용을 `Arguments`에 남긴다.

## 핵심 디렉토리

```
.claude/agents/      # 6명 + orchestrator 정의
.claude/skills/      # 6 빌드 스킬 + politikast-hackathon 오케스트레이터
_workspace/
  contracts/         # 4개 JSON 박제 (data_paths, api_contract, result_schema, llm_strategy)
  data/scenarios/    # 5 region 시드 (data-engineer가 채움)
  db/                # politikast.duckdb, llm_cache.sqlite
  checkpoints/       # capacity_probe.json, policy.json, policy_log.md
  research/          # camel_gemini_compat.md (백그라운드 조사 결과)
  snapshots/         # 결과 JSON, KG export, figures
src/                 # 빌드 산출물 (data/llm/sim/kg)
ui/dashboard/        # Streamlit
paper/               # elex-kg-final.tex / .pdf (paper-writer가 갱신)
docs/references/     # hackathon_guide.md, perplexity 대화록 등 참고자료
docker/              # Dockerfile, requirements.txt
docker-compose.yml   # 런타임 환경 (app + dashboard 서비스)
.env                 # GEMINI_API_KEYS 등 (gitignored, .env.example 참조)
```

## 시간 체크포인트

| 시각 | Phase | 점검 항목 |
|------|-------|----------|
| 12:30 | Phase 1 종료 | DuckDB 인제션 + capacity probe + policy 박제 |
| 13:30 | Phase 2 중간 | VoterAgent 동작 확인 |
| 14:30 | Phase 2 후반 | KG retrieval + 단일 region 통합 |
| 15:00 | Phase 3 시작 | P0 5 region 통합 |
| 16:00 | Phase 3 종료 | 발표 준비 가능 상태 |
| **16:30** | Phase 4 | **HARD FREEZE — 새 기능 금지** |
| 17:00 | Phase 5 | **제출 준비 모드 진입 (사용자 직접)** |

각 체크포인트에서 미완 시 `policy-engineer`가 다운스케일 권고 → 사용자 결정 → broadcast.

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-04-26 | 초기 구성 (v4) | 6명 팀 + 7 스킬 + contracts | 12h 해커톤, 5 region 풀스펙 + 동적 다운스케일 |
| 2026-04-26 | CAMEL/Gemini 호환성 백그라운드 조사 결과 반영 | `llm_strategy.json` | Plan A (CAMEL native) 확정 |
| 2026-04-26 | 공용 `scratchpad.md` 협업 프로토콜 추가 | `CLAUDE.md`, `AGENTS.md`, `scratchpad.md` | 다중 Claude/Codex 세션 간 상태 공유 및 중복 작업 방지 |
