"""Hill-climbing harness — R0 baseline + R1 4-variant prompt enrichment.

Run::

    docker compose run --rm \
      -e POLITIKAST_ENV=dev \
      app python -m _workspace.research.hill_climbing.run_round \
        --personas-path <personas_json_path> \
        --variants R0,v1,v2,v4,v5 \
        --out-dir _workspace/snapshots/hill_climbing

Each variant uses VoterAgent.vote() with prompt monkey-patches; a single asyncio
.gather batch fires all variants × all personas. Result per variant:

    {
      "variant": "v4",
      "n_personas": 10,
      "votes": [{"persona_id":..., "vote":..., "reason":...}, ...],
      "vote_count": {"c_seoul_dpk": x, "c_seoul_ppp": y, ...},
      "renorm_share": {"c_seoul_dpk": 0.x, "c_seoul_ppp": 0.y},
      "official_consensus": {"c_seoul_dpk": 0.5702, "c_seoul_ppp": 0.4298},
      "metrics": {"mae": ..., "rmse": ..., "leader_match": ..., "kl_div": ...},
      "system_prompt_sample": str (first persona),
      "user_prompt_sample": str (first persona)
    }

R1_summary.md aggregates the 5 variants into a comparison table.

This module assumes data-engineer has written a JSON file with 10 personas
(format: list of dicts with persona_core fields + persona_text fields nested or
flat). The harness is tolerant — falls back to DuckDB sample if the file is
missing.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import logging
import math
import os
import sys
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from src.sim.voter_agent import VoterAgent, build_default_backend  # noqa: E402

logger = logging.getLogger(__name__)

SEOUL_SCENARIO = REPO / "_workspace" / "data" / "scenarios" / "seoul_mayor.json"
DUCKDB_PATH = REPO / "_workspace" / "db" / "politikast.duckdb"

# NESDC consensus target — fetched from poll_consensus_daily where
# region_id='seoul_mayor' and as_of_date <= cutoff. Values from V8c:
DEFAULT_OFFICIAL_CONSENSUS: dict[str, float] = {
    "c_seoul_dpk": 0.5702,
    "c_seoul_ppp": 0.4298,
}
# Raw NESDC consensus (data-engineer canonical) keyed by candidate_id, p_hat
# preserved (sum < 1.0 = NESDC undecided/unmapped slack). Set from persona file
# at runtime via load_personas_and_truth(); fallback values are seoul-specific.
OFFICIAL_CONSENSUS_RAW: dict[str, float] = {
    "c_seoul_dpk": 0.4723,
    "c_seoul_ppp": 0.3560,
}


# ============================================================================
# Persona loading
# ============================================================================
def load_personas_and_truth(
    path: str | None, n: int = 10
) -> tuple[list[dict[str, Any]], dict[str, float] | None, str | None]:
    """Return (personas, official_consensus_renorm or None, region_id or None).

    Persona file format (data-engineer canonical, 2026-04-26):
      {
        "region_id": "...",
        "ground_truth": {
          "consensus_renorm_intersection": [
            {"candidate_id": "...", "p_hat_renorm": 0.5702}, ...
          ]
        },
        "personas": [<persona dicts>]
      }

    Falls back to DuckDB reservoir sample (region=seoul_mayor) if no file.
    """
    if path:
        p = Path(path)
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            consensus: dict[str, float] | None = None
            region_id: str | None = None
            if isinstance(data, dict):
                personas = data.get("personas") or []
                region_id = data.get("region_id")
                gt = data.get("ground_truth") or {}
                renorm = gt.get("consensus_renorm_intersection")
                if isinstance(renorm, list):
                    consensus = {
                        str(r["candidate_id"]): float(r["p_hat_renorm"])
                        for r in renorm
                        if "candidate_id" in r and "p_hat_renorm" in r
                    }
                # Capture raw too — v4 prompt uses raw with undecided slack.
                raw = gt.get("consensus_raw")
                if isinstance(raw, list):
                    global OFFICIAL_CONSENSUS_RAW
                    OFFICIAL_CONSENSUS_RAW = {
                        str(r["candidate_id"]): float(r["p_hat"])
                        for r in raw
                        if "candidate_id" in r and "p_hat" in r
                    }
            elif isinstance(data, list):
                personas = data
            else:
                raise ValueError(f"unexpected personas format in {p}")
            if len(personas) > n:
                personas = personas[:n]
            return [_normalize_persona(p) for p in personas], consensus, region_id
        logger.warning("personas-path %s not found — fallback to DuckDB sample.", path)


def load_personas(path: str | None, n: int = 10) -> list[dict[str, Any]]:
    """Backwards-compat wrapper — drops ground_truth + region_id."""
    if path:
        out = load_personas_and_truth(path, n)
        if out is not None:
            return out[0]

    # DuckDB fallback
    import duckdb  # type: ignore
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    try:
        cols = [
            d[0]
            for d in con.execute(
                "select * from personas_seoul_mayor limit 0"
            ).description
        ]
        rows = con.execute(
            f"select * from personas_seoul_mayor using sample {n} rows (reservoir, 13)"
        ).fetchall()
        text_cols = [
            d[0] for d in con.execute("select * from persona_text limit 0").description
        ]
        out = []
        for r in rows:
            d = dict(zip(cols, r))
            uuid = d.get("uuid")
            text_row = con.execute(
                "select * from persona_text where uuid = ?", [uuid]
            ).fetchone()
            persona_text = (
                dict(zip(text_cols, text_row)) if text_row else {}
            )
            d["persona_text"] = persona_text
            out.append(_normalize_persona(d))
        return out
    finally:
        con.close()


def _normalize_persona(p: dict[str, Any]) -> dict[str, Any]:
    """Split flat persona row into (persona_core, persona_text) dicts.

    Returns: {**persona_core_fields, "persona_text": {**text_fields}}
    """
    text_keys = (
        "persona",
        "professional_persona",
        "family_persona",
        "cultural_background",
        "sports_persona",
        "arts_persona",
        "travel_persona",
        "culinary_persona",
    )
    pt = p.get("persona_text") if isinstance(p.get("persona_text"), dict) else {}
    if not pt:
        pt = {k: p[k] for k in text_keys if k in p and isinstance(p[k], str)}
    return {**p, "persona_text": pt}


# ============================================================================
# Prompt variants
# ============================================================================
def _scenario() -> dict[str, Any]:
    with SEOUL_SCENARIO.open("r", encoding="utf-8") as f:
        return json.load(f)


def _candidate_lines_baseline(candidates: list[dict[str, Any]]) -> str:
    lines = []
    for c in candidates:
        tag = "[출마 포기] " if c.get("withdrawn") else ""
        lines.append(
            f"- {tag}{c['id']} | {c.get('name', c['id'])} ({c.get('party', '무소속')})"
        )
    return "\n".join(lines)


def _candidate_lines_with_policy(
    candidates: list[dict[str, Any]], scenario: dict[str, Any]
) -> str:
    """v2 — inject background + key_pledges from scenario JSON."""
    raw = {c.get("id"): c for c in scenario.get("candidates", [])}
    lines = []
    for c in candidates:
        cid = c["id"]
        bg = raw.get(cid, {})
        tag = "[출마 포기] " if c.get("withdrawn") else ""
        pledges = bg.get("key_pledges", [])
        bg_short = (bg.get("background") or "").strip()
        # Truncate background to keep prompts compact
        if len(bg_short) > 120:
            bg_short = bg_short[:120] + "…"
        pledge_str = " · ".join(pledges) if pledges else "공약 정보 없음"
        lines.append(
            f"- {tag}{cid} | {c.get('name', cid)} ({c.get('party', '무소속')})"
            f"\n    배경: {bg_short or '정보 없음'}"
            f"\n    핵심공약: {pledge_str}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Variant prompt builders
# ---------------------------------------------------------------------------
class _PromptVariant:
    name: str = "R0"

    def __init__(self, scenario: dict[str, Any]):
        self.scenario = scenario
        self.candidates = scenario["candidates"]

    def system_prompt(self, agent: VoterAgent) -> str:
        # Use the agent's default
        return agent.system_prompt()

    def user_prompt(self, agent: VoterAgent, t: int) -> str:
        return agent.user_prompt(self.candidates, "(추가 정보 없음)", t, "secret_ballot")


class _R0Baseline(_PromptVariant):
    name = "R0"


class _V1NoRule1(_PromptVariant):
    """Drop Rule 1 ('use only provided context') from system prompt."""
    name = "v1_no_rule1"

    def system_prompt(self, agent: VoterAgent) -> str:
        sp = agent.system_prompt()
        # Remove the Rule 1 line and renumber
        return sp.replace(
            "1. 제공된 컨텍스트(이슈·여론조사·이벤트) 외 정보를 사용하지 마세요.\n"
            "2. 출마를 포기한 후보는 선택할 수 없습니다.\n"
            "3. 미래 결과를 안다고 가정하지 마세요. 페르소나의 가치관·관심사로만 추론하세요.\n"
            "4. 반드시 단일 JSON 객체로만 응답합니다",
            "1. 출마를 포기한 후보는 선택할 수 없습니다.\n"
            "2. 미래 결과(예: 선거 결과)를 안다고 가정하지 마세요. 다만 정당 강령·후보 이력·지역 성향 등 일반 정치 상식은 자유롭게 활용하세요.\n"
            "3. 반드시 단일 JSON 객체로만 응답합니다",
        )


class _V2CandidatePolicy(_PromptVariant):
    """Inject candidate background + key_pledges into user_prompt."""
    name = "v2_candidate_policy"

    def user_prompt(self, agent: VoterAgent, t: int) -> str:
        cand_block = _candidate_lines_with_policy(self.candidates, self.scenario)
        mode_text = (
            "지금은 투표소 안입니다. 비공개 투표용지에 단 한 명을 기표하세요. "
            "reason은 한 줄로 짧게."
        )
        return (
            f"=== {agent.region_label} (timestep t={t}) ===\n"
            f"[모드] secret_ballot\n{mode_text}\n\n"
            f"[후보]\n{cand_block}\n\n"
            f"[컨텍스트 (t≤{t})]\n(추가 정보 없음)\n"
        )


def _render_nesdc_block(scenario: dict[str, Any]) -> str:
    """Render NESDC consensus snippet from OFFICIAL_CONSENSUS_RAW + scenario
    candidate names. Region-agnostic — driven entirely by data-engineer's
    persona file `ground_truth.consensus_raw`.
    """
    id_to_name = {c["id"]: c.get("name", c["id"]) for c in scenario["candidates"]}
    parts: list[str] = []
    total = 0.0
    for cid, p in OFFICIAL_CONSENSUS_RAW.items():
        name = id_to_name.get(cid, cid)
        parts.append(f"{name} {p*100:.0f}%")
        total += p
    if total < 1.0:
        slack = 1.0 - total
        parts.append(f"미정·모름·기타 {slack*100:.0f}%")
    return (
        "[참고 NESDC 등록 여론조사 (DuckDB poll_consensus_daily, weighted_v1)]\n"
        f"- {' / '.join(parts)}\n"
        "  (이는 컷오프 시점 등록 여론조사 합의이며 미래 결과가 아닙니다.)"
    )


class _V4NESDCInject(_PromptVariant):
    """Inject NESDC latest poll consensus as a calibration anchor."""
    name = "v4_nesdc_inject"

    def user_prompt(self, agent: VoterAgent, t: int) -> str:
        cand_block = _candidate_lines_baseline(self.candidates)
        nesdc = _render_nesdc_block(self.scenario)
        mode_text = (
            "지금은 투표소 안입니다. 비공개 투표용지에 단 한 명을 기표하세요. "
            "reason은 한 줄로 짧게."
        )
        return (
            f"=== {agent.region_label} (timestep t={t}) ===\n"
            f"[모드] secret_ballot\n{mode_text}\n\n"
            f"[후보]\n{cand_block}\n\n"
            f"[컨텍스트 (t≤{t})]\n{nesdc}\n"
        )


class _V5CoT(_PromptVariant):
    """Add a chain-of-thought instruction to system prompt."""
    name = "v5_cot"

    def system_prompt(self, agent: VoterAgent) -> str:
        sp = agent.system_prompt()
        return sp + (
            "\n5. 투표 결정 전 먼저 페르소나에게 가장 중요한 3가지 이슈를 떠올리고, "
            "각 후보가 해당 이슈에 어떤 입장일지 스스로 추론한 뒤 투표하세요. "
            "JSON에 reasoning_steps 필드(문자열 배열, 최대 3개)를 추가해도 좋습니다."
        )


class _V4V2(_V4NESDCInject):
    """R2: v4 (NESDC inject) + v2 (candidate policy)."""
    name = "v4_v2_nesdc_plus_policy"

    def user_prompt(self, agent: VoterAgent, t: int) -> str:
        cand_block = _candidate_lines_with_policy(self.candidates, self.scenario)
        nesdc = _render_nesdc_block(self.scenario)
        mode_text = (
            "지금은 투표소 안입니다. 비공개 투표용지에 단 한 명을 기표하세요. "
            "reason은 한 줄로 짧게."
        )
        return (
            f"=== {agent.region_label} (timestep t={t}) ===\n"
            f"[모드] secret_ballot\n{mode_text}\n\n"
            f"[후보]\n{cand_block}\n\n"
            f"[컨텍스트 (t≤{t})]\n{nesdc}\n"
        )


class _V4V5(_V4NESDCInject):
    """R2: v4 (NESDC inject) + v5 (CoT)."""
    name = "v4_v5_nesdc_plus_cot"

    def system_prompt(self, agent: VoterAgent) -> str:
        sp = agent.system_prompt()
        return sp + (
            "\n5. 투표 결정 전 먼저 페르소나에게 가장 중요한 3가지 이슈를 떠올리고, "
            "각 후보가 해당 이슈에 어떤 입장일지 스스로 추론한 뒤 투표하세요. "
            "JSON에 reasoning_steps 필드(문자열 배열, 최대 3개)를 추가해도 좋습니다."
        )


class _V4V1(_V4NESDCInject):
    """R2: v4 (NESDC inject) + v1 (no rule1)."""
    name = "v4_v1_nesdc_plus_no_rule1"

    def system_prompt(self, agent: VoterAgent) -> str:
        sp = agent.system_prompt()
        return sp.replace(
            "1. 제공된 컨텍스트(이슈·여론조사·이벤트) 외 정보를 사용하지 마세요.\n"
            "2. 출마를 포기한 후보는 선택할 수 없습니다.\n"
            "3. 미래 결과를 안다고 가정하지 마세요. 페르소나의 가치관·관심사로만 추론하세요.\n"
            "4. 반드시 단일 JSON 객체로만 응답합니다",
            "1. 출마를 포기한 후보는 선택할 수 없습니다.\n"
            "2. 미래 결과(예: 선거 결과)를 안다고 가정하지 마세요. 다만 정당 강령·후보 이력·지역 성향 등 일반 정치 상식은 자유롭게 활용하세요.\n"
            "3. 반드시 단일 JSON 객체로만 응답합니다",
        )


class _V4AltFormat(_V4NESDCInject):
    """R2: NESDC info embedded in [컨텍스트] body as one of multiple bullets,
    not at the top of the [컨텍스트] block. Tests prompt-position salience.
    """
    name = "v4_alt_format"

    def user_prompt(self, agent: VoterAgent, t: int) -> str:
        cand_block = _candidate_lines_baseline(self.candidates)
        # Build a multi-bullet context with NESDC as 2nd of 2 bullets
        id_to_name = {c["id"]: c.get("name", c["id"]) for c in self.candidates}
        snippet_parts = []
        total = 0.0
        for cid, p in OFFICIAL_CONSENSUS_RAW.items():
            snippet_parts.append(f"{id_to_name.get(cid, cid)} {p*100:.0f}%")
            total += p
        if total < 1.0:
            snippet_parts.append(f"미정·기타 {(1.0-total)*100:.0f}%")
        ctx = (
            "- 본 선거는 4년 임기 지방선거입니다.\n"
            f"- 직전 등록 여론조사 평균: {' / '.join(snippet_parts)}.\n"
            "- 컷오프 시점까지 알려진 정보 외 추정은 자제하세요."
        )
        mode_text = (
            "지금은 투표소 안입니다. 비공개 투표용지에 단 한 명을 기표하세요. "
            "reason은 한 줄로 짧게."
        )
        return (
            f"=== {agent.region_label} (timestep t={t}) ===\n"
            f"[모드] secret_ballot\n{mode_text}\n\n"
            f"[후보]\n{cand_block}\n\n"
            f"[컨텍스트 (t≤{t})]\n{ctx}\n"
        )


# ---------------------------------------------------------------------------
# KG-enriched variants (kg-engineer P0+P1 — 2026-04-26 15:21)
# ---------------------------------------------------------------------------
_KG_RETRIEVER: Any | None = None


def _maybe_load_kg() -> Any | None:
    """Load KGRetriever once. Idempotent. Returns None if KG unavailable."""
    global _KG_RETRIEVER
    if _KG_RETRIEVER is not None:
        return _KG_RETRIEVER
    try:
        from src.kg.builder import build_kg_from_scenarios  # type: ignore
        from src.kg.retriever import KGRetriever  # type: ignore

        scenario_dir = REPO / "_workspace" / "data" / "scenarios"
        G, index = build_kg_from_scenarios(scenario_dir)
        _KG_RETRIEVER = KGRetriever(G, index)
        logger.info(
            "KG loaded for hill_climbing — nodes=%d", G.number_of_nodes()
        )
        return _KG_RETRIEVER
    except Exception as e:  # pragma: no cover
        logger.warning("KG unavailable for hill_climbing: %s", e)
        return None


class _V2_1KGEnriched(_PromptVariant):
    """v2.1 — KG-enriched context (kg-engineer P0+P1):
    [후보 프로필] + [지역 정세] + [주요 이벤트] from KGRetriever, replacing the
    R0 placeholder '(추가 정보 없음)'. Strictly architectural (no hardcoded
    scenario reads in voter_agent), uses the same code path that prod
    run_scenario.py uses.
    """
    name = "v2_1_kg_enriched"

    def user_prompt(self, agent: VoterAgent, t: int) -> str:
        cand_block = _candidate_lines_baseline(self.candidates)
        ctx = "(추가 정보 없음)"
        kg = _maybe_load_kg()
        region_id = self.scenario.get("region_id", "seoul_mayor")
        if kg is not None:
            try:
                res = kg.subgraph_at(
                    agent.persona, t, region_id=region_id, k=5
                )
                if getattr(res, "context_text", "").strip():
                    ctx = "[KG 컨텍스트]\n" + res.context_text.strip()
            except Exception as e:
                logger.debug("KG retrieval failed for %s: %s", agent.persona_id, e)
        mode_text = (
            "지금은 투표소 안입니다. 비공개 투표용지에 단 한 명을 기표하세요. "
            "reason은 한 줄로 짧게."
        )
        return (
            f"=== {agent.region_label} (timestep t={t}) ===\n"
            f"[모드] secret_ballot\n{mode_text}\n\n"
            f"[후보]\n{cand_block}\n\n"
            f"[컨텍스트 (t≤{t})]\n{ctx}\n"
        )


class _V2_2KGProfileHighSalience(_PromptVariant):
    """v2.2 — KG-derived candidate profile in [후보] section (high-salience
    position) + KG context_text without duplicate profile. Same content as
    v2.1 but in v2's salient position. Tests location vs content.

    Requires kg-engineer's `candidate_profile_lines(region_id)` API and
    `subgraph_at(..., include_candidate_profile=False)` flag.
    """
    name = "v2_2_kg_profile_high_salience"

    def _profile_block(self) -> str:
        kg = _maybe_load_kg()
        if kg is None or not hasattr(kg, "candidate_profile_lines"):
            return _candidate_lines_baseline(self.candidates)
        try:
            profiles = kg.candidate_profile_lines(
                self.scenario.get("region_id", "seoul_mayor")
            )
        except Exception as e:
            logger.debug("KG candidate_profile_lines failed: %s", e)
            return _candidate_lines_baseline(self.candidates)
        lines: list[str] = []
        for p in profiles:
            line_str = p.get("line") if isinstance(p, dict) else None
            if line_str:
                lines.append(line_str)
        return "\n".join(lines) or _candidate_lines_baseline(self.candidates)

    def _kg_context_no_profile(self, agent: VoterAgent, t: int) -> str:
        kg = _maybe_load_kg()
        if kg is None:
            return "(추가 정보 없음)"
        try:
            res = kg.subgraph_at(
                agent.persona,
                t,
                region_id=self.scenario.get("region_id", "seoul_mayor"),
                k=5,
                include_candidate_profile=False,
            )
        except TypeError:
            # older KG without the flag — fall back to full retrieval
            res = kg.subgraph_at(
                agent.persona,
                t,
                region_id=self.scenario.get("region_id", "seoul_mayor"),
                k=5,
            )
        text = getattr(res, "context_text", "") or ""
        return text.strip() or "(추가 정보 없음)"

    def user_prompt(self, agent: VoterAgent, t: int) -> str:
        cand_block = self._profile_block()
        ctx = self._kg_context_no_profile(agent, t)
        mode_text = (
            "지금은 투표소 안입니다. 비공개 투표용지에 단 한 명을 기표하세요. "
            "reason은 한 줄로 짧게."
        )
        return (
            f"=== {agent.region_label} (timestep t={t}) ===\n"
            f"[모드] secret_ballot\n{mode_text}\n\n"
            f"[후보]\n{cand_block}\n\n"
            f"[컨텍스트 (t≤{t})]\n{ctx}\n"
        )


class _V4V2_2(_V2_2KGProfileHighSalience, _V4NESDCInject):
    """v4 (NESDC inject) + v2.2 (KG profile in [후보] section + KG ctx without
    duplicate). Strongest stack with high-salience candidate placement.
    """
    name = "v4_v2_2_nesdc_plus_kg_profile_salient"

    def user_prompt(self, agent: VoterAgent, t: int) -> str:
        cand_block = self._profile_block()
        ctx_kg = self._kg_context_no_profile(agent, t)
        nesdc = _render_nesdc_block(self.scenario)
        mode_text = (
            "지금은 투표소 안입니다. 비공개 투표용지에 단 한 명을 기표하세요. "
            "reason은 한 줄로 짧게."
        )
        ctx_full = nesdc
        if ctx_kg and ctx_kg != "(추가 정보 없음)":
            ctx_full = f"{nesdc}\n\n[KG 컨텍스트]\n{ctx_kg}"
        return (
            f"=== {agent.region_label} (timestep t={t}) ===\n"
            f"[모드] secret_ballot\n{mode_text}\n\n"
            f"[후보]\n{cand_block}\n\n"
            f"[컨텍스트 (t≤{t})]\n{ctx_full}\n"
        )


class _V4V2_1(_V4NESDCInject):
    """v4 (NESDC inject) + v2.1 (KG-enriched context). Strongest combined
    architectural signal: real consensus anchor + real KG-derived context.
    """
    name = "v4_v2_1_nesdc_plus_kg"

    def user_prompt(self, agent: VoterAgent, t: int) -> str:
        cand_block = _candidate_lines_baseline(self.candidates)
        nesdc = _render_nesdc_block(self.scenario)
        kg = _maybe_load_kg()
        region_id = self.scenario.get("region_id", "seoul_mayor")
        kg_block = ""
        if kg is not None:
            try:
                res = kg.subgraph_at(
                    agent.persona, t, region_id=region_id, k=5
                )
                if getattr(res, "context_text", "").strip():
                    kg_block = "\n\n[KG 컨텍스트]\n" + res.context_text.strip()
            except Exception:
                pass
        mode_text = (
            "지금은 투표소 안입니다. 비공개 투표용지에 단 한 명을 기표하세요. "
            "reason은 한 줄로 짧게."
        )
        return (
            f"=== {agent.region_label} (timestep t={t}) ===\n"
            f"[모드] secret_ballot\n{mode_text}\n\n"
            f"[후보]\n{cand_block}\n\n"
            f"[컨텍스트 (t≤{t})]\n{nesdc}{kg_block}\n"
        )


VARIANT_REGISTRY: dict[str, type[_PromptVariant]] = {
    "R0": _R0Baseline,
    "v1": _V1NoRule1,
    "v2": _V2CandidatePolicy,
    "v4": _V4NESDCInject,
    "v5": _V5CoT,
    # R2 mutations:
    "v4_v2": _V4V2,
    "v4_v5": _V4V5,
    "v4_v1": _V4V1,
    "v4_alt": _V4AltFormat,
    # KG-enriched (kg-engineer P0+P1):
    "v2_1": _V2_1KGEnriched,
    "v4_v2_1": _V4V2_1,
    # KG profile in high-salience position (kg-engineer 2026-04-26 v2.2):
    "v2_2": _V2_2KGProfileHighSalience,
    "v4_v2_2": _V4V2_2,
}


# ---------------------------------------------------------------------------
# R5 region-local mutation — daegu_mayor (김부겸 비TK 정체성 강화)
# ---------------------------------------------------------------------------
# scenario.candidates의 background field가 김부겸의 outlier popularity (전
# 국무총리, 행정자치부 장관, 대구 비TK 정체성)를 명시 안 함 → lite-tier 모델이
# TK 지역 반사로 PPP_choo (현 PPP 원내대표) 선호. 이 mutation은 daegu_mayor
# 시나리오에 한해 김부겸 candidate에 추가 framing 라인을 inject.
class _V4V2DaeguLocal(_V4V2):
    name = "v4_v2_daegu_local"

    _DAEGU_OVERRIDE: dict[str, dict[str, Any]] = {
        "c_daegu_dpk": {
            "extra_lines": [
                "    추가 정보: 전 국무총리(2021~2022), 전 행정자치부 장관, "
                "대구 출신 비TK 정체성. 보수 색이 강한 TK 지역에서도 합리적 "
                "중도진보 정치인으로 폭넓게 평가받음. NESDC 등록 여론조사에서 "
                "큰 격차로 1위.",
            ],
        },
        "c_daegu_ppp_choo": {
            "extra_lines": [
                "    추가 정보: 현 국민의힘 원내대표. 보수 강세 TK에서 "
                "전통 조직 기반 강함.",
            ],
        },
    }

    def user_prompt(self, agent: VoterAgent, t: int) -> str:
        nesdc = _render_nesdc_block(self.scenario)
        # Build candidate block with locale-specific overrides applied AFTER
        # the standard hardcoded policy lines.
        raw_by_id = {c.get("id"): c for c in self.scenario.get("candidates", [])}
        lines: list[str] = []
        for c in self.candidates:
            cid = c["id"]
            tag = "[출마 포기] " if c.get("withdrawn") else ""
            party = c.get("party_name") or c.get("party", "무소속")
            lines.append(f"- {tag}{cid} | {c.get('name', cid)} ({party})")
            bg = (raw_by_id.get(cid, {}).get("background") or "").strip()
            if bg:
                if len(bg) > 160:
                    bg = bg[:160] + "…"
                lines.append(f"    배경: {bg}")
            pledges = raw_by_id.get(cid, {}).get("key_pledges") or []
            if pledges:
                lines.append(f"    핵심공약: {' · '.join(str(p) for p in pledges[:5])}")
            override = self._DAEGU_OVERRIDE.get(cid, {})
            for extra in override.get("extra_lines", []):
                lines.append(extra)
        cand_block = "\n".join(lines)
        mode_text = (
            "지금은 투표소 안입니다. 비공개 투표용지에 단 한 명을 기표하세요. "
            "reason은 한 줄로 짧게."
        )
        return (
            f"=== {agent.region_label} (timestep t={t}) ===\n"
            f"[모드] secret_ballot\n{mode_text}\n\n"
            f"[후보]\n{cand_block}\n\n"
            f"[컨텍스트 (t≤{t})]\n{nesdc}\n"
        )


VARIANT_REGISTRY["v4_v2_daegu_local"] = _V4V2DaeguLocal


class _V4V2KG(_V4V2):
    """v4_v2 + Track A KG event/notes block (no candidate profile from KG to
    avoid double-injection with hardcoded [후보] block).

    Use case: surface KG-derived context (Person/Source attribution, region
    political narrative) on top of the hill-climbing winner v4_v2 prompt.
    """
    name = "v4_v2_kg"

    def user_prompt(self, agent: VoterAgent, t: int) -> str:
        cand_block = _candidate_lines_with_policy(self.candidates, self.scenario)
        nesdc = _render_nesdc_block(self.scenario)
        kg = _maybe_load_kg()
        kg_block = ""
        region_id = self.scenario.get("region_id", "seoul_mayor")
        if kg is not None:
            try:
                res = kg.subgraph_at(
                    agent.persona,
                    t,
                    region_id=region_id,
                    k=5,
                    include_candidate_profile=False,
                )
            except TypeError:
                res = kg.subgraph_at(
                    agent.persona, t, region_id=region_id, k=5
                )
            text = (getattr(res, "context_text", "") or "").strip()
            if text:
                kg_block = "\n\n[KG 컨텍스트]\n" + text
        mode_text = (
            "지금은 투표소 안입니다. 비공개 투표용지에 단 한 명을 기표하세요. "
            "reason은 한 줄로 짧게."
        )
        return (
            f"=== {agent.region_label} (timestep t={t}) ===\n"
            f"[모드] secret_ballot\n{mode_text}\n\n"
            f"[후보]\n{cand_block}\n\n"
            f"[컨텍스트 (t≤{t})]\n{nesdc}{kg_block}\n"
        )


VARIANT_REGISTRY["v4_v2_kg"] = _V4V2KG


# ============================================================================
# Run a single variant on N personas
# ============================================================================
async def _run_variant(
    variant: _PromptVariant,
    personas: list[dict[str, Any]],
    backend,
    region_label: str,
    contest_id: str,
) -> dict[str, Any]:
    candidates = variant.candidates
    valid_ids = [c["id"] for c in candidates if not c.get("withdrawn")]

    async def _one(p: dict[str, Any]) -> dict[str, Any]:
        # Build a VoterAgent and override prompts via variant
        agent = VoterAgent(
            persona=p,
            persona_text=p.get("persona_text", {}),
            backend=backend,
            region_label=region_label,
            contest_id=contest_id,
        )
        sp = variant.system_prompt(agent)
        up = variant.user_prompt(agent, t=0)
        # Bypass agent.vote() to use variant prompts directly. Keep retry+parse.
        from src.sim.voter_agent import _parse_voter_json, ABSTAIN_RESPONSE  # type: ignore
        import time, random
        for attempt in range(3):
            try:
                t0 = time.monotonic()
                raw = await backend(sp, up, {"max_output_tokens": 2048, "temperature": 1.0})
                latency_ms = (time.monotonic() - t0) * 1000.0
                parsed = _parse_voter_json(raw, valid_ids)
                parsed["_persona_id"] = agent.persona_id
                parsed["_latency_ms"] = round(latency_ms, 1)
                return parsed
            except Exception:
                await asyncio.sleep(0.2 + random.random() * 0.3)
        out = dict(ABSTAIN_RESPONSE)
        out["_persona_id"] = agent.persona_id
        return out

    votes = await asyncio.gather(*[_one(p) for p in personas])
    return _aggregate(variant, personas, votes)


def _aggregate(
    variant: _PromptVariant,
    personas: list[dict[str, Any]],
    votes: list[dict[str, Any]],
) -> dict[str, Any]:
    # Count votes
    counts: dict[str, int] = {}
    n_abstain = 0
    for v in votes:
        cand = v.get("vote")
        if cand:
            counts[cand] = counts.get(cand, 0) + 1
        else:
            n_abstain += 1

    rated_keys = list(DEFAULT_OFFICIAL_CONSENSUS.keys())
    sub_total = sum(counts.get(k, 0) for k in rated_keys)
    if sub_total > 0:
        renorm = {k: counts.get(k, 0) / sub_total for k in rated_keys}
    else:
        renorm = {k: 0.0 for k in rated_keys}

    official = DEFAULT_OFFICIAL_CONSENSUS

    # If no official consensus available (gwangju/dalseo: no NESDC poll
    # registered), report diversity-only — vote distribution + abstain. MAE /
    # leader_match cannot be evaluated.
    if not official:
        sample_first = personas[0] if personas else None
        sample_sys = sample_user = ""
        if sample_first is not None:
            sample_agent = VoterAgent(
                persona=sample_first,
                persona_text=sample_first.get("persona_text", {}),
                backend=lambda *a, **k: None,
                region_label="(region)",
            )
            sample_sys = variant.system_prompt(sample_agent)
            sample_user = variant.user_prompt(sample_agent, t=0)
        return {
            "variant": variant.name,
            "n_personas": len(personas),
            "n_abstain": n_abstain,
            "votes": [
                {
                    "persona_id": v.get("_persona_id"),
                    "vote": v.get("vote"),
                    "reason": (v.get("reason") or "")[:240],
                    "key_factors": v.get("key_factors") or [],
                }
                for v in votes
            ],
            "vote_count": counts,
            "renorm_share": {},
            "official_consensus": {},
            "metrics": {
                "available": False,
                "reason": "no NESDC poll_consensus_daily for region",
                "mae": None,
                "rmse": None,
                "margin_error": None,
                "leader_match": None,
                "kl_div": None,
                "n_rated": 0,
                "n_distinct_votes": len(counts),
            },
            "system_prompt_sample": sample_sys,
            "user_prompt_sample": sample_user,
        }

    errors = {k: renorm[k] - official[k] for k in rated_keys}
    abs_errs = [abs(e) for e in errors.values()]
    sq_errs = [e * e for e in errors.values()]
    mae = sum(abs_errs) / len(abs_errs) if abs_errs else 0.0
    rmse = math.sqrt(sum(sq_errs) / len(sq_errs)) if sq_errs else 0.0

    sim_leader = max(renorm.items(), key=lambda kv: kv[1])[0] if sub_total else None
    off_leader = max(official.items(), key=lambda kv: kv[1])[0]
    leader_match = sim_leader == off_leader

    # KL(sim||off) — guard with epsilon
    eps = 1e-6
    kl = 0.0
    for k in rated_keys:
        p_ = max(eps, renorm[k])
        q_ = max(eps, official[k])
        kl += p_ * math.log(p_ / q_)

    # Sample prompts (first persona)
    first_persona = personas[0] if personas else None
    sample_sys = sample_user = ""
    if first_persona is not None:
        sample_agent = VoterAgent(
            persona=first_persona,
            persona_text=first_persona.get("persona_text", {}),
            backend=lambda *a, **k: None,
            region_label="서울특별시장",
        )
        sample_sys = variant.system_prompt(sample_agent)
        sample_user = variant.user_prompt(sample_agent, t=0)

    return {
        "variant": variant.name,
        "n_personas": len(personas),
        "n_abstain": n_abstain,
        "votes": [
            {
                "persona_id": v.get("_persona_id"),
                "vote": v.get("vote"),
                "reason": (v.get("reason") or "")[:240],
                "key_factors": v.get("key_factors") or [],
                "latency_ms": v.get("_latency_ms"),
            }
            for v in votes
        ],
        "vote_count": counts,
        "renorm_share": renorm,
        "official_consensus": official,
        "metrics": {
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "leader_match": bool(leader_match) if sim_leader else None,
            "kl_div": round(kl, 4),
            "n_rated": sub_total,
        },
        "system_prompt_sample": sample_sys,
        "user_prompt_sample": sample_user,
    }


# ============================================================================
# Main
# ============================================================================
async def _main_async(args: argparse.Namespace) -> int:
    loaded = load_personas_and_truth(args.personas_path, n=args.n)
    if loaded is None:
        # DuckDB fallback
        personas = load_personas(args.personas_path, n=args.n)
        gt_consensus = None
        region_id = None
    else:
        personas, gt_consensus, region_id = loaded
    if not personas:
        print("FAIL: no personas loaded.", file=sys.stderr)
        return 2

    # If persona file came with ground_truth, override the harness default.
    # If missing (e.g. gwangju, dalseo), set sentinel to indicate unavailable.
    global DEFAULT_OFFICIAL_CONSENSUS
    if gt_consensus:
        DEFAULT_OFFICIAL_CONSENSUS = gt_consensus
    else:
        # Sentinel — `_aggregate` checks emptiness to emit `available=false`.
        DEFAULT_OFFICIAL_CONSENSUS = {}

    # Region-aware scenario loading
    scenario_path = SEOUL_SCENARIO
    if region_id and region_id != "seoul_mayor":
        candidate_path = (
            REPO / "_workspace" / "data" / "scenarios" / f"{region_id}.json"
        )
        if candidate_path.exists():
            scenario_path = candidate_path
    with scenario_path.open("r", encoding="utf-8") as f:
        scenario = json.load(f)

    print(
        f"[hill_climbing] loaded {len(personas)} personas; region={region_id or 'seoul_mayor'}; "
        f"gt={DEFAULT_OFFICIAL_CONSENSUS}"
    )

    backend = build_default_backend()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    selected = [v.strip() for v in args.variants.split(",") if v.strip()]
    variants = []
    for s in selected:
        cls = VARIANT_REGISTRY.get(s)
        if not cls:
            print(f"WARN unknown variant '{s}'", file=sys.stderr)
            continue
        variants.append(cls(scenario))

    started = dt.datetime.now(dt.timezone.utc)
    results = await asyncio.gather(
        *[
            _run_variant(
                v, personas, backend,
                region_label="서울특별시장",
                contest_id=scenario.get("contest_id", "seoul_mayor_2026"),
            )
            for v in variants
        ]
    )
    elapsed = (dt.datetime.now(dt.timezone.utc) - started).total_seconds()

    # Write per-variant JSON
    for r in results:
        name = r["variant"]
        if name == "R0":
            fname = "R0_baseline.json"
        else:
            fname = f"R1_{name}.json"
        path = out_dir / fname
        path.write_text(
            json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[hill_climbing] wrote {path}: MAE={r['metrics']['mae']} "
              f"leader_match={r['metrics']['leader_match']} "
              f"renorm={r['renorm_share']}")

    # Build summary
    summary_path = out_dir / "R1_summary.md"
    lines = [
        "# Hill-Climbing Round 0 + Round 1 Summary",
        "",
        f"Generated: {dt.datetime.now(dt.timezone.utc).isoformat()}",
        f"Personas: n={len(personas)} (seoul)",
        f"Wall: {elapsed:.1f}s",
        f"Official target (NESDC weighted_v1, intersection-renormalized): "
        f"정원오 0.5702 / 오세훈 0.4298",
        "",
        "## Variant comparison",
        "",
        "| variant | MAE | RMSE | KL(sim‖off) | leader_match | sim leader share | abstain | n_rated |",
        "|---|---:|---:|---:|---|---|---:|---:|",
    ]
    for r in results:
        m = r["metrics"]
        renorm = r["renorm_share"]
        sim_lead = max(renorm.items(), key=lambda kv: kv[1])
        sim_lead_str = f"{sim_lead[0]} {sim_lead[1]*100:.1f}%"
        lines.append(
            f"| {r['variant']} | {m['mae']} | {m['rmse']} | {m['kl_div']} | "
            f"{m['leader_match']} | {sim_lead_str} | {r['n_abstain']} | {m['n_rated']} |"
        )

    # Best variant (lowest MAE, leader_match preferred)
    rated = [r for r in results if r["metrics"]["leader_match"] is not None]
    if rated:
        best = min(
            rated,
            key=lambda r: (
                0 if r["metrics"]["leader_match"] else 1,
                r["metrics"]["mae"],
            ),
        )
        lines.extend(
            [
                "",
                f"## Best variant: **{best['variant']}**",
                f"- MAE: {best['metrics']['mae']}",
                f"- leader_match: {best['metrics']['leader_match']}",
                f"- sim leader: {max(best['renorm_share'].items(), key=lambda kv: kv[1])}",
            ]
        )

    summary_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[hill_climbing] wrote {summary_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=os.environ.get("POLITIKAST_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Hill-climbing prompt variants")
    parser.add_argument("--personas-path", default=None,
                        help="JSON file from data-engineer with 10 personas")
    parser.add_argument("--variants", default="R0,v1,v2,v4,v5",
                        help="Comma-separated variant names")
    parser.add_argument("--n", type=int, default=10)
    parser.add_argument("--out-dir", default="_workspace/snapshots/hill_climbing")
    args = parser.parse_args(argv)
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    sys.exit(main())
