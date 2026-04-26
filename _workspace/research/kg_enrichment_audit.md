# KG Enrichment Audit (read-only, pre-decision)

작성: 2026-04-26 14:55 KST · `claude-politikast-kg-96691` / kg-engineer v2

목적: 사용자 지시에 따라 **KG 가 voter agent prompt 에 surface 하는 정보의 현 깊이**를 정량화하고, **외부 소스 (뉴스/나무위키/NESDC) enrichment 우선순위**를 박제. 코드 변경 없음.

---

## 1. 현재 KG 가 ingest 하는 source

| Source | 위치 | 내용 | 비고 |
|---|---|---|---|
| **시드 시나리오 JSON** (5개) | `_workspace/data/scenarios/{region}.json` | candidates / parties / issues / frames / **events** / polls | **유일한 외부 입력**. data-engineer 가 큐레이션. |
| historical outcomes | `_workspace/data/scenarios/historical_outcomes/*.json` | 과거 본 선거 result | KG 빌더 미사용 (validation-first 산출물). 후속 `KGRetriever` 가 history 노드로 흡수 가능. |
| (없음) | — | 뉴스 RSS / 네이버 / 나무위키 / 후보 공식 SNS / NESDC PDF | **현재 0건**. |

`src/kg/builder.py` 는 scenario JSON 만 읽는다. 외부 fetcher 없음.

## 2. 시나리오 JSON 의 정보 깊이 (region 별, line 단위)

| Region | 파일 line | candidates | events | polls | issues | scenario_notes |
|---|---:|---:|---:|---:|---:|---|
| seoul_mayor | 122 | 3 | 2 | 3 | 3 | 있음 |
| gwangju_mayor | 109 | 4 | 1 | 1 | 3 | 있음 |
| daegu_mayor | 139 | 4 | 3 | 1 | 4 | 있음 |
| busan_buk_gap | 117 | 3 | 2 | 1 | 4 | 있음 |
| daegu_dalseo_gap | 123 | 4 | 2 | 1 | 3 | 있음 |
| **합계** | 610 | 18 | 10 | 7 | 17 | — |

- **이벤트 13건 global** (KG snapshots 기준; 보궐 이벤트 일부 중복) — voter prompt 에 한 region 당 **최대 5 bullet** surface.
- **scenario_notes**: 사람이 쓴 region 정세 메모 (수 문장). **현재 KG 미수입 + 미surface**.
- **candidates 의 `background` / `key_pledges`**: 후보 프로필. **KG 빌더가 ingest 하지 않음 (drop)**, voter prompt 에도 미주입.
- **`key_issues[].frame`**: 이슈 프레임 라벨. KG 는 NarrativeFrame 노드는 만들지만, **프레임 → 후보/이슈 의미 매핑은 voter prompt 까지 surface 되지 않음** (단지 한 이벤트의 frame_label 만).

## 3. KGRetriever 가 voter agent 에게 전달하는 포맷

`src/sim/election_env.py::_build_context()` →

```
[KG 컨텍스트]
- [2026-04-19] (PressConference) 정원오, 민주당 서울시장 후보 확정 — 오세훈 무능 심판 — 정서:부정(-0.30) / 대상: 정원오 / 프레임: 정권심판
- [2026-04-15] (PollPublication) 여론조사 #2 — 정서:중립(+0.00) / 대상: 정원오
... (top-k=5)
[직전 여론조사 합의치]
- 정원오 (p_dem): 여론조사 평균 38.0% (ΔU_poll=+0.10)
...
[중앙정부 지지율] 32.5%
[주요 사건]
- t=0 [seed_event] ... (target=...)
```

`voter_agent.user_prompt()` 가 **후보 list 부분**에 띄우는 정보:
```
[후보]
- c_seoul_dpk | 정원오 (p_dem)
- c_seoul_ppp | 오세훈 (p_ppp)
```

**Critical gap**: candidate 의 `background`("전 서울 성동구청장 3선. 슬로건 '오세훈 무능 심판'") 와 `key_pledges`("기본사회 서울", "지방행정 실무 경험") 가 **scenario JSON 에 박제되어 있는데 prompt 어디에도 안 들어간다**. 즉 LLM 은 후보를 **이름과 정당 ID** 만으로 판단 — sweep 결과가 ideology stereotype 에 수렴할 수밖에 없는 1차 원인.

## 4. Coverage gap 정리

