"""Perplexity LLM 어댑터 — 5 region 컨텍스트 캐시 재현 가능 (`perplexity` source).

기존 `_workspace/data/perplexity/{region}.json` 5개 (수동 큐레이션 시드) 를
PipelineRunner 가 동일하게 재생산할 수 있도록 SourceAdapter 형태로 래핑한다.
같은 cutoff_ts (≤ 2026-04-26) 와 같은 region 셋을 받으면 항상 같은 triple을
반환 (= regression-safe).

- fetch(ctx): config["regions"] (default 전체 5 region) × `_workspace/data/perplexity/{region}.json`
              을 단순 로드. 자동 Perplexity 호출은 out of scope (해커톤);
              ctx.config["use_live_perplexity"]=True 이면 LLMPool 통해 prompt 호출 후 캐시.
- parse(payload, ctx): candidate_event_facts → stg_kg_triple row 변환 (멱등 PK).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from src.ingest.base import (
    FetchPayload,
    IngestRunContext,
    ParseResult,
    SourceAdapter,
)
from src.ingest.resolver import EntityResolver, ResolveStatus, Scope


logger = logging.getLogger("ingest.perplexity")

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PERPLEXITY_DIR = REPO_ROOT / "_workspace" / "data" / "perplexity"

PERPLEXITY_PROMPT_VERSION = "v1"

PERPLEXITY_LLM_SYSTEM = (
    "You curate political event facts for a Korean local-election KG. "
    "Output JSON only. For each fact include: event_id, type, ts (ISO8601), "
    "source, source_url, title, speaker, party_id, about (list of candidate ids), "
    "mentions (list of person ids). Use only facts datable to ts ≤ cutoff_ts."
)

DEFAULT_REGIONS = (
    "seoul_mayor",
    "busan_buk_gap",
    "daegu_mayor",
    "gwangju_mayor",
    "daegu_dalseo_gap",
)


def _flatten_event(
    ev: dict[str, Any], region_id: str
) -> dict[str, Any]:
    """Perplexity event → flat envelope used by parse()."""
    return {
        "event_id": ev.get("event_id"),
        "type": ev.get("type"),
        "ts": ev.get("ts"),
        "source": ev.get("source"),
        "source_url": ev.get("source_url"),
        "title": ev.get("title", ""),
        "speaker": ev.get("speaker"),
        "party_id": ev.get("party_id"),
        "about": list(ev.get("about") or []),
        "mentions": list(ev.get("mentions") or []),
        "region_id": region_id,
        "frame_id": ev.get("frame_id"),
        "sentiment": ev.get("sentiment"),
    }


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------
@dataclass
class PerplexityAdapter:
    source_id: str = "perplexity"
    kind: str = "llm"
    target_kind: str = "kg_triple"
    perplexity_dir: Optional[Path] = None

    def fetch(self, ctx: IngestRunContext) -> FetchPayload:
        cfg = dict(ctx.config or {})
        directory = Path(cfg.get("perplexity_dir") or self.perplexity_dir or DEFAULT_PERPLEXITY_DIR)
        regions = list(cfg.get("regions") or DEFAULT_REGIONS)

        items: list[dict[str, Any]] = []
        missing: list[str] = []
        for region in regions:
            p = directory / f"{region}.json"
            if not p.exists():
                missing.append(region)
                continue
            with p.open("r", encoding="utf-8") as f:
                blob = json.load(f)
            for ev in blob.get("candidate_event_facts") or []:
                items.append(_flatten_event(ev, region_id=blob.get("region_id") or region))

        # Live perplexity 호출 (옵션) — LLMPool 사용으로 sqlite cache 활용 가능.
        if cfg.get("use_live_perplexity") and ctx.llm_pool is not None and missing:
            for region in missing:
                rsp = self._call_live(ctx, region, cfg.get("cutoff_ts"))
                items.extend(rsp)

        return FetchPayload(
            source_id=self.source_id,
            items=items,
            notes={
                "perplexity_dir": str(directory),
                "regions": regions,
                "missing_regions": missing,
                "n_events": len(items),
            },
        )

    def parse(self, payload: FetchPayload, ctx: IngestRunContext) -> ParseResult:
        rows: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []
        triple_idx = 0
        resolver: EntityResolver | None = ctx.resolver

        for ev in payload.items:
            event_id = ev.get("event_id") or "unknown"
            speaker = ev.get("speaker") or ""
            ts = ev.get("ts")
            region_id = ev.get("region_id")
            base_meta = {
                "ts": ts,
                "region_id": region_id,
                "source_url": ev.get("source_url"),
                "raw_text": (ev.get("title") or "")[:512],
            }

            # speaker → party (party_id) — registry 검증 + cache
            if speaker and ev.get("party_id"):
                rows.append(self._row(
                    run_id=ctx.run_id, src_doc_id=event_id, idx=triple_idx,
                    subj=self._maybe(resolver, speaker, Scope.PERSON, region_id, ctx.run_id) or speaker,
                    pred="memberOf",
                    obj=self._maybe(resolver, ev["party_id"], Scope.PARTY, region_id, ctx.run_id) or ev["party_id"],
                    subj_kind="person",
                    obj_kind="party",
                    confidence=0.9, **base_meta,
                ))
                triple_idx += 1

            # speaker (or candidate) → event type (announces / pledges / criticizes)
            pred = self._infer_pred(ev.get("type"))
            if speaker and pred:
                for cand_id in ev.get("about") or [event_id]:
                    rows.append(self._row(
                        run_id=ctx.run_id, src_doc_id=event_id, idx=triple_idx,
                        subj=self._maybe(resolver, speaker, Scope.PERSON, region_id, ctx.run_id) or speaker,
                        pred=pred,
                        obj=self._maybe(resolver, cand_id, Scope.CANDIDATE, region_id, ctx.run_id) or cand_id,
                        subj_kind="person",
                        obj_kind="candidate",
                        confidence=0.85, **base_meta,
                    ))
                    triple_idx += 1

            # mentions → person
            for m in ev.get("mentions") or []:
                rows.append(self._row(
                    run_id=ctx.run_id, src_doc_id=event_id, idx=triple_idx,
                    subj=self._maybe(resolver, speaker, Scope.PERSON, region_id, ctx.run_id) or speaker or event_id,
                    pred="mentions",
                    obj=self._maybe(resolver, m, Scope.PERSON, region_id, ctx.run_id) or m,
                    subj_kind="person",
                    obj_kind="person",
                    confidence=0.8, **base_meta,
                ))
                triple_idx += 1

            if not rows or rows[-1]["src_doc_id"] != event_id:
                # 행이 하나도 안 만들어진 이벤트는 unresolved 큐로
                unresolved.append({
                    "alias": event_id, "kind": "perplexity_event",
                    "context": {"reason": "no_triple_extracted", "region_id": region_id},
                })

        return ParseResult(
            table="stg_kg_triple",
            rows=rows,
            unresolved=unresolved,
            extras={
                "prompt_version": PERPLEXITY_PROMPT_VERSION,
                "n_events": len(payload.items),
                "n_triples": len(rows),
            },
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _infer_pred(ev_type: str | None) -> str | None:
        if not ev_type:
            return None
        t = ev_type.lower()
        if "press" in t or "announce" in t:
            return "announces"
        if "pledge" in t or "policy" in t:
            return "pledges"
        if "criti" in t or "attack" in t or "clash" in t:
            return "criticizes"
        if "endorse" in t:
            return "endorses"
        return "mentions"

    @staticmethod
    def _row(
        *, run_id: str, src_doc_id: str, idx: int,
        subj: str, pred: str, obj: str,
        subj_kind: str, obj_kind: str,
        confidence: float, ts: Any, region_id: Any,
        source_url: Any, raw_text: str,
    ) -> dict[str, Any]:
        # PipelineRunner 가 run_id 자동 stamp — 어댑터 row 에는 포함하지 않는다
        # (nec_candidate 와 동일 12-col 표준). run_id 인자는 resolver 호출용.
        del run_id  # noqa: F841 — kept in signature for resolver context only
        return {
            "src_doc_id": src_doc_id, "triple_idx": idx,
            "subj": subj, "pred": pred, "obj": obj,
            "subj_kind": subj_kind, "obj_kind": obj_kind,
            "ts": ts, "region_id": region_id,
            "confidence": confidence,
            "source_url": source_url, "raw_text": raw_text,
        }

    @staticmethod
    def _maybe(
        resolver: EntityResolver | None,
        raw: str,
        scope: Scope,
        region_id: Any,
        run_id: str,
    ) -> Optional[str]:
        if resolver is None or not raw:
            return None
        r = resolver.resolve(
            raw, scope=scope,
            context={"region_id": region_id} if region_id else None,
            run_id=run_id,
        )
        if r.status in (ResolveStatus.CACHE_HIT, ResolveStatus.RULE_HIT, ResolveStatus.LLM_HIT):
            return r.canonical_id
        return None

    def _call_live(
        self, ctx: IngestRunContext, region_id: str, cutoff_ts: Any
    ) -> list[dict[str, Any]]:
        """Live Perplexity prompt — sqlite-cached via LLMPool. 옵션 경로."""
        if ctx.llm_pool is None:
            return []
        prompt = json.dumps(
            {
                "region_id": region_id,
                "cutoff_ts": cutoff_ts,
                "instruction": (
                    "List political event facts for the region with ts ≤ cutoff_ts. "
                    "JSON shape: {events: [{...candidate_event_facts schema...}]}."
                ),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        try:
            text = ctx.llm_pool.chat(
                [{"role": "user", "content": prompt}],
                system_instruction=PERPLEXITY_LLM_SYSTEM,
                temperature=0.0,
                max_output_tokens=2048,
                json_mode=True,
                cache=True,
                source_id=self.source_id,
                prompt_version=PERPLEXITY_PROMPT_VERSION,
                region_id=region_id,
            )
        except Exception:
            logger.exception("perplexity live call failed (region=%s)", region_id)
            return []
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []
        events = data.get("events") if isinstance(data, dict) else None
        if not isinstance(events, list):
            return []
        return [_flatten_event(ev, region_id=region_id) for ev in events if isinstance(ev, dict)]


def get_adapter() -> SourceAdapter:
    return PerplexityAdapter()


__all__ = [
    "PerplexityAdapter",
    "PERPLEXITY_PROMPT_VERSION",
    "PERPLEXITY_LLM_SYSTEM",
    "get_adapter",
]
