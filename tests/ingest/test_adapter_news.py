"""NewsArticleAdapter — fake LLMPool stub 으로 prompt → JSON → triple 검증."""
from __future__ import annotations

import json

import duckdb
import pytest

from src.ingest.adapters.news_article import (
    NEWS_LLM_PROMPT_VERSION,
    NewsArticleAdapter,
)
from src.ingest.base import IngestRunContext
from src.ingest.resolver import EntityResolver
from src.ingest.staging import ensure_stg_tables


class FakeLLM:
    """Stub LLMPool — records calls + returns canned JSON."""

    def __init__(self, response: str):
        self.response = response
        self.calls: list[dict] = []

    def chat(self, messages, **kwargs):
        self.calls.append({"messages": messages, "kwargs": kwargs})
        return self.response


@pytest.fixture
def db():
    con = duckdb.connect(":memory:")
    ensure_stg_tables(con)
    yield con
    con.close()


def _ctx(db, llm, run_id: str = "run_news_test"):
    resolver = EntityResolver(db_conn=db)
    return IngestRunContext(
        run_id=run_id, source_id="news_article",
        db_conn=db, llm_pool=llm, resolver=resolver,
    )


def test_news_adapter_fetch_seeds():
    adapter = NewsArticleAdapter()
    ctx = IngestRunContext(run_id="r", source_id="news_article")
    payload = adapter.fetch(ctx)
    assert payload.source_id == "news_article"
    assert len(payload.items) >= 1
    assert payload.items[0].get("article_id")


def test_news_adapter_parse_returns_triples(db):
    adapter = NewsArticleAdapter()
    llm_resp = json.dumps({
        "triples": [
            {"subj": "오세훈", "pred": "criticizes", "obj": "이재명",
             "subj_kind": "candidate", "obj_kind": "person",
             "ts": "2026-04-14T10:00:00", "confidence": 0.9},
            {"subj": "오세훈", "pred": "pledges", "obj": "GTX 연장",
             "subj_kind": "candidate", "obj_kind": "issue",
             "ts": "2026-04-14T10:00:00", "confidence": 0.85},
        ]
    })
    llm = FakeLLM(llm_resp)
    ctx = _ctx(db, llm)
    payload = adapter.fetch(ctx)
    result = adapter.parse(payload, ctx)

    assert result.table == "stg_kg_triple"
    assert len(result.rows) >= 2
    # Resolver 가 canonical id 로 치환했는지 확인
    obj_ids = {r["obj"] for r in result.rows}
    # "이재명" → p_lee_jaemyung (PersonRegistry alias resolve)
    assert "p_lee_jaemyung" in obj_ids
    # "GTX 연장" → i_transport
    assert "i_transport" in obj_ids
    assert result.extras["prompt_version"] == NEWS_LLM_PROMPT_VERSION


def test_news_adapter_handles_invalid_json(db):
    adapter = NewsArticleAdapter()
    llm = FakeLLM("not a json at all")
    ctx = _ctx(db, llm)
    payload = adapter.fetch(ctx)
    result = adapter.parse(payload, ctx)
    assert result.rows == []
    # 모든 article 이 unresolved 큐에 적재되어야 함
    assert len(result.unresolved) == len(payload.items)
    assert all(u["context"]["reason"] in {"json_parse_fail", "llm_failure", "empty_content_text"}
               for u in result.unresolved)


def test_news_adapter_strips_code_fences(db):
    adapter = NewsArticleAdapter()
    llm = FakeLLM('```json\n{"triples": [{"subj":"오세훈","pred":"announces","obj":"GTX 연장","subj_kind":"candidate","obj_kind":"issue","confidence":0.9}]}\n```')
    ctx = _ctx(db, llm)
    payload = adapter.fetch(ctx)
    result = adapter.parse(payload, ctx)
    assert any(r["pred"] == "announces" for r in result.rows)


def test_news_adapter_passes_cache_kwargs_to_llm(db):
    """source_id + prompt_version 가 chat() kwargs 로 넘어가 cache key에 포함되는지."""
    adapter = NewsArticleAdapter()
    llm = FakeLLM('{"triples": []}')
    ctx = _ctx(db, llm)
    payload = adapter.fetch(ctx)
    adapter.parse(payload, ctx)
    assert llm.calls, "LLM was not called"
    kw = llm.calls[0]["kwargs"]
    assert kw["temperature"] == 0.0
    assert kw["source_id"] == "news_article"
    assert kw["prompt_version"] == NEWS_LLM_PROMPT_VERSION
