"""Scenario JSON → networkx MultiDiGraph 빌더.

입력: ``_workspace/data/scenarios/{region_id}.json`` (data-engineer 산출).
출력: 글로벌 ``MultiDiGraph`` + ``ScenarioIndex`` (region별 메타).

스키마 (scenario JSON) — 누락 필드는 default로 채움:

```jsonc
{
  "scenario_id": "seoul_mayor_2026",
  "region_id": "seoul_mayor",
  "election": {"election_id": "ROK_local_2026", "name": "...",
               "date": "2026-06-03", "type": "local"},
  "contest":  {"contest_id": "seoul_mayor_2026",
               "position_type": "metropolitan_mayor"},
  "district": {"province": "서울특별시", "district": null, "population": 9700000},
  "parties":  [{"party_id": "p_dem", "name": "더불어민주당", "ideology": -0.4}, ...],
  "candidates": [
    {"candidate_id": "c_kim", "name": "김XX",
     "party": "p_dem", "withdrawn": false}, ...
  ],
  "issues":  [{"issue_id": "i_housing", "name": "부동산", "type": "경제"}],
  "frames":  [{"frame_id": "f_judgement", "label": "정권심판"}],
  "events":  [
    {"event_id": "e1", "type": "ScandalEvent",
     "ts": "2026-04-10T09:00:00", "source": "조선일보",
     "title": "X후보 자녀 입시 의혹", "sentiment": -0.4,
     "severity": 0.7, "credibility": 0.5,
     "target_candidate_id": "c_kim", "frame_id": "f_judgement",
     "about": ["c_kim"], "mentions": ["i_education"]}
  ],
  "polls": [
    {"poll_id": 1, "ts": "2026-04-15T00:00:00",
     "sample_size": 1000, "leader_candidate": "c_kim", "leader_share": 0.42}
  ],
  "simulation": {"t_start": "2026-04-01T00:00:00",
                 "t_end":   "2026-06-03T00:00:00",
                 "timesteps": 4}
}
```
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import networkx as nx

from src.kg.ontology import EVENT_NODE_TYPES

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCENARIO_DIR = REPO_ROOT / "_workspace" / "data" / "scenarios"
DEFAULT_PERPLEXITY_DIR = REPO_ROOT / "_workspace" / "data" / "perplexity"
DEFAULT_COHORT_PRIOR_DIR = REPO_ROOT / "_workspace" / "data" / "cohort_priors"

# 한국 정당명 → 이념 좌표 (-1 진보 ↔ +1 보수). 시드값.
_PARTY_IDEOLOGY: dict[str, float] = {
    "더불어민주당": -0.55,
    "민주당": -0.55,
    "DPK": -0.55,
    "조국혁신당": -0.65,
    "진보당": -0.75,
    "정의당": -0.55,
    "녹색정의당": -0.55,
    "기본소득당": -0.50,
    "국민의힘": +0.55,
    "PPP": +0.55,
    "우리공화당": +0.80,
    "자유통일당": +0.85,
    "무소속": 0.0,
    "Independent": 0.0,
}

# data-engineer 의 event "type" → 우리 ontology event 노드 type.
_EVENT_TYPE_MAP: dict[str, str] = {
    "poll": "PollPublication",
    "polls": "PollPublication",
    "official": "MediaEvent",
    "report": "MediaEvent",
    "news": "MediaEvent",
    "scandal": "ScandalEvent",
    "investigation": "Investigation",
    "verdict": "Verdict",
    "press": "PressConference",
    "press_conference": "PressConference",
}


# ---------------------------------------------------------------------------
# Node id helpers
# ---------------------------------------------------------------------------
def nid(node_type: str, ident: str) -> str:
    """Canonical node id: ``"<Type>:<id>"``."""
    return f"{node_type}:{ident}"


def _slug(text: str) -> str:
    """한국어 안전 slug — 영숫자만 남기고 lowercase, 기타는 _."""
    out: list[str] = []
    for ch in text or "":
        if ch.isalnum():
            out.append(ch.lower())
        elif out and out[-1] != "_":
            out.append("_")
    return "".join(out).strip("_") or "x"


def _is_data_engineer_schema(scenario: dict[str, Any]) -> bool:
    """data-engineer 시드 스키마 (id/date/label/election_date) 감지.

    내부 normalized 스키마와의 차이:
      - 후보의 식별자 키: ``id``         vs ``candidate_id``
      - 이슈 식별자/이름:   ``id``/``label``  vs ``issue_id``/``name``
      - 이벤트 타임스탬프:  ``date``       vs ``ts``
      - 선거일 위치:        top-level ``election_date`` vs ``election.date``
      - polls 가 별도 list (각 row 가 후보 컬럼)
    """
    if "election_date" in scenario:
        return True
    cands = scenario.get("candidates") or []
    if cands and isinstance(cands[0], dict) and "id" in cands[0] and "candidate_id" not in cands[0]:
        return True
    events = scenario.get("events") or []
    if events and isinstance(events[0], dict) and "date" in events[0] and "ts" not in events[0]:
        return True
    return False


def _normalize_de_scenario(s: dict[str, Any]) -> dict[str, Any]:
    """data-engineer 시드 → builder 내부 정규화 dict.

    누락된 필드는 default. 전환 결과는 ``_ingest_scenario`` 가 그대로 소비.
    """
    region_id: str = s.get("region_id") or "?"
    election_date_raw: Any = s.get("election_date") or "2026-06-03"
    election_date = parse_ts(election_date_raw, default=datetime(2026, 6, 3))
    label: str = s.get("label") or region_id

    # ---- election / contest / district
    # data-engineer 가 nested ``election`` block 을 박제했으면 그 값을 우선.
    nested_el = s.get("election") or {}
    nested_co = s.get("contest") or {}
    nested_di = s.get("district") or {}

    election = {
        "election_id": (
            nested_el.get("election_id")
            or s.get("election_id")
            or f"ROK_local_2026_{region_id}"
        ),
        "name": nested_el.get("name") or s.get("election_name") or "제9회 전국동시지방선거",
        "date": nested_el.get("date") or election_date_raw,
        "type": (
            nested_el.get("type")
            or ("local" if (s.get("election_type") or "").endswith("mayor") else None)
            or s.get("election_type")
            or "local"
        ),
    }
    contest = {
        "contest_id": (
            nested_co.get("contest_id")
            or s.get("contest_id")
            or f"{region_id}_contest"
        ),
        "position_type": (
            nested_co.get("position_type")
            or s.get("election_type")
            or "metropolitan_mayor"
        ),
    }
    district = {
        "province": (
            nested_di.get("province")
            or s.get("district_province")
            or s.get("province")
            or label
        ),
        "district": nested_di.get("district") or s.get("district"),
        "population": nested_di.get("population") or s.get("population"),
    }

    # ---- parties (collect unique party names)
    # Bug fix (2026-04-26): if `c.party` already looks like a party_id (starts
    # with "p_"), reuse it as-is and pull the human-readable name from
    # `c.party_name`. Otherwise the slugger emits `p_p_dem` etc., which then
    # fails to match Perplexity-derived `Person.party_id="p_dem"` edges.
    party_name_to_id: dict[str, str] = {}
    parties_out: list[dict[str, Any]] = []
    for c in s.get("candidates", []) or []:
        pname = c.get("party")
        if not pname or pname in party_name_to_id:
            continue
        if pname.startswith("p_"):
            # Already an id. Use party_name as the displayable label.
            pid = pname
            display_name = c.get("party_name") or pname
        else:
            pid = f"p_{_slug(pname)}"
            display_name = pname
        party_name_to_id[pname] = pid
        parties_out.append(
            {
                "party_id": pid,
                "name": display_name,
                "ideology": _PARTY_IDEOLOGY.get(display_name, 0.0),
            }
        )

    # ---- candidates
    candidates_out: list[dict[str, Any]] = []
    for c in s.get("candidates", []) or []:
        cid = c.get("candidate_id") or c.get("id")
        if not cid:
            continue
        # P0 enrichment (2026-04-26): preserve human-curated profile fields so
        # builder/retriever can surface them to the voter prompt instead of
        # dropping them silently.
        candidates_out.append(
            {
                "candidate_id": cid,
                "name": c.get("name", cid),
                "party": party_name_to_id.get(c.get("party") or "", c.get("party") or ""),
                "party_name": c.get("party_name", c.get("party") or ""),
                "background": (c.get("background") or "").strip(),
                "key_pledges": list(c.get("key_pledges") or []),
                "withdrawn": bool(c.get("withdrawn", False)),
            }
        )

    # ---- issues + frames (key_issues 의 frame 도 NarrativeFrame 으로 승격)
    issues_out: list[dict[str, Any]] = []
    frames_out: list[dict[str, Any]] = []
    seen_frames: set[str] = set()
    for iss in s.get("key_issues", []) or []:
        iid = iss.get("issue_id") or iss.get("id")
        if not iid:
            continue
        issues_out.append(
            {
                "issue_id": iid,
                "name": iss.get("name") or iss.get("label", iid),
                "type": iss.get("type") or iss.get("frame") or "기타",
            }
        )
        frame_label = iss.get("frame")
        if frame_label and frame_label not in seen_frames:
            seen_frames.add(frame_label)
            frames_out.append(
                {"frame_id": f"f_{_slug(frame_label)}", "label": frame_label}
            )
    for fr in s.get("frames", []) or []:
        fid = fr.get("frame_id") or f"f_{_slug(fr.get('label', 'frame'))}"
        if fid in seen_frames:
            continue
        seen_frames.add(fid)
        frames_out.append({"frame_id": fid, "label": fr.get("label", fid)})

    # ---- events (description → title; date → ts; type 매핑)
    events_out: list[dict[str, Any]] = []
    for ev in s.get("events", []) or []:
        eid = ev.get("event_id") or ev.get("id")
        if not eid:
            continue
        ev_type = _EVENT_TYPE_MAP.get(
            (ev.get("type") or "report").lower(), "MediaEvent"
        )
        ts = ev.get("ts") or ev.get("date")
        title = ev.get("title") or ev.get("description") or eid
        norm = {
            "event_id": eid,
            "type": ev_type,
            "ts": ts,
            "source": ev.get("source", ""),
            "title": title,
            "sentiment": float(ev.get("sentiment", 0.0)),
            "frame_id": ev.get("frame_id"),
            "about": ev.get("about", []) or [],
            "mentions": ev.get("mentions", []) or [],
        }
        for f_ in (
            "severity",
            "credibility",
            "stage",
            "outcome",
            "speaker",
            "party_id",
            "target_candidate_id",
        ):
            if f_ in ev:
                norm[f_] = ev[f_]
        events_out.append(norm)

    # ---- polls (별도 flat list → PollPublication)
    polls_out: list[dict[str, Any]] = []
    candidate_ids = {c["candidate_id"] for c in candidates_out}
    for i, p in enumerate(s.get("polls", []) or [], start=1):
        # extract candidate columns
        leader_cid: str | None = None
        leader_share: float = -1.0
        for k, v in p.items():
            if k in ("date", "method", "undecided", "sample_size", "source", "poll_id", "ts"):
                continue
            if k in candidate_ids and isinstance(v, (int, float)):
                share = float(v) / 100.0 if float(v) > 1.0 else float(v)
                if share > leader_share:
                    leader_share = share
                    leader_cid = k
        polls_out.append(
            {
                "poll_id": p.get("poll_id", i),
                "ts": p.get("ts") or p.get("date"),
                "sample_size": p.get("sample_size"),
                "leader_candidate": leader_cid,
                "leader_share": leader_share if leader_share >= 0 else None,
                "source": p.get("method", p.get("source", "")),
            }
        )

    # ---- simulation defaults (없을 때만)
    sim = s.get("simulation") or {}
    if "t_end" not in sim:
        sim["t_end"] = election_date_raw
    if "t_start" not in sim:
        # 시뮬 시작 = 선거일 - 40일 ≈ 4-25 (2026-06-03 기준)
        sim["t_start"] = (election_date - timedelta(days=40)).isoformat()
    if "timesteps" not in sim:
        sim["timesteps"] = 4

    return {
        "scenario_id": s.get("scenario_id", region_id),
        "region_id": region_id,
        "election": election,
        "contest": contest,
        "district": district,
        "parties": parties_out,
        "candidates": candidates_out,
        "issues": issues_out,
        "frames": frames_out,
        "events": events_out,
        "polls": polls_out,
        "simulation": sim,
        # P1 enrichment (2026-04-26): preserve human-curated region notes so
        # builder/retriever can surface them as a `[지역 정세]` block.
        "scenario_notes": s.get("scenario_notes"),
    }


def parse_ts(value: Any, default: datetime | None = None) -> datetime:
    """ISO 문자열/datetime/None 을 **naive** datetime 으로 정규화.

    KST(+09:00) 등 timezone 이 포함된 문자열은 datetime 으로 파싱한 후
    ``replace(tzinfo=None)`` — 비교/firewall 일관성을 위해 모든 ts 를
    timezone-naive 로 통일한다.
    """
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo is not None else value
    if isinstance(value, str):
        s = value.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            # 마지막 수단: date-only fallback
            dt = datetime.fromisoformat(s.split("T", 1)[0])
        return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt
    if default is not None:
        return default
    raise ValueError(f"Cannot parse timestamp from: {value!r}")


# ---------------------------------------------------------------------------
# ScenarioIndex
# ---------------------------------------------------------------------------
@dataclass
class ScenarioMeta:
    """region별 시뮬레이션 시간 매핑 — Temporal Firewall이 사용."""

    scenario_id: str
    region_id: str
    contest_id: str
    t_start: datetime
    t_end: datetime
    timesteps: int  # T (1..4 권장)

    def t_to_realtime(self, t: int) -> datetime:
        """timestep ``t`` (0..T-1) → 실제 시각.

        선거일까지의 구간을 timesteps-1 등분하여 t에 해당하는 ``t_real``을 반환.
        ``t == 0`` → ``t_start``, ``t == T-1`` → ``t_end``.
        ``T == 1`` 인 경우는 항상 ``t_end`` 반환 (단일 시점).
        """
        if self.timesteps <= 1:
            return self.t_end
        t_clamped = max(0, min(int(t), self.timesteps - 1))
        span = (self.t_end - self.t_start) / (self.timesteps - 1)
        return self.t_start + span * t_clamped


@dataclass
class ScenarioIndex:
    """region_id → ScenarioMeta 룩업.

    또한 ``region_id → contest_id``, ``region_id → list[candidate_id]`` 인덱스
    를 미리 계산하여 retriever가 ``O(1)`` 조회 가능하게 한다.
    """

    by_region: dict[str, ScenarioMeta] = field(default_factory=dict)
    contest_for_region: dict[str, str] = field(default_factory=dict)
    candidates_in_contest: dict[str, list[str]] = field(default_factory=dict)
    region_for_contest: dict[str, str] = field(default_factory=dict)

    def add(self, meta: ScenarioMeta, candidate_ids: list[str]) -> None:
        self.by_region[meta.region_id] = meta
        self.contest_for_region[meta.region_id] = meta.contest_id
        self.region_for_contest[meta.contest_id] = meta.region_id
        self.candidates_in_contest[meta.contest_id] = list(candidate_ids)


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------
def _add_node(G: nx.MultiDiGraph, node_id: str, **attrs: Any) -> None:
    if node_id in G.nodes:
        # 멱등 — 새 attrs 로 덮어쓰기
        G.nodes[node_id].update(attrs)
    else:
        G.add_node(node_id, **attrs)


def _add_edge(
    G: nx.MultiDiGraph, src: str, dst: str, rel: str, **attrs: Any
) -> None:
    G.add_edge(src, dst, key=rel, rel=rel, **attrs)


def _ingest_scenario(
    G: nx.MultiDiGraph,
    index: ScenarioIndex,
    scenario: dict[str, Any],
    *,
    source_path: Path | None = None,
) -> None:
    """단일 시나리오 dict 를 G 에 머지.

    data-engineer 시드 스키마는 자동 normalize 후 처리.
    """
    if _is_data_engineer_schema(scenario):
        scenario = _normalize_de_scenario(scenario)

    region_id = scenario.get("region_id")
    if not region_id:
        log.warning("[kg] scenario missing region_id: %s", source_path)
        return

    # Skip non-election payloads that share the scenario directory but carry
    # only persona/target metadata (e.g. data-engineer's hill-climbing target
    # files). Without this guard they would register a stub contest and
    # silently overwrite the real ``contest_for_region`` mapping, leaving
    # ``candidates_in_contest`` empty for the affected region.
    if not (scenario.get("candidates") or scenario.get("contest")):
        log.info(
            "[kg] skipping non-election scenario %s (no candidates/contest)",
            source_path,
        )
        return

    # ---- Election
    el = scenario.get("election") or {}
    election_id = el.get("election_id", f"election:{region_id}")
    el_node = nid("Election", election_id)
    _add_node(
        G,
        el_node,
        type="Election",
        label=el.get("name", election_id),
        election_id=election_id,
        name=el.get("name"),
        date=parse_ts(el.get("date"), default=datetime(2026, 6, 3)),
        election_type=el.get("type", "local"),
    )

    # ---- District
    d = scenario.get("district") or {}
    # P1 enrichment (2026-04-26): pull human-written `scenario_notes` (region
    # 정세 한 줄 메모) onto the District node so retriever can surface it as a
    # `[지역 정세]` block. Stored as a string regardless of source shape.
    raw_notes = scenario.get("scenario_notes")
    if isinstance(raw_notes, list):
        notes_str = " ".join(str(x).strip() for x in raw_notes if x)
    elif isinstance(raw_notes, dict):
        notes_str = " ".join(
            f"{k}: {v}" for k, v in raw_notes.items() if v
        )
    elif isinstance(raw_notes, str):
        notes_str = raw_notes.strip()
    else:
        notes_str = ""
    dist_node = nid("District", region_id)
    _add_node(
        G,
        dist_node,
        type="District",
        label=d.get("province", region_id),
        region_id=region_id,
        province=d.get("province", ""),
        district=d.get("district"),
        population=d.get("population"),
        scenario_notes=notes_str,
    )

    # ---- Contest
    c = scenario.get("contest") or {}
    contest_id = c.get("contest_id", f"{region_id}_contest")
    contest_node = nid("Contest", contest_id)
    _add_node(
        G,
        contest_node,
        type="Contest",
        label=f"{region_id}/{c.get('position_type','contest')}",
        contest_id=contest_id,
        election_id=election_id,
        region_id=region_id,
        position_type=c.get("position_type", "metropolitan_mayor"),
    )
    _add_edge(G, contest_node, el_node, "inElection")
    _add_edge(G, contest_node, dist_node, "heldIn")

    # ---- Parties
    party_ids: dict[str, str] = {}  # local id -> graph node
    for p in scenario.get("parties", []) or []:
        pid = p.get("party_id") or p.get("name")
        if not pid:
            continue
        p_node = nid("Party", pid)
        _add_node(
            G,
            p_node,
            type="Party",
            label=p.get("name", pid),
            party_id=pid,
            name=p.get("name", pid),
            ideology=float(p.get("ideology", 0.0)),
        )
        party_ids[pid] = p_node

    # ---- Candidates
    # P0 enrichment (2026-04-26): persist human-curated `background`,
    # `key_pledges`, `party_name` fields so KGRetriever can prepend a
    # `[후보 프로필]` block to the voter prompt. Scenario JSON already carries
    # these — without this loop they were dropped, causing voter LLMs to see
    # only `id | name (party_id)` and collapse into ideology stereotypes.
    party_id_to_name: dict[str, str] = {
        pid: G.nodes[node].get("name", pid)
        for pid, node in party_ids.items()
    }
    candidate_node_ids: list[str] = []
    for cand in scenario.get("candidates", []) or []:
        cid = cand.get("candidate_id")
        if not cid:
            continue
        party_id = cand.get("party")
        party_name = (
            cand.get("party_name")
            or (party_id_to_name.get(party_id) if party_id else None)
            or party_id
            or ""
        )
        c_node = nid("Candidate", cid)
        _add_node(
            G,
            c_node,
            type="Candidate",
            label=cand.get("name", cid),
            candidate_id=cid,
            contest_id=contest_id,
            name=cand.get("name", cid),
            party=party_id,
            party_name=party_name,
            background=(cand.get("background") or "").strip(),
            key_pledges=list(cand.get("key_pledges") or []),
            withdrawn=bool(cand.get("withdrawn", False)),
        )
        _add_edge(G, c_node, contest_node, "candidateIn")
        if cand.get("party") and cand["party"] in party_ids:
            _add_edge(G, c_node, party_ids[cand["party"]], "belongsTo")
        candidate_node_ids.append(cid)

    # ---- Issues
    for issue in scenario.get("issues", []) or []:
        iid = issue.get("issue_id") or issue.get("name")
        if not iid:
            continue
        _add_node(
            G,
            nid("PolicyIssue", iid),
            type="PolicyIssue",
            label=issue.get("name", iid),
            issue_id=iid,
            name=issue.get("name", iid),
            issue_type=issue.get("type", "기타"),
        )

    # ---- Frames
    for frame in scenario.get("frames", []) or []:
        fid = frame.get("frame_id") or frame.get("label")
        if not fid:
            continue
        _add_node(
            G,
            nid("NarrativeFrame", fid),
            type="NarrativeFrame",
            label=frame.get("label", fid),
            frame_id=fid,
        )

    # ---- Events
    sim = scenario.get("simulation") or {}
    t_start = parse_ts(sim.get("t_start"), default=datetime(2026, 4, 1))
    t_end = parse_ts(sim.get("t_end"), default=datetime(2026, 6, 3))

    for ev in scenario.get("events", []) or []:
        eid = ev.get("event_id")
        if not eid:
            continue
        ev_type = ev.get("type", "MediaEvent")
        if ev_type not in EVENT_NODE_TYPES:
            log.warning("[kg] unknown event type %s, falling back to MediaEvent", ev_type)
            ev_type = "MediaEvent"
        ev_node = nid(ev_type, eid)
        ts = parse_ts(ev.get("ts"), default=t_start)

        attrs = {
            "type": ev_type,
            "label": ev.get("title", eid),
            "event_id": eid,
            "ts": ts,
            "source": ev.get("source", ""),
            "title": ev.get("title", ""),
            "sentiment": float(ev.get("sentiment", 0.0)),
            "frame_id": ev.get("frame_id"),
            "region_id": region_id,
        }
        # subtype-specific fields
        for f_ in ("severity", "credibility", "stage", "outcome", "speaker", "party_id"):
            if f_ in ev:
                attrs[f_] = ev[f_]
        if "target_candidate_id" in ev:
            attrs["target_candidate_id"] = ev["target_candidate_id"]
        _add_node(G, ev_node, **attrs)

        # edges: about → Candidate|Party
        for tgt in ev.get("about", []) or []:
            # target may be candidate_id or party_id; try both
            for ttype in ("Candidate", "Party"):
                t_node = nid(ttype, tgt)
                if t_node in G.nodes:
                    _add_edge(G, ev_node, t_node, "about")
                    break
        # edges: mentions → PolicyIssue
        for iss in ev.get("mentions", []) or []:
            i_node = nid("PolicyIssue", iss)
            if i_node in G.nodes:
                _add_edge(G, ev_node, i_node, "mentions")
        # edges: framedBy → NarrativeFrame
        if ev.get("frame_id"):
            f_node = nid("NarrativeFrame", ev["frame_id"])
            if f_node in G.nodes:
                _add_edge(G, ev_node, f_node, "framedBy")

    # ---- Polls
    for poll in scenario.get("polls", []) or []:
        pid = poll.get("poll_id")
        if pid is None:
            continue
        p_node = nid("PollPublication", str(pid))
        ts = parse_ts(poll.get("ts"), default=t_start)
        # poll_id may be int or str (e.g. "prediction_prior_dalseo_20260426").
        try:
            poll_id_typed: Any = int(pid)
        except (TypeError, ValueError):
            poll_id_typed = str(pid)
        _add_node(
            G,
            p_node,
            type="PollPublication",
            label=f"poll#{pid}",
            event_id=str(pid),
            poll_id=poll_id_typed,
            ts=ts,
            contest_id=contest_id,
            region_id=region_id,
            sample_size=poll.get("sample_size"),
            leader_candidate=poll.get("leader_candidate"),
            leader_share=poll.get("leader_share"),
            sentiment=0.0,
            title=f"여론조사 #{pid}",
            source=poll.get("source", ""),
        )
        _add_edge(G, p_node, contest_node, "publishesPoll")
        if poll.get("leader_candidate"):
            ld_node = nid("Candidate", poll["leader_candidate"])
            if ld_node in G.nodes:
                _add_edge(G, p_node, ld_node, "about")

    # ---- ScenarioIndex registration
    timesteps = int(sim.get("timesteps", 4))
    meta = ScenarioMeta(
        scenario_id=scenario.get("scenario_id", region_id),
        region_id=region_id,
        contest_id=contest_id,
        t_start=t_start,
        t_end=t_end,
        timesteps=timesteps,
    )
    index.add(meta, candidate_node_ids)


# ---------------------------------------------------------------------------
# P2/P3 enrichment — Perplexity-curated facts (2026-04-26)
# ---------------------------------------------------------------------------
def _ingest_cohort_priors(
    G: nx.MultiDiGraph,
    facts: dict[str, Any],
    *,
    source_path: Path | None = None,
) -> dict[str, int]:
    """Track B — ingest CohortPrior nodes from `cohort_priors/*.json`.

    Each cohort prior carries a fully-source-attributed party_lean dict.
    Retriever 's `get_cohort_prior(age, gender, region)` resolves the most
    specific match (region+age+gender > region+age > national+age+gender >
    national+age).
    """
    counters = {"cohort_priors": 0, "sources": 0}

    for src in facts.get("sources", []) or []:
        sid = src.get("source_id")
        if not sid:
            continue
        s_node = nid("Source", sid)
        _add_node(
            G, s_node,
            type="Source",
            label=src.get("name", sid),
            source_id=sid,
            name=src.get("name", sid),
            url_root=src.get("url_root", ""),
            media_type=src.get("media_type", "newspaper"),
            ideology=float(src.get("ideology", 0.0)),
        )
        counters["sources"] += 1

    for prior in facts.get("cohort_priors", []) or []:
        cid = prior.get("cohort_id")
        if not cid:
            continue
        publish_ts_raw = prior.get("publish_ts")
        try:
            publish_ts = parse_ts(publish_ts_raw) if publish_ts_raw else None
        except Exception:
            publish_ts = None
        c_node = nid("CohortPrior", cid)
        attrs = {
            "type": "CohortPrior",
            "label": cid,
            "cohort_id": cid,
            "age_band": prior.get("age_band", "ALL"),
            "gender": prior.get("gender", "ALL"),
            "scope": prior.get("scope", "national"),
            "region_id": prior.get("region_id"),
            "party_lean": dict(prior.get("party_lean") or {}),
            "ideological_lean": dict(prior.get("ideological_lean") or {}),
            "n_polls": int(prior.get("n_polls", 0)),
            "sample_size": int(prior.get("sample_size", 0)),
            "source": prior.get("source", ""),
            "source_url": prior.get("source_url", ""),
            "publish_ts": publish_ts,
            "notes": prior.get("notes", ""),
            "additional_context": prior.get("additional_context", ""),
            "provenance": "cohort_priors",
        }
        _add_node(G, c_node, **attrs)
        counters["cohort_priors"] += 1

        # Edge: CohortPrior -> Region (District), CohortPrior -> Party (with lean weight)
        if prior.get("region_id"):
            d_node = nid("District", prior["region_id"])
            if d_node in G.nodes:
                _add_edge(G, c_node, d_node, "appliesToRegion")
        for party_key, lean in (prior.get("party_lean") or {}).items():
            if not lean or party_key in ("undecided", "other"):
                continue
            # party_lean uses keys "ppp"/"dpk"/"rebuild" — map to canonical Party node ids
            party_id_map = {"ppp": "p_ppp", "dpk": "p_dem", "rebuild": "p_rebuild"}
            pid = party_id_map.get(party_key)
            if not pid:
                continue
            p_node = nid("Party", pid)
            if p_node in G.nodes:
                _add_edge(G, c_node, p_node, "leansToward", weight=float(lean))

    return counters


def _ingest_perplexity_facts(
    G: nx.MultiDiGraph,
    index: ScenarioIndex,
    facts: dict[str, Any],
    *,
    source_path: Path | None = None,
    cutoff_ts: datetime | None = None,
) -> dict[str, int]:
    """Merge a Perplexity-derived fact bundle into the global KG.

    Schema (per region):
      - ``candidate_event_facts``: list of MediaEvent/PressConference dicts
        (same shape as scenario ``events`` — `event_id`/`type`/`ts`/`title`/
        `source`/`source_url`/`sentiment`/`frame_id`/`speaker`/`party_id`/
        `about`/`mentions`).
      - ``candidate_pledge_extras``: ``{candidate_id: [extra pledge str, ...]}``
        — appended to the existing ``key_pledges`` attribute on the Candidate
        node (P0 surface point).
      - ``people``: list of Person dicts (``person_id``/`name`/`role`/`party_id`).
      - ``sources``: list of Source dicts (``source_id``/`name`/`url_root`/
        `media_type`/`ideology`).
      - ``event_source_links``: list of ``{event_id, source_id}`` to wire the
        ``attributedTo`` relation between an Event node and a Source.

    All event ts are validated against ``cutoff_ts`` (default: 2026-04-26
    23:59:59) — Perplexity hallucinations / future-dated rumors are dropped.

    Returns counters used for the final summary log.
    """
    cutoff = cutoff_ts or datetime(2026, 4, 26, 23, 59, 59)
    region_id = facts.get("region_id")
    applies_to_regions: list[str] = list(facts.get("applies_to_regions") or [])
    # Track A cross-region narrative: when `applies_to_regions` is set, ingest
    # the events for *each* region (region_id rotates per copy). The container
    # `region_id` (e.g. "_global_ppp_leadership") is not itself a contest.
    multi_region_mode = bool(applies_to_regions)

    if not multi_region_mode:
        if not region_id:
            log.warning("[kg/perplexity] missing region_id: %s", source_path)
            return {}
        if region_id not in index.contest_for_region:
            log.warning(
                "[kg/perplexity] region %s has no scenario contest yet — "
                "skip Perplexity ingest for %s",
                region_id, source_path,
            )
            return {}

    counters = {
        "events": 0, "events_dropped_future": 0, "events_dropped_no_ts": 0,
        "people": 0, "sources": 0, "event_source_links": 0,
        "candidate_pledge_extras": 0, "damages_party_links": 0,
    }

    # ---- Sources first (events may cite them)
    for src in facts.get("sources", []) or []:
        sid = src.get("source_id")
        if not sid:
            continue
        s_node = nid("Source", sid)
        _add_node(
            G, s_node,
            type="Source",
            label=src.get("name", sid),
            source_id=sid,
            name=src.get("name", sid),
            url_root=src.get("url_root", ""),
            media_type=src.get("media_type", "newspaper"),
            ideology=float(src.get("ideology", 0.0)),
        )
        counters["sources"] += 1

    # ---- People
    for p in facts.get("people", []) or []:
        pid = p.get("person_id")
        if not pid:
            continue
        p_node = nid("Person", pid)
        _add_node(
            G, p_node,
            type="Person",
            label=p.get("name", pid),
            person_id=pid,
            name=p.get("name", pid),
            role=p.get("role", ""),
            party_id=p.get("party_id"),
        )
        # Person → Party affiliation
        party_id = p.get("party_id")
        if party_id:
            party_node = nid("Party", party_id)
            if party_node in G.nodes:
                _add_edge(G, p_node, party_node, "affiliatedTo")
        counters["people"] += 1

    # ---- Candidate pledge extras (append to existing list, dedupe)
    for cid, extras in (facts.get("candidate_pledge_extras") or {}).items():
        c_node = nid("Candidate", cid)
        attrs = G.nodes.get(c_node)
        if attrs is None:
            log.debug(
                "[kg/perplexity] pledge_extras for unknown candidate %s "
                "(region=%s) — skip", cid, region_id,
            )
            continue
        existing = list(attrs.get("key_pledges") or [])
        for extra in extras or []:
            if extra and extra not in existing:
                existing.append(extra)
                counters["candidate_pledge_extras"] += 1
        attrs["key_pledges"] = existing

    # ---- Events
    # In multi_region_mode, emit a copy of each event for every region in
    # applies_to_regions (with region_id-suffixed event_id). In single-region
    # mode, emit once with region_id.
    target_regions: list[str]
    if multi_region_mode:
        target_regions = [r for r in applies_to_regions if r in index.contest_for_region]
    else:
        target_regions = [region_id]  # type: ignore[list-item]

    for ev in facts.get("candidate_event_facts", []) or []:
        eid = ev.get("event_id")
        if not eid:
            continue
        ev_type = ev.get("type", "MediaEvent")
        if ev_type not in EVENT_NODE_TYPES:
            log.warning(
                "[kg/perplexity] unknown event type %s, falling back to MediaEvent",
                ev_type,
            )
            ev_type = "MediaEvent"
        try:
            sim_meta = index.by_region.get(target_regions[0]) if target_regions else None
            fallback_ts = sim_meta.t_start if sim_meta else datetime(2026, 4, 1)
            ts = parse_ts(ev.get("ts"), default=fallback_ts)
        except Exception:
            counters["events_dropped_no_ts"] += 1
            continue
        if ts > cutoff:
            counters["events_dropped_future"] += 1
            continue

        for tgt_region in target_regions:
            # Use suffixed id in multi-region mode so per-region snapshots
            # carry distinct event nodes (each with its own region_id attr).
            scoped_eid = f"{eid}__{tgt_region}" if multi_region_mode else eid
            ev_node = nid(ev_type, scoped_eid)
            attrs = {
                "type": ev_type,
                "label": ev.get("title", scoped_eid),
                "event_id": scoped_eid,
                "ts": ts,
                "source": ev.get("source", ""),
                "source_url": ev.get("source_url", ""),
                "title": ev.get("title", ""),
                "sentiment": float(ev.get("sentiment", 0.0)),
                "frame_id": ev.get("frame_id"),
                "region_id": tgt_region,
                "provenance": "perplexity",
                "applies_to": "multi_region" if multi_region_mode else "single_region",
                "narrative_kind": ev.get("narrative_kind") or (
                    "ppp_leadership" if multi_region_mode else None
                ),
            }
            for f_ in ("speaker", "party_id", "severity", "credibility",
                       "stage", "outcome"):
                if f_ in ev:
                    attrs[f_] = ev[f_]
            if "target_candidate_id" in ev:
                attrs["target_candidate_id"] = ev["target_candidate_id"]
            _add_node(G, ev_node, **attrs)

            # about → Candidate | Party | Person
            for t_ in ev.get("about", []) or []:
                for ttype in ("Candidate", "Party", "Person"):
                    t_node = nid(ttype, t_)
                    if t_node in G.nodes:
                        _add_edge(G, ev_node, t_node, "about")
                        break
            # mentions → PolicyIssue
            for iss in ev.get("mentions", []) or []:
                i_node = nid("PolicyIssue", iss)
                if i_node in G.nodes:
                    _add_edge(G, ev_node, i_node, "mentions")
            # framedBy → NarrativeFrame
            if ev.get("frame_id"):
                f_node = nid("NarrativeFrame", ev["frame_id"])
                if f_node in G.nodes:
                    _add_edge(G, ev_node, f_node, "framedBy")
            # speaker → Person (match by name)
            speaker = ev.get("speaker")
            if speaker:
                for n, nattrs in G.nodes(data=True):
                    if nattrs.get("type") == "Person" and nattrs.get("name") == speaker:
                        _add_edge(G, ev_node, n, "speakerIs")
                        break
            counters["events"] += 1

    # ---- event ↔ source attribution
    by_event_id: dict[str, str] = {}
    for ev in facts.get("candidate_event_facts", []) or []:
        eid = ev.get("event_id")
        ev_type = ev.get("type", "MediaEvent")
        if ev_type not in EVENT_NODE_TYPES:
            ev_type = "MediaEvent"
        if eid:
            by_event_id[eid] = ev_type
    for link in facts.get("event_source_links", []) or []:
        eid = link.get("event_id")
        sid = link.get("source_id")
        if not eid or not sid:
            continue
        ev_type = by_event_id.get(eid, "MediaEvent")
        s_node = nid("Source", sid)
        if multi_region_mode:
            # one attributedTo edge per per-region copy
            for tgt_region in target_regions:
                ev_node = nid(ev_type, f"{eid}__{tgt_region}")
                if ev_node in G.nodes and s_node in G.nodes:
                    _add_edge(G, ev_node, s_node, "attributedTo")
                    counters["event_source_links"] += 1
        else:
            ev_node = nid(ev_type, eid)
            if ev_node in G.nodes and s_node in G.nodes:
                _add_edge(G, ev_node, s_node, "attributedTo")
                counters["event_source_links"] += 1

    # ---- damages_party_links — Track A new relation for narrative events that
    # erode a party's standing (e.g. PPP leadership missteps). Severity is a
    # 0..1 weight that voter agents / dashboards can reason about.
    for link in facts.get("damages_party_links", []) or []:
        eid = link.get("event_id")
        pid = link.get("party_id")
        if not eid or not pid:
            continue
        ev_type = by_event_id.get(eid, "MediaEvent")
        p_node = nid("Party", pid)
        if multi_region_mode:
            for tgt_region in target_regions:
                ev_node = nid(ev_type, f"{eid}__{tgt_region}")
                if ev_node in G.nodes and p_node in G.nodes:
                    _add_edge(
                        G, ev_node, p_node, "damagesParty",
                        severity=float(link.get("severity", 0.5)),
                    )
                    counters["damages_party_links"] += 1
        else:
            ev_node = nid(ev_type, eid)
            if ev_node in G.nodes and p_node in G.nodes:
                _add_edge(
                    G, ev_node, p_node, "damagesParty",
                    severity=float(link.get("severity", 0.5)),
                )
                counters["damages_party_links"] += 1

    return counters


def build_kg_from_scenarios(
    scenario_dir: Path | str = DEFAULT_SCENARIO_DIR,
    perplexity_dir: Path | str | None = DEFAULT_PERPLEXITY_DIR,
    cohort_prior_dir: Path | str | None = DEFAULT_COHORT_PRIOR_DIR,
) -> tuple[nx.MultiDiGraph, ScenarioIndex]:
    """디렉토리의 모든 ``*.json`` 시나리오를 union 한 글로벌 KG.

    P2/P3 (2026-04-26): Optionally also ingest Perplexity-curated facts from
    ``perplexity_dir`` (Person/Source/extra events). Pass ``None`` to disable.

    Track B (2026-04-26): Optionally ingest CohortPrior nodes from
    ``cohort_prior_dir`` (national + regional voter party-lean priors).
    """
    G = nx.MultiDiGraph()
    index = ScenarioIndex()
    sdir = Path(scenario_dir)
    if not sdir.exists():
        log.warning("[kg] scenario dir missing: %s", sdir)
        return G, index
    files = sorted(sdir.glob("*.json"))
    if not files:
        log.warning("[kg] no scenario files under %s", sdir)
    for path in files:
        try:
            scenario = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            log.error("[kg] failed to load %s: %s", path, exc)
            continue
        # 한 파일에 여러 시나리오가 들어있을 수도 있도록 list 도 허용
        items: Iterable[dict[str, Any]]
        if isinstance(scenario, list):
            items = scenario
        else:
            items = [scenario]
        for s in items:
            _ingest_scenario(G, index, s, source_path=path)

    # ---- P2/P3 Perplexity ingest (after scenarios are in place)
    if perplexity_dir is not None:
        pdir = Path(perplexity_dir)
        if pdir.exists():
            agg: dict[str, int] = {}
            for path in sorted(pdir.glob("*.json")):
                try:
                    facts = json.loads(path.read_text(encoding="utf-8"))
                except Exception as exc:
                    log.error("[kg/perplexity] failed to load %s: %s", path, exc)
                    continue
                counters = _ingest_perplexity_facts(
                    G, index, facts, source_path=path
                )
                for k, v in counters.items():
                    agg[k] = agg.get(k, 0) + v
            if agg:
                log.info("[kg/perplexity] ingested: %s", agg)

    # ---- Track B CohortPrior ingest
    if cohort_prior_dir is not None:
        cdir = Path(cohort_prior_dir)
        if cdir.exists():
            cagg: dict[str, int] = {}
            for path in sorted(cdir.glob("*.json")):
                try:
                    facts = json.loads(path.read_text(encoding="utf-8"))
                except Exception as exc:
                    log.error("[kg/cohort] failed to load %s: %s", path, exc)
                    continue
                counters = _ingest_cohort_priors(G, facts, source_path=path)
                for k, v in counters.items():
                    cagg[k] = cagg.get(k, 0) + v
            if cagg:
                log.info("[kg/cohort] ingested: %s", cagg)

    return G, index


def build_kg_from_dicts(
    scenarios: Iterable[dict[str, Any]],
) -> tuple[nx.MultiDiGraph, ScenarioIndex]:
    """In-memory 시나리오 dict 목록으로부터 KG 빌드 (테스트/스텁용)."""
    G = nx.MultiDiGraph()
    index = ScenarioIndex()
    for s in scenarios:
        _ingest_scenario(G, index, s)
    return G, index


# ---------------------------------------------------------------------------
# CLI: docker compose run --rm app python -m src.kg.builder
# ---------------------------------------------------------------------------
def _summary(G: nx.MultiDiGraph, index: ScenarioIndex) -> dict[str, Any]:
    type_counts: dict[str, int] = {}
    for _, attrs in G.nodes(data=True):
        type_counts[attrs.get("type", "?")] = type_counts.get(attrs.get("type", "?"), 0) + 1
    rel_counts: dict[str, int] = {}
    for _, _, k in G.edges(keys=True):
        rel_counts[k] = rel_counts.get(k, 0) + 1
    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "regions": list(index.by_region.keys()),
        "node_type_counts": type_counts,
        "edge_relation_counts": rel_counts,
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    G, index = build_kg_from_scenarios()
    summary = _summary(G, index)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
