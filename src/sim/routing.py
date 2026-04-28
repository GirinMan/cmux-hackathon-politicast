"""Persona-conditional model routing strategies for VoterAgent.

Background
----------
사용자 결정 (12:11) — Plan D + bachelor cutoff:
- voter normal (학사 미만): `LITELLM_MODEL_VOTER_NORMAL` (default ``gpt-5.4-nano``)
- voter educated (학사 이상): `LITELLM_MODEL_VOTER_EDUCATED` (default ``gpt-5.4-mini``)

이 모듈은 그 결정을 ``RoutingStrategy`` Protocol + ``EducationLevelRouting``
구현으로 분리한다. 단순 키워드 매치 한 줄을 voter_agent.py 본체에서 분리해
- 추가 라우팅 정책 (지역/연령/이슈 살리언스 등) 도입을 쉽게 만들고
- ``_normalize_education_level()`` 단위 테스트가 가능하도록 한다.

Voter agent 의 기본 동작은 보존된다 (``EducationLevelRouting()`` 인스턴스가
싱글톤으로 사용됨).
"""
from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol


# ---------------------------------------------------------------------------
# Education level normalization
# ---------------------------------------------------------------------------
# 한국어/영어 학사 이상 표지. NFKC 정규화 + lowercase 후 substring 매치로 사용.
DEFAULT_BACHELOR_KEYWORDS: tuple[str, ...] = (
    "학사",
    "대학교",
    "대졸",
    "학부",
    "bachelor",
    "석사",
    "박사",
    "master",
    "doctor",
    "phd",
)

EDU_LEVEL_BACHELOR_PLUS = "bachelor_plus"
EDU_LEVEL_BELOW_BACHELOR = "below_bachelor"
EDU_LEVEL_UNKNOWN = "unknown"


def _coerce_education_field(persona: dict[str, Any]) -> str:
    """페르소나에서 학력 라벨을 강건하게 추출."""
    if not isinstance(persona, dict):
        return ""
    raw: Any = (
        persona.get("education_level")
        or persona.get("education")
        or persona.get("edu")
        or ""
    )
    if raw is None:
        return ""
    if not isinstance(raw, str):
        raw = str(raw)
    return raw


def normalize_education_level(
    persona: dict[str, Any],
    bachelor_keywords: tuple[str, ...] = DEFAULT_BACHELOR_KEYWORDS,
) -> str:
    """페르소나 학력 라벨을 3-state(`bachelor_plus`/`below_bachelor`/`unknown`)로 분류.

    강건성 처리:
    - dict 가 아니거나 학력 필드가 비면 ``unknown``.
    - NFKC 정규화로 전각/반각, 합성/분해 차이 흡수.
    - 영어는 lowercase 후 키워드 substring.
    - 한글은 그대로 substring (공백·문장부호 제거).
    """
    raw = _coerce_education_field(persona).strip()
    if not raw:
        return EDU_LEVEL_UNKNOWN

    norm = unicodedata.normalize("NFKC", raw).lower()
    # 공백/특수문자 제거로 "대학교 졸업" / "대학교졸업" 동일 처리.
    compact = "".join(ch for ch in norm if not ch.isspace())

    for kw in bachelor_keywords:
        kw_norm = unicodedata.normalize("NFKC", kw).lower()
        if kw_norm and kw_norm in compact:
            return EDU_LEVEL_BACHELOR_PLUS
    return EDU_LEVEL_BELOW_BACHELOR


# ---------------------------------------------------------------------------
# Strategy interface
# ---------------------------------------------------------------------------
class RoutingStrategy(Protocol):
    """Persona → LiteLLM 모델 식별자 매핑."""

    def model_for(self, persona: dict[str, Any]) -> str:  # pragma: no cover - protocol
        ...


