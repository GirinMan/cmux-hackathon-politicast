"""PersonaAxis registry + IncomeBasedRouting 검증."""
from __future__ import annotations

import pytest

from src.schemas.persona_axis import load_persona_axes
from src.sim.routing import (
    INCOME_LEVEL_HIGH,
    INCOME_LEVEL_LOW,
    INCOME_LEVEL_MIDDLE,
    INCOME_LEVEL_UNKNOWN,
    IncomeBasedRouting,
)


def test_registry_has_known_axes() -> None:
    reg = load_persona_axes()
    ids = {ax.axis_id for ax in reg.axes}
    assert {"education", "age", "income", "region"} <= ids


def test_education_axis_default_routing_points_to_strategy() -> None:
    reg = load_persona_axes()
    edu = reg.get("education")
    assert edu is not None
    assert edu.default_routing == "src.sim.routing.EducationLevelRouting"


def test_income_routing_buckets() -> None:
    routing = IncomeBasedRouting()
    assert routing.bucket({"income": 100_000_000}) == INCOME_LEVEL_HIGH
    assert routing.bucket({"household_income": 50_000_000}) == INCOME_LEVEL_MIDDLE
    assert routing.bucket({"annual_income_krw": 10_000_000}) == INCOME_LEVEL_LOW
    assert routing.bucket({"income": "not-a-number"}) == INCOME_LEVEL_UNKNOWN
    assert routing.bucket({}) == INCOME_LEVEL_UNKNOWN


def test_income_routing_model_for(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LITELLM_MODEL_VOTER_HIGH_INCOME", raising=False)
    monkeypatch.delenv("LITELLM_MODEL_VOTER_MIDDLE_INCOME", raising=False)
    monkeypatch.delenv("LITELLM_MODEL_VOTER_LOW_INCOME", raising=False)
    routing = IncomeBasedRouting()
    assert routing.model_for({"income": 100_000_000}) == "gpt-5.4-mini"
    assert routing.model_for({"income": 50_000_000}) == "gpt-5.4-nano"
    assert routing.model_for({"income": 10_000_000}) == "gpt-5.4-nano"
    # unknown -> middle 버킷 default
    assert routing.model_for({}) == "gpt-5.4-nano"


def test_income_routing_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LITELLM_MODEL_VOTER_HIGH_INCOME", "claude-sonnet-4-6")
    monkeypatch.setenv("LITELLM_MODEL_VOTER_LOW_INCOME", "gemini/gemini-3.1-flash-lite-preview")
    routing = IncomeBasedRouting()
    assert routing.model_for({"income": 100_000_000}) == "claude-sonnet-4-6"
    assert (
        routing.model_for({"income": 5_000_000})
        == "gemini/gemini-3.1-flash-lite-preview"
    )
