"""GraphRAG retriever — 페르소나 + 시점 t → 컨텍스트 텍스트.

핵심 책임:
1. **Temporal Information Firewall**: 모든 event에 대해
   ``event.ts <= meta.t_to_realtime(t)`` 강제. 이 함수를 통하지 않은 어떤
   query도 retrieve 결과에 미래 사실을 노출해서는 안 된다.
2. **Persona-aware scoring**: degree × recency_decay × persona_relevance.
3. **Bullet 직렬화**: voter agent prompt에 그대로 주입 가능한 짧은 텍스트.

Fallback: 빈 KG / 미박제 시 ``RetrievalResult.empty()`` — sim baseline 안전.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Optional

import networkx as nx

from src.kg.builder import ScenarioIndex, ScenarioMeta, nid
from src.kg.ontology import EVENT_NODE_TYPES

log = logging.getLogger(__name__)

# 이슈 키워드 → 페르소나 occupation/age/skills heuristic 매칭.
# 단순 lookup 으로 시작 — 추후 확장 가능.
_PERSONA_RELEVANT_ISSUE_KEYWORDS: dict[str, tuple[str, ...]] = {
    # 생활/도메인
    "부동산": ("주택", "전세", "임대", "건설", "부동산", "재개발", "분양"),
    "교육": ("학생", "학부모", "교사", "교육", "입시", "대학", "사교육"),
    "환경": ("환경", "녹색", "기후", "에너지", "탄소"),
    "경제": ("자영업", "소상공인", "기업", "임금", "고용", "경제", "취업", "창업"),
    "복지": ("노인", "복지", "장애", "돌봄", "보육", "연금"),
    "안보": ("군", "안보", "국방", "한미", "북한"),
    "지역개발": ("개발", "교통", "철도", "지하철", "GTX", "균형발전", "광역", "신청사"),
    # 담론/정체성 (data-engineer Phase 1 KST 재분류 반영)
    "정치": (
        "시민", "투표", "정치", "선거", "정당", "정권", "민주주의",
        "진보", "보수", "참여", "여당", "야당", "공약", "토론",
    ),
    "이념": (
        "보수", "진보", "좌파", "우파", "가치관", "신념", "지역색",
        "정체성", "이념", "세대", "TK", "호남", "영남",
    ),
    "역사": (
        "역사", "전쟁", "광주", "518", "5·18", "민주화", "세대", "기성",
        "독재", "유신",
    ),
    # 영문 alias (시나리오 type 이 영문일 때 fallback)
    "politics": ("시민", "투표", "정치", "선거", "정당", "정권"),
    "ideology": ("보수", "진보", "좌파", "우파", "이념"),
    "history": ("역사", "광주", "518", "민주화", "세대"),
}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------
@dataclass
class RetrievedEvent:
    event_id: str
    type: str
    ts: datetime
    title: str
    sentiment: float
    frame: Optional[str]
    target: Optional[str]
    score: float

    def to_kg_event(self, timestep: int) -> dict[str, Any]:
        """``result_schema.kg_events_used`` 항목 변환."""
        return {
            "event_id": self.event_id,
            "type": self.type,
            "target": self.target or "",
            "timestep": timestep,
        }


@dataclass
class RetrievalResult:
    context_text: str
    events_used: list[dict[str, Any]] = field(default_factory=list)
    triples: list[tuple[str, str, str]] = field(default_factory=list)
    cutoff_ts: Optional[datetime] = None

    @classmethod
    def empty(cls, cutoff: Optional[datetime] = None) -> "RetrievalResult":
        return cls(
            context_text="(이 시점에 노출된 주요 이벤트 없음)",
            events_used=[],
            triples=[],
            cutoff_ts=cutoff,
        )


# ---------------------------------------------------------------------------
# KGRetriever
# ---------------------------------------------------------------------------
class KGRetriever:
    """페르소나-서브그래프 GraphRAG.

    ``subgraph_at(persona, t, region_id)`` 가 핵심 API.
    voter prompt 의 ``context_block`` 에 그대로 주입.

    Args:
        G: ``builder.build_kg_from_scenarios`` 로 생성된 글로벌 MultiDiGraph.
        index: 동시에 만들어진 ScenarioIndex (region_id → ScenarioMeta).
        recency_tau_days: recency decay τ (기본 14일).
        max_context_chars: 직렬화 컨텍스트 최대 길이 — sim-engineer가 prompt
            예산 따라 조정.
    """

    def __init__(
        self,
        G: nx.MultiDiGraph,
        index: ScenarioIndex,
        *,
        recency_tau_days: float = 14.0,
        max_context_chars: int = 1500,
    ) -> None:
        self.G = G
        self.index = index
        self.recency_tau_days = max(1.0, float(recency_tau_days))
        self.max_context_chars = int(max_context_chars)

    # ------------------------------------------------------------------
    # Firewall-protected primitive
    # ------------------------------------------------------------------
    def _events_visible_at(
        self, region_id: str, cutoff_ts: datetime
    ) -> list[tuple[str, dict[str, Any]]]:
        """region에 연결된 모든 이벤트 노드 중 ``ts <= cutoff_ts`` 만 반환.

        **Firewall**: 호출자가 cutoff 를 우회할 수 없도록 이 메서드가 항상
        ``ts <= cutoff`` 필터 후의 list 만 노출. 미래 노드는 return list에
        절대 포함되지 않는다 (firewall.py 가 검증).
        """
        contest_id = self.index.contest_for_region.get(region_id)
        candidates_in_region: set[str] = set()
        if contest_id:
            for cid in self.index.candidates_in_contest.get(contest_id, []):
                candidates_in_region.add(nid("Candidate", cid))

        # 후보 약식 — region_id로 직접 묶인 이벤트도 (e.g., poll, generic media)
        visible: list[tuple[str, dict[str, Any]]] = []
        for n, attrs in self.G.nodes(data=True):
            t_ = attrs.get("type")
            if t_ not in EVENT_NODE_TYPES:
                continue
            ts = attrs.get("ts")
            if not isinstance(ts, datetime):
                # ts 가 없거나 잘못된 타입 — firewall 보수적으로 제외
                continue
            if ts > cutoff_ts:
                continue  # ★ firewall
            # region 필터: 이벤트의 about-edge 가 region 후보를 향하거나
            #              이벤트 attrs.region_id 가 일치하면 포함.
            if attrs.get("region_id") == region_id:
                visible.append((n, attrs))
                continue
            # about edge target check
            for _, dst, k in self.G.out_edges(n, keys=True):
                if k != "about":
                    continue
                if dst in candidates_in_region:
                    visible.append((n, attrs))
                    break
        return visible

    # ------------------------------------------------------------------
    # Persona relevance
    # ------------------------------------------------------------------
    def _persona_text_blob(self, persona: dict[str, Any]) -> str:
        parts: list[str] = []
        for k in ("occupation", "department", "job_title", "skills_and_expertise",
                  "hobbies_and_interests", "education_level", "district",
                  "professional_persona", "cultural_persona"):
            v = persona.get(k)
            if isinstance(v, str) and v:
                parts.append(v)
        return " ".join(parts).lower()

    def _persona_issue_relevance(
        self, persona_blob: str, event_node: str
    ) -> float:
        """이벤트가 mentions 하는 PolicyIssue 가 페르소나 키워드와 겹치면 가산."""
        rel = 0.0
        for _, dst, k in self.G.out_edges(event_node, keys=True):
            if k != "mentions":
                continue
            issue_attrs = self.G.nodes.get(dst, {})
            issue_name = issue_attrs.get("name") or issue_attrs.get("label") or ""
            issue_type = issue_attrs.get("issue_type") or ""
            keywords = list(_PERSONA_RELEVANT_ISSUE_KEYWORDS.get(issue_type, ()))
            if issue_name:
                keywords.append(issue_name)
            for kw in keywords:
                if kw and kw.lower() in persona_blob:
                    rel += 0.5
                    break
        return rel

    def _score(
        self,
        event_node: str,
        attrs: dict[str, Any],
        persona_blob: str,
        cutoff_ts: datetime,
    ) -> float:
        # degree (event 가 얼마나 많은 엔티티와 연결되는가)
        deg = self.G.degree(event_node)
        # recency decay
        ts: datetime = attrs["ts"]
        days = max(0.0, (cutoff_ts - ts).total_seconds() / 86400.0)
        recency = math.exp(-days / self.recency_tau_days)
        # persona issue relevance
        relevance = 1.0 + self._persona_issue_relevance(persona_blob, event_node)
        # subtype prior — 스캔들/평결은 voter에게 더 두드러짐
        prior = {
            "ScandalEvent": 1.4,
            "Verdict": 1.3,
            "Investigation": 1.2,
            "PressConference": 1.0,
            "PollPublication": 0.9,
            "MediaEvent": 1.0,
        }.get(attrs.get("type", "MediaEvent"), 1.0)
        return float(deg) * recency * relevance * prior

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def cutoff_for(self, region_id: str, t: int) -> Optional[datetime]:
        meta = self.index.by_region.get(region_id)
        if meta is None:
            return None
        return meta.t_to_realtime(t)

    # ------------------------------------------------------------------
    # P0/P1 enrichment helpers (P1) — surface candidate profile +
    # region context that scenario JSON already carries but voter prompt
    # was previously missing.
    # ------------------------------------------------------------------
    def _candidate_profile_block(
        self, region_id: str, max_bg_chars: int = 160, max_pledges: int = 3
    ) -> str:
        """`[후보 프로필]` block — bullet per (non-withdrawn) candidate with
        `background` + top-N `key_pledges`. Time-invariant data, so no
        firewall filter is needed.
        """
        contest_id = self.index.contest_for_region.get(region_id)
        if not contest_id:
            return ""
        lines: list[str] = []
        for cid in self.index.candidates_in_contest.get(contest_id, []):
            attrs = self.G.nodes.get(nid("Candidate", cid)) or {}
            if attrs.get("withdrawn"):
                continue
            name = attrs.get("name", cid)
            party_label = attrs.get("party_name") or attrs.get("party") or ""
            head = f"- {name} ({party_label})" if party_label else f"- {name}"
            bg = (attrs.get("background") or "").strip()
            pledges = [
                str(p).strip() for p in (attrs.get("key_pledges") or [])
                if str(p).strip()
            ][:max_pledges]
            parts = [head]
            if bg:
                parts.append(f": {bg[:max_bg_chars]}")
            if pledges:
                parts.append(" / 핵심공약: " + ", ".join(pledges))
            lines.append("".join(parts))
        if not lines:
            return ""
        return "[후보 프로필]\n" + "\n".join(lines)

    # ------------------------------------------------------------------
    # Track B (P1) — CohortPrior lookup. Voters have age + sex; this
    # returns the most-specific Korean polling cohort prior so the LLM grounds
    # its prior in real Korean party-lean cross-tab data (not American
    # "younger=progressive" defaults).
    # ------------------------------------------------------------------
    @staticmethod
    def _age_to_band(age: Any) -> str:
        try:
            a = int(age)
        except (TypeError, ValueError):
            return "ALL"
        if a < 18:
            return "ALL"
        if a < 30:
            return "18-29"
        if a < 40:
            return "30-39"
        if a < 50:
            return "40-49"
        if a < 60:
            return "50-59"
        if a < 70:
            return "60-69"
        return "70+"

    @staticmethod
    def _norm_gender(g: Any) -> str:
        if not isinstance(g, str):
            return "ALL"
        gl = g.strip().lower()
        if gl in ("m", "male", "남", "남성"):
            return "M"
        if gl in ("f", "female", "여", "여성"):
            return "F"
        return "ALL"

    def get_cohort_prior(
        self,
        age: Any = None,
        gender: Any = None,
        region_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Resolve the most-specific CohortPrior matching (age, gender, region).

        Resolution order (most → least specific):
          1. region + age_band + gender
          2. region + ALL + ALL  (region baseline)
          3. national + age_band + gender
          4. national + age_band + ALL
          5. national + ALL + ALL  (last resort)

        Returns the prior dict (party_lean + source_url + ...) or None.
        """
        age_band = self._age_to_band(age)
        gn = self._norm_gender(gender)

        candidates: list[tuple[int, dict[str, Any]]] = []
        for n, attrs in self.G.nodes(data=True):
            if attrs.get("type") != "CohortPrior":
                continue
            score = 0
            ab = attrs.get("age_band") or "ALL"
            ag = attrs.get("gender") or "ALL"
            r = attrs.get("region_id")
            scope = attrs.get("scope") or "national"
            if r and region_id and r == region_id:
                score += 100
            elif scope == "region" and region_id and r == region_id:
                score += 100
            elif scope == "national":
                score += 10
            else:
                continue  # mismatched region-specific prior
            if ab == age_band:
                score += 30
            elif ab == "ALL":
                score += 5
            else:
                continue  # mismatched age band
            if ag == gn:
                score += 20
            elif ag == "ALL":
                score += 3
            else:
                continue  # mismatched gender
            # snapshot-friendly dict
            candidates.append((score, dict(attrs)))

        if not candidates:
            return None
        candidates.sort(key=lambda x: -x[0])
        prior = candidates[0][1]
        # sim-engineer interop (P1): augment with `block_text` /
        # `cohort_label` / `source` / `n_polls` so `ElectionEnv._render_cohort_prior`
        # picks up our pre-rendered block via its duck-typed fallback path.
        try:
            prior = dict(prior)
            prior.setdefault("block_text", self.cohort_prior_block(
                age=age, gender=gender, region_id=region_id,
            ))
            ab = prior.get("age_band") or "ALL"
            gn = prior.get("gender") or "ALL"
            gn_disp = {"M": "남성", "F": "여성", "ALL": "전체"}.get(gn, "전체")
            ab_disp = ab if ab != "ALL" else "전체 연령"
            scope_disp = prior.get("region_id") or "전국"
            prior.setdefault("cohort_label", f"{ab_disp} {gn_disp}, {scope_disp}")
            if not prior.get("source"):
                prior["source"] = prior.get("source_url") or ""
            prior["n_polls"] = int(prior.get("n_polls", 0) or 0)
        except Exception:
            pass
        return prior

    def cohort_prior_block(
        self,
        age: Any = None,
        gender: Any = None,
        region_id: Optional[str] = None,
    ) -> str:
        """Render a `[코호트 사전 정보]` block ready for voter prompt injection.

        Surfaces TWO priors when both are available:
          1. National age × gender prior (e.g. "20대 남성") — captures the
             well-known Korean cross-tab patterns the LLM otherwise misses.
          2. Regional baseline (e.g. "부산/울산/경남 전체") — adapts the prior
             to the contest's geography.

        Returns "" if neither prior matches.
        """
        # 1) Region baseline — drop region constraint to ensure national branch
        #    if no regional prior exists.
        regional = self.get_cohort_prior(age=None, gender=None, region_id=region_id) if region_id else None
        # 2) National age × gender — force national scope by passing region=None.
        national = self._lookup_national_age_gender(age, gender)

        # Drop duplicates (e.g. region baseline ≈ national fallback).
        seen_ids: set[str] = set()
        chunks: list[str] = []
        for label, prior in (("국가 (연령·성별)", national), ("지역 평균", regional)):
            if not prior:
                continue
            pid = prior.get("cohort_id")
            if pid in seen_ids:
                continue
            seen_ids.add(pid)
            chunks.append(self._fmt_prior_line(label, prior))

        if not chunks:
            return ""
        return "[코호트 사전 정보]\n" + "\n".join(chunks)

    def _lookup_national_age_gender(
        self, age: Any, gender: Any
    ) -> Optional[dict[str, Any]]:
        """National-scope cohort matching (age_band × gender). Falls back to
        age_band × ALL, then ALL × ALL."""
        age_band = self._age_to_band(age)
        gn = self._norm_gender(gender)
        candidates: list[tuple[int, dict[str, Any]]] = []
        for n, attrs in self.G.nodes(data=True):
            if attrs.get("type") != "CohortPrior":
                continue
            if (attrs.get("scope") or "national") != "national":
                continue
            ab = attrs.get("age_band") or "ALL"
            ag = attrs.get("gender") or "ALL"
            score = 10
            if ab == age_band:
                score += 30
            elif ab == "ALL":
                score += 5
            else:
                continue
            if ag == gn:
                score += 20
            elif ag == "ALL":
                score += 3
            else:
                continue
            candidates.append((score, dict(attrs)))
        if not candidates:
            return None
        candidates.sort(key=lambda x: -x[0])
        return candidates[0][1]

    @staticmethod
    def _fmt_prior_line(label: str, prior: dict[str, Any]) -> str:
        pl = prior.get("party_lean") or {}
        ppp = pl.get("ppp", 0.0)
        dpk = pl.get("dpk", 0.0)
        rebuild = pl.get("rebuild", 0.0)
        und = pl.get("undecided", 0.0)
        ab = prior.get("age_band") or "ALL"
        gn = prior.get("gender") or "ALL"
        gn_disp = {"M": "남성", "F": "여성", "ALL": "전체"}.get(gn, "전체")
        ab_disp = ab if ab != "ALL" else "전체 연령"
        src = (prior.get("source") or "")[:80]
        notes = (prior.get("notes") or "").strip()
        head = f"- [{label}] {ab_disp} {gn_disp}: 더민주 {dpk*100:.0f}% / 국힘 {ppp*100:.0f}% / 개혁 {rebuild*100:.0f}% / 무당 {und*100:.0f}%"
        if src:
            head += f" (출처: {src})"
        if notes:
            head += f"\n   ※ {notes[:140]}"
        return head

    # ------------------------------------------------------------------
    # Public helpers — sim-engineer can pull candidate-profile lines and
    # inject them directly into the high-salience `[후보]` section of the
    # voter prompt (v2.2 ablation: KG profile + `[후보]` placement). This is
    # the same source-of-truth as the `[후보 프로필]` block embedded in
    # ``context_text`` — choosing one over the other avoids double-injection.
    # ------------------------------------------------------------------
    def candidate_profile_lines(
        self,
        region_id: str,
        *,
        max_bg_chars: int = 160,
        max_pledges: int = 3,
        include_withdrawn: bool = False,
    ) -> list[dict[str, Any]]:
        """Per-candidate profile dicts for the contest in ``region_id``.

        Each dict carries ``candidate_id``, ``name``, ``party_id``,
        ``party_name``, ``background`` (trimmed), ``key_pledges`` (trimmed
        list), and a pre-rendered ``line`` string ready for direct injection
        into the voter prompt's ``[후보]`` section. Time-invariant — no
        firewall filter needed.
        """
        contest_id = self.index.contest_for_region.get(region_id)
        if not contest_id:
            return []
        out: list[dict[str, Any]] = []
        for cid in self.index.candidates_in_contest.get(contest_id, []):
            attrs = self.G.nodes.get(nid("Candidate", cid)) or {}
            if attrs.get("withdrawn") and not include_withdrawn:
                continue
            name = attrs.get("name", cid)
            party_id = attrs.get("party") or ""
            party_label = attrs.get("party_name") or party_id
            bg = (attrs.get("background") or "").strip()
            if max_bg_chars and len(bg) > max_bg_chars:
                bg = bg[:max_bg_chars]
            pledges = [
                str(p).strip()
                for p in (attrs.get("key_pledges") or [])
                if str(p).strip()
            ][:max_pledges]
            head = f"- {cid} | {name} ({party_label})" if party_label else f"- {cid} | {name}"
            parts = [head]
            if bg:
                parts.append(f"\n    배경: {bg}")
            if pledges:
                parts.append("\n    핵심공약: " + " · ".join(pledges))
            out.append(
                {
                    "candidate_id": cid,
                    "name": name,
                    "party_id": party_id,
                    "party_name": party_label,
                    "background": bg,
                    "key_pledges": pledges,
                    "withdrawn": bool(attrs.get("withdrawn", False)),
                    "line": "".join(parts),
                }
            )
        return out

    def _region_notes_block(self, region_id: str, max_chars: int = 220) -> str:
        """`[지역 정세]` block — scenario_notes from District node."""
        attrs = self.G.nodes.get(nid("District", region_id)) or {}
        notes = (attrs.get("scenario_notes") or "").strip()
        if not notes:
            return ""
        if len(notes) > max_chars:
            notes = notes[: max_chars - 1] + "…"
        return "[지역 정세]\n" + notes

    def subgraph_at(
        self,
        persona: dict[str, Any],
        t: int,
        region_id: str,
        k: int = 5,
        *,
        include_candidate_profile: bool = True,
    ) -> RetrievalResult:
        """페르소나 + timestep t → 컨텍스트 블록.

        Returns:
            RetrievalResult — context_text 는 voter prompt 에 그대로 주입.
            firewall 보장: ``cutoff = meta.t_to_realtime(t)`` 이후 이벤트는 결과에 없음.

        P0/P1 enrichment (P1): context_text now starts with
        ``[후보 프로필]`` + ``[지역 정세]`` blocks (time-invariant, sourced from
        the human-curated scenario JSON), then the firewall-filtered event
        bullets. This breaks the "id | name (party_id)" minimalism that was
        causing voter LLMs to collapse into ideology stereotypes.

        Args:
            include_candidate_profile: When ``False``, omit ``[후보 프로필]``
                from ``context_text``. Useful when sim-engineer injects the
                same profile lines (via :meth:`candidate_profile_lines`) into
                the high-salience ``[후보]`` section of the voter prompt and
                wants to avoid double-injection.
        """
        meta: Optional[ScenarioMeta] = self.index.by_region.get(region_id)
        if meta is None:
            log.debug("[kg] no scenario meta for region %s", region_id)
            return RetrievalResult.empty()

        # P0/P1 blocks — independent of timestep / firewall.
        profile_block = (
            self._candidate_profile_block(region_id)
            if include_candidate_profile
            else ""
        )
        notes_block = self._region_notes_block(region_id)
        # Track B — cohort prior block (Korean party-lean by age × gender).
        cohort_block = self.cohort_prior_block(
            age=persona.get("age"),
            gender=persona.get("sex") or persona.get("gender"),
            region_id=region_id,
        )

        cutoff = meta.t_to_realtime(t)
        visible = self._events_visible_at(region_id, cutoff)
        if not visible:
            # Even with no visible events, profile + notes + cohort are useful.
            head_blocks = [b for b in (profile_block, notes_block, cohort_block) if b]
            if head_blocks:
                head_text = "\n\n".join(head_blocks)
                if len(head_text) > self.max_context_chars:
                    head_text = head_text[: self.max_context_chars - 1] + "…"
                return RetrievalResult(
                    context_text=head_text,
                    events_used=[],
                    triples=[],
                    cutoff_ts=cutoff,
                )
            return RetrievalResult.empty(cutoff)

        persona_blob = self._persona_text_blob(persona)

        scored: list[tuple[float, str, dict[str, Any]]] = []
        for n, attrs in visible:
            s = self._score(n, attrs, persona_blob, cutoff)
            scored.append((s, n, attrs))
        scored.sort(key=lambda x: -x[0])
        top = scored[: max(1, int(k))]

        retrieved: list[RetrievedEvent] = []
        triples: list[tuple[str, str, str]] = []
        lines: list[str] = []

        for score, n, attrs in top:
            ev_type = attrs.get("type", "MediaEvent")
            ts: datetime = attrs["ts"]
            title = attrs.get("title") or attrs.get("label") or n
            sentiment = float(attrs.get("sentiment", 0.0))
            frame_id = attrs.get("frame_id")
            frame_label = None
            if frame_id:
                f_attrs = self.G.nodes.get(nid("NarrativeFrame", frame_id), {})
                frame_label = f_attrs.get("label", frame_id)

            # primary target (about edge)
            target_id: Optional[str] = None
            target_label: Optional[str] = None
            for _, dst, key in self.G.out_edges(n, keys=True):
                if key != "about":
                    continue
                t_attrs = self.G.nodes.get(dst, {})
                if t_attrs.get("type") in ("Candidate", "Party"):
                    target_id = t_attrs.get("candidate_id") or t_attrs.get("party_id")
                    target_label = t_attrs.get("name", target_id)
                    triples.append((n, "about", dst))
                    break
            for _, dst, key in self.G.out_edges(n, keys=True):
                if key in ("mentions", "framedBy"):
                    triples.append((n, key, dst))

            retrieved.append(
                RetrievedEvent(
                    event_id=attrs.get("event_id", n),
                    type=ev_type,
                    ts=ts,
                    title=title,
                    sentiment=sentiment,
                    frame=frame_label,
                    target=target_id,
                    score=score,
                )
            )

            # bullet line — 한국어 voter prompt에 자연스러운 형식
            sentiment_tag = (
                "긍정" if sentiment > 0.15
                else "부정" if sentiment < -0.15
                else "중립"
            )
            target_str = f" / 대상: {target_label}" if target_label else ""
            frame_str = f" / 프레임: {frame_label}" if frame_label else ""
            lines.append(
                f"- [{ts.strftime('%Y-%m-%d')}] ({ev_type}) {title}"
                f" — 정서:{sentiment_tag}({sentiment:+.2f}){target_str}{frame_str}"
            )

        events_text = "\n".join(lines)
        # P0/P1 enrichment: profile + notes header before firewall events.
        # Track B: cohort prior block right after profile so the LLM sees
        # demographic baseline before specific events.
        events_block = ("[주요 이벤트]\n" + events_text) if events_text else ""
        all_blocks = [b for b in (profile_block, cohort_block, notes_block, events_block) if b]
        text = "\n\n".join(all_blocks)
        if len(text) > self.max_context_chars:
            text = text[: self.max_context_chars - 1] + "…"

        return RetrievalResult(
            context_text=text,
            events_used=[ev.to_kg_event(t) for ev in retrieved],
            triples=triples,
            cutoff_ts=cutoff,
        )

    # ------------------------------------------------------------------
    # Convenience: stable triple iteration (for debugging / dashboards)
    # ------------------------------------------------------------------
    def iter_triples(self) -> Iterable[tuple[str, str, str]]:
        for u, v, k in self.G.edges(keys=True):
            yield (u, k, v)

    # ------------------------------------------------------------------
    # Aggregate events visible across an entire run (sim-engineer 사용)
    # ------------------------------------------------------------------
    def events_used_summary(
        self, region_id: str, until_t: int
    ) -> list[dict[str, Any]]:
        """region_id 의 timestep 0..until_t 범위에서 firewall-visible 이벤트
        union (event_id 로 dedupe). ``result_schema.kg_events_used`` 의 직접
        source 로 사용 가능.

        timestep 필드는 처음 노출된 timestep 으로 기록.
        """
        meta: Optional[ScenarioMeta] = self.index.by_region.get(region_id)
        if meta is None:
            return []

        seen: dict[str, dict[str, Any]] = {}
        until = max(0, min(int(until_t), meta.timesteps - 1))
        for t in range(until + 1):
            cutoff = meta.t_to_realtime(t)
            for n, attrs in self._events_visible_at(region_id, cutoff):
                eid = attrs.get("event_id") or n
                if eid in seen:
                    continue
                # primary target via about edge (best-effort)
                target = ""
                for _, dst, key in self.G.out_edges(n, keys=True):
                    if key != "about":
                        continue
                    t_attrs = self.G.nodes.get(dst, {})
                    target = (
                        t_attrs.get("candidate_id")
                        or t_attrs.get("party_id")
                        or t_attrs.get("name")
                        or dst
                    )
                    break
                seen[eid] = {
                    "event_id": eid,
                    "type": attrs.get("type", "MediaEvent"),
                    "target": target,
                    "timestep": t,
                }
        # stable order: first-seen timestep, then event_id
        return sorted(seen.values(), key=lambda d: (d["timestep"], d["event_id"]))


