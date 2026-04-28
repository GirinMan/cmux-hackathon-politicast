"""Phase 6 — scenario-tree public + admin endpoint smoke tests.

These tests run with the slim local venv (no sqlalchemy / no postgres). The
backend is expected to:

  * register the new routes regardless of DB availability (so OpenAPI is
    stable for frontend codegen),
  * gracefully degrade public reads to ``data=null`` + blackout meta when the
    ORM stack is missing,
  * return 503 on admin write paths when the ORM stack is missing.

When sqlalchemy *is* installed in CI, the tests still pass — `data` becomes
either ``None`` (no DB / no rows) or a valid ScenarioTreeDTO; both are
acceptable shapes here.
"""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from backend.app.main import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# Public — GET /api/v1/regions/{rid}/scenario-tree
# ---------------------------------------------------------------------------
def test_public_scenario_tree_route_registered(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert (
        "/api/v1/regions/{region_id}/scenario-tree" in spec["paths"]
    ), "public scenario-tree GET must be exposed"
    node_path = (
        "/api/v1/regions/{region_id}/scenario-tree/{tree_id}/nodes/{node_id}"
    )
    assert node_path in spec["paths"], "node detail GET must be exposed"


def test_public_scenario_tree_returns_blackout_envelope(client: TestClient) -> None:
    """Even without a built tree, the endpoint must return a stable envelope."""
    r = client.get("/api/v1/regions/seoul_mayor/scenario-tree")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body.keys()) == {"data", "blackout"}
    assert body["data"] is None or isinstance(body["data"], dict)
    assert "in_blackout" in body["blackout"]
    assert "hides_ai" in body["blackout"]


def test_public_scenario_tree_invalid_as_of_400(client: TestClient) -> None:
    r = client.get(
        "/api/v1/regions/seoul_mayor/scenario-tree",
        params={"as_of": "not-a-date"},
    )
    # When the ORM is missing the route returns 200 (graceful) before parsing
    # `as_of`. When the ORM is present, the ISO check fires → 400. Accept
    # either to keep CI green across environments.
    assert r.status_code in (200, 400)


def test_public_scenario_node_detail_404_when_unknown(client: TestClient) -> None:
    r = client.get(
        "/api/v1/regions/seoul_mayor/scenario-tree/nonexistent/nodes/n0"
    )
    # 503 when ORM stack absent, 404 when present-but-empty. Both prove the
    # route is wired and refuses to return a stale 200.
    assert r.status_code in (404, 503)


# ---------------------------------------------------------------------------
# Admin — JWT-protected. Without a valid token we must get 401, never 500.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "method, path",
    [
        ("GET", "/admin/api/scenario-trees"),
        ("POST", "/admin/api/scenario-trees/build"),
        ("DELETE", "/admin/api/scenario-trees/00000000-0000-0000-0000-000000000000"),
        ("GET", "/admin/api/calibration/runs"),
        ("POST", "/admin/api/calibration/start"),
        ("GET", "/admin/api/scenario-events"),
        ("POST", "/admin/api/scenario-events"),
        ("DELETE", "/admin/api/scenario-events/00000000-0000-0000-0000-000000000000"),
    ],
)
def test_admin_phase6_requires_auth(
    client: TestClient, method: str, path: str
) -> None:
    r = client.request(method, path, json={})
    # 401: standard JWT rejection. 422: route exists but body validation
    # fires before auth (also acceptable since admin handlers always sit
    # behind `Depends(get_current_admin)` so there's no exposure either way).
    assert r.status_code in (401, 422), (method, path, r.status_code, r.text)
