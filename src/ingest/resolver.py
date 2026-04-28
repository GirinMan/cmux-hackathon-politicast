"""EntityResolver — alias → canonical entity 매핑 (4-단 fallback).

흐름:
  (1) `entity_alias` DuckDB 캐시 hit
  (2) registries/{scope}.json rule 매칭 — parties/candidates/issues/persons
  (3) LLMPool judge call (temperature=0, prompt 고정, sqlite cache 활용)
  (4) confidence ≥ MIN_CONFIDENCE → entity_alias INSERT + canonical 반환
      미달 → unresolved_entity INSERT, ResolveStatus.UNRESOLVED 반환

resolve(raw, scope, context, run_id) -> ResolveResult
"""
from __future__ import annotations

import datetime as dt
import enum
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from src.schemas.candidate_registry import (
    CandidateRegistry,
    load_candidate_registry,
)
from src.schemas.issue_registry import IssueRegistry, load_issue_registry
from src.schemas.party import PartyRegistry, load_party_registry
from src.schemas.person_registry import PersonRegistry, load_person_registry


logger = logging.getLogger(__name__)


# Resolve scope = registry name. resolver.resolve(raw, scope=Scope.CANDIDATE, ...)
class Scope(str, enum.Enum):
    PARTY = "party"
    CANDIDATE = "candidate"
    ISSUE = "issue"
    PERSON = "person"

    @classmethod
    def coerce(cls, v: "str | Scope") -> "Scope":
        if isinstance(v, Scope):
            return v
        return cls(str(v))


class ResolveStatus(str, enum.Enum):
    CACHE_HIT = "cache_hit"
    RULE_HIT = "rule_hit"
    LLM_HIT = "llm_hit"
    UNRESOLVED = "unresolved"


# LLM judge confidence floor: 미달 시 unresolved_entity 적재.
MIN_CONFIDENCE = 0.8

# LLM judge prompt — 결정성을 위해 영구 고정. 변경 시 cache 무효화.
RESOLVER_LLM_PROMPT_VERSION = "v1"
RESOLVER_LLM_SYSTEM = (
    "You are an entity resolver for a Korean political knowledge graph.\n"
    "Given an alias text and a list of canonical candidates, choose the best id "
    "(or none). Always reply with JSON of shape "
    '{"id": <string-or-null>, "confidence": <float 0..1>, "reason": <short-string>}.\n'
    "Use confidence < 0.8 if you are not sure."
)


