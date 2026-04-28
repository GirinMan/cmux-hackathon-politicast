"""Admin moderation — report list/resolve + ban."""
from __future__ import annotations

import os

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from backend.app.deps import limiter
from backend.app.main import create_app
from backend.app.services._community_store import get_store
from backend.app.services import auth_service
from backend.app.settings import get_settings


@pytest.fixture
def admin_client(monkeypatch):
    get_store().reset_for_test()
    auth_service.reset_users_for_test()
    limiter.reset()
    monkeypatch.setenv("ADMIN_BOOTSTRAP_PASSWORD", "test-admin-password-1234")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_USER", "admin")
    get_settings.cache_clear()
    # TestClient 가 lifespan 을 자동 호출하지 않으므로 명시적으로 admin 시드.
    auth_service.bootstrap_admin_user(get_settings())
    c = TestClient(create_app())
    r = c.post("/admin/api/auth/login",
               json={"username": "admin", "password": "test-admin-password-1234"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    c.headers["Authorization"] = f"Bearer {token}"
    yield c
    get_store().reset_for_test()
    auth_service.reset_users_for_test()
    limiter.reset()
    get_settings.cache_clear()


@pytest.fixture
def user_client():
    limiter.reset()
    c = TestClient(create_app())
    r = c.post("/api/v1/users/anonymous")
    c.cookies.set("politikast_uid", r.json()["id"])
    return c


def test_admin_list_reports_empty(admin_client):
    r = admin_client.get("/admin/api/reports")
    assert r.status_code == 200
    assert r.json() == []


def test_admin_resolve_dismissed(admin_client, user_client):
    rc = user_client.post("/api/v1/comments", json={
        "scope_type": "region", "scope_id": "seoul_mayor", "body": "x",
    })
    cid = rc.json()["id"]
    user_client.post(f"/api/v1/comments/{cid}/report",
                     json={"reason": "spam"})
    rl = admin_client.get("/admin/api/reports?status=open")
    assert len(rl.json()) == 1
    rid = rl.json()[0]["id"]
    rr = admin_client.post(f"/admin/api/reports/{rid}/resolve",
                           json={"resolution": "dismissed"})
    assert rr.status_code == 200
    assert rr.json()["status"] == "resolved"
    assert rr.json()["resolution"] == "dismissed"
    # comment still exists
    from backend.app.services._community_store import get_store as _gs
    assert _gs().get_comment(cid).deleted_at is None


def test_admin_resolve_soft_deleted_marks_target(admin_client, user_client):
    rc = user_client.post("/api/v1/comments", json={
        "scope_type": "region", "scope_id": "seoul_mayor", "body": "x",
    })
    cid = rc.json()["id"]
    user_client.post(f"/api/v1/comments/{cid}/report", json={"reason": "abuse"})
    rid = admin_client.get("/admin/api/reports").json()[0]["id"]
    rr = admin_client.post(f"/admin/api/reports/{rid}/resolve",
                           json={"resolution": "soft_deleted"})
    assert rr.json()["resolution"] == "soft_deleted"
    from backend.app.services._community_store import get_store as _gs
    assert _gs().get_comment(cid).deleted_at is not None


def test_admin_resolve_banned_user(admin_client, user_client):
    rc = user_client.post("/api/v1/comments", json={
        "scope_type": "region", "scope_id": "seoul_mayor", "body": "x",
    })
    cid = rc.json()["id"]
    # comment 의 user_id 가 곧 author 이므로 그걸 사용 (cookie jar 충돌 회피)
    from backend.app.services._community_store import get_store as _gs
    uid = _gs().get_comment(cid).user_id
    user_client.post(f"/api/v1/comments/{cid}/report", json={"reason": "abuse"})
    rid = admin_client.get("/admin/api/reports").json()[0]["id"]
    admin_client.post(f"/admin/api/reports/{rid}/resolve",
                      json={"resolution": "banned_user"})
    from backend.app.services import anon_user_service
    u = anon_user_service.get_user(uid)
    assert u.banned is True


def test_admin_ban_user_directly(admin_client, user_client):
    # 사용자 1명 만들어서 그 user_id 로 ban (cookie jar 충돌 회피)
    rc = user_client.post("/api/v1/comments", json={
        "scope_type": "region", "scope_id": "seoul_mayor", "body": "x",
    })
    from backend.app.services._community_store import get_store as _gs
    uid = _gs().get_comment(rc.json()["id"]).user_id
    r = admin_client.post(f"/admin/api/users/{uid}/ban", json={"reason": "test"})
    assert r.status_code == 200
    assert r.json()["banned"] is True


def test_admin_pin_topic(admin_client, user_client):
    rt = user_client.post("/api/v1/board/topics", json={
        "region_id": "seoul_mayor", "title": "A", "body": "x",
    })
    tid = rt.json()["id"]
    r = admin_client.post(f"/admin/api/board/topics/{tid}/pin?pinned=true")
    assert r.status_code == 200
    assert r.json()["pinned"] is True


def test_admin_invalid_resolution_400(admin_client, user_client):
    rc = user_client.post("/api/v1/comments", json={
        "scope_type": "region", "scope_id": "seoul_mayor", "body": "x",
    })
    user_client.post(f"/api/v1/comments/{rc.json()['id']}/report",
                     json={"reason": "abuse"})
    rid = admin_client.get("/admin/api/reports").json()[0]["id"]
    r = admin_client.post(f"/admin/api/reports/{rid}/resolve",
                          json={"resolution": "garbage"})
    assert r.status_code == 400


def test_unauthenticated_admin_403(user_client):
    r = user_client.get("/admin/api/reports")
    assert r.status_code in (401, 403)
