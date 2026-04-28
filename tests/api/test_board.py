"""Board topic endpoints + comment_count auto-update."""
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


def test_create_topic_requires_cookie():
    get_store().reset_for_test()
    limiter.reset()
    c = TestClient(create_app())
    r = c.post("/api/v1/board/topics", json={
        "region_id": "seoul_mayor", "title": "안녕", "body": "본문",
    })
    assert r.status_code == 401


def test_create_and_get_topic(client):
    r = client.post("/api/v1/board/topics", json={
        "region_id": "seoul_mayor", "title": "안녕", "body": "본문",
    })
    assert r.status_code == 201, r.text
    tid = r.json()["id"]

    r2 = client.get(f"/api/v1/board/topics/{tid}")
    assert r2.status_code == 200
    body = r2.json()
    assert body["topic"]["title"] == "안녕"
    assert body["topic"]["comment_count"] == 0
    assert body["first_comments"] == []


def test_list_topics_with_region_filter(client):
    client.post("/api/v1/board/topics",
                json={"region_id": "seoul_mayor", "title": "A", "body": "x"})
    client.post("/api/v1/board/topics",
                json={"region_id": "daegu_mayor", "title": "B", "body": "x"})
    r = client.get("/api/v1/board/topics?region_id=seoul_mayor")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["data"][0]["title"] == "A"


def test_comment_count_increments_on_board_comment(client):
    rt = client.post("/api/v1/board/topics", json={
        "region_id": "seoul_mayor", "title": "A", "body": "x",
    })
    tid = rt.json()["id"]
    rc = client.post("/api/v1/comments", json={
        "scope_type": "board_topic", "scope_id": tid, "body": "댓글1",
    })
    assert rc.status_code == 201
    r = client.get(f"/api/v1/board/topics/{tid}")
    assert r.json()["topic"]["comment_count"] == 1
    # delete 시 다시 0
    cid = rc.json()["id"]
    client.delete(f"/api/v1/comments/{cid}")
    r2 = client.get(f"/api/v1/board/topics/{tid}")
    assert r2.json()["topic"]["comment_count"] == 0


def test_update_topic_only_author(client):
    rt = client.post("/api/v1/board/topics", json={
        "region_id": "seoul_mayor", "title": "A", "body": "x",
    })
    tid = rt.json()["id"]

    other = TestClient(create_app())
    r_o = other.post("/api/v1/users/anonymous")
    other.cookies.set("politikast_uid", r_o.json()["id"])
    r = other.put(f"/api/v1/board/topics/{tid}", json={"title": "Z"})
    assert r.status_code == 403


def test_topic_validation_400(client):
    r = client.post("/api/v1/board/topics", json={
        "region_id": "seoul_mayor", "title": "", "body": "x",
    })
    assert r.status_code == 400


def test_report_topic_201(client):
    rt = client.post("/api/v1/board/topics", json={
        "region_id": "seoul_mayor", "title": "A", "body": "x",
    })
    tid = rt.json()["id"]
    r = client.post(f"/api/v1/board/topics/{tid}/report",
                    json={"reason": "abuse"})
    assert r.status_code == 201
