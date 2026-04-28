"""Internal router — service token 인증 + sim 결과 업로드."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.settings import get_settings


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("POLITIKAST_API_INTERNAL_SERVICE_TOKEN", "test-secret-xyz")
    monkeypatch.setenv("POLITIKAST_API_SNAPSHOTS_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield TestClient(create_app())
    get_settings.cache_clear()


def test_internal_health_requires_token(client):
    r = client.get("/internal/health")
    assert r.status_code == 401


def test_internal_health_accepts_token(client):
    r = client.get("/internal/health", headers={"X-Service-Token": "test-secret-xyz"})
    assert r.status_code == 200
    assert r.json()["scope"] == "internal"


def test_internal_health_accepts_bearer(client):
    r = client.get(
        "/internal/health", headers={"Authorization": "Bearer test-secret-xyz"}
    )
    assert r.status_code == 200


def test_sim_upload_writes_snapshot(client, tmp_path: Path):
    payload = {
        "schema_version": "v1",
        "scenario_id": "seoul_mayor_2026",
        "region_id": "seoul_mayor",
        "contest_id": "seoul_mayor_2026",
        "timestep_count": 1,
        "persona_n": 10,
        "candidates": [{"id": "c_a", "name": "A"}],
        "poll_trajectory": [],
        "final_outcome": {"vote_share_by_candidate": {"c_a": 1.0}, "winner": "c_a"},
        "meta": {"env": "test"},
    }
    r = client.post(
        "/internal/sim-results",
        json=payload,
        headers={"X-Service-Token": "test-secret-xyz"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["scenario_id"] == "seoul_mayor_2026"
    assert body["bytes_written"] > 0
    files = list(tmp_path.glob("seoul_mayor__seoul_mayor_2026__upload_*.json"))
    assert len(files) == 1
    written = json.loads(files[0].read_text())
    assert written["region_id"] == "seoul_mayor"


def test_sim_upload_rejects_bad_payload(client):
    r = client.post(
        "/internal/sim-results",
        json={"region_id": "x"},  # missing required scenario_id/contest_id
        headers={"X-Service-Token": "test-secret-xyz"},
    )
    assert r.status_code in (400, 422)
