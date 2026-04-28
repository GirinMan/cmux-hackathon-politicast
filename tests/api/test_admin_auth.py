"""Admin auth + admin router 보호 검증.

argon2 + PyJWT 가 설치돼있어야 동작 (없으면 skip).
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("argon2")
pytest.importorskip("jwt")

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.main import create_app  # noqa: E402
from backend.app.services import auth_service  # noqa: E402
from backend.app.settings import get_settings  # noqa: E402


PWD = "s3cret-test-password"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("POLITIKAST_API_ADMIN_JWT_SECRET", "test-jwt-secret-xyz")
    monkeypatch.setenv("POLITIKAST_API_ADMIN_JWT_ALG", "HS256")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_USER", "admin")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_PASSWORD", PWD)
    get_settings.cache_clear()
    auth_service.reset_users_for_test()
    with TestClient(create_app()) as c:
        yield c
    get_settings.cache_clear()
    auth_service.reset_users_for_test()


def test_login_invalid_credentials(client):
    r = client.post("/admin/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_login_success_returns_token(client):
    r = client.post("/admin/api/auth/login", json={"username": "admin", "password": PWD})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["username"] == "admin"
    assert body["access_token"].count(".") == 2  # JWT 3-part


def test_me_requires_bearer(client):
    r = client.get("/admin/api/auth/me")
    assert r.status_code == 401


def test_me_with_token(client):
    tok = client.post(
        "/admin/api/auth/login", json={"username": "admin", "password": PWD}
    ).json()["access_token"]
    r = client.get("/admin/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "admin"
    assert body["role"] == "admin"


def test_admin_endpoints_protected(client):
    # 토큰 없이 데이터 소스 조회 → 401
    for path in (
        "/admin/api/sim-runs",
        "/admin/api/data-sources",
        "/admin/api/unresolved-entities",
    ):
        r = client.get(path)
        assert r.status_code == 401, f"{path} should be protected"


def test_data_sources_endpoint_with_token(client):
    tok = client.post(
        "/admin/api/auth/login", json={"username": "admin", "password": PWD}
    ).json()["access_token"]
    r = client.get("/admin/api/data-sources", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert "sources" in body or "version" in body or isinstance(body, dict)


def test_password_hash_is_argon2(client):  # client fixture not needed but seeds
    h = auth_service.hash_password("hello")
    assert h.startswith("$argon2")
    assert auth_service.verify_password(h, "hello")
    assert not auth_service.verify_password(h, "bye")


def test_token_round_trip(client, monkeypatch):
    settings = get_settings()
    tok, ttl = auth_service.issue_token("alice", settings)
    assert ttl > 0
    payload = auth_service.verify_token(tok, settings)
    assert payload["sub"] == "alice"
    assert payload["role"] == "admin"
