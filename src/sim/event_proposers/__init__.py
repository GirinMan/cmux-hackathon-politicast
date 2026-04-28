"""Event proposers — sources of `BeamEvent` for scenario tree expansion.

Plug-in registry pattern: new proposer impls register themselves into
`PROPOSER_REGISTRY` on import. `BeamSearch` accepts a single `EventProposer`
instance (typically the `CompositeProposer`) and never sees the underlying
sources.

All proposers return `BeamEvent` objects whose `candidate_patches` /
`event_patches` follow `_workspace/data/interventions/<region>/*.json`
(run_counterfactual) shape so the beam search can splice them straight into
ElectionEnv `scenario_meta`.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

import datetime as dt

from src.schemas.beam_event import BeamEvent


@runtime_checkable
class EventProposer(Protocol):
    """Common protocol for KG / LLM / custom event sources.

    `propose` MUST be deterministic given the same `(region_id, current_t,
    history, k)` and proposer state — beam search relies on reproducibility
    for tree artifact stability across re-runs.
    """

    name: str

    def propose(
        self,
        region_id: str,
        current_t: dt.datetime,
        history: list[BeamEvent],
        k: int,
    ) -> list[BeamEvent]: ...


# Registry — populated by submodule imports below.
PROPOSER_REGISTRY: dict[str, type] = {}


def register(name: str):
    """Decorator: register a proposer class under `name`.

    Plugin entry point support (`pyproject.toml` `[project.entry-points."politikast.event_proposers"]`)
    can populate this dict at startup; for now in-tree imports do the work.
    """

    def _wrap(cls):
        PROPOSER_REGISTRY[name] = cls
        cls.name = name  # type: ignore[attr-defined]
        return cls

    return _wrap


# In-tree proposers — registered by import side effect.
from .kg import KGConfirmedProposer  # noqa: E402,F401
from .llm import LLMHypotheticalProposer  # noqa: E402,F401
from .custom import CustomJSONProposer  # noqa: E402,F401
from .composite import CompositeProposer  # noqa: E402,F401


__all__ = [
    "EventProposer",
    "PROPOSER_REGISTRY",
    "register",
    "KGConfirmedProposer",
    "LLMHypotheticalProposer",
    "CustomJSONProposer",
    "CompositeProposer",
]
