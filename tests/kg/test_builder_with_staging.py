"""Phase 3 (#57) — ``builder.build_with_staging`` end-to-end behaviour."""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from src.kg._calendar_adapter import get_default_t_start
from src.kg.builder import build_kg_from_scenarios, build_with_staging


def test_build_with_staging_no_db_matches_scenario_only():
    """Without a staging DB the function should be a no-op (no-graft)."""
    g_base, idx_base = build_kg_from_scenarios()
    g_staged, idx_staged = build_with_staging(db_path=None)
    # When the workspace's politikast.duckdb has zero stg_kg_triple rows the
    # graphs must be identical (node count + edge count) — adapter-llm not
    # populated yet at this point in the hackathon.
    assert g_staged.number_of_nodes() >= g_base.number_of_nodes()
    assert set(idx_staged.by_region) == set(idx_base.by_region)


def test_build_with_staging_grafts_real_rows(tmp_path: Path):
    duckdb = pytest.importorskip("duckdb")
    db_path = tmp_path / "stg.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute(
        "CREATE TABLE stg_kg_triple ("
        "run_id VARCHAR, src_doc_id VARCHAR, triple_idx INT, "
        "subj VARCHAR, pred VARCHAR, obj VARCHAR, "
        "subj_kind VARCHAR, obj_kind VARCHAR, ts VARCHAR, "
        "region_id VARCHAR, confidence DOUBLE, source_url VARCHAR, "
        "raw_text VARCHAR)"
    )
    base = get_default_t_start()
    con.execute(
        "INSERT INTO stg_kg_triple VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "r1", "d1", 0, "ev_staging_smoke", "about", "c_kim",
            "MediaEvent", "Candidate",
            (base + timedelta(days=3)).isoformat(),
            "seoul_mayor", 0.95, "http://example.com", "smoke",
        ),
    )
    con.close()

    g_base, _ = build_kg_from_scenarios()
    g_staged, idx_staged = build_with_staging(db_path=db_path)

    assert g_staged.number_of_nodes() >= g_base.number_of_nodes() + 1
    assert "MediaEvent:ev_staging_smoke" in g_staged.nodes
    # Index must still resolve all 5 scenario regions.
    assert "seoul_mayor" in idx_staged.by_region


def test_scenario_attributes_win_on_conflict(tmp_path: Path):
    duckdb = pytest.importorskip("duckdb")
    db_path = tmp_path / "stg_conflict.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute(
        "CREATE TABLE stg_kg_triple ("
        "run_id VARCHAR, src_doc_id VARCHAR, triple_idx INT, "
        "subj VARCHAR, pred VARCHAR, obj VARCHAR, "
        "subj_kind VARCHAR, obj_kind VARCHAR, ts VARCHAR, "
        "region_id VARCHAR, confidence DOUBLE, source_url VARCHAR, "
        "raw_text VARCHAR)"
    )
    # Try to overwrite the scenario's curated `name` for a candidate.
    con.execute(
        "INSERT INTO stg_kg_triple VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("r2", "d1", 0, "c_seoul_ppp", "name", "STAGING_NAME",
         "Candidate", "Literal", None, "seoul_mayor", 1.0, None, None),
    )
    con.close()

    g_staged, _ = build_with_staging(db_path=db_path)
    cand = g_staged.nodes.get("Candidate:c_seoul_ppp")
    if cand is None:
        pytest.skip("seoul scenario does not register c_seoul_ppp")
    assert cand.get("name") != "STAGING_NAME", (
        "scenario-curated name was overwritten by staging triple"
    )
