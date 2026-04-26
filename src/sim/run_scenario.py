"""Region-level simulation runner.

CLI:
    docker compose run --rm app python -m src.sim.run_scenario --region seoul_mayor
    docker compose run --rm app python -m src.sim.run_scenario --region all

Reads:
    _workspace/contracts/data_paths.json
    _workspace/data/scenarios/<region_id>.json   (if present)
    _workspace/checkpoints/policy.json           (if present — sample/timestep policy)
    DuckDB persona_core / persona_text tables    (if ingested)

Writes:
    _workspace/snapshots/results/<scenario_id>.json
    _workspace/snapshots/results_index.json
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from .election_env import ElectionEnv
from .voter_agent import VoterAgent, build_default_backend

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_PATH = REPO_ROOT / "_workspace" / "contracts" / "data_paths.json"
POLICY_PATH = REPO_ROOT / "_workspace" / "checkpoints" / "policy.json"
SCENARIO_DIR = REPO_ROOT / "_workspace" / "data" / "scenarios"
RESULTS_DIR = REPO_ROOT / "_workspace" / "snapshots" / "results"
RESULTS_INDEX = REPO_ROOT / "_workspace" / "snapshots" / "results_index.json"
SNAPSHOTS_DIR = REPO_ROOT / "_workspace" / "snapshots"  # for {region_id}_result.json mirror

# Index is appended from multiple regions concurrently; serialize the writer.
_INDEX_LOCK = asyncio.Lock()


# ---------------------------------------------------------------------------
# Config loaders
# ---------------------------------------------------------------------------
def load_contracts() -> dict[str, Any]:
    with CONTRACTS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_policy() -> dict[str, Any]:
    if not POLICY_PATH.exists():
        return {}
    try:
        with POLICY_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Could not parse policy.json: %s", e)
        return {}


def load_scenario(region_id: str) -> dict[str, Any]:
    """Return scenario dict; synthesize a stub if file missing (degraded mode).

    Adapts data-engineer's curated JSON shape to sim's internal field names:
        events[] (id/date/type/description) → seed_events[] (event_id/timestep/type/summary/target/polarity)
        polls[]  (date/method/<candidate_id>/undecided) → raw_polls[] (n/mode/day/shares/quality)
    Missing `gov_approval`, `scenario_id`, `contest_id` get sensible defaults.
    """
    path = SCENARIO_DIR / f"{region_id}.json"
    if not path.exists():
        logger.warning("No scenario file for %s; using stub.", region_id)
        return {
            "scenario_id": f"{region_id}__stub",
            "region_id": region_id,
            "contest_id": region_id,
            "label": region_id,
            "candidates": [
                {"id": "cand_A", "name": "후보 A", "party": "더불어민주당", "withdrawn": False},
                {"id": "cand_B", "name": "후보 B", "party": "국민의힘", "withdrawn": False},
                {"id": "cand_C", "name": "후보 C", "party": "무소속", "withdrawn": False},
            ],
            "seed_events": [],
            "raw_polls": [],
            "gov_approval": 0.38,
        }
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return _adapt_scenario(raw, region_id)


def _adapt_scenario(raw: dict[str, Any], region_id: str) -> dict[str, Any]:
    """Normalize the curated scenario JSON into sim's internal shape."""
    # base fields
    election_date = raw.get("election_date") or raw.get("date") or "2026-06-03"
    try:
        e_date = dt.date.fromisoformat(election_date)
    except Exception:
        e_date = dt.date(2026, 6, 3)

    candidates = []
    cand_ids: set[str] = set()
    for c in raw.get("candidates", []):
        cid = c.get("id") or c.get("candidate_id")
        if not cid:
            continue
        cand_ids.add(cid)
        # Hill-climbing R3 finding: candidate background + key_pledges in [후보]
        # block (v2 stack) drops MAE from 0.4702 → 0.2702 alone, → 0.0298 with
        # v4 NESDC anchor. Preserve through to voter_agent.user_prompt.
        candidates.append(
            {
                "id": cid,
                "name": c.get("name", cid),
                "party": c.get("party") or c.get("party_name") or "무소속",
                "party_name": c.get("party_name") or c.get("party") or "무소속",
                "withdrawn": bool(c.get("withdrawn", False)),
                "background": (c.get("background") or "").strip(),
                "key_pledges": list(c.get("key_pledges") or []),
                "slogan": (c.get("slogan") or "").strip(),
            }
        )

    # ---- events[] → seed_events[]
    raw_events = raw.get("seed_events") or raw.get("events") or []
    seed_events: list[dict[str, Any]] = []
    for ev in raw_events:
        ev_date = ev.get("date")
        try:
            d = dt.date.fromisoformat(ev_date) if ev_date else None
        except Exception:
            d = None
        ts = ev.get("timestep")
        if ts is None and d is not None:
            # normalize negative-days-to-election → timestep 0..N
            days_before = (e_date - d).days
            ts = max(0, 30 - days_before) // 7  # rough weekly bucket from 30d window
        seed_events.append(
            {
                "event_id": ev.get("event_id") or ev.get("id"),
                "timestep": int(ts or 0),
                "type": ev.get("type", "event"),
                "summary": ev.get("summary") or ev.get("description") or "",
                "target": ev.get("target"),  # may be None — media_shock then no-ops
                "polarity": float(ev.get("polarity", 0.0) or 0.0),
                "source": ev.get("source"),
            }
        )

    # ---- polls[] → raw_polls[] (shares are top-level keys matching candidate IDs)
    raw_polls = raw.get("raw_polls") or raw.get("polls") or []
    polls: list[dict[str, Any]] = []
    for p in raw_polls:
        if "shares" in p:
            shares = {k: float(v) / 100.0 if v and v > 1 else float(v or 0)
                      for k, v in p["shares"].items() if k in cand_ids}
        else:
            shares = {}
            for k, v in p.items():
                if k in cand_ids:
                    try:
                        v_f = float(v)
                        shares[k] = v_f / 100.0 if v_f > 1 else v_f
                    except (TypeError, ValueError):
                        continue
        d_str = p.get("date")
        try:
            d = dt.date.fromisoformat(d_str) if d_str else None
        except Exception:
            d = None
        day = p.get("day")
        if day is None and d is not None:
            day = (d - (e_date - dt.timedelta(days=30))).days
        polls.append(
            {
                "pollster": p.get("pollster") or p.get("method") or "unknown",
                "mode": p.get("mode") or p.get("method") or "unknown",
                "n": int(p.get("n", 1000) or 1000),
                "day": int(day or 0),
                "shares": shares,
                "quality": float(p.get("quality", 1.0) or 1.0),
            }
        )

    return {
        "scenario_id": raw.get("scenario_id") or f"{region_id}__{election_date}",
        "region_id": region_id,
        "contest_id": raw.get("contest_id") or region_id,
        "label": raw.get("label", region_id),
        "contest": raw.get("contest"),
        "district": raw.get("district"),
        "parties": raw.get("parties", []),
        "candidates": candidates,
        "seed_events": seed_events,
        "raw_polls": polls,
        "gov_approval": float(raw.get("gov_approval", 0.38)),
        "key_issues": raw.get("key_issues", []),
        "issues": raw.get("issues", []),
        "frames": raw.get("frames", []),
        "scenario_notes": raw.get("scenario_notes", ""),
        "prediction_only_assumption": raw.get("prediction_only_assumption"),
        "simulation": raw.get("simulation", {}),
        "counterfactual": raw.get("counterfactual")
        or raw.get("counterfactual_inference"),
        "election_date": election_date,
        "incumbent_party": raw.get("incumbent_party"),
    }


