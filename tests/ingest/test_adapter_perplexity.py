"""PerplexityAdapter — 5 region fixture replay regression."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from src.ingest.adapters.perplexity import (
    DEFAULT_REGIONS,
    PerplexityAdapter,
)
from src.ingest.base import IngestRunContext
from src.ingest.resolver import EntityResolver
from src.ingest.staging import ensure_stg_tables


REPO_ROOT = Path(__file__).resolve().parents[2]
PERPLEXITY_DIR = REPO_ROOT / "_workspace" / "data" / "perplexity"


@pytest.fixture
def db():
    con = duckdb.connect(":memory:")
    ensure_stg_tables(con)
    yield con
    con.close()


def _ctx(db, regions=None):
    resolver = EntityResolver(db_conn=db)
    return IngestRunContext(
        run_id="run_pplx_test",
        source_id="perplexity",
        db_conn=db,
        llm_pool=None,
        resolver=resolver,
        config={"regions": regions or list(DEFAULT_REGIONS)},
    )


def test_perplexity_fetch_loads_all_regions(db):
    adapter = PerplexityAdapter()
    ctx = _ctx(db)
    payload = adapter.fetch(ctx)
    assert len(payload.items) > 0
    # 누락된 region 없어야 함
    assert payload.notes["missing_regions"] == []
    # 5개 region 모두 등장
    region_ids = {it["region_id"] for it in payload.items}
    assert region_ids == set(DEFAULT_REGIONS)


def test_perplexity_parse_emits_kg_triples(db):
    adapter = PerplexityAdapter()
    ctx = _ctx(db, regions=["seoul_mayor"])
    payload = adapter.fetch(ctx)
    result = adapter.parse(payload, ctx)

    assert result.table == "stg_kg_triple"
    assert len(result.rows) > 0
    # 모든 row 가 stg_kg_triple PK 컬럼을 갖는지
    for row in result.rows:
        # run_id 는 PipelineRunner 가 stamp — adapter 행에는 없음.
        assert {"src_doc_id", "triple_idx", "subj", "pred", "obj"} <= set(row)
        assert "run_id" not in row
    # memberOf / announces / pledges / criticizes / mentions 중 하나여야 함
    preds = {r["pred"] for r in result.rows}
    assert preds & {"memberOf", "announces", "pledges", "criticizes", "mentions"}


def test_perplexity_regression_seoul_event_count_stable(db):
    """기존 seoul_mayor.json 의 candidate_event_facts 수와 일치해야 함."""
    fixture = json.loads((PERPLEXITY_DIR / "seoul_mayor.json").read_text(encoding="utf-8"))
    expected_events = len(fixture.get("candidate_event_facts", []))

    adapter = PerplexityAdapter()
    ctx = _ctx(db, regions=["seoul_mayor"])
    payload = adapter.fetch(ctx)
    seoul_events = [it for it in payload.items if it["region_id"] == "seoul_mayor"]
    assert len(seoul_events) == expected_events


def test_perplexity_party_resolves_via_resolver(db):
    """speaker → memberOf → party_id row 의 obj 가 canonical p_ppp/p_dem 형태."""
    adapter = PerplexityAdapter()
    ctx = _ctx(db, regions=["seoul_mayor"])
    payload = adapter.fetch(ctx)
    result = adapter.parse(payload, ctx)
    party_rows = [r for r in result.rows if r["pred"] == "memberOf"]
    assert party_rows, "no memberOf rows generated"
    # party_id 는 등록된 canonical id 에서만 와야 함
    assert all(r["obj"] in {"p_dem", "p_ppp", "p_rebuild", "p_indep", "p_jp", "p_ourrep"}
               for r in party_rows)


def test_perplexity_idempotent_pk_keys(db):
    """같은 fetch+parse 두 번 실행 시 (run_id, src_doc_id, triple_idx) 가 stable."""
    adapter = PerplexityAdapter()
    ctx = _ctx(db, regions=["seoul_mayor"])
    payload = adapter.fetch(ctx)
    a = adapter.parse(payload, ctx)
    b = adapter.parse(payload, ctx)
    pks_a = sorted((r["src_doc_id"], r["triple_idx"]) for r in a.rows)
    pks_b = sorted((r["src_doc_id"], r["triple_idx"]) for r in b.rows)
    assert pks_a == pks_b


def test_perplexity_missing_region_recorded(db):
    adapter = PerplexityAdapter()
    ctx = _ctx(db, regions=["seoul_mayor", "nonexistent_region"])
    payload = adapter.fetch(ctx)
    assert "nonexistent_region" in payload.notes["missing_regions"]
