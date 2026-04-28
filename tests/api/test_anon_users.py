"""Anonymous user endpoints — cookie politikast_uid + nickname update + ban gate."""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from backend.app.deps import limiter
from backend.app.main import create_app
from backend.app.services._community_store import get_store
from backend.app.services import anon_user_service


@pytest.fixture
def client():
    get_store().reset_for_test()
    limiter.reset()
    yield TestClient(create_app())
    get_store().reset_for_test()
    limiter.reset()


def test_post_anonymous_sets_cookie(client):
    r = client.post("/api/v1/users/anonymous")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"].startswith("u_")
    assert body["display_name"]
    assert body["banned"] is False
    # Cookie set with httponly + samesite=lax
    cookie_header = r.headers.get("set-cookie", "")
    assert "politikast_uid=" in cookie_header.lower() or "politikast_uid" in cookie_header
    assert "httponly" in cookie_header.lower()
    assert "samesite=lax" in cookie_header.lower()


def test_post_anonymous_idempotent_when_cookie_present(client):
    r1 = client.post("/api/v1/users/anonymous")
    uid = r1.json()["id"]
    client.cookies.set("politikast_uid", uid)
    r2 = client.post("/api/v1/users/anonymous")
    assert r2.json()["id"] == uid


def test_get_me_no_cookie_returns_null(client):
    r = client.get("/api/v1/users/me")
    assert r.status_code == 200
    assert r.json() is None


def test_get_me_with_cookie_returns_user(client):
    r1 = client.post("/api/v1/users/anonymous")
    uid = r1.json()["id"]
    client.cookies.set("politikast_uid", uid)
    r2 = client.get("/api/v1/users/me")
    assert r2.status_code == 200
    assert r2.json()["id"] == uid


def test_put_me_requires_cookie(client):
    r = client.put("/api/v1/users/me", json={"display_name": "새이름"})
    assert r.status_code == 401
    assert "consent" in r.json()["detail"].lower()


def test_put_me_updates_nickname(client):
    r1 = client.post("/api/v1/users/anonymous")
    uid = r1.json()["id"]
    client.cookies.set("politikast_uid", uid)
    r2 = client.put("/api/v1/users/me", json={"display_name": "새닉네임"})
    assert r2.status_code == 200, r2.text
    assert r2.json()["display_name"] == "새닉네임"


def test_put_me_validates_length(client):
    r1 = client.post("/api/v1/users/anonymous")
    uid = r1.json()["id"]
    client.cookies.set("politikast_uid", uid)
    r2 = client.put("/api/v1/users/me", json={"display_name": ""})
    assert r2.status_code == 400


def test_banned_user_blocked_from_writes(client):
    r1 = client.post("/api/v1/users/anonymous")
    uid = r1.json()["id"]
    anon_user_service.ban_user(uid, reason="test")
    client.cookies.set("politikast_uid", uid)
    r2 = client.put("/api/v1/users/me", json={"display_name": "x"})
    assert r2.status_code == 401
    assert "banned" in r2.json()["detail"].lower()
