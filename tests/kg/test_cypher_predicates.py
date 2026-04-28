"""Phase 4 (#78 / #79) — retriever + firewall Cypher equivalents."""
from __future__ import annotations

from datetime import datetime, timedelta

from src.kg._calendar_adapter import get_default_t_start
from src.kg.firewall import assert_no_future_leakage_cypher
from src.kg.retriever import (
    events_used_summary_cypher,
    get_cohort_prior_cypher,
    subgraph_at_cypher,
)


def test_subgraph_at_cypher_carries_cutoff_and_event_labels():
    base = get_default_t_start()
    q, params = subgraph_at_cypher("seoul_mayor", base + timedelta(days=10), k=5)
    assert "n.ts <= $cutoff" in q
    assert params["region_id"] == "seoul_mayor"
    assert params["k"] == 5
    assert "MediaEvent" in params["event_labels"]
    assert "PollPublication" in params["event_labels"]


def test_get_cohort_prior_cypher_scoring_rule():
    q, params = get_cohort_prior_cypher("seoul_mayor", "30-39", "M")
    # Every score branch must appear so we don't silently drop a cohort tier.
    for needle in (
        "n.region_id = $region_id", "scope = 'national'",
        "n.age_band = $age_band", "n.gender = $gender",
        "WHERE score > 0", "LIMIT 1",
    ):
        assert needle in q
    assert params == {
        "region_id": "seoul_mayor", "age_band": "30-39", "gender": "M",
    }


def test_events_used_summary_cypher_orders_by_ts():
    q, params = events_used_summary_cypher(
        "daegu_mayor", datetime(2030, 5, 1)
    )
    assert "ORDER BY n.ts" in q
    assert "OPTIONAL MATCH (n)-[:about]->(t)" in q
    assert params["region_id"] == "daegu_mayor"
    assert "ScandalEvent" in params["event_labels"]


def test_firewall_cypher_asks_for_future_events_only():
    q, params = assert_no_future_leakage_cypher(
        "busan_buk_gap", datetime(2030, 1, 1)
    )
    assert "n.ts > $cutoff" in q
    assert params["region_id"] == "busan_buk_gap"
    assert "MediaEvent" in params["event_labels"]