@dataclass(frozen=True)
class EducationLevelRouting:
    """학력 cutoff (default = 학사) 기반 모델 라우팅.

    환경변수로 모델 식별자를 override 가능:
    - ``LITELLM_MODEL_VOTER_EDUCATED`` (default ``gpt-5.4-mini``)
    - ``LITELLM_MODEL_VOTER_NORMAL``   (default ``gpt-5.4-nano``)
    """

    educated_model_env: str = "LITELLM_MODEL_VOTER_EDUCATED"
    educated_model_default: str = "gpt-5.4-mini"
    normal_model_env: str = "LITELLM_MODEL_VOTER_NORMAL"
    normal_model_default: str = "gpt-5.4-nano"
    bachelor_keywords: tuple[str, ...] = field(
        default_factory=lambda: DEFAULT_BACHELOR_KEYWORDS
    )

    def normalize(self, persona: dict[str, Any]) -> str:
        return normalize_education_level(persona, self.bachelor_keywords)

    def is_educated(self, persona: dict[str, Any]) -> bool:
        return self.normalize(persona) == EDU_LEVEL_BACHELOR_PLUS

    def model_for(self, persona: dict[str, Any]) -> str:
        if self.is_educated(persona):
            return os.environ.get(self.educated_model_env, self.educated_model_default)
        # ``unknown`` 도 normal 버킷으로 라우팅 — 보수적 (cheaper) 기본값.
        return os.environ.get(self.normal_model_env, self.normal_model_default)


# Process-wide default — voter_agent 가 thin shim 으로 호출.
DEFAULT_ROUTING: RoutingStrategy = EducationLevelRouting()


# ---------------------------------------------------------------------------
# Income-based routing — generic axis 일반화 예시 (Phase 2 외화 대비)
# ---------------------------------------------------------------------------
INCOME_LEVEL_HIGH = "high"
INCOME_LEVEL_MIDDLE = "middle"
INCOME_LEVEL_LOW = "low"
INCOME_LEVEL_UNKNOWN = "unknown"


def _coerce_income(persona: dict[str, Any]) -> Optional[float]:
    """페르소나에서 소득 값을 float 으로 강건 추출. 알 수 없으면 None."""
    if not isinstance(persona, dict):
        return None
    for field_name in ("income", "household_income", "annual_income_krw"):
        raw = persona.get(field_name)
        if raw is None or raw == "":
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return None


@dataclass(frozen=True)
class IncomeBasedRouting:
    """소득 분위별 모델 라우팅 (예시 strategy).

    `_workspace/data/registries/persona_axes.json` 의 income axis 와 buckets
    정의를 그대로 따른다. 환경변수 override:
    - ``LITELLM_MODEL_VOTER_HIGH_INCOME``   (default ``gpt-5.4-mini``)
    - ``LITELLM_MODEL_VOTER_MIDDLE_INCOME`` (default ``gpt-5.4-nano``)
    - ``LITELLM_MODEL_VOTER_LOW_INCOME``    (default ``gpt-5.4-nano``)
    """

    high_threshold: float = 80_000_000.0
    middle_threshold: float = 30_000_000.0
    high_model_env: str = "LITELLM_MODEL_VOTER_HIGH_INCOME"
    high_model_default: str = "gpt-5.4-mini"
    middle_model_env: str = "LITELLM_MODEL_VOTER_MIDDLE_INCOME"
    middle_model_default: str = "gpt-5.4-nano"
    low_model_env: str = "LITELLM_MODEL_VOTER_LOW_INCOME"
    low_model_default: str = "gpt-5.4-nano"
    unknown_routes_to_middle: bool = True

    def bucket(self, persona: dict[str, Any]) -> str:
        v = _coerce_income(persona)
        if v is None:
            return INCOME_LEVEL_UNKNOWN
        if v >= self.high_threshold:
            return INCOME_LEVEL_HIGH
        if v >= self.middle_threshold:
            return INCOME_LEVEL_MIDDLE
        return INCOME_LEVEL_LOW

    def model_for(self, persona: dict[str, Any]) -> str:
        b = self.bucket(persona)
        if b == INCOME_LEVEL_HIGH:
            return os.environ.get(self.high_model_env, self.high_model_default)
        if b == INCOME_LEVEL_LOW:
            return os.environ.get(self.low_model_env, self.low_model_default)
        # MIDDLE 또는 UNKNOWN(보수적 fallback)
        return os.environ.get(self.middle_model_env, self.middle_model_default)


__all__ = [
    "DEFAULT_BACHELOR_KEYWORDS",
    "DEFAULT_ROUTING",
    "EDU_LEVEL_BACHELOR_PLUS",
    "EDU_LEVEL_BELOW_BACHELOR",
    "EDU_LEVEL_UNKNOWN",
    "EducationLevelRouting",
    "INCOME_LEVEL_HIGH",
    "INCOME_LEVEL_LOW",
    "INCOME_LEVEL_MIDDLE",
    "INCOME_LEVEL_UNKNOWN",
    "IncomeBasedRouting",
    "RoutingStrategy",
    "normalize_education_level",
]