| 신호 | 현재 surface? | 기대 효과 | 비용 |
|---|---|---|---|
| **A. 후보 background / key_pledges** (scenario JSON 에 이미 존재) | ❌ | 후보별 차별화 (1차 ideology stereotype 깨기) | **0 fetch** — KG/prompt 코드 30분 |
| **B. scenario_notes** (사람이 쓴 region 정세) | ❌ | region 컨텍스트 풍부화 | 0 fetch — 10분 |
| **C. 나무위키 후보 1줄 요약** (외부) | ❌ | 후보 권위·이력 (전직, 출신지, 대표 정책) | 17 후보 × 1 GET ≈ 60-90분 |
| **D. 후보별 최근 30일 뉴스 헤드라인** (외부) | ❌ | 시점성 ScandalEvent / Investigation surface | naver/google news 90-120분 |
| **E. 이슈별 frame ↔ 정당 매핑** (KG 안에 NarrativeFrame 있음) | partial | issue 별 voter 정렬 강화 | 30분 |
| **F. NESDC 보고서 PDF (질문지/표본/가중치)** | ❌ | poll metadata 정확도 | secondary, 2-3시간 |
| **G. 이벤트 추가 ScandalEvent / Investigation / Verdict** | ❌ (instance 0) | adversarial 시그널 — sweep 깨기 | scenario 직접 큐레이션 (data-engineer 영역) |

## 5. Enrichment 권장 순서 (P0 → P3)

### P0 — **0-fetch / 30분**: 후보 프로필 surface
1. `src/kg/builder.py::_ingest_scenario()` 의 Candidate 노드에 `background`, `key_pledges`, `party_name` 어트리뷰트 추가 (이미 시드 JSON 에 있음, drop 만 막으면 됨).
2. `src/kg/retriever.py::subgraph_at()` 가 voter persona 가 보는 region 의 **모든 candidate** 에 대해 `background` (≤120자) + `key_pledges` (top-2) 를 한 줄씩 prepend → context_text 의 머리에 `[후보 프로필]` 블록 추가.
3. `src/sim/election_env.py::_build_context()` 가 `[KG 컨텍스트]` 합칠 때 그대로 통과 (코드 변경 1줄).

**파괴력**: 가장 큰 ROI. 후보별 이름·이력·공약이 prompt 에 들어가면 LLM 이 ideology 만으로 sweep 하지 않는다. **시뮬을 살리는 핵심 1수.**

### P1 — **0-fetch / +20분**: scenario_notes + frame mapping
4. `_ingest_scenario` 가 `scenario_notes` 를 District 노드 어트리뷰트로 흡수.
5. `subgraph_at()` 가 prompt 머리에 `[지역 정세]` 블록 (≤200자) 추가.
6. NarrativeFrame 노드를 candidate 와 연결: 후보 의 `key_pledges` 키워드와 frame 라벨 매칭 → `c_seoul_dpk —[promotes]→ NarrativeFrame:정권심판`. retriever 가 후보 프로필 라인에 `(주 프레임: 정권심판)` 첨부.

### P2 — **외부 fetch / 60-90분**: 나무위키 후보 요약
7. 신규 `src/kg/sources/namuwiki.py` (read-only, requests + lxml). 17명 후보 페이지 → 첫 lead paragraph (≤300자) 캐싱 → `_workspace/research/namuwiki_cache/{candidate_id}.json` (timestamp 박제).
8. **Temporal firewall 주의**: 나무위키 내용은 fetch 시점 snapshot. 페이지 last-edit timestamp 가 cutoff (현재 04-25/26) 이후면 위험 — 보수적으로 페이지 last-edit ≤ cutoff 만 사용. (실무: 안전을 위해 fetch 후 manual freeze hash 박제 → fetch 시점 ≤ cutoff_ts 지키도록 caching 정책에 박제.)
9. 후보 노드 어트리뷰트 `wiki_summary` 추가 → `[후보 프로필]` 블록에 1줄 추가.

**리스크**: 나무위키는 편향/오류 가능. **명시적으로 출처 표시 (`출처: 나무위키`)** 하여 LLM 이 fact 로 받지 않도록.

### P3 — **외부 fetch / 90-120분**: 뉴스 헤드라인 batch
10. 신규 `src/kg/sources/news_naver.py` — 후보별 검색어 (`"한동훈" 부산`) 로 네이버 뉴스 RSS / open API 30일 헤드라인 수집. 결과 → MediaEvent 노드 자동 생성 (sentiment 0, source=naver_news, ts=publish_ts).
11. 시점성 = ts 가 자연히 cutoff 이전인 것만 KG 에 들어감 → firewall 자동 적용.
12. 1 region 당 평균 +20~50 events → top-k=5 retrieval 이 스토리 풍부해짐.

**리스크**:
- API 키 / 스크래핑 — 해커톤 시간 잠식 위험. fetch 실패 시 P0/P1 만으로 충분히 시뮬 살릴 수 있다는 가정으로 P3 는 stretch.
- noise / hallucination signal: 헤드라인 sentiment 분류 (LLM call) 비용. ⇒ MVP 는 sentiment=0 으로 박제.

