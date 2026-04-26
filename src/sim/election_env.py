"""ElectionEnv — timestep loop, poll consensus, secret-ballot tally.

The env coordinates a list of `VoterAgent` instances across `T` timesteps:
    for t in 0..T-1:
        - retrieve KG-derived context for each persona at time t
        - voter.vote(mode="poll_response") → aggregate share/turnout
        - feed bandwagon/underdog ΔU^poll back into next timestep's prompt
    final secret_ballot wave at t=T → final_outcome
    sample N personas → virtual_interview wave (long-form reasons)

Output dict matches `_workspace/contracts/result_schema.json::scenario_result`.

KG retriever protocol (kg-engineer's `KGRetriever`):
    subgraph_at(persona: dict, t: int, region_id: str, k: int = 5) -> Result
    where Result has .context_text:str, .events_used:list[dict], .triples:list[tuple]
A null retriever (for offline smoke / degraded mode) returns empty fields.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import math
import os
import random
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .poll_consensus import aggregate_poll_response, bandwagon_underdog
from .voter_agent import VoterAgent

logger = logging.getLogger(__name__)

# Repository root — used by the `_inject_validation_metrics` step (V6,
# validation-first redesign) to read `poll_consensus_daily` from
# `_workspace/db/politikast.duckdb`.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DUCKDB_PATH = _REPO_ROOT / "_workspace" / "db" / "politikast.duckdb"


# ---------------------------------------------------------------------------
# KG retriever protocol (duck-typed; kg-engineer ships the real impl)
# ---------------------------------------------------------------------------
@dataclass
class _RetrievalShim:
    context_text: str = ""
    events_used: list[dict[str, Any]] = field(default_factory=list)
    triples: list[tuple[str, str, str]] = field(default_factory=list)


class _NullRetriever:
    """Fallback when kg-engineer hasn't shipped the retriever yet."""

    def subgraph_at(
        self,
        persona: Any,
        t: int,
        region_id: str | None = None,
        k: int = 5,
    ) -> _RetrievalShim:
        return _RetrievalShim()


def _coerce_retriever(retriever: Any) -> Any:
    if retriever is None:
        return _NullRetriever()
    if not hasattr(retriever, "subgraph_at"):
        logger.warning("KG retriever missing subgraph_at(); using null retriever.")
        return _NullRetriever()
    return retriever


def _normalize_retrieval(raw: Any) -> _RetrievalShim:
    """Accept either a string (legacy) or an object with .context_text/.events_used/.triples."""
    if raw is None:
        return _RetrievalShim()
    if isinstance(raw, str):
        return _RetrievalShim(context_text=raw)
    return _RetrievalShim(
        context_text=str(getattr(raw, "context_text", "") or ""),
        events_used=list(getattr(raw, "events_used", []) or []),
        triples=list(getattr(raw, "triples", []) or []),
    )


# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------
def _read_features() -> set[str]:
    # `cohort_prior` is on by default — degrades gracefully if KG retriever
    # doesn't yet expose `get_cohort_prior` (Task #27 + #28).
    raw = os.environ.get(
        "POLITIKAST_FEATURES",
        "bandwagon,underdog,second_order,kg_retrieval,cohort_prior",
    )
    return {x.strip() for x in raw.split(",") if x.strip()}


def _read_timesteps(default: int = 4) -> int:
    raw = os.environ.get("POLITIKAST_TIMESTEPS")
    if raw and raw.isdigit():
        return max(1, int(raw))
    return default


