"""FastAPI app smoke — health + OpenAPI."""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from backend.app.main import create_app


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "politikast-backend"


def test_openapi_paths_published(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json().get("paths") or {}
    # public + internal 핵심 경로 노출 확인
    for p in (
        "/health",
        "/api/v1/regions",
        "/api/v1/regions/{region_id}",
        "/api/v1/scenarios",
        "/internal/sim-results",
        "/internal/health",
    ):
        assert p in paths, p


def test_cors_preflight(client):
    r = client.options(
        "/api/v1/regions",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code in (200, 204)
    assert "access-control-allow-origin" in {k.lower() for k in r.headers}


def test_admin_optional_no_500(client):
    """admin router 미구현이면 404 여야 함 (500 금지)."""
    r = client.get("/admin/health")
    assert r.status_code in (404, 401)
