"""Smoke tests for src.data.ingest helper functions (no DuckDB I/O)."""
from __future__ import annotations

from src.data.ingest import pick_first_existing, split_columns


def test_pick_first_existing_returns_first_match() -> None:
    available = {"province", "district", "uuid"}
    assert pick_first_existing(["region", "province"], available) == "province"


def test_pick_first_existing_none_when_missing() -> None:
    assert pick_first_existing(["foo", "bar"], {"baz"}) is None


def test_pick_first_existing_priority_order() -> None:
    available = {"a", "b"}
    # 첫 번째 후보가 우선
    assert pick_first_existing(["b", "a"], available) == "b"


def test_split_columns_separates_persona_text() -> None:
    cols = ["uuid", "age", "professional_persona", "sports_persona", "gender"]
    core, text = split_columns(cols)
    assert "uuid" in core and "age" in core and "gender" in core
    assert sorted(text) == ["professional_persona", "sports_persona"]
    # core / text는 disjoint
    assert set(core).isdisjoint(set(text))


def test_split_columns_empty_input() -> None:
    core, text = split_columns([])
    assert core == [] and text == []
