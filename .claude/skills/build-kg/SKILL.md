---
name: build-kg
description: PolitiKAST 정치 지식그래프 빌드 — Election + Event/Discourse 온톨로지(dataclass), networkx MultiDiGraph 빌더, 페르소나-서브그래프 GraphRAG retriever, Temporal Information Firewall(시점 이후 사실 차단). kg-engineer가 Phase 2에서 호출. 명시적 KG 작업 요청("KG 빌드", "온톨로지", "retriever", "firewall") 시에만 트리거.
---

# build-kg

## 트리거 시점
- orchestrator의 Phase 2 시작 신호 (data-engineer 시나리오 JSON 박제 후)
- 명시적 호출 ("KG 만들어", "graph build", "retrieval 구현")

## 온톨로지 (dataclass, no OWL)

```python
# src/kg/ontology.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Literal

@dataclass
class Election:
    election_id: str; name: str; date: datetime; type: str

@dataclass
class Contest:
    contest_id: str; election_id: str; region_id: str; position_type: str

@dataclass
class Candidate:
    candidate_id: str; contest_id: str; name: str; party: str; withdrawn: bool

@dataclass
class Party:
    party_id: str; name: str; ideology: float  # -1 progressive, +1 conservative

@dataclass
class District:
    region_id: str; province: str; district: Optional[str]; population: Optional[int]

@dataclass
class PolicyIssue:
    issue_id: str; name: str; type: str  # 부동산/경제/환경/...

@dataclass
class NarrativeFrame:
    frame_id: str; label: str  # "정권심판" / "경제심판" / "안정호소" / "지역개발"

@dataclass
class MediaEvent:
    event_id: str; ts: datetime; source: str; title: str; sentiment: float; frame_id: Optional[str]

@dataclass
class ScandalEvent(MediaEvent):
    severity: float; target_candidate_id: str; credibility: float

@dataclass
class Investigation(MediaEvent):
    target_candidate_id: str; stage: Literal["allegation","probe","indictment","trial"]

@dataclass
class Verdict(MediaEvent):
    target_candidate_id: str; outcome: Literal["acquittal","conviction","appeal"]

@dataclass
class PressConference(MediaEvent):
    speaker: str; party_id: str

@dataclass
class PollPublication:
    poll_id: int; ts: datetime; contest_id: str  # raw_poll table reference
```

## Builder

```python
# src/kg/builder.py
import networkx as nx, json

def build_kg_from_scenarios(scenario_dir="_workspace/data/scenarios"):
    G = nx.MultiDiGraph()
    for path in sorted(Path(scenario_dir).glob("*.json")):
        scenario = json.load(open(path))
        # add Election, Contest, District, Candidates, Parties
        # add events with edges: about(event→candidate), promotes(party→frame), mentions(event→issue)
        ...
    return G
```

엣지 라벨:
- `candidateIn(Candidate, Contest)`, `belongsTo(Candidate, Party)`, `heldIn(Contest, District)`
- `about(MediaEvent, Candidate|Party)`, `promotes(Party, Frame)`, `mentions(Event, Issue)`, `interpretedBy(Issue, Verdict)`

## Retriever (Temporal Firewall 핵심)

```python
# src/kg/retriever.py
class KGRetriever:
    def __init__(self, G, cutoff_ts):  # cutoff_ts = scenario['simulation_t_end']
        self.G = G
        self.cutoff = cutoff_ts

    def subgraph_at(self, persona, t, region_id, k=5) -> str:
        """
        시점 t (simulation timestep)와 페르소나 컨텍스트로부터
        관련 이벤트/이슈/프레임을 retrieve하여 텍스트 bullet로 직렬화.
        Firewall: event.ts <= t_real_for_step(t) 강제.
        """
        t_real = self._t_to_realtime(t)
        # 1) region match
        district_node = f"District:{region_id}"
        candidates_in_region = list(self.G.neighbors(district_node))
        # 2) events about those candidates with ts <= t_real
        events = []
        for c in candidates_in_region:
            for u, v, key, data in self.G.in_edges(c, keys=True, data=True):
                node = self.G.nodes[u]
                if node.get("type") in ("MediaEvent","ScandalEvent","Investigation","Verdict","PressConference") and node["ts"] <= t_real:
                    score = self._score(node, persona, t_real)
                    events.append((score, u, node))
        events.sort(key=lambda x: -x[0])
        top = events[:k]
        # 3) serialize as bullets
        lines = []
        for score, u, node in top:
            lines.append(f"- [{node['ts'].date()}] {node['title']} (정서: {node['sentiment']:+.1f}, 프레임: {node.get('frame_id','?')})")
        return "\n".join(lines) if lines else "(이 시점에 노출된 주요 이벤트 없음)"

    def _score(self, event_node, persona, t_real):
        # degree * recency_decay * persona_relevance
        ...
```

## Firewall 검증 (unit test 필수)

```python
# src/kg/firewall.py
def test_firewall(G, cutoff):
    retriever = KGRetriever(G, cutoff)
    result = retriever.subgraph_at({"district":"...","age":40}, t=2, region_id="seoul_mayor")
    # assert no event with ts > t_real_for_step(2) appears in result text
    ...
```

## 시각화 export (P1)

```python
# src/kg/export_d3.py
def export_kg_for_dashboard(G, region_id, t):
    nodes = [{"id": n, "label": d.get("label",n), "type": d.get("type"), "ts": d.get("ts")} for n,d in G.nodes(data=True)]
    edges = [{"src": u, "dst": v, "rel": k} for u,v,k in G.edges(keys=True)]
    json.dump({"nodes": nodes, "edges": edges, "t": t},
              open(f"_workspace/snapshots/kg_{region_id}_t{t}.json","w"))
```

## Downscale 트리거
- 14:30 retriever 미완 → stub로 빈 컨텍스트 반환 (sim-engineer는 baseline 가능)
- 풀 KG 실패 → dict-keyword retrieval (이슈명 → 이벤트 list)로 대체
- 시각화 export → P1 (대시보드 KG viewer 페이지 컷)

## 산출물 체크리스트
- [ ] `src/kg/ontology.py`
- [ ] `src/kg/builder.py`
- [ ] `src/kg/retriever.py`
- [ ] `src/kg/firewall.py` (단위 테스트 1개 이상)
- [ ] `src/kg/export_d3.py` (P1)
- [ ] `_workspace/snapshots/kg_{region_id}_t{t}.json` (P1)

## 다른 에이전트와의 인터페이스
- sim-engineer: `from src.kg.retriever import KGRetriever; retriever.subgraph_at(persona, t, region_id)` 호출 → 컨텍스트 텍스트
- dashboard-engineer: `_workspace/snapshots/kg_*.json` 폴링
- paper-writer: KG 통계 (노드 수, 이벤트 타입 분포, 평균 degree) SendMessage