def _read_llm_cache_enabled() -> bool:
    raw = os.environ.get("POLITIKAST_LLM_CACHE", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _read_final_poll_feedback_enabled() -> bool:
    raw = os.environ.get("POLITIKAST_FINAL_POLL_FEEDBACK", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _read_poll_targets_visible_to_agents() -> bool:
    """Whether held-out poll labels may be rendered into voter prompts.

    Default is false: NESDC/poll_consensus rows are calibration and validation
    labels, not the voter's information state. Turn this on only for explicit
    poll-exposure ablations.
    """
    raw = os.environ.get("POLITIKAST_POLL_TARGETS_VISIBLE_TO_AGENTS", "0")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Main env
# ---------------------------------------------------------------------------
class ElectionEnv:
    def __init__(
        self,
        *,
        region_id: str,
        contest_id: str,
        candidates: list[dict[str, Any]],
        timesteps: int | None = None,
        kg_retriever: Any | None = None,
        scenario_meta: dict[str, Any] | None = None,
        concurrency: int = 16,
        n_interviews: int = 5,
    ) -> None:
        self.region_id = region_id
        self.contest_id = contest_id
        self.candidates = candidates
        self.timesteps = timesteps or _read_timesteps(default=4)
        self.kg = _coerce_retriever(kg_retriever)
        self.scenario_meta = scenario_meta or {}
        self.concurrency = concurrency
        self.n_interviews = n_interviews
        self.features = _read_features()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    # Korean labels for party_id → display name (cohort_prior_block default).
    # Used when KG payload keys match scenario.parties[].party_id.
    _PARTY_LABEL_OVERRIDES: dict[str, str] = {
        "p_ppp": "국민의힘",
        "p_dem": "더불어민주당",
        "p_rebuild": "조국혁신당",
        "p_jp": "정의당",
        "p_indep": "무소속",
        "ppp": "국민의힘",
        "dem": "더불어민주당",
        "dpk": "더불어민주당",
        "etc": "기타",
        "other": "기타",
        "undecided": "미정",
        "none": "미정",
        "no_response": "무응답",
    }

    def _party_label(self, key: str) -> str | None:
        """Map a party_id (scenario or KG canonical) to a human label."""
        if key in self._PARTY_LABEL_OVERRIDES:
            return self._PARTY_LABEL_OVERRIDES[key]
        for p in self.scenario_meta.get("parties", []) or []:
            if p.get("party_id") == key or p.get("id") == key:
                return p.get("name") or p.get("party_id") or key
        return None

    def _render_cohort_prior(
        self, cp: Any, age: int | None, gender: str | None
    ) -> str | None:
        """Render KG `CohortPrior` node payload as a voter-prompt block.

        Canonical schema (team-lead spec, kg-engineer Track B):
          - shares: dict[party_id|cand_id, float]  (0..1)
          - cohort_label: str (e.g. "20대 남성")
          - n: int (sample size)
          - period_start / period_end: ISO date
          - source / source_url: str
          - block_text: optional pre-rendered string

        Returns None when payload is unparseable / empty.
        """
        if cp is None:
            return None
        if isinstance(cp, str):
            return cp.strip() or None
        if isinstance(cp, dict) and isinstance(cp.get("block_text"), str):
            text = cp["block_text"].strip()
            return text or None

        def _attr(obj: Any, key: str, default: Any = None) -> Any:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        shares = (
            _attr(cp, "shares")
            or _attr(cp, "party_lean")
            or _attr(cp, "lean")
            or _attr(cp, "distribution")
            or {}
        )
        cohort_label = _attr(cp, "cohort_label") or _attr(cp, "label")
        source = _attr(cp, "source") or _attr(cp, "source_url")
        sample_n = _attr(cp, "n") or _attr(cp, "sample_size") or _attr(cp, "n_polls")
        period_start = _attr(cp, "period_start") or _attr(cp, "field_start")
        period_end = _attr(cp, "period_end") or _attr(cp, "field_end")

        # Synthesize cohort label if missing
        if not cohort_label and (age is not None or gender):
            decade = (age // 10) * 10 if isinstance(age, int) else None
            decade_str = f"{decade}대" if decade else ""
            gender_str = (
                "여성"
                if gender in ("여", "여성", "female", "F", "f")
                else "남성"
                if gender in ("남", "남성", "male", "M", "m")
                else (gender or "")
            )
            cohort_label = " ".join(
                [p for p in (decade_str, gender_str) if p]
            ) or "동일 cohort"

        if not shares:
            return None

        # Decide whether keys are party_ids or candidate_ids — prefer party
        # display names per team-lead schema. Falls back to candidate names.
        cand_id_to_name = {c["id"]: c.get("name", c["id"]) for c in self.candidates}
        rendered: list[str] = []
        for key, val in shares.items():
            try:
                pf = float(val)
            except (TypeError, ValueError):
                continue
            key_str = str(key)
            label = (
                self._party_label(key_str)
                or cand_id_to_name.get(key_str)
                or key_str
            )
            rendered.append(f"{label}: {pf*100:.0f}%")
        if not rendered:
            return None

        # Provenance line (team-lead spec): 표본 수 N, 기간 …, 출처 …
        meta_parts: list[str] = []
        if sample_n is not None:
            meta_parts.append(f"표본 수 {sample_n}")
        if period_start and period_end:
            meta_parts.append(f"기간 {period_start} ~ {period_end}")
        elif period_start or period_end:
            meta_parts.append(f"기간 {period_start or period_end}")
        if source:
            meta_parts.append(f"출처: {source}")
        meta_line = ("- " + ", ".join(meta_parts)) if meta_parts else ""

        head = f"[같은 cohort 여론조사 평균 ({cohort_label}, {self.region_id})]"
        body = "- " + " / ".join(rendered)
        guidance = (
            "- 본인 baseline prior로만 참고. "
            "후보 자질·공약·지역 이슈와 종합 판단."
        )
        lines = [head, body]
        if meta_line:
            lines.append(meta_line)
        lines.append(guidance)
        return "\n".join(lines)

    def _nesdc_anchor_block(self) -> str | None:
        """Render official poll targets into prompts only for explicit ablation.

        NESDC `poll_consensus_daily` is the hidden calibration/validation target
        by default. Exposing it to voter agents is a separate poll-exposure
        experiment controlled by `POLITIKAST_POLL_TARGETS_VISIBLE_TO_AGENTS=1`.

        Returns rendered block or None when DuckDB / consensus rows missing.
        Disabled if `no_nesdc_anchor` feature flag set.
        """
        if not _read_poll_targets_visible_to_agents():
            return None
        if "no_nesdc_anchor" in self.features:
            return None
        try:
            cutoff_date = dt.date.fromisoformat(
                str(self._resolve_cutoff_ts()).split("T")[0]
            )
        except Exception:
            return None
        anchor_max = cutoff_date - dt.timedelta(days=1)
        if not _DUCKDB_PATH.exists():
            return None
        try:
            import duckdb  # type: ignore
            con = duckdb.connect(str(_DUCKDB_PATH), read_only=True)
        except Exception:
            return None
        try:
            tables = {
                r[0]
                for r in con.execute(
                    "select table_name from information_schema.tables "
                    "where table_schema='main'"
                ).fetchall()
            }
            if "poll_consensus_daily" not in tables:
                return None
            row = con.execute(
                """
                select max(as_of_date) from poll_consensus_daily
                where contest_id = ? and region_id = ? and as_of_date <= ?
                """,
                [self.contest_id, self.region_id, anchor_max],
            ).fetchone()
            anchor_date = row[0] if row else None
            if anchor_date is None:
                return None
            cand_rows = con.execute(
                """
                select candidate_id, p_hat from poll_consensus_daily
                where contest_id = ? and region_id = ? and as_of_date = ?
                """,
                [self.contest_id, self.region_id, anchor_date],
            ).fetchall()
        finally:
            con.close()
        if not cand_rows:
            return None
        id_to_name = {c["id"]: c.get("name", c["id"]) for c in self.candidates}
        parts: list[str] = []
        total = 0.0
        for cid, p in cand_rows:
            try:
                pf = float(p)
            except (TypeError, ValueError):
                continue
            parts.append(f"{id_to_name.get(cid, cid)} {pf*100:.0f}%")
            total += pf
        if total < 1.0:
            slack = 1.0 - total
            if slack > 0.005:
                parts.append(f"미정·기타 {slack*100:.0f}%")
        return (
            "[참고 NESDC 등록 여론조사 (poll_consensus_daily, weighted_v1, "
            f"as_of {anchor_date.isoformat()} ≤ cutoff−1d)]\n"
            f"- {' / '.join(parts)}\n"
            "  (직전 등록 여론조사 합의이며 미래 결과·검증 타깃이 아닙니다.)"
        )

    def _build_context(
        self,
        voter: "VoterAgent",
        t: int,
        last_consensus: dict[str, dict[str, float]] | None,
    ) -> tuple[str, list[dict[str, Any]]]:
        parts: list[str] = []
        events_used: list[dict[str, Any]] = []

        # Hill-climbing R3 winner stack head: NESDC anchor at top of [컨텍스트].
        nesdc = self._nesdc_anchor_block()
        if nesdc:
            parts.append(nesdc)

        if "kg_retrieval" in self.features:
            try:
                raw = self.kg.subgraph_at(
                    voter.persona, t, region_id=self.region_id, k=5
                )
            except TypeError:
                # legacy positional signature — fall back
                raw = self.kg.subgraph_at(voter.persona_id, t, region_id=self.region_id)
            shim = _normalize_retrieval(raw)
            if shim.context_text:
                parts.append("[KG 컨텍스트]\n" + shim.context_text)
            events_used.extend(shim.events_used)

        # Task #28 — cohort prior block. Calls KG `get_cohort_prior(age, gender,
        # region)` if available; degrades gracefully when KG Track B (CohortPrior
        # nodes) hasn't shipped yet. Renders as a high-salience block so voters
        # know "people like me" lean.
        if "cohort_prior" in self.features and hasattr(
            self.kg, "get_cohort_prior"
        ):
            try:
                age_raw = voter.persona.get("age")
                age = int(age_raw) if age_raw is not None else None
                gender = (
                    voter.persona.get("sex")
                    or voter.persona.get("gender")
                    or None
                )
                cp = self.kg.get_cohort_prior(
                    age=age, gender=gender, region_id=self.region_id
                )
                if cp:
                    block = self._render_cohort_prior(cp, age, gender)
                    if block:
                        parts.append(block)
            except Exception as e:  # pragma: no cover
                logger.debug(
                    "cohort_prior unavailable for %s: %s", voter.persona_id, e
                )

        # Inject last simulated poll consensus as a bounded bandwagon/underdog
        # signal. This is endogenous model output, not an external poll.
        if last_consensus and ("bandwagon" in self.features or "underdog" in self.features):
            lines = []
            lines.append(
                "아래 수치는 실제 외부 여론조사가 아니라 직전 모의응답 집계입니다. "
                "페르소나와 후보 정보를 우선하고, 이 수치를 그대로 복사하지 마세요."
            )
            for c in self.candidates:
                cid = c["id"]
                p = last_consensus.get(cid, {}).get("p_hat", 0.0)
                delta = bandwagon_underdog(
                    {k: v["p_hat"] for k, v in last_consensus.items()},
                    cid,
                    enable_bandwagon="bandwagon" in self.features,
                    enable_underdog="underdog" in self.features,
                )
                lines.append(
                    f"- {c.get('name', cid)} ({c.get('party', '')}): "
                    f"직전 모의응답 {p*100:.1f}% (ΔU_poll={delta:+.2f})"
                )
            parts.append("[직전 모의응답 요약]\n" + "\n".join(lines))

        if "second_order" in self.features:
            gov = self.scenario_meta.get("gov_approval")
            if gov is not None:
                parts.append(f"[중앙정부 지지율] {float(gov)*100:.1f}%")

        # Pre-baked seed events from scenario JSON (curated, not LLM hallucinated)
        seed_events = self.scenario_meta.get("seed_events") or []
        ev_lines = []
        for ev in seed_events:
            if int(ev.get("timestep", 0)) <= t:
                ev_lines.append(
                    f"- t={ev.get('timestep')} [{ev.get('type', 'event')}] "
                    f"{ev.get('summary', '')} (target={ev.get('target', '-')})"
                )
        if ev_lines:
            parts.append("[주요 사건]\n" + "\n".join(ev_lines))

        return "\n\n".join(parts), events_used

    async def _vote_wave(
        self,
        voters: list[VoterAgent],
        t: int,
        mode: str,
        last_consensus: dict[str, dict[str, float]] | None,
        events_collector: list[dict[str, Any]] | None = None,
        extras: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        sem = asyncio.Semaphore(self.concurrency)

        async def _one(v: VoterAgent) -> dict[str, Any]:
            async with sem:
                ctx, ev = self._build_context(v, t, last_consensus)
                if events_collector is not None:
                    events_collector.extend(ev)
                return await v.vote(
                    self.candidates, ctx, t, mode=mode, extras=extras
                )

        return await asyncio.gather(*[_one(v) for v in voters])

    # ------------------------------------------------------------------
    # Tally helpers
    # ------------------------------------------------------------------
    def _tally_secret_ballot(
        self, responses: list[dict[str, Any]]
    ) -> dict[str, Any]:
        agg = aggregate_poll_response(responses, self.candidates)
        shares = agg["support_by_candidate"]
        winner = max(shares.items(), key=lambda kv: kv[1])[0] if shares else None
        return {
            "turnout": agg["turnout_intent"],
            "vote_share_by_candidate": shares,
            "winner": winner,
            "n_responses": agg["n_responses"],
            "n_abstain": agg["n_abstain"],
        }

    def _demographics_breakdown(
        self,
        voters: list[VoterAgent],
        responses: list[dict[str, Any]],
    ) -> dict[str, Any]:
        def _age_group(age: Any) -> str:
            try:
                a = int(age)
            except (TypeError, ValueError):
                return "unknown"
            if a < 30:
                return "20s"
            if a < 40:
                return "30s"
            if a < 50:
                return "40s"
            if a < 60:
                return "50s"
            return "60s+"

        groupers = {
            "by_age_group": lambda v: _age_group(v.persona.get("age")),
            "by_education": lambda v: str(v.persona.get("education_level") or "unknown"),
            "by_district": lambda v: str(
                v.persona.get("district") or v.persona.get("city") or "unknown"
            ),
        }
        out: dict[str, Any] = {}
        for key, fn in groupers.items():
            buckets: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
            totals: dict[str, int] = defaultdict(int)
            for v, r in zip(voters, responses):
                bucket = fn(v)
                vote = r.get("vote")
                totals[bucket] += 1
                if vote:
                    buckets[bucket][vote] += 1
            out[key] = {
                bucket: {
                    cid: cnt / max(1, totals[bucket]) for cid, cnt in cands.items()
                }
                for bucket, cands in buckets.items()
            }
        return out

    # ------------------------------------------------------------------
    # Validation injection (V6 — validation-first redesign)
    # ------------------------------------------------------------------
    def _resolve_cutoff_ts(self) -> str:
        """Pick cutoff_ts (ISO 8601, KST) used for rolling-origin gate.

        Order of precedence:
          1. POLITIKAST_VALIDATION_CUTOFF_TS env var
          2. scenario.simulation.t_start
          3. now() in KST
        """
        env_ts = os.environ.get("POLITIKAST_VALIDATION_CUTOFF_TS")
        if env_ts:
            return env_ts
        sim = self.scenario_meta.get("simulation") or {}
        t_start = sim.get("t_start")
        if t_start:
            return str(t_start)
        kst = dt.timezone(dt.timedelta(hours=9))
        return dt.datetime.now(kst).isoformat()

    def _consensus_from_duckdb(
        self, cutoff_date: dt.date
    ) -> tuple[dict[str, float], list[str], dt.date | None] | None:
        """Pull weighted_v1 poll_consensus_daily for this contest at the latest
        as_of_date <= cutoff_date.

        Returns (shares, source_poll_ids, as_of_date) or None on miss/error.
        """
        if not _DUCKDB_PATH.exists():
            return None
        try:
            import duckdb  # type: ignore
        except Exception as e:  # pragma: no cover
            logger.debug("duckdb import failed for validation: %s", e)
            return None
        try:
            con = duckdb.connect(str(_DUCKDB_PATH), read_only=True)
        except Exception as e:
            logger.debug("duckdb open failed for validation: %s", e)
            return None
        try:
            tables = {
                r[0]
                for r in con.execute(
                    "select table_name from information_schema.tables "
                    "where table_schema='main'"
                ).fetchall()
            }
            if "poll_consensus_daily" not in tables:
                return None
            row = con.execute(
                """
                select max(as_of_date)
                from poll_consensus_daily
                where contest_id = ? and region_id = ? and as_of_date <= ?
                """,
                [self.contest_id, self.region_id, cutoff_date],
            ).fetchone()
            as_of: dt.date | None = row[0] if row else None
            if as_of is None:
                return None
            cand_rows = con.execute(
                """
                select candidate_id, p_hat, source_poll_ids
                from poll_consensus_daily
                where contest_id = ? and region_id = ? and as_of_date = ?
                """,
                [self.contest_id, self.region_id, as_of],
            ).fetchall()
        finally:
            con.close()
        if not cand_rows:
            return None
        shares: dict[str, float] = {}
        ids: set[str] = set()
        for cid, p_hat, src in cand_rows:
            try:
                shares[str(cid)] = float(p_hat)
            except (TypeError, ValueError):
                continue
            if isinstance(src, str) and src:
                try:
                    parsed = json.loads(src)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, list):
                    for s in parsed:
                        if s:
                            ids.add(str(s))
                else:
                    for s in src.split(","):
                        s = s.strip()
                        if s:
                            ids.add(s)
            elif isinstance(src, (list, tuple)):
                for s in src:
                    if s:
                        ids.add(str(s))
        if not shares:
            return None
        return shares, sorted(ids), as_of

    def _consensus_from_scenario(
        self, cutoff_date: dt.date
    ) -> tuple[dict[str, float], list[str], dt.date | None] | None:
        """Fallback: derive a quality-weighted consensus from
        scenario.raw_polls (curated). Used when poll_consensus_daily is not
        yet ingested. method_version emitted as `scenario_fallback_v1`.
        """
        polls = self.scenario_meta.get("raw_polls") or []
        if not polls:
            return None
        e_date_raw = (self.scenario_meta.get("election_date")
                      or self.scenario_meta.get("election", {}).get("date")
                      or "2026-06-03")
        try:
            e_date = dt.date.fromisoformat(str(e_date_raw))
        except Exception:
            e_date = dt.date(2026, 6, 3)

        weighted: dict[str, float] = defaultdict(float)
        weight_total: dict[str, float] = defaultdict(float)
        ids: list[str] = []
        latest: dt.date | None = None
        for p in polls:
            shares = p.get("shares") or {}
            if not shares:
                continue
            quality = float(p.get("quality", 1.0) or 1.0)
            n = float(p.get("n", 1000) or 1000)
            w = max(quality, 0.1) * math.sqrt(max(n, 1.0))
            # Filter by date if available
            day = p.get("day")
            ts = p.get("ts")
            poll_date: dt.date | None = None
            if isinstance(ts, str):
                try:
                    poll_date = dt.date.fromisoformat(ts.split("T")[0])
                except Exception:
                    poll_date = None
            elif isinstance(day, (int, float)):
                # day is offset relative to (election - 30d)
                poll_date = (e_date - dt.timedelta(days=30)) + dt.timedelta(
                    days=int(day)
                )
            if poll_date is not None:
                if poll_date > cutoff_date:
                    continue
                if latest is None or poll_date > latest:
                    latest = poll_date
            for cid, share in shares.items():
                try:
                    val = float(share)
                except (TypeError, ValueError):
                    continue
                if val > 1.0:  # percent — normalize
                    val /= 100.0
                weighted[cid] += val * w
                weight_total[cid] += w
            pid = p.get("poll_id") or p.get("pollster")
            if pid is not None:
                ids.append(str(pid))
        if not weight_total:
            return None
        shares_out = {
            cid: weighted[cid] / weight_total[cid] for cid in weight_total
        }
        return shares_out, sorted(set(ids)), latest

    def _inject_validation_metrics(
        self, result: dict[str, Any]
    ) -> None:
        """Compute and attach `meta.official_poll_validation` block per
        `_workspace/validation/official_poll_validation_targets.md`.

        Tries DuckDB `poll_consensus_daily` first (method_version="weighted_v1"),
        falls back to scenario.raw_polls (`scenario_fallback_v1`) only for
        validation-eligible scenarios. Prediction-only scenarios explicitly
        opt out because their media priors are not held-out labels. When no
        label is usable, writes a `target_series="missing"` stub so
        dashboard/paper always sees the field.
        """
        cutoff_ts = self._resolve_cutoff_ts()
        try:
            cutoff_date = dt.date.fromisoformat(str(cutoff_ts).split("T")[0])
        except Exception:
            cutoff_date = dt.date.today()

        counterfactual = (
            self.scenario_meta.get("counterfactual")
            or self.scenario_meta.get("counterfactual_inference")
        )
        if isinstance(counterfactual, dict) and counterfactual.get("enabled"):
            result["meta"]["official_poll_validation"] = {
                "target_series": "counterfactual_prediction",
                "as_of_date": None,
                "method_version": "not_applicable",
                "cutoff_ts": cutoff_ts,
                "source_poll_ids": counterfactual.get("source_urls", []),
                "metrics": {
                    "mae": None,
                    "rmse": None,
                    "margin_error": None,
                    "leader_match": None,
                },
                "by_candidate": {},
                "counterfactual_prediction": True,
                "reason": counterfactual.get(
                    "reason",
                    "Counterfactual inference run: no train/validation target is available.",
                ),
                "intervention_id": counterfactual.get("intervention_id"),
                "base_region_id": counterfactual.get("base_region_id"),
                "calibration_profile": counterfactual.get("calibration_profile"),
                "frozen_params": counterfactual.get("frozen_params"),
                "poll_targets_visible_to_agents": _read_poll_targets_visible_to_agents(),
            }
            logger.info(
                "[%s] counterfactual prediction — skip official-poll validation.",
                self.region_id,
            )
            return

        prediction_only = self.scenario_meta.get("prediction_only_assumption")
        if (
            isinstance(prediction_only, dict)
            and prediction_only.get("not_for_validation")
        ):
            result["meta"]["official_poll_validation"] = {
                "target_series": "prediction_only",
                "as_of_date": None,
                "method_version": "not_applicable",
                "cutoff_ts": cutoff_ts,
                "source_poll_ids": prediction_only.get("source_urls", []),
                "metrics": {
                    "mae": None,
                    "rmse": None,
                    "margin_error": None,
                    "leader_match": None,
                },
                "by_candidate": {},
                "prediction_only": True,
                "poll_targets_visible_to_agents": _read_poll_targets_visible_to_agents(),
                "reason": prediction_only.get(
                    "reason",
                    "Media priors are used for hypothetical simulation only.",
                ),
            }
            logger.info(
                "[%s] prediction-only scenario — skip official-poll validation.",
                self.region_id,
            )
            return

        primary = self._consensus_from_duckdb(cutoff_date)
        method = "weighted_v1"
        target_series = "poll_consensus_daily"
        if primary is None:
            primary = self._consensus_from_scenario(cutoff_date)
            method = "scenario_fallback_v1"
            target_series = "scenario_fallback_v1"

        block: dict[str, Any] = {
            "target_series": target_series,
            "as_of_date": None,
            "method_version": method,
            "cutoff_ts": cutoff_ts,
            "source_poll_ids": [],
            "metrics": {
                "mae": None,
                "rmse": None,
                "margin_error": None,
                "leader_match": None,
            },
            "by_candidate": {},
        }

        if primary is None:
            block["target_series"] = "missing"
            block["method_version"] = "none"
            result["meta"]["official_poll_validation"] = block
            logger.warning(
                "[%s] no poll consensus available — emitting validation stub.",
                self.region_id,
            )
            return

        official, source_poll_ids, as_of_date = primary
        block["source_poll_ids"] = source_poll_ids
        block["as_of_date"] = as_of_date.isoformat() if as_of_date else None

        # Simulated final shares (exclude undecided/abstain implicit — they're
        # already excluded by aggregate_poll_response which divides by counted
        # ballots).
        final_outcome = result.get("final_outcome") or {}
        sim_shares: dict[str, float] = dict(
            final_outcome.get("vote_share_by_candidate") or {}
        )

        # Renormalize each side to the union of candidates that appear in BOTH
        # sim and official series — this avoids penalizing sim for placeholder
        # candidates the official polls don't cover, and vice versa.
        union_cids = sorted(set(sim_shares) & set(official))
        if not union_cids:
            block["target_series"] = "missing_candidate_overlap"
            result["meta"]["official_poll_validation"] = block
            logger.warning(
                "[%s] no candidate overlap between sim and consensus.",
                self.region_id,
            )
            return

        def _renorm(d: dict[str, float], keys: list[str]) -> dict[str, float]:
            sub = {k: float(d.get(k, 0.0) or 0.0) for k in keys}
            tot = sum(sub.values())
            if tot <= 0:
                return {k: 0.0 for k in keys}
            return {k: v / tot for k, v in sub.items()}

        sim_n = _renorm(sim_shares, union_cids)
        off_n = _renorm(official, union_cids)

        errors: dict[str, float] = {}
        for cid in union_cids:
            errors[cid] = sim_n[cid] - off_n[cid]
        abs_errors = [abs(e) for e in errors.values()]
        sq_errors = [e * e for e in errors.values()]
        mae = sum(abs_errors) / len(abs_errors) if abs_errors else 0.0
        rmse = math.sqrt(sum(sq_errors) / len(sq_errors)) if sq_errors else 0.0

        sim_leader = max(sim_n.items(), key=lambda kv: kv[1])
        off_leader = max(off_n.items(), key=lambda kv: kv[1])
        leader_match = sim_leader[0] == off_leader[0]

        # Margin error: |(sim_top - sim_2nd) - (off_top - off_2nd)|
        sim_sorted = sorted(sim_n.values(), reverse=True)
        off_sorted = sorted(off_n.values(), reverse=True)
        sim_margin = sim_sorted[0] - (sim_sorted[1] if len(sim_sorted) > 1 else 0.0)
        off_margin = off_sorted[0] - (off_sorted[1] if len(off_sorted) > 1 else 0.0)
        margin_error = abs(sim_margin - off_margin)

        block["metrics"] = {
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "margin_error": round(margin_error, 4),
            "leader_match": bool(leader_match),
        }
        block["by_candidate"] = {
            cid: {
                "simulated_share": round(sim_n[cid], 4),
                "official_consensus": round(off_n[cid], 4),
                "error": round(errors[cid], 4),
            }
            for cid in union_cids
        }
        result["meta"]["official_poll_validation"] = block
        logger.info(
            "[%s] validation: target=%s method=%s mae=%.4f leader_match=%s "
            "as_of=%s n_cands=%d",
            self.region_id,
            target_series,
            method,
            mae,
            leader_match,
            block["as_of_date"],
            len(union_cids),
        )

    # ------------------------------------------------------------------
    # Public run loop
    # ------------------------------------------------------------------
    async def run(self, voters: list[VoterAgent]) -> dict[str, Any]:
        if not voters:
            raise ValueError("ElectionEnv.run requires at least one voter.")
        for v in voters:
            v.region_label = self.scenario_meta.get("label", self.region_id)
            v.contest_id = self.contest_id

        llm_cache_enabled = _read_llm_cache_enabled()
        final_poll_feedback_enabled = _read_final_poll_feedback_enabled()
        poll_targets_visible = _read_poll_targets_visible_to_agents()
        result: dict[str, Any] = {
            "scenario_id": self.scenario_meta.get("scenario_id", self.region_id),
            "region_id": self.region_id,
            "contest_id": self.contest_id,
            "timestep_count": self.timesteps,
            "persona_n": len(voters),
            "candidates": [
                {"id": c["id"], "name": c.get("name", c["id"]), "party": c.get("party", "")}
                for c in self.candidates
            ],
            "poll_trajectory": [],
            "final_outcome": None,
            "demographics_breakdown": {},
            "virtual_interviews": [],
            "kg_events_used": [],
            "meta": {
                "features": sorted(self.features),
                "concurrency": self.concurrency,
                "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                # Provenance for dashboard/paper. policy_version is set by the
                # operator via env (run_scenario doesn't parse policy.version
                # itself). provider/model are pool-default; per-call overrides
                # appear in voter_stats.calls_by_model.
                "policy_version": os.environ.get(
                    "POLITIKAST_POLICY_VERSION", "unknown"
                ),
                "env": os.environ.get("POLITIKAST_ENV", "prod"),
                "llm_cache_enabled": llm_cache_enabled,
                "final_poll_feedback_enabled": final_poll_feedback_enabled,
                "poll_targets_visible_to_agents": poll_targets_visible,
                "counterfactual": self.scenario_meta.get("counterfactual")
                or self.scenario_meta.get("counterfactual_inference"),
            },
        }

        # ----- Poll waves -------------------------------------------------
        llm_extras = {"cache": llm_cache_enabled}
        last_consensus: dict[str, dict[str, float]] | None = None
        base_date = dt.date.today()
        events_collector: list[dict[str, Any]] = []
        for t in range(self.timesteps):
            logger.info(
                "[%s] poll wave t=%d/%d (n=%d)",
                self.region_id,
                t,
                self.timesteps,
                len(voters),
            )
            responses = await self._vote_wave(
                voters,
                t,
                "poll_response",
                last_consensus,
                events_collector,
                extras=llm_extras,
            )
            agg = aggregate_poll_response(responses, self.candidates)
            poll_entry = {
                "timestep": t,
                "date": (base_date + dt.timedelta(days=t)).isoformat(),
                "support_by_candidate": agg["support_by_candidate"],
                "turnout_intent": agg["turnout_intent"],
                "consensus_var": agg["consensus_var"],
            }
            result["poll_trajectory"].append(poll_entry)
            # Build "consensus" purely from this wave (no external pollster mix here)
            last_consensus = {
                cid: {"p_hat": s, "var": agg["consensus_var"]}
                for cid, s in agg["support_by_candidate"].items()
            }

        # ----- Secret ballot ---------------------------------------------
        logger.info("[%s] secret ballot wave (final)", self.region_id)
        final_responses = await self._vote_wave(
            voters,
            self.timesteps,
            "secret_ballot",
            last_consensus if final_poll_feedback_enabled else None,
            events_collector,
            extras=llm_extras,
        )
        result["final_outcome"] = self._tally_secret_ballot(final_responses)
        result["demographics_breakdown"] = self._demographics_breakdown(
            voters, final_responses
        )

        # ----- Virtual interviews ----------------------------------------
        if self.n_interviews > 0:
            sample = random.sample(voters, min(self.n_interviews, len(voters)))
            # Interview wave uses a stronger reasoning model (사용자 결정:
            # claude-sonnet-4-6) to produce richer reason/key_factors. dev 모드면
            # LLMPool이 어차피 DEV_OVERRIDE_MODEL로 라우팅하므로 prod에서만 적용됨.
            interview_model = os.environ.get(
                "LITELLM_MODEL_INTERVIEW", "claude-sonnet-4-6"
            )
            # max_output_tokens은 VoterAgent.vote가 virtual_interview에서 3072로
            # default 처리 (dev 모드 Gemini lite의 thinking-free 출력에서도 안전).
            interview_extras: dict[str, Any] = {"model": interview_model, **llm_extras}
            interviews = await self._vote_wave(
                sample,
                self.timesteps,
                "virtual_interview",
                last_consensus if final_poll_feedback_enabled else None,
                extras=interview_extras,
            )
            for v, r in zip(sample, interviews):
                result["virtual_interviews"].append(
                    {
                        "persona_id": v.persona_id,
                        "persona_summary": (v.persona_text or {}).get("persona", "")[:240]
                        if v.persona_text
                        else "",
                        "vote": r.get("vote"),
                        "reason": r.get("reason", ""),
                        "key_factors": r.get("key_factors", []),
                        "timestep": self.timesteps,
                    }
                )

        # ----- KG events used --------------------------------------------
        # Prefer kg-engineer's authoritative summary if available; else dedupe what
        # we collected per-retrieval.
        kg_events: list[dict[str, Any]] = []
        if hasattr(self.kg, "events_used_summary"):
            try:
                kg_events = list(
                    self.kg.events_used_summary(
                        region_id=self.region_id, until_t=self.timesteps
                    )
                )
            except Exception as e:  # pragma: no cover
                logger.warning("kg.events_used_summary failed: %s", e)
        if not kg_events and events_collector:
            seen: set[Any] = set()
            for ev in events_collector:
                key = ev.get("event_id") or (ev.get("type"), ev.get("target"), ev.get("timestep"))
                if key in seen:
                    continue
                seen.add(key)
                kg_events.append(ev)
        result["kg_events_used"] = kg_events

        # ----- Per-voter stat rollup -------------------------------------
        agg_stats = {"calls": 0, "parse_fail": 0, "abstain": 0, "latency_ms_sum": 0.0}
        calls_by_model: dict[str, int] = defaultdict(int)
        for v in voters:
            for k in agg_stats:
                agg_stats[k] += v.stats.get(k, 0)
            for bucket, cnt in (v.stats.get("calls_by_model") or {}).items():
                calls_by_model[bucket] += int(cnt)
        agg_stats["calls_by_model"] = dict(calls_by_model)
        # Derive convenience metrics for paper-writer's `tab:capacity` row.
        calls = max(1, agg_stats["calls"])
        agg_stats["mean_latency_ms"] = round(agg_stats["latency_ms_sum"] / calls, 1)
        agg_stats["parse_fail_rate"] = round(agg_stats["parse_fail"] / calls, 4)
        agg_stats["abstain_rate"] = round(agg_stats["abstain"] / calls, 4)
        result["meta"]["voter_stats"] = agg_stats
        # ----- LLMPool stats (cache_hit_rate / total_calls) --------------
        # Voters share a single backend closure; pool is reachable only if it
        # exposed a `.stats()` method via the closure (ducktyped).
        try:
            backend_self = getattr(voters[0].backend, "__closure__", None)
            pool = None
            if backend_self:
                for cell in backend_self:
                    obj = cell.cell_contents
                    if hasattr(obj, "stats") and callable(obj.stats):
                        pool = obj
                        break
            if pool is not None:
                pool_stats = pool.stats()
                hits = pool_stats.get("cache_hits", 0)
                misses = pool_stats.get("cache_misses", 0)
                total = hits + misses
                pool_stats["cache_hit_rate"] = round(hits / total, 4) if total else 0.0
                result["meta"]["pool_stats"] = pool_stats
                # Top-level provenance (team-lead 13:43 req): actual_keys_used
                # for round-robin context (3-key Gemini pool capacity claim).
                result["meta"]["actual_keys_used"] = int(pool_stats.get("n_keys", 1))
                # Pool default model is misleading when dev override fires —
                # report the runtime override target as the source of truth.
                if os.environ.get("POLITIKAST_ENV", "prod").lower() == "dev":
                    result["meta"]["effective_model"] = os.environ.get(
                        "DEV_OVERRIDE_MODEL", "gemini/gemini-3.1-flash-lite-preview"
                    )
                    result["meta"]["effective_provider"] = "gemini"
                else:
                    result["meta"]["effective_model"] = pool_stats.get("model", "unknown")
                    result["meta"]["effective_provider"] = pool_stats.get("provider", "unknown")
        except Exception as e:  # pragma: no cover
            logger.debug("pool stats lookup failed: %s", e)
        # ----- Validation injection (V6 — rolling-origin gate) -----------
        # Always run; emits a `target_series="missing"` stub if no consensus
        # is available so paper/dashboard always see the field.
        try:
            self._inject_validation_metrics(result)
        except Exception as e:  # pragma: no cover
            logger.warning(
                "[%s] validation injection failed: %s — emitting error stub.",
                self.region_id,
                e,
            )
            result["meta"]["official_poll_validation"] = {
                "target_series": "error",
                "method_version": "none",
                "cutoff_ts": self._resolve_cutoff_ts(),
                "error": repr(e),
                "metrics": {
                    "mae": None,
                    "rmse": None,
                    "margin_error": None,
                    "leader_match": None,
                },
                "by_candidate": {},
                "source_poll_ids": [],
            }

        finished_at = dt.datetime.now(dt.timezone.utc)
        result["meta"]["finished_at"] = finished_at.isoformat()
        # Wall seconds — paper-writer's `tab:capacity` "Wall (s)" column directly.
        try:
            started_at = dt.datetime.fromisoformat(result["meta"]["started_at"])
            result["meta"]["wall_seconds"] = round((finished_at - started_at).total_seconds(), 2)
        except Exception:
            pass
        return result
