"""BeamSearch — scenario tree expansion coordinator.

Phase 6 (pipeline-model). Produces a `ScenarioTree` artifact by repeatedly:

1. Asking an `EventProposer` for K successor events at each active leaf.
2. Splicing the events into the base scenario as `event_patches` /
   `candidate_patches` (run_counterfactual-compatible shape).
3. Re-running `ElectionEnv` for each child (signature unchanged — sim is a
   pure dependency).
4. Pruning to the top `beam_width` by `cumulative_p`.

The runner is injectable via `sim_runner` so tests can substitute a
deterministic shim for `ElectionEnv.run`. The CLI (`__main__`) wires up the
real default backend, the KG retriever, and writes the artifact to
`_workspace/snapshots/scenario_trees/{tree_id}.json`.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import datetime as dt
import json
import logging
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from src.kg.firewall import FirewallViolation
from src.schemas.beam_event import BeamEvent
from src.schemas.scenario_tree import BeamConfig, BeamNode, ScenarioTree
from src.sim.event_proposers import (
    CompositeProposer,
    CustomJSONProposer,
    EventProposer,
    KGConfirmedProposer,
    LLMHypotheticalProposer,
    PROPOSER_REGISTRY,
)

from .election_env import ElectionEnv
from .run_counterfactual import (
    _apply_candidate_patches,
    _event_patch_to_seed_event,
)
from .run_scenario import (
    REPO_ROOT,
    load_contracts,
    load_personas_for_region,
    load_policy,
    load_scenario,
)
from .voter_agent import VoterAgent, build_default_backend

logger = logging.getLogger(__name__)

TREES_DIR = REPO_ROOT / "_workspace" / "snapshots" / "scenario_trees"

# ---------------------------------------------------------------------------
# Sim-runner protocol
# ---------------------------------------------------------------------------
# Async callable that takes (scenario_meta, context_kwargs) and returns the
# dict produced by ElectionEnv.run. Tests substitute a deterministic shim;
# the real runner constructs ElectionEnv + voters per call.
SimRunner = Callable[[dict[str, Any], dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass
class _Leaf:
    """Internal mutable state for the active leaves between depth steps."""

    node: BeamNode
    history: list[BeamEvent]
    scenario: dict[str, Any]
    occurs_at: dt.datetime


# ---------------------------------------------------------------------------
# Helpers — patch splicing
# ---------------------------------------------------------------------------
def _splice_event_into_scenario(
    base: dict[str, Any], event: BeamEvent
) -> dict[str, Any]:
    """Apply a single BeamEvent's patches onto a (deep-copied) scenario.

    Two patch shapes are first-class supported (decision: 2026-04-28, team-lead
    task #21 — declarative shape adopted as the BeamEvent canonical form):

    * **Declarative** (PRIMARY — used by pipeline-counterfactual seed JSON and
      by LLM/custom proposers). Free-form key/value modifiers consumed by the
      downstream prompt context and KG enrichment layer:

        candidate_patches=[{"candidate_id": "...", "boost": 0.04, "reason": "..."}, ...]
        event_patches    =[{"issue": "...", "salience": 0.3}, ...]

      Declarative patches are routed to `scenario.candidate_modifiers` and
      `scenario.event_modifiers` — they don't mutate the candidate roster,
      they enrich the simulation context.

    * **Imperative / op-shape** (LEGACY — kept for run_counterfactual
      interop). Same structure that
      `src/sim/run_counterfactual.py::_apply_candidate_patches` /
      `_event_patch_to_seed_event` consumes:

        candidate_patches=[{"op": "set"|"upsert"|"remove"|"withdraw",
                            "candidate_id": "...", "fields": {...}}, ...]
        event_patches    =[{"op": "add"|"remove",
                            "event": {"event_id": "...", ...}}, ...]

      Detected by presence of any of the keys ``op`` / ``fields`` / ``candidate``
      (candidate patches) or ``op`` / ``event`` (event patches).

    The BeamEvent itself is always surfaced as a `seed_event` (so the voter
    prompt's `[주요 사건]` section reflects the splice) and the scenario is
    annotated with the `counterfactual` block so ElectionEnv's
    `_inject_validation_metrics` short-circuits to
    `target_series=counterfactual_prediction` for every beam node.
    """
    scenario = copy.deepcopy(base)

    # ----- Candidate patches ------------------------------------------------
    # Imperative shape applies via run_counterfactual; declarative shape is
    # parked under `candidate_modifiers` for downstream prompt enrichment.
    imperative_cp: list[dict[str, Any]] = []
    declarative_cp: list[dict[str, Any]] = []
    for cp in event.candidate_patches or []:
        if "op" in cp or "fields" in cp or "candidate" in cp:
            imperative_cp.append(cp)
        else:
            declarative_cp.append(cp)
    scenario["candidates"] = _apply_candidate_patches(
        scenario.get("candidates", []), imperative_cp
    )
    if declarative_cp:
        scenario.setdefault("candidate_modifiers", []).extend(declarative_cp)

    # ----- Event patches ----------------------------------------------------
    # Imperative shape becomes a `seed_event`; declarative shape goes to
    # `event_modifiers`. Both are official.
    seed_events = list(scenario.get("seed_events") or [])
    declarative_ep: list[dict[str, Any]] = []
    for patch in event.event_patches or []:
        is_imperative = (
            isinstance(patch, dict)
            and ("op" in patch or "event" in patch)
        )
        if is_imperative:
            op = str(patch.get("op", "add")).lower()
            if op == "remove":
                remove_id = patch.get("event_id") or patch.get("id")
                seed_events = [
                    ev for ev in seed_events if ev.get("event_id") != remove_id
                ]
                continue
            seed_events.append(_event_patch_to_seed_event(patch))
        else:
            declarative_ep.append(patch)
    # Surface the BeamEvent itself in seed_events so the voter prompt's
    # `[주요 사건]` section reflects the splice. (Always — even when only
    # declarative patches were attached, the event must remain visible.)
    if not any(
        se.get("event_id") == event.event_id for se in seed_events
    ):
        seed_events.append(
            {
                "event_id": event.event_id,
                "timestep": 0,
                "type": event.metadata.get("type", "event"),
                "summary": event.description,
                "target": None,
                "polarity": 0.0,
            }
        )
    scenario["seed_events"] = seed_events
    if declarative_ep:
        scenario.setdefault("event_modifiers", []).extend(declarative_ep)

    # Annotate scenario_id so result JSON is uniquely addressable per node.
    base_id = str(scenario.get("scenario_id") or scenario.get("region_id") or "scenario")
    scenario["scenario_id"] = f"{base_id}__beam_{event.event_id}"

    cf = scenario.get("counterfactual")
    if not isinstance(cf, dict):
        cf = {}
        scenario["counterfactual"] = cf
    cf.update(
        {
            "enabled": True,
            "mode": "scenario_tree_branch",
            "intervention_id": event.event_id,
            "base_region_id": scenario.get("region_id"),
            "calibration_profile": "frozen_current",
            "frozen_params": True,
            "reason": (
                "Scenario-tree beam branch: hypothetical/confirmed event spliced "
                "in for forward simulation."
            ),
            "source_urls": [],
            "poll_targets_visible_to_agents": False,
        }
    )
    return scenario


def _leader_and_shares(
    result: dict[str, Any], candidates: list[dict[str, Any]]
) -> tuple[str, dict[str, float]]:
    final = result.get("final_outcome") or {}
    shares = dict(final.get("vote_share_by_candidate") or {})
    leader = final.get("winner")
    if not leader:
        if shares:
            leader = max(shares.items(), key=lambda kv: kv[1])[0]
        elif candidates:
            leader = candidates[0].get("id") or candidates[0].get("candidate_id") or "unknown"
        else:
            leader = "unknown"
    return str(leader), {str(k): float(v) for k, v in shares.items()}


# ---------------------------------------------------------------------------
# BeamSearch
# ---------------------------------------------------------------------------
class BeamSearch:
    """Scenario tree beam-search coordinator."""

    def __init__(
        self,
        *,
        region_id: str,
        contest_id: str,
        as_of: dt.date,
        election_date: dt.date,
        base_scenario: dict[str, Any],
        config: BeamConfig,
        proposer: EventProposer,
        sim_runner: SimRunner,
        tree_id: Optional[str] = None,
    ) -> None:
        self.region_id = region_id
        self.contest_id = contest_id
        self.as_of = as_of
        self.election_date = election_date
        self.base_scenario = copy.deepcopy(base_scenario)
        self.config = config
        self.proposer = proposer
        self.sim_runner = sim_runner
        self.tree_id = tree_id or f"{region_id}_{as_of.isoformat()}_{uuid.uuid4().hex[:8]}"
        self._nodes: dict[str, BeamNode] = {}

    # ------------------------------------------------------------------
    @property
    def _as_of_dt(self) -> dt.datetime:
        return dt.datetime.combine(self.as_of, dt.time(), tzinfo=dt.timezone.utc)

    @property
    def _election_dt(self) -> dt.datetime:
        return dt.datetime.combine(self.election_date, dt.time(), tzinfo=dt.timezone.utc)

    def _node_artifact_path(self, node_id: str) -> Path:
        return TREES_DIR / self.tree_id / "nodes" / f"{node_id}.json"

    def _persist_node_result(self, node_id: str, result: dict[str, Any]) -> str:
        path = self._node_artifact_path(node_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return str(path.relative_to(REPO_ROOT))

    # ------------------------------------------------------------------
    def _validate_temporal(self, parent_t: dt.datetime, event: BeamEvent) -> None:
        if not self.config.strict_temporal:
            return
        if event.occurs_at <= parent_t:
            raise FirewallViolation(
                f"[scenario_tree] proposed event {event.event_id} occurs_at="
                f"{event.occurs_at.isoformat()} <= parent_t={parent_t.isoformat()}"
            )

    # ------------------------------------------------------------------
    async def expand(self) -> ScenarioTree:
        # ----- Root --------------------------------------------------
        root_scenario = copy.deepcopy(self.base_scenario)
        root_id = "root"
        logger.info("[beam] running root sim for tree %s", self.tree_id)
        root_result = await self.sim_runner(
            root_scenario,
            {"node_id": root_id, "depth": 0, "region_id": self.region_id},
        )
        leader, shares = _leader_and_shares(root_result, root_scenario.get("candidates", []))
        root_ref = self._persist_node_result(root_id, root_result)
        root_node = BeamNode(
            node_id=root_id,
            parent_id=None,
            depth=0,
            event=None,
            cumulative_p=1.0,
            sim_result_ref=root_ref,
            leader_candidate_id=leader,
            predicted_shares=shares,
            children=[],
        )
        self._nodes[root_id] = root_node

        # ----- Iterate depth ----------------------------------------
        active: list[_Leaf] = [
            _Leaf(
                node=root_node,
                history=[],
                scenario=root_scenario,
                occurs_at=self._as_of_dt,
            )
        ]

        for depth in range(1, self.config.beam_depth + 1):
            if not active:
                break
            next_candidates: list[tuple[float, _Leaf, BeamEvent, BeamNode]] = []

            for leaf in active:
                if leaf.occurs_at >= self._election_dt:
                    continue
                proposals = list(
                    self.proposer.propose(
                        self.region_id,
                        leaf.occurs_at,
                        leaf.history,
                        self.config.k_propose,
                    )
                )
                logger.info(
                    "[beam] depth=%d leaf=%s proposed=%d",
                    depth,
                    leaf.node.node_id,
                    len(proposals),
                )
                for ev in proposals:
                    self._validate_temporal(leaf.occurs_at, ev)
                    child_id = f"d{depth}_{leaf.node.node_id}__{ev.event_id}"
                    child_scenario = _splice_event_into_scenario(leaf.scenario, ev)
                    child_result = await self.sim_runner(
                        child_scenario,
                        {
                            "node_id": child_id,
                            "depth": depth,
                            "region_id": self.region_id,
                            "event_id": ev.event_id,
                        },
                    )
                    c_leader, c_shares = _leader_and_shares(
                        child_result, child_scenario.get("candidates", [])
                    )
                    cum_p = leaf.node.cumulative_p * float(ev.prior_p)
                    ref = self._persist_node_result(child_id, child_result)
                    child_node = BeamNode(
                        node_id=child_id,
                        parent_id=leaf.node.node_id,
                        depth=depth,
                        event=ev,
                        cumulative_p=max(0.0, min(1.0, cum_p)),
                        sim_result_ref=ref,
                        leader_candidate_id=c_leader,
                        predicted_shares=c_shares,
                        children=[],
                    )
                    next_candidates.append((cum_p, leaf, ev, child_node))

            if not next_candidates:
                break

            # Stable sort: cumulative_p desc, then by event_id for determinism.
            next_candidates.sort(key=lambda t: (-t[0], t[3].node_id))
            kept = next_candidates[: self.config.beam_width]

            new_active: list[_Leaf] = []
            for _cum, parent_leaf, ev, child_node in kept:
                self._nodes[child_node.node_id] = child_node
                # Update parent's children list (need to rebuild — frozen model).
                parent = self._nodes[parent_leaf.node.node_id]
                updated_parent = parent.model_copy(
                    update={"children": parent.children + [child_node.node_id]}
                )
                self._nodes[parent.node_id] = updated_parent
                new_active.append(
                    _Leaf(
                        node=child_node,
                        history=parent_leaf.history + [ev],
                        scenario=_splice_event_into_scenario(parent_leaf.scenario, ev),
                        occurs_at=ev.occurs_at,
                    )
                )
            active = new_active

        tree = ScenarioTree(
            tree_id=self.tree_id,
            region_id=self.region_id,
            contest_id=self.contest_id,
            as_of=self.as_of,
            election_date=self.election_date,
            config=self.config,
            root_id=root_id,
            nodes=self._nodes,
            metadata={
                "proposer": self.config.proposer,
                "n_active_leaves_final": len(active),
            },
        )
        return tree


# ---------------------------------------------------------------------------
# Default sim runner — wires ElectionEnv + voters per call
# ---------------------------------------------------------------------------
def make_default_sim_runner(
    *,
    region_id: str,
    region_label: str,
    contracts: dict[str, Any],
    sample_n: int,
    timesteps: int | None,
    backend: Any,
    kg_retriever: Any | None,
    seed: int = 11,
) -> SimRunner:
    personas = load_personas_for_region(
        region_id, region_label, sample_n, contracts, seed=seed
    )

    async def _run(scenario: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
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
            timesteps=timesteps,
            kg_retriever=kg_retriever,
            scenario_meta=scenario,
            concurrency=int(os.environ.get("POLITIKAST_CONCURRENCY", "8")),
            n_interviews=0,  # interviews not needed per beam node
        )
        return await env.run(voters)

    return _run


# ---------------------------------------------------------------------------
# Proposer factory
# ---------------------------------------------------------------------------
def build_proposer(
    name: str,
    *,
    kg_retriever: Any | None = None,
    as_of: dt.datetime | None = None,
    seed: int = 11,
) -> EventProposer:
    if name == "kg":
        return KGConfirmedProposer(kg_retriever=kg_retriever, as_of=as_of)
    if name == "llm":
        return LLMHypotheticalProposer(seed=seed)
    if name == "custom":
        return CustomJSONProposer()
    if name == "composite":
        return CompositeProposer(
            [
                KGConfirmedProposer(kg_retriever=kg_retriever, as_of=as_of),
                CustomJSONProposer(),
                LLMHypotheticalProposer(seed=seed),
            ]
        )
    if name in PROPOSER_REGISTRY:
        return PROPOSER_REGISTRY[name]()  # best-effort default ctor
    raise ValueError(f"unknown proposer: {name!r}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _resolve_election_date(scenario: dict[str, Any]) -> dt.date:
    raw = (
        scenario.get("election_date")
        or (scenario.get("election") or {}).get("date")
        or "2026-06-03"
    )
    return dt.date.fromisoformat(str(raw))


def _load_kg_retriever() -> Any | None:
    try:
        from src.kg.builder import build_kg_from_scenarios  # type: ignore
        from src.kg.retriever import KGRetriever  # type: ignore
        from .run_scenario import SCENARIO_DIR

        G, index = build_kg_from_scenarios(SCENARIO_DIR)
        return KGRetriever(G, index)
    except Exception as e:
        logger.info("KG retriever unavailable (%s); proceeding without KG.", e)
        return None


async def _cli_main(args: argparse.Namespace) -> Path:
    contracts = load_contracts()
    policy = load_policy()
    scenario = load_scenario(args.region)
    region_label = next(
        (
            r.get("label", args.region)
            for r in contracts.get("regions", [])
            if r.get("id") == args.region
        ),
        args.region,
    )
    election_date = _resolve_election_date(scenario)
    as_of = dt.date.fromisoformat(args.as_of)

    region_policy = (policy.get("regions") or {}).get(args.region, {})
    sample_n = (
        args.sample_n
        or region_policy.get("persona_n")
        or policy.get("per_region_persona_n")
        or 8
    )
    timesteps = args.timesteps or region_policy.get("timesteps") or policy.get("timesteps")

    config = BeamConfig(
        beam_width=args.beam_width,
        beam_depth=args.beam_depth,
        k_propose=args.k_propose,
        proposer=args.proposer,
        seed=args.seed,
        sample_n=int(sample_n),
        timesteps=int(timesteps) if timesteps else None,
    )

    if args.dry_run:
        from .smoke import _mock_backend_factory

        backend = _mock_backend_factory(seed=args.seed)
    else:
        backend = build_default_backend()

    kg_retriever = _load_kg_retriever() if not args.no_kg else None
    proposer = build_proposer(
        args.proposer,
        kg_retriever=kg_retriever,
        as_of=dt.datetime.combine(as_of, dt.time(), tzinfo=dt.timezone.utc),
        seed=args.seed,
    )
    sim_runner = make_default_sim_runner(
        region_id=args.region,
        region_label=region_label,
        contracts=contracts,
        sample_n=int(sample_n),
        timesteps=int(timesteps) if timesteps else None,
        backend=backend,
        kg_retriever=kg_retriever,
        seed=args.seed,
    )
    search = BeamSearch(
        region_id=args.region,
        contest_id=scenario.get("contest_id", args.region),
        as_of=as_of,
        election_date=election_date,
        base_scenario=scenario,
        config=config,
        proposer=proposer,
        sim_runner=sim_runner,
        tree_id=args.tree_id,
    )
    tree = await search.expand()

    # Artifact location: explicit `--artifact` (used by backend
    # scenario_tree_service spawn) takes precedence over the default
    # `_workspace/snapshots/scenario_trees/{tree_id}.json` slot.
    if getattr(args, "artifact", None):
        out_path = Path(args.artifact)
    else:
        out_path = TREES_DIR / f"{tree.tree_id}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        f.write(tree.model_dump_json(indent=2))
    logger.info("[beam] wrote %s (nodes=%d)", out_path, len(tree.nodes))

    # Optional: log to MLflow if available.
    try:
        import mlflow  # type: ignore

        with mlflow.start_run(run_name=f"scenario_tree_{tree.tree_id}"):
            mlflow.log_params(
                {
                    "region_id": args.region,
                    "as_of": as_of.isoformat(),
                    "beam_width": args.beam_width,
                    "beam_depth": args.beam_depth,
                    "proposer": args.proposer,
                }
            )
            mlflow.log_artifact(str(out_path))
    except Exception as e:  # pragma: no cover
        logger.info("MLflow not available (%s); skipping log_artifact.", e)

    return out_path


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=os.environ.get("POLITIKAST_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="PolitiKAST scenario-tree beam search")
    parser.add_argument("--region", required=True)
    parser.add_argument("--as-of", required=True, help="ISO date (YYYY-MM-DD)")
    parser.add_argument("--beam-width", type=int, default=3)
    parser.add_argument("--beam-depth", type=int, default=3)
    parser.add_argument("--k-propose", type=int, default=3)
    parser.add_argument(
        "--proposer",
        choices=["kg", "llm", "custom", "composite"],
        default="composite",
    )
    parser.add_argument("--sample-n", type=int, default=None)
    parser.add_argument("--timesteps", type=int, default=None)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--tree-id", default=None)
    parser.add_argument(
        "--artifact",
        default=None,
        help=(
            "Override artifact output path. Default: "
            "_workspace/snapshots/scenario_trees/{tree_id}.json. "
            "Used by backend scenario_tree_service spawn."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="use mock LLM backend")
    parser.add_argument("--no-kg", action="store_true")
    args = parser.parse_args(argv)
    path = asyncio.run(_cli_main(args))
    print(f"[scenario_tree] OK -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
