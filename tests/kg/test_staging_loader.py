"""Phase 3 (#56) — ``stg_kg_triple`` → networkx merger."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import networkx as nx
import pytest

from src.kg._calendar_adapter import get_default_t_start
from src.kg.builder import KGSchemaError, build_kg_from_dicts
from src.kg.staging_loader import (
    StagingTriple,
    load_kg_triples_from_staging,
    merge_triple_into_graph,
    merge_triples_into_graph,
    row_to_triple,
)
from tests.kg.fixtures import make_synthetic_scenario, SYNTHETIC_REGION_ID


# ---------------------------------------------------------------------------
# Loader — graceful when DB / table missing
# ---------------------------------------------------------------------------
def test_load_returns_empty_when_db_missing(tmp_path: Path):
    out = load_kg_triples_from_staging(
        db_path=tmp_path / "nonexistent.duckdb", region_id=SYNTHETIC_REGION_ID
    )
    assert out == []


def test_load_returns_empty_when_table_missing(tmp_path: Path):
    duckdb = pytest.importorskip("duckdb")
    db_path = tmp_path / "empty.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute("CREATE TABLE other(x INT)")
    con.close()
    out = load_kg_triples_from_staging(
        db_path=db_path, region_id=SYNTHETIC_REGION_ID
    )
    assert out == []


def test_load_reads_real_rows(tmp_path: Path):
    duckdb = pytest.importorskip("duckdb")
    db_path = tmp_path / "with_triples.duckdb"
    con = duckdb.connect(str(db_path))
    # Match staging.DDL_STG_KG_TRIPLE shape (with PK so duplicates can be
    # tested separately).
    con.execute(
        "CREATE TABLE stg_kg_triple ("
        "run_id VARCHAR, src_doc_id VARCHAR, triple_idx INT, "
        "subj VARCHAR, pred VARCHAR, obj VARCHAR, "
        "subj_kind VARCHAR, obj_kind VARCHAR, ts VARCHAR, "
        "region_id VARCHAR, confidence DOUBLE, source_url VARCHAR, "
        "raw_text VARCHAR)"
    )
    base = get_default_t_start()
    rows = [
        ("r1", "d1", 0, "ev_test_1", "about", "c_kim", "MediaEvent",
         "Candidate", (base + timedelta(days=2)).isoformat(),
         SYNTHETIC_REGION_ID, 0.9, "http://example.com", "title text"),
        ("r1", "d1", 1, "ev_test_1", "title", "현장 르포",
         "MediaEvent", "Literal", (base + timedelta(days=2)).isoformat(),
         SYNTHETIC_REGION_ID, 0.9, "http://example.com", None),
        # Cross-region (region_id NULL) — must be returned by region filter.
        ("r1", "d2", 0, "ev_global_1", "about", "c_kim",
         "MediaEvent", "Candidate", (base + timedelta(days=1)).isoformat(),
         None, 1.0, None, None),
    ]
    con.executemany(
        "INSERT INTO stg_kg_triple VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows
    )
    con.close()

    triples = load_kg_triples_from_staging(
        db_path=db_path, region_id=SYNTHETIC_REGION_ID
    )
    assert len(triples) == 3
    assert {t.subj for t in triples} == {"ev_test_1", "ev_global_1"}
    # ts coerced to datetime
    assert all(t.ts is None or isinstance(t.ts, datetime) for t in triples)


# ---------------------------------------------------------------------------
# row_to_triple
# ---------------------------------------------------------------------------
def test_row_to_triple_handles_unparsable_ts():
    base = get_default_t_start()
    t = row_to_triple({
        "run_id": "r", "src_doc_id": "d", "triple_idx": 7,
        "subj": "x", "pred": "p", "obj": "y",
        "subj_kind": "Party", "obj_kind": "Party",
        "ts": "not-a-date",
        "region_id": None, "confidence": "0.5",
    })
    assert t.ts is None
    assert t.confidence == 0.5
    assert t.triple_idx == 7


def test_row_to_triple_defaults():
    t = row_to_triple({})
    assert t.subj == "" and t.pred == "" and t.obj == ""
    assert t.subj_kind == "Literal" and t.obj_kind == "Literal"
    assert t.confidence == 1.0


# ---------------------------------------------------------------------------
# merge_triple_into_graph — scenario > staging
# ---------------------------------------------------------------------------
def test_event_subject_without_ts_raises():
    G = nx.MultiDiGraph()
    bad = StagingTriple(
        run_id="r", src_doc_id="d", triple_idx=0,
        subj="ev_x", pred="about", obj="c_kim",
        subj_kind="MediaEvent", obj_kind="Candidate", ts=None,
    )
    with pytest.raises(KGSchemaError):
        merge_triple_into_graph(G, bad, scenario_node_ids=set())


def test_literal_object_sets_attribute_only_if_missing():
    G, _ = build_kg_from_dicts([make_synthetic_scenario()])
    scenario_ids = set(G.nodes)
    base = get_default_t_start()
    # Try to overwrite the existing scenario title — scenario must win.
    t1 = StagingTriple(
        run_id="r", src_doc_id="d", triple_idx=0,
        subj="ev_01", pred="title", obj="STAGING OVERWRITE ATTEMPT",
        subj_kind="MediaEvent", obj_kind="Literal",
        ts=base + timedelta(days=1),
    )
    counters = merge_triple_into_graph(G, t1, scenario_node_ids=scenario_ids)
    assert counters["skipped_due_to_scenario"] == 1
    title = G.nodes["MediaEvent:ev_01"]["title"]
    assert "OVERWRITE" not in title

    # New attribute key (not in scenario) — accepted.
    t2 = StagingTriple(
        run_id="r", src_doc_id="d", triple_idx=1,
        subj="ev_01", pred="staging_note", obj="LLM 요약",
        subj_kind="MediaEvent", obj_kind="Literal",
        ts=base + timedelta(days=1),
    )
    counters = merge_triple_into_graph(G, t2, scenario_node_ids=scenario_ids)
    assert counters["attrs_added"] == 1
    assert G.nodes["MediaEvent:ev_01"]["staging_note"] == "LLM 요약"


def test_new_event_node_and_edge_get_added():
    G, _ = build_kg_from_dicts([make_synthetic_scenario()])
    base = get_default_t_start()
    t = StagingTriple(
        run_id="r", src_doc_id="d", triple_idx=0,
        subj="ev_brand_new", pred="about", obj="c_kim",
        subj_kind="MediaEvent", obj_kind="Candidate",
        ts=base + timedelta(days=2),
        region_id=SYNTHETIC_REGION_ID,
    )
    counters = merge_triple_into_graph(G, t, scenario_node_ids=set(G.nodes))
    assert counters["nodes_added"] == 1
    assert counters["edges_added"] == 1
    node = G.nodes["MediaEvent:ev_brand_new"]
    assert node["provenance"] == "staging"
    assert node["ts"] == base + timedelta(days=2)


def test_duplicate_edge_skipped():
    G, _ = build_kg_from_dicts([make_synthetic_scenario()])
    base = get_default_t_start()
    t = StagingTriple(
        run_id="r", src_doc_id="d", triple_idx=0,
        subj="ev_01", pred="about", obj="c_kim",
        subj_kind="MediaEvent", obj_kind="Candidate",
        ts=base + timedelta(days=1),
    )
    counters = merge_triple_into_graph(G, t, scenario_node_ids=set(G.nodes))
    assert counters["edges_added"] == 0
    assert counters["skipped_due_to_scenario"] == 1


def test_bulk_merge_aggregates_counters():
    G, _ = build_kg_from_dicts([make_synthetic_scenario()])
    base = get_default_t_start()
    triples = [
        StagingTriple(
            run_id="r", src_doc_id="d", triple_idx=i,
            subj=f"ev_bulk_{i}", pred="about", obj="c_kim",
            subj_kind="MediaEvent", obj_kind="Candidate",
            ts=base + timedelta(days=2 + i),
            region_id=SYNTHETIC_REGION_ID,
        )
        for i in range(3)
    ]
    summary = merge_triples_into_graph(G, triples)
    assert summary["nodes_added"] == 3
    assert summary["edges_added"] == 3