### P4 — Stretch: NESDC PDF / candidate 공식 SNS
13. 시간 잉여 시. 우선순위 낮음.

## 6. 즉시 1차 spec (P0 구현 시점에 그대로 코드)

### 6.1 builder 변경
```python
# src/kg/builder.py::_ingest_scenario(), Candidates loop:
_add_node(
    G, c_node,
    type="Candidate",
    label=cand.get("name", cid),
    candidate_id=cid,
    contest_id=contest_id,
    name=cand.get("name", cid),
    party=cand.get("party"),
    party_name=cand.get("party_name", ""),     # ★ NEW
    background=cand.get("background", ""),       # ★ NEW
    key_pledges=cand.get("key_pledges", []),     # ★ NEW
    withdrawn=bool(cand.get("withdrawn", False)),
)
```

### 6.2 retriever 변경
```python
# src/kg/retriever.py::subgraph_at() — context_text 빌드 직전:
profile_lines: list[str] = []
contest_id = self.index.contest_for_region.get(region_id)
for cid in self.index.candidates_in_contest.get(contest_id, []):
    a = self.G.nodes.get(nid("Candidate", cid), {})
    if a.get("withdrawn"):
        continue
    bg = (a.get("background") or "").strip()
    pledges = a.get("key_pledges") or []
    line = f"- {a.get('name', cid)} ({a.get('party_name', a.get('party',''))})"
    if bg:
        line += f": {bg[:140]}"
    if pledges:
        line += f" / 핵심공약: {', '.join(p[:30] for p in pledges[:3])}"
    profile_lines.append(line)
profile_block = "[후보 프로필]\n" + "\n".join(profile_lines) if profile_lines else ""

# scenario_notes (P1)
notes = self.index.by_region.get(region_id)
notes_block = ""  # P1 에서 District 노드에 박제 후 surface

text_blocks = [b for b in (profile_block, notes_block, event_text) if b]
context_text = "\n\n".join(text_blocks)
```

### 6.3 prompt 형식 (voter 가 받는 최종)
```
[후보 프로필]
- 정원오 (더불어민주당): 전 서울 성동구청장(3선). 2026-04-19 박주민·전현희 누르고 본선 후보 확정. 슬로건 '오세훈 무능 심판'. / 핵심공약: 기본사회 서울, 지방행정 실무 경험
- 오세훈 (국민의힘): ...
- 한민수 (개혁신당): ...

[KG 컨텍스트]
- [2026-04-19] (PressConference) 정원오, 민주당 서울시장 후보 확정 ...
...
```

## 7. 미수정 영역 / 영향 없음

- **Temporal Information Firewall** ($\mathcal{D}_{\le t}$): P0/P1 변경은 candidate background/pledges (시점 무관) — firewall 영향 없음. P2/P3 은 ts 박제 + cutoff 필터 추가로 firewall 그대로 유지.
- **paper/** 는 Codex / validation-first-paper 영역 — 손대지 않음.
- **`_workspace/validation/`** 은 Codex 영역 — 손대지 않음.
- **시뮬 결과 JSON 스키마** 변경 없음 (events_used 카운트만 증가 가능).
- **Firewall self-tests** 는 candidate 어트리뷰트 변경에 무관 — 영향 없음 예상 (검증 권장).

## 8. 시간 budget 추정

| Phase | 작업 | 시간 | 누적 |
|---|---|---:|---:|
| Audit (이 문서) | 박제 | 20min | 20min |
| P0 구현 + 5 region 재 fire | builder + retriever + voter_agent | 30-40min | ~60min |
| P1 구현 (notes + frame) | builder + retriever | 20min | ~80min |
| P2 (나무위키) | fetcher + cache + 통합 | 60-90min | ~150-170min |
| 사용자 결정 게이트 | P2/P3 진행 여부 | — | — |

**권장**: 사용자 결정 후 **P0 즉시 (가장 큰 ROI), P1 자동 부수, P2 는 별도 GO 신호 시.**

## 9. 미해결 의사결정 (사용자 escalate)

1. **나무위키 사용 가부** (편향/오류 vs 정보량). 출처 표시로 mitigation 충분?
2. **뉴스 fetch path**: 네이버 open API (key 필요) vs RSS 스크래핑 vs Google News.
3. **Sweep 깨기 목표 정량화**: 100% sweep → 어느 region 에서 어느 비율 (예: ≤80%) 까지 내려가야 "시뮬이 살았다"로 판정?
4. **P0 구현 → 재 fire (5 region) 비용**: ~5-10분 + Gemini 비용 (validation-first 후 cost guard 정책 확인 필요).

— 이상. 사용자 결정 대기.
