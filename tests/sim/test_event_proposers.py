"""Tests for src.sim.event_proposers (Phase 6, pipeline-model task #10)."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from src.schemas.beam_event import BeamEvent
from src.sim.event_proposers import (
    CompositeProposer,
    CustomJSONProposer,
    KGConfirmedProposer,
    LLMHypotheticalProposer,
    PROPOSER_REGISTRY,
)


def _utc(year: int, month: int, day: int) -> dt.datetime:
    return dt.datetime(year, month, day, tzinfo=dt.timezone.utc)


def test_registry_contains_all_four_proposers():
    assert set(PROPOSER_REGISTRY) >= {"kg", "llm", "custom", "composite"}


# ---------------------------------------------------------------------------
# KGConfirmedProposer
# ---------------------------------------------------------------------------
class _StubKG:
    """Duck-typed KG retriever exposing iter_events."""

    def __init__(self, events: list[dict]):
        self._events = events

    def iter_events(self, region_id, since, until):
        for ev in self._events:
            if ev.get("region_id") not in (None, region_id):
                continue
            if since < ev["ts"] <= until:
                yield ev


def test_kg_proposer_filters_by_window_and_dedupes():
    kg = _StubKG(
        [
            {"event_id": "e_old", "ts": _utc(2026, 4, 10), "type": "event", "summary": "old"},
            {"event_id": "e_in", "ts": _utc(2026, 4, 25), "type": "event", "summary": "in"},
            {"event_id": "e_dup", "ts": _utc(2026, 4, 26), "type": "event", "summary": "dup"},
            {"event_id": "e_future", "ts": _utc(2026, 5, 10), "type": "event", "summary": "future"},
        ]
    )
    proposer = KGConfirmedProposer(kg_retriever=kg, as_of=_utc(2026, 4, 28))
    history = [
        BeamEvent(
            event_id="e_dup",
            source="kg_confirmed",
            occurs_at=_utc(2026, 4, 26),
            description="dup",
            prior_p=1.0,
        )
    ]
    out = proposer.propose("seoul_mayor", _utc(2026, 4, 20), history, k=10)
    ids = [e.event_id for e in out]
    assert "e_in" in ids
    assert "e_dup" not in ids  # filtered by history dedupe
    assert "e_old" not in ids  # filtered by since
    assert "e_future" not in ids  # filtered by as_of


def test_kg_proposer_emits_prior_p_one_and_event_patch():
    kg = _StubKG(
        [{"event_id": "e1", "ts": _utc(2026, 4, 25), "type": "event", "summary": "e1"}]
    )
    proposer = KGConfirmedProposer(kg_retriever=kg, as_of=_utc(2026, 4, 28))
    out = proposer.propose("seoul_mayor", _utc(2026, 4, 20), [], k=5)
    assert len(out) == 1
    ev = out[0]
    assert ev.prior_p == 1.0
    assert ev.source == "kg_confirmed"
    assert ev.event_patches and ev.event_patches[0]["op"] == "add"


# ---------------------------------------------------------------------------
# LLMHypotheticalProposer
# ---------------------------------------------------------------------------
def test_llm_proposer_with_mock_fn_is_deterministic():
    def mock(region_id, current_t, history, k):
        return [
            BeamEvent(
                event_id="llm_a",
                source="llm_hypothetical",
                occurs_at=_utc(2026, 5, 1),
                description="가설 A",
                prior_p=0.6,
            ),
            BeamEvent(
                event_id="llm_b",
                source="llm_hypothetical",
                occurs_at=_utc(2026, 5, 2),
                description="가설 B",
                prior_p=0.3,
            ),
        ]

    proposer = LLMHypotheticalProposer(mock_fn=mock)
    a = proposer.propose("seoul_mayor", _utc(2026, 4, 28), [], k=5)
    b = proposer.propose("seoul_mayor", _utc(2026, 4, 28), [], k=5)
    assert [e.event_id for e in a] == [e.event_id for e in b] == ["llm_a", "llm_b"]


def test_llm_proposer_drops_invalid_rows_via_pydantic():
    def fake_call(prompt: str) -> str:
        return json.dumps(
            [
                {
                    "event_id": "ok",
                    "occurs_at": "2026-05-01T00:00:00+00:00",
                    "description": "ok",
                    "prior_p": 0.4,
                },
                {"event_id": "bad", "occurs_at": "not a date", "prior_p": 2.0},  # invalid
            ]
        )

    proposer = LLMHypotheticalProposer(llm_call=fake_call, seed=11)
    out = proposer.propose("seoul_mayor", _utc(2026, 4, 28), [], k=5)
    assert len(out) == 1
    assert out[0].event_id == "ok"


# ---------------------------------------------------------------------------
# CustomJSONProposer
# ---------------------------------------------------------------------------
def test_custom_proposer_loads_json_files(tmp_path: Path):
    region_dir = tmp_path / "seoul_mayor"
    region_dir.mkdir()
    (region_dir / "evt.json").write_text(
        json.dumps(
            [
                {
                    "event_id": "cust_a",
                    "occurs_at": "2026-05-15T00:00:00+00:00",
                    "description": "custom A",
                    "prior_p": 0.4,
                }
            ]
        )
    )
    proposer = CustomJSONProposer(base_dir=tmp_path)
    out = proposer.propose("seoul_mayor", _utc(2026, 4, 28), [], k=5)
    assert len(out) == 1
    assert out[0].event_id == "cust_a"
    assert out[0].source == "custom"


def test_custom_proposer_skips_stale_events(tmp_path: Path):
    region_dir = tmp_path / "seoul_mayor"
    region_dir.mkdir()
    (region_dir / "evt.json").write_text(
        json.dumps(
            [
                {
                    "event_id": "stale",
                    "occurs_at": "2026-04-10T00:00:00+00:00",
                    "description": "stale",
                    "prior_p": 0.4,
                }
            ]
        )
    )
    proposer = CustomJSONProposer(base_dir=tmp_path)
    out = proposer.propose("seoul_mayor", _utc(2026, 4, 28), [], k=5)
    assert out == []


# ---------------------------------------------------------------------------
# CompositeProposer
# ---------------------------------------------------------------------------
class _StaticProposer:
    def __init__(self, name: str, events: list[BeamEvent]):
        self.name = name
        self._events = events

    def propose(self, region_id, current_t, history, k):
        return list(self._events)[:k]


def test_composite_round_robin_dedupes_and_caps_k():
    a = _StaticProposer(
        "a",
        [
            BeamEvent(
                event_id="x",
                source="kg_confirmed",
                occurs_at=_utc(2026, 5, 1),
                description="x",
                prior_p=1.0,
            ),
            BeamEvent(
                event_id="y",
                source="kg_confirmed",
                occurs_at=_utc(2026, 5, 2),
                description="y",
                prior_p=1.0,
            ),
        ],
    )
    b = _StaticProposer(
        "b",
        [
            BeamEvent(
                event_id="x",  # duplicate
                source="llm_hypothetical",
                occurs_at=_utc(2026, 5, 3),
                description="x'",
                prior_p=0.5,
            ),
            BeamEvent(
                event_id="z",
                source="llm_hypothetical",
                occurs_at=_utc(2026, 5, 4),
                description="z",
                prior_p=0.5,
            ),
        ],
    )
    composite = CompositeProposer([a, b], strategy="round_robin")
    out = composite.propose("seoul_mayor", _utc(2026, 4, 28), [], k=3)
    ids = [e.event_id for e in out]
    # Round-robin order: a[0]=x, b[0]=x(dup-skip), a[1]=y, b[1]=z
    assert ids == ["x", "y", "z"]


def test_composite_priority_weighted_prefers_kg():
    a = _StaticProposer(
        "a",
        [
            BeamEvent(
                event_id="kg_e",
                source="kg_confirmed",
                occurs_at=_utc(2026, 5, 1),
                description="kg",
                prior_p=0.8,
            ),
        ],
    )
    b = _StaticProposer(
        "b",
        [
            BeamEvent(
                event_id="llm_e",
                source="llm_hypothetical",
                occurs_at=_utc(2026, 5, 1),
                description="llm",
                prior_p=0.99,  # higher prior_p, but lower priority weight
            ),
        ],
    )
    composite = CompositeProposer([b, a], strategy="priority_weighted")
    out = composite.propose("seoul_mayor", _utc(2026, 4, 28), [], k=2)
    assert out[0].event_id == "kg_e"
