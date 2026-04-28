"""Tests for `src.sim.routing.normalize_education_level` and EducationLevelRouting.

Voter 라우팅이 학력 라벨의 표기 변동(전각/반각, 공백, 영어/한국어)에 강건한지
확인한다. 기본 동작은 voter_agent 의 ``_is_educated`` legacy shim 과 일치해야 한다.
"""
from __future__ import annotations

import pytest

from src.sim.routing import (
    EDU_LEVEL_BACHELOR_PLUS,
    EDU_LEVEL_BELOW_BACHELOR,
    EDU_LEVEL_UNKNOWN,
    EducationLevelRouting,
    normalize_education_level,
)


@pytest.mark.parametrize(
    "edu,expected",
    [
        ("학사", EDU_LEVEL_BACHELOR_PLUS),
        ("대학교 졸업", EDU_LEVEL_BACHELOR_PLUS),
        ("대학교졸업", EDU_LEVEL_BACHELOR_PLUS),
        ("대졸", EDU_LEVEL_BACHELOR_PLUS),
        ("석사 학위", EDU_LEVEL_BACHELOR_PLUS),
        ("박사", EDU_LEVEL_BACHELOR_PLUS),
        ("Bachelor's degree", EDU_LEVEL_BACHELOR_PLUS),
        ("MASTER OF SCIENCE", EDU_LEVEL_BACHELOR_PLUS),
        ("PhD candidate", EDU_LEVEL_BACHELOR_PLUS),
        # 전각 영어
        ("Ｂａｃｈｅｌｏｒ", EDU_LEVEL_BACHELOR_PLUS),
        # below
        ("고등학교 졸업", EDU_LEVEL_BELOW_BACHELOR),
        ("중졸", EDU_LEVEL_BELOW_BACHELOR),
        ("high school", EDU_LEVEL_BELOW_BACHELOR),
        ("none", EDU_LEVEL_BELOW_BACHELOR),
        # unknown
        ("", EDU_LEVEL_UNKNOWN),
        ("   ", EDU_LEVEL_UNKNOWN),
    ],
)
def test_normalize_education_level_explicit(edu: str, expected: str) -> None:
    assert normalize_education_level({"education_level": edu}) == expected


def test_persona_alternate_keys() -> None:
    assert (
        normalize_education_level({"education": "학사 졸업"})
        == EDU_LEVEL_BACHELOR_PLUS
    )
    assert normalize_education_level({"edu": "Bachelor"}) == EDU_LEVEL_BACHELOR_PLUS


def test_non_string_persona_field_does_not_raise() -> None:
    # 잘못된 타입(숫자) 들어와도 raise 없이 결정 — 키워드 미포함이므로 below.
    assert (
        normalize_education_level({"education_level": 16})
        == EDU_LEVEL_BELOW_BACHELOR
    )


def test_missing_persona_returns_unknown() -> None:
    assert normalize_education_level({}) == EDU_LEVEL_UNKNOWN
    assert normalize_education_level({"education_level": None}) == EDU_LEVEL_UNKNOWN


def test_routing_model_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LITELLM_MODEL_VOTER_NORMAL", raising=False)
    monkeypatch.delenv("LITELLM_MODEL_VOTER_EDUCATED", raising=False)
    routing = EducationLevelRouting()

    educated = {"education_level": "Master of Science"}
    normal = {"education_level": "고등학교 졸업"}
    unknown = {}

    assert routing.is_educated(educated) is True
    assert routing.is_educated(normal) is False
    # ``unknown`` 은 normal 버킷으로 라우팅된다 (보수적 default).
    assert routing.is_educated(unknown) is False

    assert routing.model_for(educated) == "gpt-5.4-mini"
    assert routing.model_for(normal) == "gpt-5.4-nano"
    assert routing.model_for(unknown) == "gpt-5.4-nano"


def test_routing_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LITELLM_MODEL_VOTER_EDUCATED", "claude-sonnet-4-6")
    monkeypatch.setenv("LITELLM_MODEL_VOTER_NORMAL", "gemini/gemini-3.1-flash-lite-preview")
    routing = EducationLevelRouting()
    assert routing.model_for({"education_level": "박사"}) == "claude-sonnet-4-6"
    assert (
        routing.model_for({"education_level": "고졸"})
        == "gemini/gemini-3.1-flash-lite-preview"
    )


def test_legacy_shim_consistency() -> None:
    """voter_agent 의 ``_is_educated`` shim 이 RoutingStrategy 와 동일 결과."""
    from src.sim.voter_agent import _is_educated, _model_for_persona

    persona_edu = {"education_level": "대학교 졸업"}
    persona_low = {"education_level": "고등학교"}
    assert _is_educated(persona_edu) is True
    assert _is_educated(persona_low) is False
    assert _model_for_persona(persona_edu).endswith("mini")
    assert _model_for_persona(persona_low).endswith("nano")