# ---------------------------------------------------------------------------
# Stub — degraded mode (KG 빌드 실패 시 sim-engineer 가 사용)
# ---------------------------------------------------------------------------
class StubRetriever:
    """KG 빌드 실패 시 fallback. 항상 빈 컨텍스트 반환."""

    def subgraph_at(
        self,
        persona: dict[str, Any],
        t: int,
        region_id: str,
        k: int = 5,
    ) -> RetrievalResult:
        return RetrievalResult.empty()

    def cutoff_for(self, region_id: str, t: int) -> Optional[datetime]:
        return None


# ---------------------------------------------------------------------------
# Phase 3 (#59) — opt-in factory honouring POLITIKAST_KG_USE_STAGING
# ---------------------------------------------------------------------------
def _staging_enabled() -> bool:
    import os
    return os.environ.get("POLITIKAST_KG_USE_STAGING", "0").lower() in (
        "1", "true", "yes",
    )


# ---------------------------------------------------------------------------
# Phase 4 (#78) — Cypher equivalents for retriever's hot-path queries.
# These return strings + parameter dicts so they can be issued against
# Neo4j by ``backend.app.services.kg_service`` while the in-process
# networkx implementation continues to satisfy the simulation hot-path.
# ---------------------------------------------------------------------------
def subgraph_at_cypher(region_id: str, cutoff: datetime, k: int = 5) -> tuple[str, dict[str, Any]]:
    """Return ``(query, params)`` for a Neo4j-backed equivalent of
    :py:meth:`KGRetriever.subgraph_at` event scoring.

    The query emits the top-``k`` event nodes attached to ``region_id`` whose
    ``ts <= cutoff``, ordered by ``ts`` desc as a recency proxy. Persona
    relevance scoring stays in-process (executor-side) — Cypher returns the
    candidate set, the consumer ranks.
    """
    query = (
        "MATCH (n) "
        "WHERE n.region_id = $region_id "
        "  AND n.ts IS NOT NULL "
        "  AND n.ts <= $cutoff "
        "  AND any(l IN labels(n) WHERE l IN $event_labels) "
        "RETURN n.node_id AS node_id, labels(n) AS labels, "
        "       n.event_id AS event_id, n.ts AS ts, "
        "       n.title AS title, n.sentiment AS sentiment, "
        "       n.frame_id AS frame_id "
        "ORDER BY n.ts DESC "
        "LIMIT $k"
    )
    from src.kg.ontology import EVENT_NODE_TYPES
    params: dict[str, Any] = {
        "region_id": region_id,
        "cutoff": cutoff.isoformat(),
        "event_labels": sorted(EVENT_NODE_TYPES),
        "k": int(k),
    }
    return query, params


