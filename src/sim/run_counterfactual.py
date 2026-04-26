"""Counterfactual intervention runner.

CLI:
    python -m src.sim.run_counterfactual \
      --region daegu_mayor \
      --intervention choo_nomination_actual \
      --dry-run --sample-n 5 --timesteps 1

Counterfactual runs use the same persona/KG/voter loop as `run_scenario`, but
they patch the scenario-local candidate/event state and mark the result as
`target_series=counterfactual_prediction`. Official poll targets remain hidden
from voter prompts unless `--expose-poll-targets` is explicitly supplied.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import datetime as dt
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

from .election_env import ElectionEnv
from .run_scenario import (
    REPO_ROOT,
    RESULTS_DIR,
    SCENARIO_DIR,
    SNAPSHOTS_DIR,
    _append_index,
    load_contracts,
    load_personas_for_region,
    load_policy,
    load_scenario,
)
from .voter_agent import VoterAgent, build_default_backend

logger = logging.getLogger(__name__)

INTERVENTION_DIR = REPO_ROOT / "_workspace" / "data" / "interventions"


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "counterfactual"


def _load_intervention(region_id: str, ref: str) -> tuple[dict[str, Any], Path]:
    candidate = Path(ref)
    if candidate.exists():
        path = candidate
    else:
        name = ref if ref.endswith(".json") else f"{ref}.json"
        path = INTERVENTION_DIR / region_id / name
    if not path.exists():
        raise FileNotFoundError(f"intervention not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"intervention must be a JSON object: {path}")
    return data, path


def _candidate_id(candidate: dict[str, Any]) -> str | None:
    cid = candidate.get("id") or candidate.get("candidate_id")
    return str(cid) if cid else None


def _apply_candidate_patches(
    candidates: list[dict[str, Any]], patches: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    out = [copy.deepcopy(c) for c in candidates]
    by_id = {_candidate_id(c): c for c in out}

    for patch in patches:
        op = str(patch.get("op", "set")).lower()
        cid = patch.get("candidate_id") or patch.get("id")
        candidate = copy.deepcopy(patch.get("candidate") or {})
        if not cid:
            cid = _candidate_id(candidate)
        if not cid:
            raise ValueError(f"candidate patch missing candidate_id: {patch}")
        cid = str(cid)

        if op == "remove":
            out = [c for c in out if _candidate_id(c) != cid]
            by_id = {_candidate_id(c): c for c in out}
            continue

        if op in {"withdraw", "withdrawn"}:
            fields = {"withdrawn": True}
        else:
            fields = copy.deepcopy(patch.get("fields") or {})

        if op == "upsert" and cid not in by_id:
            if not candidate:
                candidate = {"id": cid, "candidate_id": cid, "name": cid, "party": "p_indep"}
            candidate.setdefault("id", cid)
            candidate.setdefault("candidate_id", cid)
            out.append(candidate)
            by_id[cid] = candidate

        if cid not in by_id:
            raise KeyError(f"candidate patch references unknown candidate_id={cid}")

        if op == "upsert" and candidate:
            by_id[cid].update(candidate)
        by_id[cid].update(fields)
        by_id[cid].setdefault("candidate_id", cid)
        by_id[cid].setdefault("id", cid)

    return out


def _event_patch_to_seed_event(patch: dict[str, Any]) -> dict[str, Any]:
    event = copy.deepcopy(patch.get("event") or patch)
    event_id = event.get("event_id") or event.get("id")
    if not event_id:
        raise ValueError(f"event patch missing event_id/id: {patch}")
    return {
        "event_id": event_id,
        "timestep": int(event.get("timestep", patch.get("timestep", 0)) or 0),
        "type": event.get("type", "event"),
        "summary": event.get("summary") or event.get("description") or "",
        "target": event.get("target"),
        "polarity": float(event.get("polarity", 0.0) or 0.0),
        "source": event.get("source"),
        "source_url": event.get("source_url"),
    }


def apply_intervention(
    base: dict[str, Any], intervention: dict[str, Any], *, region_id: str
) -> dict[str, Any]:
    scenario = copy.deepcopy(base)
    intervention_id = _slug(
        str(intervention.get("intervention_id") or intervention.get("id") or "adhoc")
    )
    base_scenario_id = str(scenario.get("scenario_id") or region_id)

    scenario["candidates"] = _apply_candidate_patches(
        scenario.get("candidates", []),
        list(intervention.get("candidate_patches") or []),
    )

    seed_events = list(copy.deepcopy(scenario.get("seed_events") or []))
    for patch in intervention.get("event_patches") or []:
        op = str(patch.get("op", "add")).lower()
        if op == "remove":
            remove_id = patch.get("event_id") or patch.get("id")
            seed_events = [ev for ev in seed_events if ev.get("event_id") != remove_id]
            continue
        seed_events.append(_event_patch_to_seed_event(patch))
    scenario["seed_events"] = seed_events

    scenario["scenario_id"] = f"{base_scenario_id}__cf_{intervention_id}"
    scenario["counterfactual"] = {
        "enabled": True,
        "intervention_id": intervention_id,
        "base_region_id": region_id,
        "base_scenario_id": base_scenario_id,
        "mode": intervention.get("mode", "counterfactual_prediction"),
        "title": intervention.get("title"),
        "reason": intervention.get(
            "reason",
            "Scenario-local intervention applied after calibration; no held-out poll label is available.",
        ),
        "calibration_profile": intervention.get("calibration_profile", "frozen_current"),
        "frozen_params": intervention.get("frozen_params", True),
        "source_urls": list(intervention.get("source_urls") or []),
        "event_patches": list(intervention.get("event_patches") or []),
        "candidate_patches": list(intervention.get("candidate_patches") or []),
        "one_candidate_per_party": intervention.get("one_candidate_per_party"),
        "poll_targets_visible_to_agents": False,
    }
    return scenario


def _find_region(contracts: dict[str, Any], region_id: str) -> dict[str, Any]:
    for region in contracts.get("regions", []):
        if region.get("id") == region_id:
            return region
    return {"id": region_id, "label": region_id}


def _policy_values(
    contracts: dict[str, Any],
    policy: dict[str, Any],
    region_id: str,
    sample_n: int | None,
    timesteps: int | None,
) -> tuple[int, int | None, int]:
    region_policy = (policy.get("regions") or {}).get(region_id, {})
    per_region_default = contracts.get("persona_sample_per_region", {})
    contract_n = (
        per_region_default.get(region_id)
        if isinstance(per_region_default, dict)
        else None
    )
    n = (
        sample_n
        or region_policy.get("persona_n")
        or policy.get("per_region_persona_n")
        or contract_n
        or int(os.environ.get("POLITIKAST_PERSONA_N", "20"))
    )
    T = timesteps or region_policy.get("timesteps") or policy.get("timesteps")
    interviews = region_policy.get(
        "interview_n",
        int(os.environ.get("POLITIKAST_N_INTERVIEWS", "5")),
    )
    return int(n), int(T) if T is not None else None, int(interviews)


def _load_kg_retriever() -> Any | None:
    try:
        from src.kg.builder import build_kg_from_scenarios  # type: ignore
        from src.kg.retriever import KGRetriever  # type: ignore

        G, index = build_kg_from_scenarios(SCENARIO_DIR)
        logger.info("KGRetriever loaded (nodes=%d).", G.number_of_nodes())
        return KGRetriever(G, index)
    except Exception as e:
        logger.info("KGRetriever unavailable (%s); trying StubRetriever.", e)
        try:
            from src.kg.retriever import StubRetriever  # type: ignore

            return StubRetriever()
        except Exception:
            logger.info("StubRetriever also unavailable; using null retriever.")
            return None


def _attach_delta(result: dict[str, Any], baseline_path: Path) -> None:
    with baseline_path.open("r", encoding="utf-8") as f:
        baseline = json.load(f)
    b_final = baseline.get("final_outcome") or {}
    r_final = result.get("final_outcome") or {}
    b_shares = dict(b_final.get("vote_share_by_candidate") or {})
    r_shares = dict(r_final.get("vote_share_by_candidate") or {})
    cids = sorted(set(b_shares) | set(r_shares))
    delta = {
        cid: round(float(r_shares.get(cid, 0.0)) - float(b_shares.get(cid, 0.0)), 4)
        for cid in cids
    }
    cf = result.setdefault("meta", {}).setdefault("counterfactual", {})
    cf["delta_vs_baseline"] = {
        "baseline_path": str(baseline_path),
        "baseline_scenario_id": baseline.get("scenario_id"),
        "baseline_winner": b_final.get("winner"),
        "intervention_winner": r_final.get("winner"),
        "winner_changed": b_final.get("winner") != r_final.get("winner"),
        "vote_share_delta": delta,
    }


async def _run(args: argparse.Namespace) -> Path:
    if args.expose_poll_targets:
        os.environ["POLITIKAST_POLL_TARGETS_VISIBLE_TO_AGENTS"] = "1"
    else:
        os.environ.setdefault("POLITIKAST_POLL_TARGETS_VISIBLE_TO_AGENTS", "0")

    contracts = load_contracts()
    policy = load_policy()
    region = _find_region(contracts, args.region)
    base = load_scenario(args.region)
    intervention, intervention_path = _load_intervention(args.region, args.intervention)
    scenario = apply_intervention(base, intervention, region_id=args.region)

    if args.dry_run and not scenario["scenario_id"].endswith("__mock"):
        scenario["scenario_id"] = f"{scenario['scenario_id']}__mock"

    n, timesteps, interview_n = _policy_values(
        contracts, policy, args.region, args.sample_n, args.timesteps
    )
    personas = load_personas_for_region(
        args.region, region.get("label", args.region), n, contracts, seed=args.seed
    )

    if args.dry_run:
        from .smoke import _mock_backend_factory

        backend = _mock_backend_factory(seed=args.seed)
        logger.warning("[dry-run] using MOCK backend — no external LLM calls.")
    else:
        backend = build_default_backend()

    voters = [
        VoterAgent(
            persona=p,
            persona_text=t,
            backend=backend,
            region_label=region.get("label", args.region),
            contest_id=scenario.get("contest_id", args.region),
        )
        for p, t in personas
    ]
    env = ElectionEnv(
        region_id=args.region,
        contest_id=scenario.get("contest_id", args.region),
        candidates=scenario["candidates"],
        timesteps=timesteps,
        kg_retriever=_load_kg_retriever(),
        scenario_meta=scenario,
        concurrency=int(os.environ.get("POLITIKAST_CONCURRENCY", "8")),
        n_interviews=interview_n,
    )
    result = await env.run(voters)
    result["meta"]["counterfactual"]["intervention_path"] = str(
        intervention_path.relative_to(REPO_ROOT)
    )
    result["meta"]["counterfactual"]["poll_targets_visible_to_agents"] = (
        os.environ.get("POLITIKAST_POLL_TARGETS_VISIBLE_TO_AGENTS", "0")
        .strip()
        .lower()
        in {"1", "true", "yes", "on"}
    )
    if args.baseline_result:
        _attach_delta(result, Path(args.baseline_result))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"{args.region}__{result['scenario_id']}.json"
    mirror_name = f"{args.region}__cf_{result['meta']['counterfactual']['intervention_id']}_result.json"
    mirror_path = SNAPSHOTS_DIR / mirror_name
    result["meta"]["result_mirror_path"] = str(mirror_path.relative_to(REPO_ROOT))
    result["meta"]["wrote_at"] = dt.datetime.now(dt.timezone.utc).isoformat()

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with mirror_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    _append_index(out_path, result)
    logger.info("[%s] wrote %s (mirror: %s)", args.region, out_path, mirror_name)
    return out_path


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=os.environ.get("POLITIKAST_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="PolitiKAST counterfactual runner")
    parser.add_argument("--region", required=True, help="base region id")
    parser.add_argument(
        "--intervention",
        required=True,
        help="intervention id under _workspace/data/interventions/<region>/ or path",
    )
    parser.add_argument("--sample-n", type=int, default=None)
    parser.add_argument("--timesteps", type=int, default=None)
    parser.add_argument("--baseline-result", default=None)
    parser.add_argument("--dry-run", action="store_true", help="use mock backend")
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument(
        "--expose-poll-targets",
        action="store_true",
        help="debug/ablation only: render official poll targets into voter prompts",
    )
    args = parser.parse_args(argv)
    path = asyncio.run(_run(args))
    print(f"[run_counterfactual] OK {args.region} -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
