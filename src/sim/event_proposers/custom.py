"""CustomJSONProposer — operator-curated events from JSON + DB rows.

JSON layout: ``_workspace/data/scenario_events/<region_id>/*.json``.
Each file is either a single object or a list of objects shaped like::

    {
      "event_id": "...",
      "occurs_at": "2026-05-12T10:00:00+09:00",
      "description": "...",
      "candidate_patches": [...],
      "event_patches": [...],
      "prior_p": 0.3,
      "metadata": {...}
    }

The DB-row pathway (`scenario_event` table from alembic 0003) is consumed via
the optional ``rows`` constructor argument — pipeline-counterfactual injects
them. Both sources are merged, de-duplicated by `event_id`, and sorted.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path
from typing import Any, Iterable, Optional

from src.schemas.beam_event import BeamEvent

from . import register

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DIR = REPO_ROOT / "_workspace" / "data" / "scenario_events"


@register("custom")
class CustomJSONProposer:
    """Operator-curated events from JSON files (+ optional DB rows)."""

    name = "custom"

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        *,
        rows: Optional[Iterable[dict[str, Any]]] = None,
    ) -> None:
        self.base_dir = Path(base_dir) if base_dir else DEFAULT_DIR
        self._rows = list(rows) if rows is not None else []

    # ------------------------------------------------------------------
    def _iter_json(self, region_id: str) -> Iterable[dict[str, Any]]:
        region_dir = self.base_dir / region_id
        if not region_dir.exists():
            return
        for path in sorted(region_dir.glob("*.json")):
            try:
                with path.open("r", encoding="utf-8") as f:
                    payload = json.load(f)
            except Exception as e:
                logger.warning("CustomJSONProposer: failed to read %s: %s", path, e)
                continue
            if isinstance(payload, list):
                yield from payload
            elif isinstance(payload, dict):
                yield payload

    def _materialize(self, raw: dict[str, Any]) -> Optional[BeamEvent]:
        try:
            return BeamEvent(
                event_id=str(raw["event_id"]),
                source="custom",
                occurs_at=raw["occurs_at"],
                description=str(raw.get("description", "")).strip() or raw["event_id"],
                candidate_patches=list(raw.get("candidate_patches") or []),
                event_patches=list(raw.get("event_patches") or []),
                prior_p=float(raw.get("prior_p", 0.5)),
                metadata=dict(raw.get("metadata") or {}),
            )
        except Exception as e:
            logger.warning("CustomJSONProposer: dropped invalid row %r: %s", raw.get("event_id"), e)
            return None

    # ------------------------------------------------------------------
    def propose(
        self,
        region_id: str,
        current_t: dt.datetime,
        history: list[BeamEvent],
        k: int,
    ) -> list[BeamEvent]:
        seen: set[str] = {ev.event_id for ev in history}
        out: list[BeamEvent] = []
        for raw in list(self._iter_json(region_id)) + [
            r for r in self._rows if (r.get("region_id") in (None, region_id))
        ]:
            ev = self._materialize(raw)
            if ev is None:
                continue
            if ev.event_id in seen:
                continue
            if ev.occurs_at <= current_t:
                # custom events are forward-looking; skip stale.
                continue
            seen.add(ev.event_id)
            out.append(ev)
        out.sort(key=lambda e: (e.occurs_at, e.event_id))
        return out[:k]


__all__ = ["CustomJSONProposer"]
