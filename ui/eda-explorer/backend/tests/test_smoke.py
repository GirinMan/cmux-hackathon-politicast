"""Smoke tests — frontend BFF endpoints + contract region filters."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import app  # noqa: E402

client = TestClient(app)


def test_root() -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["name"] == "eda-explorer-api"


def test_health() -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "degraded")
    assert body["mode"] in ("duckdb", "parquet")
    assert body["persona_core_rows"] >= 0


def test_schema() -> None:
    r = client.get("/api/schema")
    assert r.status_code == 200
    body = r.json()
    names = {t["name"] for t in body["tables"]}
    assert {"persona_core", "persona_text"}.issubset(names)


def test_regions_full() -> None:
    r = client.get("/api/regions")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    provs = {p["province"] for p in body["provinces"]}
    # 17 시도 모두 존재 (contract region 핵심 province 는 반드시)
    for must_have in ("서울", "광주", "대구", "부산"):
        assert must_have in provs


def test_regions_five() -> None:
    r = client.get("/api/regions/five")
    assert r.status_code == 200
    body = r.json()
    keys = {x["key"] for x in body["regions"]}
    assert keys == {
        "seoul_mayor",
        "gwangju_mayor",
        "daegu_mayor",
        "busan_buk_gap",
        "daegu_dalseo_gap",
    }
    counts = {x["key"]: x["count"] for x in body["regions"]}
    assert counts["busan_buk_gap"] > 0
    assert counts["daegu_dalseo_gap"] > 0


def test_demographics_global() -> None:
    r = client.get("/api/demographics")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    assert len(body["age_buckets"]) > 0
    assert len(body["sex"]) == 2
    assert len(body["education_level"]) > 0


@pytest.mark.parametrize(
    "region",
    [
        "seoul_mayor",
        "gwangju_mayor",
        "daegu_mayor",
        "busan_buk_gap",
        "daegu_dalseo_gap",
    ],
)
def test_demographics_per_region(region: str) -> None:
    r = client.get(f"/api/demographics?region={region}")
    assert r.status_code == 200
    body = r.json()
    assert body["region"] == region
    # 데이터 존재 region 은 양수
    assert body["total"] > 0


def test_demographics_unknown_region() -> None:
    r = client.get("/api/demographics?region=mars")
    assert r.status_code == 400


def test_occupations_global() -> None:
    r = client.get("/api/occupations?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total_distinct"] > 0
    assert 1 <= len(body["top"]) <= 10


def test_occupations_region() -> None:
    r = client.get("/api/occupations?region=seoul_mayor&limit=5")
    assert r.status_code == 200
    body = r.json()
    assert body["region"] == "seoul_mayor"
    assert len(body["top"]) <= 5


def test_occupations_major() -> None:
    r = client.get("/api/occupations/major?region=busan_buk_gap")
    assert r.status_code == 200
    body = r.json()
    assert body["region"] == "busan_buk_gap"
    assert body["total"] > 0
    assert sum(group["count"] for group in body["groups"]) == body["total"]
    majors = {group["major"] for group in body["groups"]}
    assert "무직·은퇴·기타" in majors
    assert body["meta"]["source"] == "heuristic_string_rollup"


def test_ontology_graph_region() -> None:
    r = client.get("/api/ontology/graph?region=seoul_mayor&cluster_limit=8&occupation_limit=6")
    assert r.status_code == 200
    body = r.json()
    assert body["region"] == "seoul_mayor"
    assert body["total"] > 0
    assert len(body["categories"]) >= 6
    assert len(body["nodes"]) > 12
    assert len(body["edges"]) > 16
    node_ids = {node["id"] for node in body["nodes"]}
    assert "root" in node_ids
    assert any(node["kind"] == "region" for node in body["nodes"])
    assert any(node["kind"] == "age_group" for node in body["nodes"])
    assert any(node["kind"] == "occupation" for node in body["nodes"])
    assert body["meta"]["cluster_source"] == "raw_categorical_sql"
    for edge in body["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids
        assert edge["count"] >= 0
        assert edge["weight"] >= 0


def test_ontology_graph_province_region() -> None:
    r = client.get("/api/ontology/graph?region=province:gyeongbuk&cluster_limit=8&occupation_limit=6")
    assert r.status_code == 200
    body = r.json()
    assert body["region"] == "province:gyeongbuk"
    assert body["total"] > 0
    labels = {node["label"] for node in body["nodes"]}
    assert "경상북" in labels
    assert any(node["kind"] == "district" for node in body["nodes"])


def test_ontology_graph_unknown_region() -> None:
    r = client.get("/api/ontology/graph?region=mars")
    assert r.status_code == 400


def test_results_summary() -> None:
    r = client.get("/api/results")
    assert r.status_code == 200
    body = r.json()
    assert len(body["regions"]) == 5
    keys = {x["region_id"] for x in body["regions"]}
    assert keys == {
        "seoul_mayor",
        "gwangju_mayor",
        "daegu_mayor",
        "busan_buk_gap",
        "daegu_dalseo_gap",
    }
    assert body["totals"]["regions_total"] == 5
    assert body["totals"]["persona_n"] >= 0
    assert body["warnings"]
    statuses = {x["status"] for x in body["regions"]}
    assert statuses <= {"live", "mock", "smoke", "placeholder", "missing"}


def test_result_detail() -> None:
    r = client.get("/api/results/seoul_mayor")
    assert r.status_code == 200
    body = r.json()
    assert body["region_id"] == "seoul_mayor"
    assert body["status"] in {"live", "mock", "smoke", "placeholder", "missing"}
    assert "result" in body
    assert isinstance(body["candidate_labels"], dict)
    assert body["paper_note"]


def test_result_detail_unknown_region() -> None:
    r = client.get("/api/results/mars")
    assert r.status_code == 400


def test_kg_snapshot_region() -> None:
    r = client.get("/api/kg?region=seoul_mayor&timestep=3")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in {"live", "placeholder", "missing"}
    assert isinstance(body["nodes"], list)
    assert isinstance(body["edges"], list)
    assert isinstance(body["available_timesteps"], list)
    assert len(body["snapshots"]) >= 0


def test_kg_snapshot_unknown_region() -> None:
    r = client.get("/api/kg?region=mars")
    assert r.status_code == 400


def test_policy_summary() -> None:
    r = client.get("/api/policy")
    assert r.status_code == 200
    body = r.json()
    assert len(body["regions"]) == 5
    assert "source_files" in body
    assert isinstance(body["downscale_ladder"], list)


def test_personas_sample() -> None:
    r = client.get("/api/personas/sample?region=gwangju_mayor&limit=5&seed=42")
    assert r.status_code == 200
    body = r.json()
    assert body["region"] == "gwangju_mayor"
    assert len(body["samples"]) <= 5
    if body["samples"]:
        s = body["samples"][0]
        assert len(s["uuid"]) == 32


def test_personas_detail_404() -> None:
    r = client.get("/api/personas/" + "0" * 32)
    assert r.status_code in (200, 404)


def test_personas_detail_invalid_uuid() -> None:
    r = client.get("/api/personas/not-a-uuid")
    assert r.status_code == 400


def test_personas_detail_real() -> None:
    """sample 에서 실제 uuid 1개 받아서 detail 조회."""
    sample_r = client.get("/api/personas/sample?limit=1")
    assert sample_r.status_code == 200
    samples = sample_r.json()["samples"]
    if not samples:
        pytest.skip("no data available")
    uuid = samples[0]["uuid"]
    r = client.get(f"/api/personas/{uuid}")
    assert r.status_code == 200
    detail = r.json()
    assert detail["uuid"] == uuid
    # *_list 는 list 형식
    assert isinstance(detail["skills_and_expertise_list"], list)
    assert isinstance(detail["hobbies_and_interests_list"], list)


def test_personas_text_stats() -> None:
    r = client.get("/api/personas/text-stats?region=seoul_mayor&sample_size=200")
    assert r.status_code == 200
    body = r.json()
    fields = {s["field"] for s in body["stats"]}
    # core 3 + long 6 = 9 필드
    assert "persona" in fields
    assert "professional_persona" in fields
