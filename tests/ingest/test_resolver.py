"""EntityResolver 4-단 fallback 검증 — rule / cache / LLM judge / unresolved."""
from __future__ import annotations

import duckdb
import pytest

from src.ingest.resolver import (
    EntityResolver,
    MIN_CONFIDENCE,
    ResolveStatus,
    Scope,
)
from src.ingest.staging import ensure_stg_tables


@pytest.fixture
def db():
    con = duckdb.connect(":memory:")
    ensure_stg_tables(con)
    yield con
    con.close()


@pytest.fixture
def resolver(db):
    return EntityResolver(db_conn=db)


# -----------------------------------------------------------------------------
# (2) rule layer — registry hits
# -----------------------------------------------------------------------------
def test_rule_hit_party(resolver):
    r = resolver.resolve("국민의힘", scope=Scope.PARTY)
    assert r.status is ResolveStatus.RULE_HIT
    assert r.canonical_id == "p_ppp"
    assert r.confidence == pytest.approx(1.0)


def test_rule_hit_party_alias(resolver):
    r = resolver.resolve("dpk", scope=Scope.PARTY)
    assert r.status is ResolveStatus.RULE_HIT
    assert r.canonical_id == "p_dem"


def test_rule_hit_candidate_with_region(resolver):
    r = resolver.resolve(
        "오세훈 시장은 ...", scope="candidate", context={"region_id": "seoul_mayor"}
    )
    assert r.status is ResolveStatus.RULE_HIT
    assert r.canonical_id == "c_seoul_ppp"


def test_rule_hit_issue(resolver):
    r = resolver.resolve("GTX 연장 공약", scope=Scope.ISSUE)
    assert r.status is ResolveStatus.RULE_HIT
    assert r.canonical_id == "i_transport"


def test_rule_hit_person_hanja_alias(resolver):
    r = resolver.resolve("어제 韓東勳 발언", scope=Scope.PERSON)
    assert r.status is ResolveStatus.RULE_HIT
    assert r.canonical_id == "p_han_donghoon"


# -----------------------------------------------------------------------------
# (1) cache layer — populated via rule, second call hits cache
# -----------------------------------------------------------------------------
def test_cache_hit_after_rule(resolver, db):
    first = resolver.resolve("국민의힘", scope=Scope.PARTY)
    assert first.status is ResolveStatus.RULE_HIT
    second = resolver.resolve("국민의힘", scope=Scope.PARTY)
    assert second.status is ResolveStatus.CACHE_HIT
    assert second.canonical_id == "p_ppp"

    # entity_alias 테이블에 1 row 박제 확인
    n = db.execute(
        "SELECT COUNT(*) FROM entity_alias WHERE alias = ? AND kind = ?",
        ("국민의힘", "party"),
    ).fetchone()[0]
    assert n == 1


# -----------------------------------------------------------------------------
# (3) LLM judge layer — mocked via llm_judge override
# -----------------------------------------------------------------------------
def test_llm_judge_hit_above_threshold(db):
    """alias never matches a rule → LLM judge returns confident answer."""
    seen = []

    def fake_judge(raw, scope, ctx, candidates):
        seen.append((raw, scope))
        return {"id": "p_ppp", "confidence": 0.95, "reason": "test"}

    resolver = EntityResolver(db_conn=db, llm_judge=fake_judge)
    r = resolver.resolve("국힘 (구어체)", scope=Scope.PARTY)
    assert r.status is ResolveStatus.LLM_HIT
    assert r.canonical_id == "p_ppp"
    assert r.confidence >= MIN_CONFIDENCE
    assert seen and seen[0][1] == "party"

    # cache로 박제되어 두 번째 호출은 cache hit
    r2 = resolver.resolve("국힘 (구어체)", scope=Scope.PARTY)
    assert r2.status is ResolveStatus.CACHE_HIT
    assert r2.canonical_id == "p_ppp"


def test_llm_judge_low_confidence_routed_to_unresolved(db):
    def fake_judge(raw, scope, ctx, candidates):
        return {"id": "p_dem", "confidence": 0.4, "reason": "unsure"}

    resolver = EntityResolver(db_conn=db, llm_judge=fake_judge)
    r = resolver.resolve(
        "애매한 정당 표현", scope=Scope.PARTY, run_id="run_x"
    )
    assert r.status is ResolveStatus.UNRESOLVED
    assert r.canonical_id is None
    assert "low_confidence" in (r.note or "")

    n_unres = db.execute(
        "SELECT COUNT(*) FROM unresolved_entity WHERE run_id = ?", ("run_x",)
    ).fetchone()[0]
    assert n_unres == 1
    # cache 에 INSERT 되지 않아야 함 (낮은 신뢰도)
    n_cache = db.execute(
        "SELECT COUNT(*) FROM entity_alias WHERE alias = ?",
        ("애매한 정당 표현",),
    ).fetchone()[0]
    assert n_cache == 0


def test_llm_judge_string_response_parsed(db):
    """LLM 이 raw JSON 문자열을 반환해도 _parse_judge 가 처리."""
    def fake_judge(raw, scope, ctx, candidates):
        return '{"id": "i_transport", "confidence": 0.9, "reason": "match"}'

    resolver = EntityResolver(db_conn=db, llm_judge=fake_judge)
    r = resolver.resolve("교통 이슈 어쩌고", scope=Scope.ISSUE)
    assert r.status is ResolveStatus.LLM_HIT
    assert r.canonical_id == "i_transport"


def test_llm_judge_code_fence_stripped(db):
    def fake_judge(raw, scope, ctx, candidates):
        return '```json\n{"id": "p_lee_jaemyung", "confidence": 0.91}\n```'

    resolver = EntityResolver(db_conn=db, llm_judge=fake_judge)
    r = resolver.resolve("LJM 라는 인물", scope=Scope.PERSON)
    assert r.status is ResolveStatus.LLM_HIT
    assert r.canonical_id == "p_lee_jaemyung"


# -----------------------------------------------------------------------------
# (4) Unresolved — neither rule nor LLM
# -----------------------------------------------------------------------------
def test_unresolved_when_no_llm_and_no_rule(db):
    resolver = EntityResolver(db_conn=db)  # no llm pool, no judge
    r = resolver.resolve(
        "완전히 무관한 텍스트 zzz", scope=Scope.ISSUE, run_id="run_y"
    )
    assert r.status is ResolveStatus.UNRESOLVED
    assert r.canonical_id is None
    n = db.execute(
        "SELECT COUNT(*) FROM unresolved_entity WHERE run_id = ?", ("run_y",)
    ).fetchone()[0]
    assert n == 1


def test_empty_alias_returns_unresolved(resolver):
    r = resolver.resolve("", scope=Scope.PARTY)
    assert r.status is ResolveStatus.UNRESOLVED
    assert r.canonical_id is None
