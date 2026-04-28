"""PartyRegistry — _PARTY_LABEL_OVERRIDES 외화 회귀 테스트.

시나리오/KG 에서 등장하는 모든 키가 동일 한국어 라벨로 매핑되는지 확인한다.
"""
from __future__ import annotations

import pytest

from src.schemas.party import PartyRegistry, load_party_registry


@pytest.fixture(scope="module")
def registry() -> PartyRegistry:
    return load_party_registry()


# election_env.py 의 기존 _PARTY_LABEL_OVERRIDES 와 1:1 일치해야 한다.
@pytest.mark.parametrize(
    "key,label",
    [
        ("p_ppp", "국민의힘"),
        ("p_dem", "더불어민주당"),
        ("p_rebuild", "조국혁신당"),
        ("p_jp", "정의당"),
        ("p_indep", "무소속"),
        ("ppp", "국민의힘"),
        ("dem", "더불어민주당"),
        ("dpk", "더불어민주당"),
        ("etc", "기타"),
        ("other", "기타"),
        ("undecided", "미정"),
        ("none", "미정"),
        ("no_response", "무응답"),
    ],
)
def test_legacy_overrides_match_registry(
    registry: PartyRegistry, key: str, label: str
) -> None:
    assert registry.label_for(key) == label


def test_unknown_key_returns_none(registry: PartyRegistry) -> None:
    assert registry.label_for("p_made_up_key") is None
    assert registry.label_for("") is None


def test_election_env_uses_registry() -> None:
    """ElectionEnv._party_label 이 registry 결과와 같은지 핀."""
    from src.sim.election_env import ElectionEnv

    # `_party_label` 은 인스턴스 메서드이지만 registry 만 사용하므로
    # 빈 인스턴스로도 호출 가능 — `__init__` 우회.
    env = ElectionEnv.__new__(ElectionEnv)
    env.scenario_meta = {}  # type: ignore[attr-defined]
    assert env._party_label("p_ppp") == "국민의힘"
    assert env._party_label("dpk") == "더불어민주당"
    assert env._party_label("undecided") == "미정"