# ---------------------------------------------------------------------------
# Persona loaders
# ---------------------------------------------------------------------------
def _synth_persona(idx: int, region_label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fallback persona used when DuckDB is empty (smoke-test path)."""
    age = 25 + (idx * 7) % 50
    sex = "여" if idx % 2 == 0 else "남"
    edu = ["고졸", "전문대졸", "대졸", "대학원졸"][idx % 4]
    occ = ["사무직", "자영업", "전문직", "학생", "주부", "은퇴자"][idx % 6]
    p = {
        "uuid": f"synth-{region_label}-{idx:04d}",
        "age": age,
        "sex": sex,
        "education_level": edu,
        "occupation": occ,
        "marital_status": "기혼" if age >= 35 else "미혼",
        "province": region_label,
        "district": region_label,
    }
    t = {
        "persona": (
            f"{age}세 {sex}성 {occ}. 평소 정치 뉴스를 가끔 챙겨보고, "
            f"생활물가와 일자리에 민감하다."
        ),
        "professional_persona": f"{occ}로서 직장과 가정의 균형을 중시한다.",
        "family_persona": "가족 안정과 자녀 교육을 우선한다.",
        "cultural_background": "지역 사회의 변화에 관심이 많다.",
    }
    return p, t


def load_personas_for_region(
    region_id: str,
    region_label: str,
    n: int,
    contracts: dict[str, Any],
    seed: int = 42,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Pull from DuckDB if available, else synthesize."""
    db_path = REPO_ROOT / contracts["duckdb_path"]
    if db_path.exists():
        try:
            import duckdb  # type: ignore

            con = duckdb.connect(str(db_path), read_only=True)
            try:
                view = f"personas_{region_id}"
                # Verify view exists
                exists = con.execute(
                    "SELECT COUNT(*) FROM duckdb_views() WHERE view_name = ?",
                    [view],
                ).fetchone()[0]
                if not exists:
                    raise RuntimeError(f"view {view} not present in DB")
                core_cols = [
                    r[0]
                    for r in con.execute(
                        f"SELECT * FROM \"{view}\" LIMIT 0"
                    ).description
                ]
                core_rows = con.execute(
                    f"SELECT * FROM \"{view}\" USING SAMPLE {n} ROWS (reservoir, {seed})"
                ).fetchall()
                core_dicts = [dict(zip(core_cols, row)) for row in core_rows]
                # text join
                uuids = [d["uuid"] for d in core_dicts if d.get("uuid")]
                text_map: dict[str, dict[str, Any]] = {}
                if uuids:
                    text_table = contracts.get("persona_text_table", "persona_text")
                    placeholders = ",".join(["?"] * len(uuids))
                    try:
                        rows = con.execute(
                            f"SELECT * FROM \"{text_table}\" WHERE uuid IN ({placeholders})",
                            uuids,
                        ).fetchall()
                        cols = [
                            r[0]
                            for r in con.execute(
                                f"SELECT * FROM \"{text_table}\" LIMIT 0"
                            ).description
                        ]
                        for row in rows:
                            d = dict(zip(cols, row))
                            text_map[d["uuid"]] = d
                    except Exception as e:
                        logger.warning("persona_text join failed: %s", e)
                out = []
                for d in core_dicts:
                    out.append((d, text_map.get(d.get("uuid"), {})))
                if out:
                    logger.info("Loaded %d personas from DuckDB view %s", len(out), view)
                    return out
            finally:
                con.close()
        except Exception as e:
            logger.warning("DuckDB persona load failed (%s); using synth.", e)
    return [_synth_persona(i, region_label) for i in range(n)]


# ---------------------------------------------------------------------------
# Per-region runner
# ---------------------------------------------------------------------------
async def run_region(
    region: dict[str, Any],
    contracts: dict[str, Any],
    policy: dict[str, Any],
    *,
    backend,
    sample_n: int | None = None,
    timesteps: int | None = None,
    kg_retriever: Any | None = None,
    is_mock: bool = False,
) -> Path:
    region_id = region["id"]
    region_label = region.get("label", region_id)
    scenario = load_scenario(region_id)
    # Tag dry-run results so the dashboard never confuses mock with live.
    # Real-LLM runs land at scenario_id = "<region>_2026"; mocks land at
    # "<region>_2026__mock". Dashboard's freshest-by-wrote_at logic then
    # picks whichever the operator most recently produced.
    if is_mock and not scenario.get("scenario_id", "").endswith("__mock"):
        scenario["scenario_id"] = f"{scenario.get('scenario_id', region_id)}__mock"

    # Resolve per-region sample_n from policy.json (regions[<id>].persona_n) → fallback
    # to global policy.per_region_persona_n → contracts → env var → 20.
    region_policy = (policy.get("regions") or {}).get(region_id, {})
    per_region_default = (
        contracts.get("persona_sample_per_region", {})
        if isinstance(contracts.get("persona_sample_per_region"), dict)
        else {}
    )
    if isinstance(per_region_default, dict):
        contract_n = per_region_default.get(region_id)
    else:
        contract_n = None
    n = (
        sample_n
        or region_policy.get("persona_n")
        or policy.get("per_region_persona_n")
        or contract_n
        or int(os.environ.get("POLITIKAST_PERSONA_N", "20"))
    )
    T = (
        timesteps
        or region_policy.get("timesteps")
        or policy.get("timesteps")
    )
    interview_n = region_policy.get(
        "interview_n",
        int(os.environ.get("POLITIKAST_N_INTERVIEWS", "5")),
    )

    personas = load_personas_for_region(region_id, region_label, n, contracts)
    voters = [
        VoterAgent(
            persona=p,
            persona_text=t,
            backend=backend,
            region_label=region_label,
            contest_id=scenario.get("contest_id", region_id),
        )
        for p, t in personas
    ]

    env = ElectionEnv(
        region_id=region_id,
        contest_id=scenario.get("contest_id", region_id),
        candidates=scenario["candidates"],
        timesteps=T,
        kg_retriever=kg_retriever,
        scenario_meta=scenario,
        concurrency=int(os.environ.get("POLITIKAST_CONCURRENCY", "8")),
        n_interviews=int(interview_n),
    )
    result = await env.run(voters)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario_id = result["scenario_id"]
    out_path = RESULTS_DIR / f"{region_id}__{scenario_id}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    # Mirror to {region_id}_result.json (per #11 task description — dashboard polls this).
    mirror_path = SNAPSHOTS_DIR / f"{region_id}_result.json"
    with mirror_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info("[%s] wrote %s (mirror: %s)", region_id, out_path, mirror_path.name)
    await _append_index_async(out_path, result)
    return out_path


def _append_index(path: Path, result: dict[str, Any]) -> None:
    """Synchronous index writer (kept for smoke.py + single-region callers)."""
    idx: list[dict[str, Any]] = []
    if RESULTS_INDEX.exists():
        try:
            with RESULTS_INDEX.open("r", encoding="utf-8") as f:
                idx = json.load(f)
            if not isinstance(idx, list):
                idx = []
        except Exception:
            idx = []
    # `__mock` = run_scenario --dry-run (real env loop, mock backend).
    # `__smoke` = src.sim.smoke fixture (mock backend, synthetic candidates).
    # Both are non-LLM artifacts and dashboard's headline filter must skip them.
    sid = result["scenario_id"]
    is_mock = sid.endswith("__mock") or sid.endswith("__smoke")
    meta = result.get("meta") or {}
    counterfactual = meta.get("counterfactual") or {}
    opv = meta.get("official_poll_validation") or {}
    entry = {
        "path": str(path.relative_to(REPO_ROOT)),
        "mirror_path": meta.get(
            "result_mirror_path",
            f"_workspace/snapshots/{result['region_id']}_result.json",
        ),
        "scenario_id": result["scenario_id"],
        "region_id": result["region_id"],
        "persona_n": result["persona_n"],
        "timestep_count": result["timestep_count"],
        "winner": (result.get("final_outcome") or {}).get("winner"),
        "is_mock": is_mock,
        "is_counterfactual": bool(counterfactual and counterfactual.get("enabled")),
        "intervention_id": counterfactual.get("intervention_id"),
        "target_series": opv.get("target_series"),
        "poll_targets_visible_to_agents": meta.get("poll_targets_visible_to_agents"),
        "wrote_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    # dedupe by scenario_id (latest wins)
    idx = [e for e in idx if e.get("scenario_id") != entry["scenario_id"]]
    idx.append(entry)
    with RESULTS_INDEX.open("w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)


async def _append_index_async(path: Path, result: dict[str, Any]) -> None:
    """Async wrapper — serializes concurrent writers under _INDEX_LOCK."""
    async with _INDEX_LOCK:
        await asyncio.to_thread(_append_index, path, result)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
async def _main_async(args: argparse.Namespace) -> int:
    contracts = load_contracts()
    policy = load_policy()

    regions = contracts["regions"]
    if args.region != "all":
        # Comma-separated multi-region support (Phase B v2 triple-fire spec):
        # `--region seoul_mayor,busan_buk_gap,daegu_mayor` runs all three in
        # the same asyncio.gather batch, sharing one LLMPool.
        wanted = {x.strip() for x in args.region.split(",") if x.strip()}
        regions = [r for r in regions if r["id"] in wanted]
        if not regions:
            print(f"[run_scenario] unknown region(s): {args.region}", file=sys.stderr)
            return 2
        missing = wanted - {r["id"] for r in regions}
        if missing:
            print(
                f"[run_scenario] WARN unknown region id(s) ignored: {sorted(missing)}",
                file=sys.stderr,
            )
    elif policy.get("p0_regions"):
        wanted = set(policy["p0_regions"])
        regions = [r for r in regions if r["id"] in wanted]

    # Apply policy.json feature_flags as POLITIKAST_FEATURES if user hasn't overridden
    if policy.get("feature_flags") and not os.environ.get("POLITIKAST_FEATURES"):
        flags = policy["feature_flags"]
        active = sorted(k for k, v in flags.items() if v)
        os.environ["POLITIKAST_FEATURES"] = ",".join(active) if active else "_none_"
        logger.info("Applied policy feature_flags: %s", active or "(none)")

    if args.dry_run:
        from .smoke import _mock_backend_factory  # local import — keeps prod path clean

        backend = _mock_backend_factory(seed=args.seed)
        logger.warning("[dry-run] using MOCK backend — no Gemini calls.")
    else:
        backend = build_default_backend()

    # Optional KG retriever — kg-engineer ships KGRetriever(G, index) +
    # build_kg_from_scenarios() reading SCENARIO_DIR. Fall back gracefully.
    kg_retriever = None
    try:
        from src.kg.builder import build_kg_from_scenarios  # type: ignore
        from src.kg.retriever import KGRetriever  # type: ignore

        G, index = build_kg_from_scenarios(SCENARIO_DIR)
        kg_retriever = KGRetriever(G, index)
        logger.info("KGRetriever loaded (nodes=%d).", G.number_of_nodes())
    except Exception as e:
        logger.info("KGRetriever unavailable (%s); trying StubRetriever.", e)
        try:
            from src.kg.retriever import StubRetriever  # type: ignore

            kg_retriever = StubRetriever()
        except Exception:
            logger.info("StubRetriever also unavailable; using null retriever.")

    # Phase 3: regions run in parallel (asyncio.gather). Failures isolated per region.
    parallel = not args.sequential
    started_at = dt.datetime.now(dt.timezone.utc)
    logger.info(
        "[run_scenario] starting %d region(s) (%s, dry_run=%s)",
        len(regions),
        "parallel" if parallel else "sequential",
        args.dry_run,
    )

    async def _run_one(region: dict[str, Any]) -> tuple[str, Path | None, str | None]:
        rid = region["id"]
        try:
            p = await run_region(
                region,
                contracts,
                policy,
                backend=backend,
                sample_n=args.sample_n,
                timesteps=args.timesteps,
                kg_retriever=kg_retriever,
                is_mock=args.dry_run,
            )
            print(f"[run_scenario] OK {rid} -> {p}")
            return rid, p, None
        except Exception as e:
            logger.exception("region %s failed: %s", rid, e)
            print(f"[run_scenario] FAIL {rid}: {e}", file=sys.stderr)
            return rid, None, repr(e)

    if parallel:
        results = await asyncio.gather(*[_run_one(r) for r in regions])
    else:
        results = []
        for r in regions:
            results.append(await _run_one(r))

    paths = [p for _, p, _ in results if p is not None]
    failures = [(rid, err) for rid, p, err in results if p is None]
    elapsed = (dt.datetime.now(dt.timezone.utc) - started_at).total_seconds()
    print(
        f"[run_scenario] wrote {len(paths)}/{len(regions)} result file(s) "
        f"in {elapsed:.1f}s. failures={len(failures)}"
    )
    if failures:
        for rid, err in failures:
            print(f"[run_scenario]   FAIL {rid}: {err}", file=sys.stderr)
    # exit 0 even on partial success — Phase 3 prefers partial > nothing
    return 0 if paths else 1


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=os.environ.get("POLITIKAST_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="PolitiKAST region runner")
    parser.add_argument("--region", default="all", help="region id from data_paths.json or 'all'")
    parser.add_argument("--sample-n", type=int, default=None)
    parser.add_argument("--timesteps", type=int, default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="use mock backend (real scenario+personas, no Gemini calls). For #10 when keys are blocked.",
    )
    parser.add_argument("--seed", type=int, default=11, help="seed for dry-run mock backend.")
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="run regions one-at-a-time (default: parallel via asyncio.gather).",
    )
    args = parser.parse_args(argv)
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    sys.exit(main())
