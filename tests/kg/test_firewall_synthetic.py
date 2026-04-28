"""Migrated firewall self-tests — operate on the synthetic fixture.

These six tests previously lived inline in ``src/kg/firewall.py`` (Phase 1).
Per task #27 the firewall module is now date-literal-free; the synthetic
scenario fixture lives in :mod:`tests.kg.fixtures.synthetic_scenario` and is
calendar-derived (so timestamps move with ``ElectionCalendar``).
"""
from __future__ import annotations

import pytest

from src.kg.builder import build_kg_from_dicts
from src.kg.firewall import assert_no_future_leakage
from src.kg.retriever import KGRetriever
from tests.kg.fixtures import make_synthetic_scenario, SYNTHETIC_REGION_ID


@pytest.fixture(scope="module")
def synthetic_retriever():
    G, index = build_kg_from_dicts([make_synthetic_scenario()])
    return KGRetriever(G, index)


def test_firewall_blocks_future(synthetic_retriever):
    persona = {
        "district": "서울특별시",
        "age": 40,
        "occupation": "사무직",
        "education_level": "대졸",
        "professional_persona": "주택 구매를 고민하는 30대 직장인",
    }
    result = assert_no_future_leakage(
        synthetic_retriever, persona, t=0, region_id=SYNTHETIC_REGION_ID
    )
    assert all("토론회" not in line for line in result.context_text.splitlines()), (
        f"t=0 에서 ev_01 가 노출됨: {result.context_text!r}"
    )


def test_firewall_progressive_disclosure(synthetic_retriever):
    persona = {
        "district": "서울특별시",
        "age": 40,
        "occupation": "사무직",
        "professional_persona": "주택 구매 관심",
    }
    counts = []
    for t in range(4):
        r = assert_no_future_leakage(
            synthetic_retriever, persona, t=t, region_id=SYNTHETIC_REGION_ID, k=20
        )
        counts.append(len(r.events_used))
    assert counts == sorted(counts), f"non-monotone visibility: {counts}"


def test_firewall_t_end_includes_all(synthetic_retriever):
    persona = {"district": "서울특별시", "age": 40, "occupation": "사무직"}
    result = assert_no_future_leakage(
        synthetic_retriever, persona, t=3, region_id=SYNTHETIC_REGION_ID, k=20
    )
    seen = {e["event_id"] for e in result.events_used}
    expected = {"ev_01", "ev_02", "ev_03", "ev_04", "ev_05"}
    missing = expected - seen
    assert not missing, f"t=T-1 누락: {missing}"


def test_no_unknown_region(synthetic_retriever):
    persona = {"district": "?", "age": 30}
    result = synthetic_retriever.subgraph_at(persona, t=2, region_id="unknown_region")
    assert result.events_used == []


def test_poll_firewall(synthetic_retriever):
    persona = {"district": "서울특별시", "age": 30}
    result = assert_no_future_leakage(
        synthetic_retriever, persona, t=0, region_id=SYNTHETIC_REGION_ID, k=20
    )
    poll_ids = [e for e in result.events_used if e["type"] == "PollPublication"]
    assert poll_ids == [], f"t=0 에서 poll 누설: {poll_ids}"


def test_persona_relevance_boost(synthetic_retriever):
    persona = {
        "district": "서울특별시",
        "age": 38,
        "occupation": "직장인",
        "professional_persona": "전세금 인상으로 주택 구매를 고민하는 30대 직장인",
    }
    result = synthetic_retriever.subgraph_at(
        persona, t=3, region_id=SYNTHETIC_REGION_ID, k=3
    )
    titles = " | ".join(e["event_id"] for e in result.events_used)
    assert "ev_03" in titles or "ev_01" in titles, (
        f"부동산 이벤트가 top-3 에 없음: {titles}"
    )
