"""Tests for the deterministic mock LLM backend (offline / CI smoke)."""
from __future__ import annotations

import asyncio
import json

import pytest

from src.sim.voter_agent import _build_mock_backend, build_default_backend


def _prompt_with_three_candidates() -> str:
    return (
        "=== 서울특별시장 (timestep t=0) ===\n"
        "[모드] poll_response\n여론조사원이 전화로 묻습니다.\n\n"
        "[후보]\n"
        "- c_seoul_dpk | 박영선 (더불어민주당)\n"
        "- c_seoul_ppp | 오세훈 (국민의힘)\n"
        "- c_seoul_rebuild | 이준석 (개혁신당)\n\n"
        "[컨텍스트 (t≤0)]\n(추가 정보 없음)\n"
    )


VALID_IDS = {"c_seoul_dpk", "c_seoul_ppp", "c_seoul_rebuild"}


def test_mock_backend_returns_valid_candidate_id() -> None:
    backend = _build_mock_backend()
    text = asyncio.run(backend("sys", _prompt_with_three_candidates(), {}))
    data = json.loads(text)
    assert data["vote"] in VALID_IDS
    assert data["turnout"] is True
    assert 0.5 <= data["confidence"] < 1.0
    assert "mock_backend" in data["key_factors"]


def test_mock_backend_deterministic_for_same_prompt() -> None:
    backend = _build_mock_backend()
    prompt = _prompt_with_three_candidates()
    a = asyncio.run(backend("sys", prompt, {}))
    b = asyncio.run(backend("sys", prompt, {}))
    assert a == b


def test_mock_backend_spreads_votes_across_candidates() -> None:
    backend = _build_mock_backend()
    base = _prompt_with_three_candidates()
    votes: list[str] = []
    for i in range(60):
        prompt = base + f"\n[페르소나 변수 {i}]"
        data = json.loads(asyncio.run(backend("sys", prompt, {})))
        votes.append(data["vote"])
    distinct = set(votes)
    assert distinct.issubset(VALID_IDS)
    assert len(distinct) >= 2, f"expected ≥2 distinct candidates, got {distinct}"


def test_mock_backend_abstains_when_prompt_has_no_candidates() -> None:
    backend = _build_mock_backend()
    text = asyncio.run(backend("sys", "이 프롬프트에는 후보 목록이 없다.", {}))
    data = json.loads(text)
    assert data["vote"] is None
    assert data["turnout"] is False
    assert "no_candidates" in data["key_factors"]


def test_mock_backend_skips_withdrawn_tag_prefix() -> None:
    """Prompt rows that start with `[출마 포기]` are still mapped to their id."""
    backend = _build_mock_backend()
    prompt = (
        "[후보]\n"
        "- [출마 포기] c_seoul_dpk | 박영선 (더불어민주당)\n"
        "- c_seoul_ppp | 오세훈 (국민의힘)\n"
    )
    text = asyncio.run(backend("sys", prompt, {}))
    data = json.loads(text)
    assert data["vote"] in {"c_seoul_dpk", "c_seoul_ppp"}


def test_build_default_backend_with_mock_pref(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLITIKAST_LLM_BACKEND", "mock")
    backend = build_default_backend()
    text = asyncio.run(backend("sys", _prompt_with_three_candidates(), {}))
    data = json.loads(text)
    assert data["vote"] in VALID_IDS
