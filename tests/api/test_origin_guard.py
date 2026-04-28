"""Tests for the CSRF origin/referer guard middleware."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app())
    # tests/api/conftest.py installs a default Origin on every TestClient so
    # that the rest of the suite passes the guard. The CSRF tests need the
    # bare baseline — drop both origin and referer.
    c.headers.pop("origin", None)
    c.headers.pop("referer", None)
    return c


def _post_topic_payload() -> dict:
    return {"title": "테스트 글", "body": "본문", "region_id": "seoul_mayor"}


def test_post_without_origin_or_referer_is_blocked(client: TestClient) -> None:
    """Default fastapi TestClient has no Origin → CSRF guard rejects."""
    r = client.post("/api/v1/board/topics", json=_post_topic_payload())
    assert r.status_code == 403
    assert "CSRF guard" in r.json()["detail"]


def test_post_with_allowed_origin_passes_guard(client: TestClient) -> None:
    """Origin in cors_origin_list flows through to the handler."""
    r = client.post(
        "/api/v1/board/topics",
        json=_post_topic_payload(),
        headers={"Origin": "http://localhost:5173"},
    )
    # past the guard — handler will respond with 401 ("consent required") since
    # we did not send the politikast_uid cookie. The point is: status != 403.
    assert r.status_code != 403


def test_post_with_disallowed_origin_blocked(client: TestClient) -> None:
    r = client.post(
        "/api/v1/board/topics",
        json=_post_topic_payload(),
        headers={"Origin": "http://evil.example"},
    )
    assert r.status_code == 403


def test_post_with_referer_only_passes_guard(client: TestClient) -> None:
    r = client.post(
        "/api/v1/board/topics",
        json=_post_topic_payload(),
        headers={"Referer": "http://localhost:5173/board"},
    )
    assert r.status_code != 403


def test_post_with_referer_disallowed_origin_blocked(client: TestClient) -> None:
    r = client.post(
        "/api/v1/board/topics",
        json=_post_topic_payload(),
        headers={"Referer": "http://evil.example/page"},
    )
    assert r.status_code == 403


def test_get_without_origin_or_referer_is_blocked(client: TestClient) -> None:
    """Cookie-auth GET 도 Origin/Referer 없으면 차단 — anonymous_uid 누설 시
    non-browser 가 PII 를 read-out 하는 경로를 봉쇄."""
    r = client.get("/api/v1/board/topics")
    assert r.status_code == 403
    assert "CSRF guard" in r.json()["detail"]


def test_get_with_allowed_origin_passes_guard(client: TestClient) -> None:
    r = client.get(
        "/api/v1/board/topics",
        headers={"Origin": "http://localhost:5173"},
    )
    assert r.status_code != 403


def test_get_with_disallowed_origin_blocked(client: TestClient) -> None:
    r = client.get(
        "/api/v1/board/topics",
        headers={"Origin": "http://evil.example"},
    )
    assert r.status_code == 403


def test_get_with_referer_only_passes_guard(client: TestClient) -> None:
    r = client.get(
        "/api/v1/board/topics",
        headers={"Referer": "http://localhost:5173/board"},
    )
    assert r.status_code != 403


def test_get_health_skips_guard(client: TestClient) -> None:
    """/health is public — no Origin required."""
    r = client.get("/health")
    assert r.status_code == 200


def test_internal_path_skips_guard(client: TestClient) -> None:
    """/internal/* uses service token, not cookie — guard skips it."""
    r = client.post("/internal/health-check", json={})
    # 404 (route not defined) or 401 (token missing) but never 403 from guard.
    assert r.status_code != 403


def test_admin_path_skips_guard(client: TestClient) -> None:
    """/admin/* uses JWT bearer — guard skips and JWT layer rejects."""
    r = client.post("/admin/api/auth/login", json={"username": "x", "password": "y"})
    # 401 (bad credentials) or 422, never 403 from guard.
    assert r.status_code != 403


def test_options_preflight_passes_through(client: TestClient) -> None:
    """OPTIONS preflight is handled by CORS middleware before guard fires."""
    r = client.options(
        "/api/v1/board/topics",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.status_code in (200, 204)
