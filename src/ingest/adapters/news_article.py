"""뉴스 기사 LLM 어댑터 — `news_article` source.

흐름:
  fetch(ctx): _workspace/data/news_seeds.json (또는 ctx.config["seeds_path"])
              에서 큐레이션된 기사 메타+본문을 읽는다. 자동 크롤링은 out of scope.

  parse(payload, ctx): 각 기사 → LLMPool 에 KG 스키마 prompt 호출 →
              JSON triples → resolver 통과 → stg_kg_triple row.
              temperature=0, prompt 고정. 빈 응답이나 JSON 파싱 실패 시
              unresolved 큐에 raw_text 와 함께 적재.

캐시 결정성: LLMPool.chat 의 source_id / prompt_version 을 cache_extra
key 로 통과시키므로 같은 기사·같은 prompt_version 은 항상 hit.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from src.ingest.base import (
    FetchPayload,
    IngestRunContext,
    ParseResult,
    SourceAdapter,
)
from src.ingest.resolver import EntityResolver, ResolveStatus, Scope

logger = logging.getLogger("ingest.news_article")

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SEEDS_PATH = REPO_ROOT / "_workspace" / "data" / "news_seeds.json"

NEWS_LLM_PROMPT_VERSION = "v1"

NEWS_LLM_SYSTEM = (
    "You extract Korean political-event triples from a news article into a "
    "fixed JSON schema. Output JSON ONLY. Schema:\n"
    '{ "triples": [\n'
    '  {"subj": <speaker-or-entity-name-in-article>, '
    '"pred": <one of: announces|pledges|criticizes|endorses|mentions|attends>, '
    '"obj": <issue/candidate/person name>, '
    '"subj_kind": <"candidate"|"person"|"party">, '
    '"obj_kind": <"issue"|"candidate"|"person"|"party">, '
    '"ts": <ISO8601 datetime, default to article published_at>, '
    '"confidence": <0..1>}\n'
    "] }\n"
    "Use exact strings from the article. If unsure, omit the triple. Be conservative."
)


def _make_user_prompt(article: dict[str, Any]) -> str:
    return json.dumps(
        {
            "article_id": article.get("article_id"),
            "region_id": article.get("region_id"),
            "publisher": article.get("publisher"),
            "published_at": article.get("published_at"),
            "title": article.get("title"),
            "content_text": article.get("content_text", ""),
            "instruction": "Extract triples for the political KG. JSON only.",
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _parse_llm_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    s = text.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.I).strip()
    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------
@dataclass
class NewsArticleAdapter:
    """뉴스 기사 → ``stg_kg_triple`` 어댑터 (LLM extraction)."""

    source_id: str = "news_article"
    kind: str = "llm"
    target_kind: str = "kg_triple"
    seeds_path: Optional[Path] = None
    max_articles_per_run: int = 50

    def fetch(self, ctx: IngestRunContext) -> FetchPayload:
        cfg = dict(ctx.config or {})
        path = Path(cfg.get("seeds_path") or self.seeds_path or DEFAULT_SEEDS_PATH)
        if not path.exists():
            return FetchPayload(source_id=self.source_id, items=[], notes={"seeds_missing": str(path)})
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        items: list[dict[str, Any]] = list(data.get("articles") or [])
        cap = int(cfg.get("max_articles_per_run", self.max_articles_per_run))
        items = items[:cap]
        return FetchPayload(
            source_id=self.source_id,
            items=items,
            notes={"seeds_path": str(path), "n_articles": len(items)},
        )

    def parse(self, payload: FetchPayload, ctx: IngestRunContext) -> ParseResult:
        rows: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []
        triple_idx_global = 0

        resolver: EntityResolver | None = ctx.resolver

        for article in payload.items:
            doc_id = article.get("article_id") or article.get("url") or "unknown"
            if not article.get("content_text"):
                unresolved.append({
                    "alias": doc_id, "kind": "news_article",
                    "context": {"reason": "empty_content_text"},
                })
                continue

            llm_response = self._call_llm(article, ctx)
            if llm_response is None:
                unresolved.append({
                    "alias": doc_id, "kind": "news_article",
                    "context": {"reason": "llm_failure"},
                })
                continue

            data = _parse_llm_json(llm_response)
            if data is None or not isinstance(data.get("triples"), list):
                unresolved.append({
                    "alias": doc_id, "kind": "news_article",
                    "context": {"reason": "json_parse_fail", "raw": llm_response[:512]},
                })
                continue

            for raw_t in data["triples"]:
                if not isinstance(raw_t, dict):
                    continue
                row = self._normalize_triple(
                    raw_t, article, doc_id, triple_idx_global, ctx.run_id, resolver
                )
                if row is None:
                    continue
                rows.append(row)
                triple_idx_global += 1

        return ParseResult(
            table="stg_kg_triple",
            rows=rows,
            unresolved=unresolved,
            extras={"prompt_version": NEWS_LLM_PROMPT_VERSION,
                    "n_articles": len(payload.items)},
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _call_llm(self, article: dict[str, Any], ctx: IngestRunContext) -> Optional[str]:
        if ctx.llm_pool is None:
            logger.warning("news_article: ctx.llm_pool=None — skipping LLM call")
            return None
        try:
            return ctx.llm_pool.chat(
                [{"role": "user", "content": _make_user_prompt(article)}],
                system_instruction=NEWS_LLM_SYSTEM,
                temperature=0.0,
                max_output_tokens=1024,
                json_mode=True,
                cache=True,
                source_id=self.source_id,
                prompt_version=NEWS_LLM_PROMPT_VERSION,
                article_id=str(article.get("article_id") or ""),
            )
        except Exception:
            logger.exception("news_article LLM call failed for %s", article.get("article_id"))
            return None

    def _normalize_triple(
        self,
        raw: dict[str, Any],
        article: dict[str, Any],
        doc_id: str,
        triple_idx: int,
        run_id: str,
        resolver: EntityResolver | None,
    ) -> dict[str, Any] | None:
        subj = (raw.get("subj") or "").strip()
        pred = (raw.get("pred") or "").strip()
        obj = (raw.get("obj") or "").strip()
        if not (subj and pred and obj):
            return None

        subj_kind = (raw.get("subj_kind") or "").strip()
        obj_kind = (raw.get("obj_kind") or "").strip()
        ts = raw.get("ts") or article.get("published_at")
        confidence = float(raw.get("confidence", 0.7) or 0.7)

        subj_canonical = subj
        obj_canonical = obj
        if resolver is not None:
            subj_canonical = self._maybe_resolve(
                resolver, subj, subj_kind, article, run_id
            ) or subj
            obj_canonical = self._maybe_resolve(
                resolver, obj, obj_kind, article, run_id
            ) or obj

        # PipelineRunner 가 run_id 를 자동 stamp (line 195) — 어댑터는 미발행.
        return {
            "src_doc_id": doc_id,
            "triple_idx": triple_idx,
            "subj": subj_canonical,
            "pred": pred,
            "obj": obj_canonical,
            "subj_kind": subj_kind,
            "obj_kind": obj_kind,
            "ts": ts,
            "region_id": article.get("region_id"),
            "confidence": confidence,
            "source_url": article.get("url"),
            "raw_text": (article.get("title") or "")[:512],
        }

    @staticmethod
    def _maybe_resolve(
        resolver: EntityResolver,
        raw: str,
        kind: str,
        article: dict[str, Any],
        run_id: str,
    ) -> Optional[str]:
        kind_l = (kind or "").lower()
        scope_map = {
            "candidate": Scope.CANDIDATE,
            "issue": Scope.ISSUE,
            "person": Scope.PERSON,
            "party": Scope.PARTY,
        }
        scope = scope_map.get(kind_l)
        if scope is None:
            return None
        r = resolver.resolve(
            raw,
            scope=scope,
            context={"region_id": article.get("region_id"),
                     "article_id": article.get("article_id")},
            run_id=run_id,
        )
        if r.status in (
            ResolveStatus.CACHE_HIT, ResolveStatus.RULE_HIT, ResolveStatus.LLM_HIT,
        ):
            return r.canonical_id
        return None


def get_adapter() -> SourceAdapter:
    return NewsArticleAdapter()


__all__ = [
    "NewsArticleAdapter",
    "NEWS_LLM_PROMPT_VERSION",
    "NEWS_LLM_SYSTEM",
    "get_adapter",
]
