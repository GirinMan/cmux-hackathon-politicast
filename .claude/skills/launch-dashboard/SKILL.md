---
name: launch-dashboard
description: PolitiKAST Streamlit 대시보드 빌드 — 6페이지(Scenario / Poll trajectory / Final Outcome / Demographics / Virtual Interviews / KG Viewer), 5 region 비교 뷰, 결과 JSON 자동 폴링, placeholder mode(빌드 깨져도 화면 살아있음). dashboard-engineer가 Phase 2~3에서 호출. 명시적 대시보드 작업 요청("대시보드", "Streamlit", "UI", "시연 화면") 시에만 트리거.
---

# launch-dashboard

## 트리거 시점
- orchestrator의 Phase 2 시작 신호 (data-engineer DuckDB 준비 후)
- 명시적 호출 ("대시보드 만들어", "Streamlit run", "시연 페이지")
- sim-engineer의 첫 결과 박제 시그널 (이미 골격 떠있으면 자동 갱신)

## 페이지 구조

### app.py (entry, multi-page)
```python
import streamlit as st
st.set_page_config(page_title="PolitiKAST", layout="wide", initial_sidebar_state="expanded")
# 사이드바: region 토글(all/seoul/gwangju/daegu/uiwang/by_election), timestep slider
# 본문은 pages/ 자동 라우팅
```

### Page 1 — Scenario Designer (`pages/1_scenario.py`)
- region 선택, 후보 목록 표시 (data_paths.json + scenarios/*.json)
- timestep, feature flags 토글 → policy.json 갱신 (정책 권한 있을 때만, policy-engineer 동의 필요)
- "Run scenario" 버튼 → `subprocess.Popen([sys.executable, "-m", "src.sim.run_scenario", "--region", region])`
- 진행 로그 tail (`_workspace/checkpoints/policy_log.md` 마지막 50줄)

### Page 2 — Poll Trajectory (`pages/2_poll.py`)
- region별 timestep × 후보 지지율 라인 차트 (plotly)
- consensus 신뢰구간 음영 (`support_var` 기반)
- raw poll dot overlay (있으면)
- 5 region 비교 모드: 5개 subplot grid

### Page 3 — Final Outcome (`pages/3_outcome.py`)
- 후보별 득표율 막대 + turnout 게이지
- 시·구 단위 choropleth (있으면; 없으면 단순 막대)
- "actual vs predicted" 비교 (placeholder OK)

### Page 4 — Demographics Breakdown (`pages/4_demographics.py`)
- 연령/학력/직업/소득별 stacked bar
- 광주(진보) vs 대구(보수) 시각 비교 패널
- 특정 세그먼트 클릭 → 가상 인터뷰 페이지로 navigation

### Page 5 — Virtual Interviews (`pages/5_interviews.py`)
- 페르소나 카드 5~50개
- 각 카드: 페르소나 요약 + vote + reason + key_factors
- 필터: region / age_group / occupation / education_level
- 데모용 highlight 5명 (사용자가 사전 지정)

### Page 6 — KG Viewer (`pages/6_kg.py`)
- pyvis 또는 plotly로 노드-링크
- 타임슬라이더(t=0..T) → 시점별 KG 변화
- 노드 색상: 타입 (Candidate/Event/Issue/Frame)
- 엣지 굵기: 빈도/중요도

## Placeholder Mode
**시뮬 결과가 없어도 화면은 살아있어야 함**:
- 결과 JSON 누락 시 `_workspace/snapshots/_placeholder/*.json` (대시보드 빌드 시 자동 생성)으로 fallback
- 친절한 메시지: "시뮬레이션 진행 중 — 결과가 박제되면 자동으로 실 데이터로 전환됩니다"
- 발표 도중 빌드 동결 후에도 안전

## 자동 폴링
```python
# components/result_loader.py
import streamlit as st, json, time
@st.cache_data(ttl=10)  # 10초마다 무효화
def load_results():
    idx = json.load(open("_workspace/snapshots/results_index.json"))
    return {r["region_id"]: json.load(open(r["path"])) for r in idx["results"]}
```

## 실행 명령
```bash
cd /Users/girinman/repos/cmux-hackathon-politicast
streamlit run ui/dashboard/app.py --server.port 8501 --server.headless true
```

## Downscale 트리거
- 6페이지 → 4페이지 (KG Viewer, Demographics 컷)
- choropleth 어려우면 막대로
- 인터뷰 50명 → 5명
- 모든 페이지에 placeholder mode 우선 보장 (실 데이터 없어도 깨지지 않음)

## 산출물 체크리스트
- [ ] `ui/dashboard/app.py`
- [ ] `ui/dashboard/pages/{1_scenario,2_poll,3_outcome,4_demographics,5_interviews,6_kg}.py`
- [ ] `ui/dashboard/components/{result_loader,plotly_factory,kg_viewer}.py`
- [ ] `ui/dashboard/_placeholder/` (placeholder JSON, 빌드 시 자동)
- [ ] requirements: `streamlit, plotly, pyvis, pandas, duckdb`

## 다른 에이전트와의 인터페이스
- data-engineer: `from src.data.queries import ...` + DuckDB 직접
- sim-engineer: `_workspace/snapshots/results/*.json` 폴링
- kg-engineer: `_workspace/snapshots/kg_*.json` 폴링
- paper-writer: 17:00 이후 페이지별 스크린샷 캡처 가이드 발신
