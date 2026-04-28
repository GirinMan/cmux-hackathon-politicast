"""Comment endpoints — CRUD + report + scope_type validation."""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from backend.app.deps import limiter
from backend.app.main import create_app
from backend.app.services._community_store import get_store


@pytest.fixture
def client():
    get_store().reset_for_test()
    limiter.reset()
    c = TestClient(create_app())
    r = c.post("/api/v1/users/anonymous")
    c.cookies.set("politikast_uid", r.json()["id"])
    yield c
    get_store().reset_for_test()
    limiter.reset()


def test_post_comment_no_cookie_returns_401():
    get_store().reset_for_test()
    limiter.reset()
    c = TestClient(create_app())
    r = c.post("/api/v1/comments", json={
        "scope_type": "region", "scope_id": "seoul_mayor", "body": "hi",
    })
    assert r.status_code == 401


def test_create_and_list_comment(client):
    r = client.post("/api/v1/comments", json={
        "scope_type": "region", "scope_id": "seoul_mayor", "body": "안녕",
    })
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    assert cid.startswith("c_")

    r2 = client.get("/api/v1/comments?scope_type=region&scope_id=seoul_mayor")
    assert r2.status_code == 200
    body = r2.json()
    assert body["total"] == 1
    assert body["data"][0]["id"] == cid
    assert body["data"][0]["body"] == "안녕"


def test_scenario_tree_scope_accepted(client):
    """Phase 6 — scenario_tree scope must be a first-class scope_type."""
    tree_id = "tree-7c3e1f"
    r = client.post(
        "/api/v1/comments",
        json={
            "scope_type": "scenario_tree",
            "scope_id": tree_id,
            "body": "이 분기 시나리오 흥미롭네요",
        },
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    r2 = client.get(
        f"/api/v1/comments?scope_type=scenario_tree&scope_id={tree_id}"
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["total"] == 1
    assert body["data"][0]["id"] == cid
    assert body["data"][0]["scope_type"] == "scenario_tree"
    assert body["data"][0]["scope_id"] == tree_id


def test_invalid_scope_type_400(client):
    r = client.post("/api/v1/comments", json={
        "scope_type": "garbage", "scope_id": "x", "body": "hi",
    })
    assert r.status_code == 400


def test_empty_body_400(client):
    r = client.post("/api/v1/comments", json={
        "scope_type": "region", "scope_id": "x", "body": "   ",
    })
    assert r.status_code == 400


def test_update_only_author(client):
    r1 = client.post("/api/v1/comments", json={
        "scope_type": "region", "scope_id": "seoul_mayor", "body": "v1",
    })
    cid = r1.json()["id"]

    r2 = client.put(f"/api/v1/comments/{cid}", json={"body": "v2"})
    assert r2.status_code == 200
    assert r2.json()["body"] == "v2"
    assert r2.json()["edited_count"] == 1

    # 다른 사용자
    other = TestClient(create_app())
    r_o = other.post("/api/v1/users/anonymous")
    other.cookies.set("politikast_uid", r_o.json()["id"])
    r3 = other.put(f"/api/v1/comments/{cid}", json={"body": "hack"})
    assert r3.status_code == 403


def test_soft_delete_returns_204(client):
    r1 = client.post("/api/v1/comments", json={
        "scope_type": "region", "scope_id": "seoul_mayor", "body": "x",
    })
    cid = r1.json()["id"]
    r2 = client.delete(f"/api/v1/comments/{cid}")
    assert r2.status_code == 204
    # 더 이상 list 에 잡히지 않음
    r3 = client.get("/api/v1/comments?scope_type=region&scope_id=seoul_mayor")
    assert r3.json()["total"] == 0


def test_report_creates_report_row(client):
    r1 = client.post("/api/v1/comments", json={
        "scope_type": "region", "scope_id": "seoul_mayor", "body": "x",
    })
    cid = r1.json()["id"]
    r2 = client.post(f"/api/v1/comments/{cid}/report",
                     json={"reason": "스팸입니다"})
    assert r2.status_code == 201
    assert r2.json()["status"] == "open"


def test_parent_comment_must_exist_and_match_scope(client):
    r = client.post("/api/v1/comments", json={
        "scope_type": "region", "scope_id": "seoul_mayor", "body": "x",
        "parent_id": "c_doesnotexist",
    })
    assert r.status_code == 400
