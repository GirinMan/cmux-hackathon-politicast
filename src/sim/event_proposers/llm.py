"""LLMHypotheticalProposer — Gemini/Claude-backed hypothetical events.

The LLM returns a JSON array of candidate future events with prior_p
estimates. We validate every entry against `BeamEvent` (Pydantic v2,
extra='forbid') — malformed rows are dropped, never silently coerced.

A `mock_fn` hook is provided so tests can inject deterministic synthetic
events without hitting the live LLM pool.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
from typing import Any, Callable, Optional

from src.schemas.beam_event import BeamEvent

from . import register

logger = logging.getLogger(__name__)


_PROMPT_TEMPLATE = """\
You are a Korean local-election scenario analyst. The user is exploring how
the {region_id} race might unfold AFTER {current_t}. Given the past confirmed
events, propose UP TO {k} distinct hypothetical events that could plausibly
occur between {current_t} and the election. Output a JSON array; each entry
must contain: event_id (slug), occurs_at (ISO datetime > {current_t}),
description (Korean), prior_p (0..1, sums across siblings need NOT be 1),
candidate_patches (list, may be []), event_patches (list, may be []).
History (most recent last):
{history}
"""


@register("llm")
class LLMHypotheticalProposer:
    """Propose hypothetical events via an LLM backend.

    Parameters
    ----------
    llm_call:
        Sync callable `(prompt: str) -> str` returning JSON. May be `None`
        when `mock_fn` is supplied.
    mock_fn:
        Test-only hook — `(region_id, current_t, history, k) -> list[BeamEvent]`.
        Bypasses the LLM entirely. When set, `llm_call` is ignored.
    seed:
        Deterministic seed used to suffix `event_id` so two runs with the
        same context produce stable IDs.
    """

    name = "llm"

    def __init__(
        self,
        llm_call: Optional[Callable[[str], str]] = None,
        *,
        mock_fn: Optional[
            Callable[[str, dt.datetime, list[BeamEvent], int], list[BeamEvent]]
        ] = None,
        seed: int = 11,
    ) -> None:
        self.llm_call = llm_call
        self.mock_fn = mock_fn
        self.seed = seed

    # ------------------------------------------------------------------
    def _stable_suffix(self, region_id: str, current_t: dt.datetime, idx: int) -> str:
        h = hashlib.sha1(
            f"{region_id}|{current_t.isoformat()}|{self.seed}|{idx}".encode("utf-8")
        ).hexdigest()
        return h[:8]

    def _coerce(
        self,
        raw: list[dict[str, Any]],
        region_id: str,
        current_t: dt.datetime,
    ) -> list[BeamEvent]:
        out: list[BeamEvent] = []
        for idx, row in enumerate(raw):
            try:
                eid = row.get("event_id") or f"llm_{self._stable_suffix(region_id, current_t, idx)}"
                event = BeamEvent(
                    event_id=str(eid),
                    source="llm_hypothetical",
                    occurs_at=row.get("occurs_at"),  # validated by pydantic
                    description=str(row.get("description", "")).strip() or f"hypothetical {eid}",
                    candidate_patches=list(row.get("candidate_patches") or []),
                    event_patches=list(row.get("event_patches") or []),
                    prior_p=float(row.get("prior_p", 0.0)),
                    metadata={"raw": row, "seed": self.seed},
                )
            except Exception as e:  # pragma: no cover — Pydantic validation
                logger.warning("LLM proposer: dropped malformed row idx=%d: %s", idx, e)
                continue
            out.append(event)
        return out

    # ------------------------------------------------------------------
    def propose(
        self,
        region_id: str,
        current_t: dt.datetime,
        history: list[BeamEvent],
        k: int,
    ) -> list[BeamEvent]:
        if self.mock_fn is not None:
            events = list(self.mock_fn(region_id, current_t, history, k))
            for ev in events:
                if not isinstance(ev, BeamEvent):
                    raise TypeError(
                        f"mock_fn must return BeamEvent instances, got {type(ev)!r}"
                    )
            return events[:k]
        if self.llm_call is None:
            logger.info("LLMHypotheticalProposer: no llm_call/mock_fn — emit empty.")
            return []
        prompt = _PROMPT_TEMPLATE.format(
            region_id=region_id,
            current_t=current_t.isoformat(),
            k=k,
            history="\n".join(f"- {h.occurs_at.isoformat()} {h.description}" for h in history) or "(none)",
        )
        try:
            raw_str = self.llm_call(prompt)
            parsed = json.loads(raw_str)
            if not isinstance(parsed, list):
                logger.warning("LLM proposer: top-level JSON not a list — dropping.")
                return []
        except Exception as e:
            logger.warning("LLMHypotheticalProposer call failed: %s", e)
            return []
        return self._coerce(parsed, region_id, current_t)[:k]


__all__ = ["LLMHypotheticalProposer"]
