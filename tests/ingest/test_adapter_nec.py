"""NEC 후보 등록부 어댑터 (#47) 테스트.

candidates.json 시드 → stg_kg_triple row 생성 회귀 + 시나리오 fallback.
"""
from __future__ import annotations

from src.ingest.adapters.nec_candidate import (
    NECCandidateAdapter,
    REGION_TO_CONTEST,
)
from src.ingest.base import IngestRunContext


def _ctx(**cfg: object) -> IngestRunContext:
    return IngestRunContext(run_id="t-nec-1", source_id="nec_candidate", config=cfg)


def test_protocol_attributes() -> None:
    a = NECCandidateAdapter()
    assert a.source_id == "nec_candidate"
    assert a.kind == "structured"
    assert a.target_kind == "kg_triple"


def test_registry_mode_emits_kg_triples() -> None:
    a = NECCandidateAdapter()
    payload = a.fetch(_ctx())
    result = a.parse(payload, _ctx())
    assert result.table == "stg_kg_triple"
    # 16 후보 × 최소 3 triples (hasName, runsInContest, ±memberOfParty)
    assert len(result.rows) >= 16 * 3
    # DDL NOT NULL 컬럼 모두 채움 (run_id 는 pipeline 이 stamp).
    for r in result.rows:
        assert r.get("src_doc_id"), f"missing src_doc_id: {r}"
        assert r.get("triple_idx") is not None, f"missing triple_idx: {r}"
        assert r.get("subj"), f"missing subj: {r}"
        assert r.get("pred"), f"missing pred: {r}"
        assert r.get("obj"), f"missing obj: {r}"
        assert r.get("ts"), f"missing ts: {r}"
    # subj_kind 일관
    assert all(r["subj_kind"] == "Candidate" for r in result.rows)


def test_kg_triples_cover_all_regions() -> None:
    a = NECCandidateAdapter()
    rows = a.parse(a.fetch(_ctx()), _ctx()).rows
    regions = {r["region_id"] for r in rows}
    assert regions == set(REGION_TO_CONTEST.keys())
    # src_doc_id 가 source:region:cand 형식
    for r in rows:
        parts = r["src_doc_id"].split(":")
        assert parts[0] == "nec_candidate"
        assert parts[1] == r["region_id"]
        assert parts[2] == r["subj"]


def test_alias_triples_emitted() -> None:
    a = NECCandidateAdapter()
    rows = a.parse(a.fetch(_ctx()), _ctx()).rows
    # 등록부 시드에 alias 가 박혀있는 후보(c_seoul_ppp 오세훈)는 alias 행이 있다
    aliases = [
        r["obj"] for r in rows
        if r["subj"] == "c_seoul_ppp" and r["pred"] == "hasAlias"
    ]
    assert any("Oh" in a for a in aliases)
    assert "吳世勳" in aliases


def test_idempotency() -> None:
    a = NECCandidateAdapter()
    r1 = a.parse(a.fetch(_ctx()), _ctx()).rows
    r2 = a.parse(a.fetch(_ctx()), _ctx()).rows
    assert r1 == r2


def test_scenarios_mode_fallback() -> None:
    a = NECCandidateAdapter()
    rows = a.parse(a.fetch(_ctx(mode="scenarios")), _ctx(mode="scenarios")).rows
    assert rows  # 5 region 시나리오에서 후보 추출
    # 시나리오 candidates 는 alias 가 비어있을 수 있어 hasName 만 보장
    assert any(r["pred"] == "hasName" for r in rows)


def test_triple_idx_unique_per_doc() -> None:
    """(run_id, src_doc_id, triple_idx) PK 충돌 방지."""
    a = NECCandidateAdapter()
    rows = a.parse(a.fetch(_ctx()), _ctx()).rows
    seen: dict[str, set[int]] = {}
    for r in rows:
        bucket = seen.setdefault(r["src_doc_id"], set())
        idx = r["triple_idx"]
        assert idx not in bucket, f"duplicate triple_idx for {r['src_doc_id']}: {idx}"
        bucket.add(idx)


def test_unknown_mode_raises() -> None:
    a = NECCandidateAdapter()
    import pytest as _p

    with _p.raises(ValueError):
        a.fetch(_ctx(mode="banana"))


def test_get_adapter_factory() -> None:
    from src.ingest.adapters.nec_candidate import get_adapter

    a = get_adapter()
    assert hasattr(a, "fetch") and hasattr(a, "parse")
