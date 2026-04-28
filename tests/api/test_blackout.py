"""Blackout policy — date-mock 기준 hide AI vs reveal."""
from __future__ import annotations

import datetime as dt

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

import backend.app.services.blackout_service as bsvc
from backend.app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def _patch_today(monkeypatch, target: dt.date):
    """Override blackout_service.dt.date.today via real_today shim."""
    real_get_status = bsvc.get_status

    def fake_get_status(region_id, today=None):
        return real_get_status(region_id, today=target)

    monkeypatch.setattr(bsvc, "get_status", fake_get_status)
    # public router 가 이미 import 한 reference 도 갈아끼움
    from backend.app.routers import public as _pub
    monkeypatch.setattr(_pub, "get_blackout_status", fake_get_status)


def test_blackout_meta_when_inside_window(client, monkeypatch):
    _patch_today(monkeypatch, dt.date(2026, 5, 30))  # blackout 5/28-6/3
    r = client.get("/api/v1/regions/seoul_mayor/poll-trajectory")
    assert r.status_code == 200
    body = r.json()
    assert body["blackout"]["in_blackout"] is True
    assert body["blackout"]["region_id"] == "seoul_mayor"
    # AI 차트 hidden by default (POLITIKAST_BLACKOUT_HIDE_AI=1 default)
    assert body["data"] == []


def test_blackout_meta_when_outside_window(client, monkeypatch):
    _patch_today(monkeypatch, dt.date(2026, 4, 30))
    r = client.get("/api/v1/regions/seoul_mayor/poll-trajectory")
    body = r.json()
    assert body["blackout"]["in_blackout"] is False
    # data 는 trajectory 그대로 (snapshot 있을 수 있음, 없으면 빈 list)
    assert isinstance(body["data"], list)


def test_blackout_does_not_hide_when_env_disabled(client, monkeypatch):
    _patch_today(monkeypatch, dt.date(2026, 5, 30))
    monkeypatch.setenv("POLITIKAST_BLACKOUT_HIDE_AI", "0")
    r = client.get("/api/v1/regions/seoul_mayor/poll-trajectory")
    body = r.json()
    assert body["blackout"]["in_blackout"] is True
    assert body["blackout"]["hides_ai"] is False
    # data 는 hide 되지 않음 (실 snapshot 따라 빈 list 일 수도 있음)
    assert isinstance(body["data"], list)


def test_scenario_outcome_hidden_during_blackout(client, monkeypatch):
    _patch_today(monkeypatch, dt.date(2026, 5, 30))
    r = client.get("/api/v1/scenarios/seoul_mayor_2026/outcome")
    if r.status_code == 404:
        pytest.skip("seed scenario not present in test env")
    body = r.json()
    assert body["blackout"]["in_blackout"] is True
    assert body["data"] is None


def test_kg_subgraph_unaffected_by_blackout(client, monkeypatch):
    """Blackout 정책: AI 차트만 숨김. KG/페르소나/댓글은 노출."""
    _patch_today(monkeypatch, dt.date(2026, 5, 30))
    r = client.get("/api/v1/regions/seoul_mayor/kg-subgraph?k=5")
    assert r.status_code == 200
    body = r.json()
    assert body["region_id"] == "seoul_mayor"
    assert "nodes" in body and "edges" in body