@dataclass
class ResolveResult:
    """resolve(...) 의 출력."""

    raw: str
    scope: Scope
    canonical_id: Optional[str]
    confidence: float
    status: ResolveStatus
    source: str  # "cache" | "rule" | "llm" | "unresolved"
    note: Optional[str] = None


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------
class EntityResolver:
    """alias → canonical 매핑 + DuckDB 캐시 + LLM judge fallback.

    파라미터:
      db_conn: duckdb connection (entity_alias / unresolved_entity 사용).
               None 이면 cache miss 동작 + persistence 비활성화 (테스트용).
      llm_pool: src.llm.llm_pool.LLMPool 인스턴스 (temperature=0 강제).
                None 이면 LLM 단계 skip.
      registries_dir: 모든 registries 루트 (기본은 _workspace/data/registries/).
      llm_judge: 옵션 — 외부 callable 로 override (테스트 mock 용).
                 시그니처: (raw, scope, context, candidates) -> dict
    """

    def __init__(
        self,
        db_conn: Any = None,
        llm_pool: Any = None,
        registries_dir: Optional[Path] = None,
        *,
        party_registry: Optional[PartyRegistry] = None,
        candidate_registry: Optional[CandidateRegistry] = None,
        issue_registry: Optional[IssueRegistry] = None,
        person_registry: Optional[PersonRegistry] = None,
        llm_judge: Any = None,
        llm_model: Optional[str] = None,
    ) -> None:
        self.db = db_conn
        self.llm = llm_pool
        self.llm_judge = llm_judge
        self.llm_model = llm_model
        self.registries_dir = registries_dir

        self.parties = party_registry or self._load_with_dir(
            load_party_registry, "parties.json"
        )
        self.candidates = candidate_registry or self._load_with_dir(
            load_candidate_registry, "candidates.json"
        )
        self.issues = issue_registry or self._load_with_dir(
            load_issue_registry, "issues.json"
        )
        self.persons = person_registry or self._load_with_dir(
            load_person_registry, "persons.json"
        )

    def _load_with_dir(self, loader, fname: str):
        if self.registries_dir is None:
            return loader()
        return loader(self.registries_dir / fname)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def resolve(
        self,
        raw: str,
        scope: "str | Scope",
        context: Optional[dict[str, Any]] = None,
        run_id: Optional[str] = None,
    ) -> ResolveResult:
        scope_e = Scope.coerce(scope)
        ctx = context or {}
        raw_norm = (raw or "").strip()

        if not raw_norm:
            return ResolveResult(
                raw=raw or "",
                scope=scope_e,
                canonical_id=None,
                confidence=0.0,
                status=ResolveStatus.UNRESOLVED,
                source="unresolved",
                note="empty raw",
            )

        # (1) cache
        cached = self._cache_lookup(raw_norm, scope_e)
        if cached:
            cid, conf = cached
            return ResolveResult(
                raw=raw, scope=scope_e, canonical_id=cid,
                confidence=conf, status=ResolveStatus.CACHE_HIT, source="cache",
            )

        # (2) rule
        rule = self._rule_resolve(raw_norm, scope_e, ctx)
        if rule is not None:
            cid, conf = rule
            self._cache_insert(raw_norm, scope_e, cid, conf, source="rule")
            return ResolveResult(
                raw=raw, scope=scope_e, canonical_id=cid,
                confidence=conf, status=ResolveStatus.RULE_HIT, source="rule",
            )

        # (3) LLM judge
        if self.llm is not None or self.llm_judge is not None:
            judge = self._llm_resolve(raw_norm, scope_e, ctx)
            if judge is not None:
                cid, conf, note = judge
                if cid and conf >= MIN_CONFIDENCE:
                    self._cache_insert(raw_norm, scope_e, cid, conf, source="llm")
                    return ResolveResult(
                        raw=raw, scope=scope_e, canonical_id=cid,
                        confidence=conf, status=ResolveStatus.LLM_HIT,
                        source="llm", note=note,
                    )
                # confidence 미달 → unresolved 큐 적재 + reject
                self._unresolved_insert(
                    raw_norm, scope_e, ctx, run_id,
                    suggested_id=cid, note=f"low_confidence={conf:.2f} {note or ''}".strip(),
                )
                return ResolveResult(
                    raw=raw, scope=scope_e, canonical_id=None,
                    confidence=conf, status=ResolveStatus.UNRESOLVED,
                    source="llm",
                    note=f"low_confidence={conf:.2f} suggested={cid}",
                )

        # (4) unresolved
        self._unresolved_insert(raw_norm, scope_e, ctx, run_id)
        return ResolveResult(
            raw=raw, scope=scope_e, canonical_id=None, confidence=0.0,
            status=ResolveStatus.UNRESOLVED, source="unresolved",
        )

    # ------------------------------------------------------------------
    # (1) cache
    # ------------------------------------------------------------------
    def _cache_lookup(
        self, alias: str, scope: Scope
    ) -> Optional[tuple[str, float]]:
        if self.db is None:
            return None
        try:
            row = self.db.execute(
                "SELECT canonical_id, confidence FROM entity_alias "
                "WHERE alias = ? AND kind = ?",
                (alias, scope.value),
            ).fetchone()
        except Exception:
            logger.exception("entity_alias lookup failed (table missing?)")
            return None
        if row is None:
            return None
        cid, conf = row[0], float(row[1] or 1.0)
        return cid, conf

    def _cache_insert(
        self,
        alias: str,
        scope: Scope,
        canonical_id: str,
        confidence: float,
        *,
        source: str,
    ) -> None:
        if self.db is None:
            return
        try:
            self.db.execute(
                "INSERT OR REPLACE INTO entity_alias "
                "(alias, kind, canonical_id, confidence, source, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (alias, scope.value, canonical_id, float(confidence), source,
                 dt.datetime.now(dt.timezone.utc).isoformat()),
            )
        except Exception:
            logger.exception("entity_alias insert failed")

    def _unresolved_insert(
        self,
        alias: str,
        scope: Scope,
        context: dict[str, Any],
        run_id: Optional[str],
        *,
        suggested_id: Optional[str] = None,
        note: Optional[str] = None,
    ) -> None:
        if self.db is None or run_id is None:
            return
        try:
            self.db.execute(
                "INSERT OR REPLACE INTO unresolved_entity "
                "(run_id, alias, kind, context, suggested_id, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    alias,
                    scope.value,
                    json.dumps(
                        {**context, "note": note} if note else context,
                        ensure_ascii=False,
                    ),
                    suggested_id,
                    "pending",
                ),
            )
        except Exception:
            logger.exception("unresolved_entity insert failed")

    # ------------------------------------------------------------------
    # (2) rule
    # ------------------------------------------------------------------
    def _rule_resolve(
        self,
        raw: str,
        scope: Scope,
        ctx: dict[str, Any],
    ) -> Optional[tuple[str, float]]:
        if scope is Scope.PARTY:
            # 1차: id / display_name / alias 정확 일치
            for entry in self.parties.parties:
                if (
                    entry.id == raw
                    or entry.display_name == raw
                    or raw in entry.aliases
                ):
                    return entry.id, 1.0
            # 2차: 부분 문자열 (예: "더불어민주당 후보")
            for entry in self.parties.parties:
                for k in [entry.id, entry.display_name, *entry.aliases]:
                    if k and k in raw:
                        return entry.id, 0.9
            return None

        if scope is Scope.CANDIDATE:
            entry = self.candidates.resolve(
                raw, region_id=ctx.get("region_id") if ctx else None
            )
            if entry is not None:
                return entry.id, 1.0
            return None

        if scope is Scope.ISSUE:
            entry = self.issues.resolve(raw)
            if entry is not None:
                return entry.id, 1.0
            return None

        if scope is Scope.PERSON:
            entry = self.persons.resolve(raw)
            if entry is not None:
                return entry.id, 1.0
            return None

        return None

    # ------------------------------------------------------------------
    # (3) LLM judge
    # ------------------------------------------------------------------
    def _candidate_pool_for_prompt(
        self, scope: Scope, ctx: dict[str, Any]
    ) -> list[dict[str, str]]:
        if scope is Scope.PARTY:
            return [
                {"id": e.id, "name": e.display_name, "aliases": ", ".join(e.aliases)}
                for e in self.parties.parties
            ]
        if scope is Scope.CANDIDATE:
            region = ctx.get("region_id") if ctx else None
            entries = (
                self.candidates.for_region(region)
                if region
                else [e for _, e in self.candidates.all_entries()]
            )
            return [
                {"id": e.id, "name": e.name, "aliases": ", ".join(e.aliases)}
                for e in entries
            ]
        if scope is Scope.ISSUE:
            return [
                {"id": e.id, "name": e.name, "aliases": ", ".join(e.aliases)}
                for e in self.issues.issues
            ]
        if scope is Scope.PERSON:
            return [
                {"id": e.id, "name": e.name, "aliases": ", ".join(e.aliases)}
                for e in self.persons.persons
            ]
        return []

    def _llm_resolve(
        self,
        raw: str,
        scope: Scope,
        ctx: dict[str, Any],
    ) -> Optional[tuple[Optional[str], float, Optional[str]]]:
        candidates = self._candidate_pool_for_prompt(scope, ctx)
        # Test/external override
        if self.llm_judge is not None:
            try:
                out = self.llm_judge(raw, scope.value, ctx, candidates)
            except Exception:
                logger.exception("llm_judge override failed")
                return None
            return self._parse_judge(out)

        if self.llm is None:
            return None

        prompt_user = json.dumps(
            {
                "alias": raw,
                "scope": scope.value,
                "context": ctx,
                "candidates": candidates,
                "min_confidence": MIN_CONFIDENCE,
                "instruction": (
                    "Choose the best canonical id from candidates. "
                    "If none clearly matches return id=null and confidence<0.8."
                ),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        try:
            resp_text = self.llm.chat(
                [{"role": "user", "content": prompt_user}],
                system_instruction=RESOLVER_LLM_SYSTEM,
                temperature=0.0,
                max_output_tokens=256,
                json_mode=True,
                cache=True,
                resolver_prompt_version=RESOLVER_LLM_PROMPT_VERSION,
                resolver_scope=scope.value,
                **({"model": self.llm_model} if self.llm_model else {}),
            )
        except Exception:
            logger.exception("LLM judge call failed")
            return None
        return self._parse_judge(resp_text)

    @staticmethod
    def _parse_judge(
        out: Any,
    ) -> Optional[tuple[Optional[str], float, Optional[str]]]:
        if out is None:
            return None
        if isinstance(out, dict):
            data = out
        elif isinstance(out, str):
            text = out.strip()
            if not text:
                return None
            # Strip ```json ... ``` 코드 펜스 (LLM이 가끔 둘러쌈).
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I).strip()
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                return (None, 0.0, "judge returned non-JSON")
        else:
            return None
        cid = data.get("id")
        try:
            conf = float(data.get("confidence", 0.0))
        except (TypeError, ValueError):
            conf = 0.0
        return (cid, max(0.0, min(1.0, conf)), data.get("reason"))


__all__ = [
    "EntityResolver",
    "ResolveResult",
    "ResolveStatus",
    "Scope",
    "MIN_CONFIDENCE",
    "RESOLVER_LLM_PROMPT_VERSION",
]
