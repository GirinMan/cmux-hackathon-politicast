"""Public router 핵심 경로 — 5 region SoT 위에서 동작."""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from backend.app.main import create_app


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


EXPECTED_REGIONS = {
    "seoul_mayor", "busan_buk_gap", "daegu_mayor",
    "gwangju_mayor", "daegu_dalseo_gap",
}


def test_list_regions_5(client):
    r = client.get("/api/v1/regions")
    assert r.status_code == 200
    ids = {row["region_id"] for row in r.json()}
    assert EXPECTED_REGIONS.issubset(ids)


def test_get_region_known(client):
    r = client.get("/api/v1/regions/seoul_mayor")
    assert r.status_code == 200
    body = r.json()
    assert body["region_id"] == "seoul_mayor"
    assert body["election_date"] == "2026-06-03"
    assert body["timezone"] == "Asia/Seoul"
    assert "in_blackout" in body


def test_get_region_unknown_404(client):
    r = client.get("/api/v1/regions/nope_does_not_exist")
    assert r.status_code == 404


def test_region_summary_known(client):
    r = client.get("/api/v1/regions/seoul_mayor/summary")
    assert r.status_code == 200
    assert r.json()["region_id"] == "seoul_mayor"


def test_list_scenarios_returns_array(client):
    r = client.get("/api/v1/scenarios")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_scenario_unknown_404(client):
    r = client.get("/api/v1/scenarios/nope_xx")
    assert r.status_code == 404


def test_poll_trajectory_returns_envelope(client):
    """Phase 5 — response wrapped with `data` + `blackout` meta."""
    r = client.get("/api/v1/regions/seoul_mayor/poll-trajectory")
    assert r.status_code == 200
    body = r.json()
    assert "data" in body and isinstance(body["data"], list)
    assert "blackout" in body and "in_blackout" in body["blackout"]


def test_prediction_trajectory_envelope_shape(client):
    r = client.get("/api/v1/regions/seoul_mayor/prediction-trajectory")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body.get("data"), list)
    assert "blackout" in body
    if body["data"]:
        first = body["data"][0]
        for k in ("timestep", "predicted_share", "leader", "margin_top2"):
            assert k in first


def test_kg_subgraph_returns_envelope(client):
    r = client.get("/api/v1/regions/seoul_mayor/kg-subgraph?k=10")
    assert r.status_code == 200
    body = r.json()
    assert body["region_id"] == "seoul_mayor"
    assert "nodes" in body and "edges" in body
