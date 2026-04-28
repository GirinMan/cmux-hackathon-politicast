"""CompositeProposer — merges KG / LLM / custom proposers.

Two strategies are supported:

* ``round_robin`` — visits proposers in order, taking 1 event each, until
  ``k`` events are collected or every proposer is exhausted.
* ``priority_weighted`` — concatenates all proposers' outputs, then keeps
  the top ``k`` by ``priority_weight × prior_p`` (stable tie-break by
  ``(occurs_at, event_id)``).

Both strategies preserve determinism: given the same wrapped proposers and
context, the output ordering is reproducible across runs.
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Iterable, Literal, Sequence

from src.schemas.beam_event import BeamEvent

from . import EventProposer, register

logger = logging.getLogger(__name__)

CompositeStrategy = Literal["round_robin", "priority_weighted"]


@register("composite")
class CompositeProposer:
    """Wrap multiple `EventProposer` impls into a single proposer."""

    name = "composite"

    def __init__(
        self,
        proposers: Sequence[EventProposer],
        *,
        strategy: CompositeStrategy = "round_robin",
        priority_weights: dict[str, float] | None = None,
    ) -> None:
        if not proposers:
            raise ValueError("CompositeProposer requires at least one inner proposer")
        self.proposers = list(proposers)
        self.strategy = strategy
        # Default weights — KG confirmed > custom > LLM hypothetical.
        self.priority_weights = priority_weights or {
            "kg_confirmed": 1.0,
            "custom": 0.7,
            "llm_hypothetical": 0.4,
        }

    # ------------------------------------------------------------------
    def _gather(
        self,
        region_id: str,
        current_t: dt.datetime,
        history: list[BeamEvent],
        k: int,
    ) -> list[list[BeamEvent]]:
        """Per-proposer outputs (length = len(proposers))."""
        out: list[list[BeamEvent]] = []
        for p in self.proposers:
            try:
                events = list(p.propose(region_id, current_t, history, k))
            except Exception as e:  # pragma: no cover
                logger.warning("Inner proposer %s failed: %s", getattr(p, "name", p), e)
                events = []
            out.append(events)
        return out

    # ------------------------------------------------------------------
    def propose(
        self,
        region_id: str,
        current_t: dt.datetime,
        history: list[BeamEvent],
        k: int,
    ) -> list[BeamEvent]:
        per_proposer = self._gather(region_id, current_t, history, k)

        if self.strategy == "round_robin":
            cursors = [0] * len(per_proposer)
            seen: set[str] = {h.event_id for h in history}
            out: list[BeamEvent] = []
            while len(out) < k:
                progressed = False
                for i, lst in enumerate(per_proposer):
                    if cursors[i] >= len(lst):
                        continue
                    ev = lst[cursors[i]]
                    cursors[i] += 1
                    progressed = True
                    if ev.event_id in seen:
                        continue
                    seen.add(ev.event_id)
                    out.append(ev)
                    if len(out) >= k:
                        break
                if not progressed:
                    break
            return out

        # priority_weighted
        flat: list[BeamEvent] = []
        for lst in per_proposer:
            flat.extend(lst)
        # de-dup keeping first occurrence
        deduped: list[BeamEvent] = []
        seen_ids: set[str] = {h.event_id for h in history}
        for ev in flat:
            if ev.event_id in seen_ids:
                continue
            seen_ids.add(ev.event_id)
            deduped.append(ev)
        deduped.sort(
            key=lambda e: (
                -(self.priority_weights.get(e.source, 0.5) * e.prior_p),
                e.occurs_at,
                e.event_id,
            )
        )
        return deduped[:k]


__all__ = ["CompositeProposer", "CompositeStrategy"]
