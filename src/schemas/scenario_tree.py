"""ScenarioTree — Phase 6 beam-search artifact schema.

`BeamSearch.expand()` (in `src/sim/scenario_tree.py`) emits a `ScenarioTree`
that the public API surfaces as a vertical Sankey. Node-level data may be
several thousand entries — store as flat dict keyed by `node_id` for O(1)
lookup; tree topology lives in each node's `parent_id` / `children` fields.

`extra="forbid"` — 박제된 후 외부 수정/허위 필드 금지.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .beam_event import BeamEvent

ProposerName = Literal["kg", "llm", "custom", "composite"]


class BeamConfig(BaseModel):
    """Parameters fed into `BeamSearch.expand()` — frozen on the artifact."""

    model_config = ConfigDict(extra="forbid")

    beam_width: int = Field(ge=1, description="top-W kept per depth")
    beam_depth: int = Field(ge=1, description="max depth (root excluded)")
    k_propose: int = Field(default=3, ge=1, description="events proposed per leaf")
    proposer: ProposerName = "composite"
    # Random seed for deterministic LLM proposers / sim-level sampling.
    seed: int = 11
    # Optional cap on number of voter agents per ElectionEnv.run() inside the
    # beam loop. Falls back to scenario/policy default when None.
    sample_n: Optional[int] = None
    # Optional cap on ElectionEnv timesteps per node simulation.
    timesteps: Optional[int] = None
    # When True, `BeamSearch` raises FirewallViolation if a proposed event
    # has occurs_at <= node.event.occurs_at (or <= as_of for root children).
    strict_temporal: bool = True


class BeamNode(BaseModel):
    """One node in the scenario tree — root or expanded leaf.

    Root has `parent_id=None` and `event=None` — it represents the as_of
    state with frozen calibrated params + KG snapshot at cutoff=as_of.
    """

    model_config = ConfigDict(extra="forbid")

    node_id: str
    parent_id: Optional[str] = None
    depth: int = Field(ge=0)
    event: Optional[BeamEvent] = None  # root → None
    cumulative_p: float = Field(ge=0.0, le=1.0)
    sim_result_ref: str = Field(
        ...,
        description=(
            "_workspace/snapshots/results/{scenario_id}.json relative path; "
            "stored so frontend can drill down to ScenarioResult on click."
        ),
    )
    leader_candidate_id: str
    predicted_shares: dict[str, float] = Field(default_factory=dict)
    children: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _root_consistency(self) -> "BeamNode":
        if self.parent_id is None and self.depth != 0:
            raise ValueError("root node (parent_id=None) must have depth=0")
        if self.parent_id is None and self.event is not None:
            raise ValueError("root node must not carry an event")
        if self.parent_id is not None and self.depth == 0:
            raise ValueError("non-root node must have depth >= 1")
        return self


class ScenarioTree(BaseModel):
    """Top-level beam-search artifact — written under
    `_workspace/snapshots/scenario_trees/{tree_id}.json`.
    """

    model_config = ConfigDict(extra="forbid")

    tree_id: str
    region_id: str
    contest_id: str
    as_of: dt.date
    election_date: dt.date
    config: BeamConfig
    root_id: str
    nodes: dict[str, BeamNode]
    mlflow_run_id: Optional[str] = None
    built_at: dt.datetime = Field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc)
    )
    # Free-form provenance — beam search version, KG snapshot ref, calibration
    # profile id, etc. Always present (default {}) so downstream readers don't
    # branch on missing key.
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _tree_invariants(self) -> "ScenarioTree":
        if self.root_id not in self.nodes:
            raise ValueError(
                f"root_id={self.root_id!r} not present in nodes dict"
            )
        root = self.nodes[self.root_id]
        if root.parent_id is not None or root.depth != 0 or root.event is not None:
            raise ValueError("root node violates root invariants")
        # cross-reference parent / child consistency
        for nid, node in self.nodes.items():
            if node.parent_id is not None and node.parent_id not in self.nodes:
                raise ValueError(
                    f"node {nid} parent_id={node.parent_id!r} missing from nodes"
                )
            for cid in node.children:
                if cid not in self.nodes:
                    raise ValueError(
                        f"node {nid} child {cid!r} missing from nodes"
                    )
                child = self.nodes[cid]
                if child.parent_id != nid:
                    raise ValueError(
                        f"child {cid} parent_id mismatch (expected {nid}, got {child.parent_id})"
                    )
        return self


__all__ = ["BeamConfig", "BeamNode", "ScenarioTree", "ProposerName"]
