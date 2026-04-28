"""KGConfirmedProposer — surfaces confirmed events from the KG.

Confirmed events have `prior_p = 1.0` because they really happened (within
the time window between the parent node's clock and "today"). They translate
to `event_patches` of `op="add"` so the spliced scenario re-injects the same
narrative into the voter prompt context.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Iterable, Optional

from src.schemas.beam_event import BeamEvent

from . import register


def _normalize_ts(raw: Any) -> Optional[dt.datetime]:
    if isinstance(raw, dt.datetime):
        return raw
    if isinstance(raw, dt.date):
        return dt.datetime.combine(raw, dt.time(), tzinfo=dt.timezone.utc)
    if isinstance(raw, str):
        try:
            return dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


@register("kg")
class KGConfirmedProposer:
    """KG-backed proposer.

    `kg_retriever` may be None — degraded mode emits zero events. It's also
    duck-typed: anything exposing `iter_events(region_id, since, until)` is
    accepted. networkx-based retrievers can pass in their `G` directly via
    the `graph` kwarg as a fallback.
    """

    name = "kg"

    def __init__(
        self,
        kg_retriever: Any | None = None,
        *,
        graph: Any | None = None,
        as_of: dt.datetime | None = None,
    ) -> None:
        self.kg = kg_retriever
        self.graph = graph
        # Upper bound for "confirmed" — events with ts > as_of are NOT yet
        # confirmed and must be left to LLM/custom proposers.
        self.as_of = as_of or dt.datetime.now(dt.timezone.utc)

    # ------------------------------------------------------------------
    def _iter_events(
        self, region_id: str, since: dt.datetime, until: dt.datetime
    ) -> Iterable[dict[str, Any]]:
        if self.kg is not None and hasattr(self.kg, "iter_events"):
            try:
                yield from self.kg.iter_events(region_id, since, until)
                return
            except Exception:
                pass
        graph = self.graph
        if graph is None and self.kg is not None and hasattr(self.kg, "G"):
            graph = self.kg.G
        if graph is None:
            return
        try:
            from src.kg.ontology import EVENT_NODE_TYPES  # type: ignore
        except Exception:
            EVENT_NODE_TYPES = set()  # type: ignore
        for node_id, attrs in graph.nodes(data=True):
            if EVENT_NODE_TYPES and attrs.get("type") not in EVENT_NODE_TYPES:
                continue
            ts = _normalize_ts(attrs.get("ts"))
            if ts is None or ts <= since or ts > until:
                continue
            if attrs.get("region_id") and attrs["region_id"] != region_id:
                continue
            yield {
                "event_id": attrs.get("event_id") or str(node_id),
                "ts": ts,
                "type": attrs.get("type", "event"),
                "title": attrs.get("title") or attrs.get("summary") or "",
                "summary": attrs.get("summary") or attrs.get("title") or "",
                "target": attrs.get("target"),
                "polarity": attrs.get("polarity", 0.0),
            }

    # ------------------------------------------------------------------
    def propose(
        self,
        region_id: str,
        current_t: dt.datetime,
        history: list[BeamEvent],
        k: int,
    ) -> list[BeamEvent]:
        seen = {ev.event_id for ev in history}
        out: list[BeamEvent] = []
        for raw in self._iter_events(region_id, current_t, self.as_of):
            eid = str(raw["event_id"])
            if eid in seen:
                continue
            ts: dt.datetime = raw["ts"]
            description = (
                raw.get("title")
                or raw.get("summary")
                or f"[KG] {raw.get('type')}"
            ).strip() or f"KG event {eid}"
            event_patch = {
                "op": "add",
                "event": {
                    "event_id": eid,
                    "type": raw.get("type", "event"),
                    "summary": raw.get("summary") or description,
                    "target": raw.get("target"),
                    "polarity": float(raw.get("polarity", 0.0) or 0.0),
                    "ts": ts.isoformat(),
                },
            }
            out.append(
                BeamEvent(
                    event_id=eid,
                    source="kg_confirmed",
                    occurs_at=ts,
                    description=description,
                    candidate_patches=[],
                    event_patches=[event_patch],
                    prior_p=1.0,
                    metadata={"kg_node": eid},
                )
            )
        # Stable order: oldest first, then by event_id.
        out.sort(key=lambda e: (e.occurs_at, e.event_id))
        return out[:k]


__all__ = ["KGConfirmedProposer"]
