"""Tests for src.schemas.pollster.PollsterRegistry — load + sanity range check.

Covers:
  - Default registry loads from _workspace/data/registries/pollsters.json
  - All effects bounded |x| ≤ 0.05
  - alias flattening: aliases share parent's effect in as_*_dict
  - default_house_effect / default_mode_effect (used by poll_consensus.consensus)
    return non-empty dicts
  - Validation rejects out-of-bound effects
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.schemas.pollster import (
    HOUSE_EFFECT_BOUND,
    MODE_EFFECT_BOUND,
    HouseEffect,
    ModeEffect,
    PollsterRegistry,
    load_pollster_registry,
)
from src.sim.poll_consensus import default_house_effect, default_mode_effect


REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "_workspace" / "data" / "registries" / "pollsters.json"


def test_registry_path_exists() -> None:
    assert REGISTRY_PATH.exists(), (
        "pollsters.json missing — Phase 2 #38 should have moved poll_priors.json here."
    )


def test_registry_loads_and_validates() -> None:
    reg = load_pollster_registry()
    assert isinstance(reg, PollsterRegistry)
    assert reg.version
    assert len(reg.houses) > 0
    assert len(reg.modes) > 0


def test_all_house_effects_within_sanity_bound() -> None:
    reg = load_pollster_registry()
    for h in reg.houses:
        assert abs(h.effect) <= HOUSE_EFFECT_BOUND, (
            f"{h.pollster} effect={h.effect} exceeds ±{HOUSE_EFFECT_BOUND}"
        )


def test_all_mode_effects_within_sanity_bound() -> None:
    reg = load_pollster_registry()
    for m in reg.modes:
        assert abs(m.effect) <= MODE_EFFECT_BOUND


def test_alias_flatten_propagates_effect() -> None:
    reg = PollsterRegistry(
        houses=[HouseEffect(pollster="갤럽", effect=0.0, aliases=["Gallup"])],
        modes=[ModeEffect(mode="phone", effect=0.0, aliases=["interview"])],
    )
    house = reg.as_house_effect_dict()
    mode = reg.as_mode_effect_dict()
    assert house["갤럽"] == 0.0
    assert house["Gallup"] == 0.0
    assert mode["phone"] == mode["interview"] == 0.0


def test_house_effect_rejects_out_of_bound() -> None:
    with pytest.raises(ValidationError):
        HouseEffect(pollster="bad", effect=0.10)


def test_mode_effect_rejects_out_of_bound() -> None:
    with pytest.raises(ValidationError):
        ModeEffect(mode="bad", effect=-0.99)


def test_default_house_mode_effects_nonempty() -> None:
    house = default_house_effect()
    mode = default_mode_effect()
    assert isinstance(house, dict) and isinstance(mode, dict)
    # 한국 주요 기관 + 모드 키가 최소한 등록되어 있어야 함.
    assert any(k in house for k in ("한국갤럽", "갤럽", "리얼미터"))
    assert "phone" in mode and "ARS" in mode


def test_legacy_format_coercion(tmp_path: Path) -> None:
    """Legacy poll_priors.json (flat house_effect/mode_effect) must still parse."""
    legacy = {
        "_meta": {"purpose": "legacy", "sources": ["a", "b"]},
        "house_effect": {"foo": 0.01},
        "mode_effect": {"phone": 0.0},
    }
    p = tmp_path / "pollsters.json"
    p.write_text(json.dumps(legacy), encoding="utf-8")
    # Bypass lru_cache by passing path explicitly.
    reg = load_pollster_registry(str(p))
    assert reg.as_house_effect_dict()["foo"] == pytest.approx(0.01)
    assert reg.as_mode_effect_dict()["phone"] == 0.0


def test_missing_file_returns_empty_registry(tmp_path: Path) -> None:
    p = tmp_path / "nonexistent.json"
    reg = load_pollster_registry(str(p))
    assert reg.as_house_effect_dict() == {}
    assert reg.as_mode_effect_dict() == {}
