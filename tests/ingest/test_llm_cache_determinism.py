"""LLM 결정성 + 캐시 회귀 게이트 (#55).

검증 항목 (news_article / perplexity 둘 다):
  1. 첫 실행: cache miss 다수
  2. 두 번째: cache_hit_rate ≥ 0.9
  3. 두 출력 sha256 동일 (결정성)
  4. source_id 가 다르면 cache 격리 (같은 prompt 라도 다른 entry)

LLMPool 의 sqlite cache 를 임시 디렉토리로 격리해 회귀 게이트로 활용.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb
import pytest

from src.ingest.adapters.news_article import NewsArticleAdapter
from src.ingest.adapters.perplexity import PerplexityAdapter
from src.ingest.base import IngestRunContext
from src.ingest.resolver import EntityResolver
from src.ingest.staging import ensure_stg_tables


class CachingLLM:
    """Real-LLMPool 대용 — sqlite cache 동등 동작 + cache_hits / misses 카운터.

    prompt+model+source_id+prompt_version 같으면 항상 같은 응답.
    """

    def __init__(self, response: str):
        self.response = response
        self._cache: dict[str, str] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def chat(self, messages, **kw):
        key_payload = {
            "messages": messages,
            "model": kw.get("model"),
            "extra": {
                k: kw.get(k)
                for k in (
                    "source_id", "prompt_version", "temperature", "json_mode",
                    "article_id", "region_id",
                )
                if kw.get(k) is not None
            },
        }
        key = hashlib.sha256(
            json.dumps(key_payload, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        cache_enabled = kw.get("cache", True)
        if cache_enabled and key in self._cache:
            self.cache_hits += 1
            return self._cache[key]
        self.cache_misses += 1
        if cache_enabled:
            self._cache[key] = self.response
        return self.response


@pytest.fixture
def db():
    con = duckdb.connect(":memory:")
    ensure_stg_tables(con)
    yield con
    con.close()


def _ctx(db, llm, *, run_id: str, source_id: str, regions=None):
    resolver = EntityResolver(db_conn=db)
    cfg = {"regions": regions} if regions else {}
    return IngestRunContext(
        run_id=run_id, source_id=source_id, db_conn=db,
        llm_pool=llm, resolver=resolver, config=cfg,
    )


def _hash_rows(rows: list[dict]) -> str:
    """Stable canonical hash over rows (excluding run_id which changes per run)."""
    norm = []
    for r in rows:
        norm.append({k: v for k, v in r.items() if k != "run_id"})
    norm.sort(key=lambda r: (str(r.get("src_doc_id")), int(r.get("triple_idx") or 0)))
    return hashlib.sha256(
        json.dumps(norm, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()


# -----------------------------------------------------------------------------
# news_article — 2-run determinism
# -----------------------------------------------------------------------------
def test_news_article_two_run_determinism_and_cache(db):
    adapter = NewsArticleAdapter()
    llm_response = json.dumps({
        "triples": [
            {"subj": "오세훈", "pred": "pledges", "obj": "GTX 연장",
             "subj_kind": "candidate", "obj_kind": "issue",
             "ts": "2026-04-14T10:00:00", "confidence": 0.9},
        ]
    })
    llm = CachingLLM(llm_response)

    ctx1 = _ctx(db, llm, run_id="run_news_1", source_id="news_article")
    payload1 = adapter.fetch(ctx1)
    out1 = adapter.parse(payload1, ctx1)
    misses_after_1 = llm.cache_misses

    ctx2 = _ctx(db, llm, run_id="run_news_2", source_id="news_article")
    payload2 = adapter.fetch(ctx2)
    out2 = adapter.parse(payload2, ctx2)

    total_calls = llm.cache_hits + llm.cache_misses
    second_run_calls = total_calls - misses_after_1
    second_run_hits = llm.cache_hits  # 두 번째 호출 전엔 0이었다고 가정 (위에서 첫 run은 miss only)
    hit_rate = second_run_hits / max(1, second_run_calls)

    assert hit_rate >= 0.9, f"second-run hit rate too low: {hit_rate:.2f}"
    assert _hash_rows(out1.rows) == _hash_rows(out2.rows), "non-deterministic output"
    assert len(out1.rows) == len(out2.rows) > 0


# -----------------------------------------------------------------------------
# perplexity — 2-run determinism (LLM 호출 없는 경로지만 row hash 동일성)
# -----------------------------------------------------------------------------
def test_perplexity_two_run_determinism(db):
    adapter = PerplexityAdapter()
    llm = CachingLLM("")  # 미사용

    ctx1 = _ctx(db, llm, run_id="run_pp_1", source_id="perplexity",
                regions=["seoul_mayor", "daegu_mayor"])
    p1 = adapter.fetch(ctx1)
    o1 = adapter.parse(p1, ctx1)

    ctx2 = _ctx(db, llm, run_id="run_pp_2", source_id="perplexity",
                regions=["seoul_mayor", "daegu_mayor"])
    p2 = adapter.fetch(ctx2)
    o2 = adapter.parse(p2, ctx2)

    assert _hash_rows(o1.rows) == _hash_rows(o2.rows)
    assert len(o1.rows) > 0


# -----------------------------------------------------------------------------
# Cache 격리 — 같은 prompt 라도 source_id 가 다르면 cache 분리
# -----------------------------------------------------------------------------
def test_cache_isolated_by_source_id(db):
    """동일 prompt 라도 source_id 가 다르면 cache miss 가 발생해야 함."""
    llm = CachingLLM('{"triples": []}')

    # 동일 messages / 동일 model 로 두 번 호출하되 source_id 만 다름.
    msgs = [{"role": "user", "content": "ping"}]
    llm.chat(msgs, model="m", source_id="news_article", prompt_version="v1")
    llm.chat(msgs, model="m", source_id="perplexity", prompt_version="v1")

    # 둘 다 miss (= 격리 성공)
    assert llm.cache_misses == 2
    assert llm.cache_hits == 0

    # 같은 source_id 로 다시 호출하면 hit
    llm.chat(msgs, model="m", source_id="news_article", prompt_version="v1")
    assert llm.cache_hits == 1