def get_cohort_prior_cypher(
    region_id: Optional[str], age_band: str, gender: str,
) -> tuple[str, dict[str, Any]]:
    """Cypher for :py:meth:`KGRetriever.get_cohort_prior` resolution. Returns
    the most-specific ``CohortPrior`` for ``(region_id, age_band, gender)``
    with the same scoring rule as the in-process implementation."""
    query = (
        "MATCH (n:CohortPrior) "
        "WHERE n.region_id = $region_id OR n.scope = 'national' "
        "WITH n, "
        "  ((CASE WHEN n.region_id = $region_id THEN 100 ELSE 0 END) "
        " + (CASE WHEN coalesce(n.scope,'national') = 'national' THEN 10 ELSE 0 END) "
        " + (CASE WHEN n.age_band = $age_band THEN 30 "
        "         WHEN n.age_band = 'ALL' THEN 5 ELSE -100 END) "
        " + (CASE WHEN n.gender = $gender THEN 20 "
        "         WHEN n.gender = 'ALL' THEN 3 ELSE -100 END)) AS score "
        "WHERE score > 0 "
        "RETURN n LIMIT 1"
    )
    return query, {
        "region_id": region_id,
        "age_band": age_band,
        "gender": gender,
    }


def events_used_summary_cypher(region_id: str, cutoff: datetime) -> tuple[str, dict[str, Any]]:
    """Cypher version of :py:meth:`KGRetriever.events_used_summary` (used by
    snapshot serialisation in the FastAPI scenario route)."""
    from src.kg.ontology import EVENT_NODE_TYPES
    query = (
        "MATCH (n) "
        "WHERE n.region_id = $region_id "
        "  AND any(l IN labels(n) WHERE l IN $event_labels) "
        "  AND n.ts IS NOT NULL AND n.ts <= $cutoff "
        "OPTIONAL MATCH (n)-[:about]->(t) "
        "RETURN n.event_id AS event_id, n.type AS type, "
        "       coalesce(t.candidate_id, t.party_id, t.name, '') AS target "
        "ORDER BY n.ts"
    )
    return query, {
        "region_id": region_id,
        "cutoff": cutoff.isoformat(),
        "event_labels": sorted(EVENT_NODE_TYPES),
    }


def make_retriever(
    *,
    db_path: Any = None,
    region_id: Optional[str] = None,
    **kwargs: Any,
) -> "KGRetriever":
    """Construct a :class:`KGRetriever` honoring the staging opt-in flag.

    Default (``POLITIKAST_KG_USE_STAGING`` unset / ``0``): identical to
    Phase 2 — only ``build_kg_from_scenarios`` is used. Setting the variable
    to ``1`` switches to :func:`src.kg.builder.build_with_staging`, which
    layers ``stg_kg_triple`` rows on top of the curated scenario KG (with
    scenario > staging precedence).

    Phase 3 contract: when staging is enabled but the DB / table is absent,
    this remains a no-op — sim-engineer's existing path stays green.
    """
    if _staging_enabled():
        from src.kg.builder import build_with_staging
        G, index = build_with_staging(db_path=db_path, region_id=region_id)
    else:
        from src.kg.builder import build_kg_from_scenarios
        G, index = build_kg_from_scenarios()
    return KGRetriever(G, index, **kwargs)
