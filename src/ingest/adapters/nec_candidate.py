"""선관위 후보 등록부 어댑터 (stg_kg_triple target).

NEC (선거관리위원회) 공개 API 또는 후보 등록부 페이지를 수집하여 KG triple
형태로 staging 한다. 하커톤 기간엔 NEC API 셋업이 부담이므로 본 어댑터는
다음 두 모드를 지원한다:

1. ``mode = "registry"`` (default): `_workspace/data/registries/candidates.json`
   을 정형 진실 소스로 보고 5 region × 후보 alias 를 KG triple 로 변환.
   회귀 게이트와 KG builder 가 동일 결과를 reproduce 할 수 있도록 결정적.

2. ``mode = "scenarios"``: `_workspace/data/scenarios/*.json` 의 candidates
   섹션을 스캔. registry 가 비어있을 때 fallback.

생성되는 stg_kg_triple row 의 키 (DDL 컬럼 1:1 일치):
    {src_doc_id, triple_idx, subj, pred, obj, subj_kind, obj_kind,
     ts, region_id, confidence, source_url, raw_text}

`run_id` 는 PipelineRunner 가 row 에 자동 stamp 하므로 어댑터는 emit 안 함.
`src_doc_id` 는 후보별 stable 식별자 (`nec_candidate:{region_id}:{candidate_id}`)
로 멀티-run 멱등성 + KG staging_loader 의 doc 단위 dedupe 보장.
`triple_idx` 는 (src_doc_id 내) 0-based 순번.

PipelineRunner / KG staging_loader 가 이를 networkx node/edge 로 변환한다.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

from src.ingest.base import (
    FetchPayload,
    IngestRunContext,
    ParseResult,
    SourceAdapter,
)
from src.schemas.candidate_registry import (
    CandidateEntry,
    CandidateRegistry,
    load_candidate_registry,
)


logger = logging.getLogger("ingest.nec_candidate")

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY_PATH = (
    REPO_ROOT / "_workspace" / "data" / "registries" / "candidates.json"
)
DEFAULT_SCENARIO_DIR = REPO_ROOT / "_workspace" / "data" / "scenarios"

# nesdc_poll.REGION_TO_CONTEST 와 동일 — 본 어댑터에서도 직접 사용.
REGION_TO_CONTEST = {
    "seoul_mayor": "seoul_mayor_2026",
    "gwangju_mayor": "gwangju_mayor_2026",
    "daegu_mayor": "daegu_mayor_2026",
    "busan_buk_gap": "busan_buk_gap_2026",
    "daegu_dalseo_gap": "daegu_dalseo_gap_2026",
}

# triple ts 가 빠지면 firewall 이 reject 하므로, 등록부는 시나리오 cutoff
# 이전 시점으로 box 를 박는다. 사용자가 ctx.config["registered_at"] 로 override
# 가능. 그 외 default 는 election cycle 시작 (2026-01-01 KST).
DEFAULT_REGISTERED_AT = "2026-01-01T00:00:00+09:00"

# 선관위 후보 등록부 페이지 (region 별로 다르지만 본 어댑터는 registry/시나리오
# 진실 소스를 사용하므로 source_url 은 NEC 후보 등록 안내 페이지로 통일).
NEC_CANDIDATE_PAGE = (
    "https://www.nec.go.kr/site/nec/ex/bbs/View.do?cbIdx=1090&bcIdx=181520"
)


@dataclass
class NECCandidateAdapter:
    """선관위/후보 등록부 → ``stg_kg_triple`` 어댑터."""

    source_id: str = "nec_candidate"
    kind: str = "structured"
    target_kind: str = "kg_triple"
    mode: str = "registry"  # "registry" | "scenarios"
    registry_path: Optional[Path] = None
    scenario_dir: Optional[Path] = None
    registered_at: str = DEFAULT_REGISTERED_AT

    # ------------------------------------------------------------------
    def fetch(self, ctx: IngestRunContext) -> FetchPayload:
        cfg = dict(ctx.config or {})
        mode = cfg.get("mode", self.mode)
        if mode == "registry":
            registry = self._load_registry(cfg)
            items = list(self._registry_items(registry))
            note = {
                "mode": "registry",
                "n_regions": len(registry.regions),
            }
        elif mode == "scenarios":
            items = list(self._scenario_items(cfg))
            note = {"mode": "scenarios", "n_items": len(items)}
        else:
            raise ValueError(
                f"NECCandidateAdapter: unknown mode={mode!r}. "
                "허용: 'registry' | 'scenarios'."
            )
        return FetchPayload(
            source_id=self.source_id,
            items=items,
            fetched_at=cfg.get("registered_at", self.registered_at),
            cursor=None,
            notes=note,
        )

    # ------------------------------------------------------------------
    def parse(self, payload: FetchPayload, ctx: IngestRunContext) -> ParseResult:
        cfg = dict(ctx.config or {})
        ts = cfg.get("registered_at", payload.fetched_at or self.registered_at)
        source_url = cfg.get("source_url", NEC_CANDIDATE_PAGE)
        rows: list[dict[str, Any]] = []
        for it in payload.items:
            cand_id = it.get("candidate_id")
            name = it.get("name")
            region_id = it.get("region_id")
            party_id = it.get("party_id")
            aliases = it.get("aliases") or []
            contest_id = REGION_TO_CONTEST.get(region_id, "")
            if not (cand_id and name and region_id):
                continue
            # 후보별 stable doc id — multi-run 멱등 + KG staging_loader doc dedupe.
            src_doc_id = f"{self.source_id}:{region_id}:{cand_id}"
            # 한 후보에 대한 triple 들의 0-based 인덱스. PK (run_id, src_doc_id, triple_idx)
            triple_idx = 0

            def _row(
                pred: str,
                obj: str,
                obj_kind: str,
            ) -> dict[str, Any]:
                nonlocal triple_idx
                row = {
                    "src_doc_id": src_doc_id,
                    "triple_idx": triple_idx,
                    "subj": cand_id,
                    "pred": pred,
                    "obj": obj,
                    "subj_kind": "Candidate",
                    "obj_kind": obj_kind,
                    "ts": ts,
                    "region_id": region_id,
                    "confidence": 0.95,
                    "source_url": source_url,
                    "raw_text": None,
                }
                triple_idx += 1
                return row

            # 핵심 triples — name / party / contest 소속.
            rows.append(_row("hasName", name, "Literal"))
            if party_id:
                rows.append(_row("memberOfParty", party_id, "Party"))
            if contest_id:
                rows.append(_row("runsInContest", contest_id, "Contest"))
            # alias 들은 동일 predicate 'hasAlias' 로 다중 row.
            for alias in aliases:
                if not alias:
                    continue
                rows.append(_row("hasAlias", alias, "Literal"))
        return ParseResult(
            table="stg_kg_triple",
            rows=rows,
            extras={
                "n_in": len(payload.items),
                "n_out": len(rows),
                "ts": ts,
                "source_url": source_url,
            },
        )

    # ------------------------------------------------------------------
    # Registry / scenario loading
    # ------------------------------------------------------------------
    def _load_registry(self, cfg: dict[str, Any]) -> CandidateRegistry:
        path = Path(cfg.get("registry_path") or self.registry_path or DEFAULT_REGISTRY_PATH)
        return load_candidate_registry(path)

    @staticmethod
    def _registry_items(registry: CandidateRegistry) -> Iterable[dict[str, Any]]:
        for region_id, entries in registry.regions.items():
            for entry in entries:
                yield {
                    "candidate_id": entry.id,
                    "name": entry.name,
                    "region_id": region_id,
                    "party_id": entry.party_id,
                    "aliases": list(entry.aliases),
                }

    def _scenario_items(self, cfg: dict[str, Any]) -> Iterable[dict[str, Any]]:
        scen_dir = Path(cfg.get("scenario_dir") or self.scenario_dir or DEFAULT_SCENARIO_DIR)
        for path in sorted(scen_dir.glob("*.json")):
            if path.stem.startswith(("historical", "baseline", "cf_")):
                continue
            try:
                data = json.load(path.open("r", encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as e:
                logger.warning("scenario %s read 실패: %s", path.name, e)
                continue
            region_id = (
                (data.get("contest") or {}).get("region_id")
                or data.get("region_id")
                or path.stem
            )
            for c in data.get("candidates", []) or []:
                yield {
                    "candidate_id": c.get("id") or c.get("candidate_id"),
                    "name": c.get("name"),
                    "region_id": region_id,
                    "party_id": c.get("party") or c.get("party_id"),
                    "aliases": c.get("aliases") or [],
                }


def get_adapter() -> SourceAdapter:
    return NECCandidateAdapter()  # type: ignore[return-value]


__all__ = ["NECCandidateAdapter", "REGION_TO_CONTEST", "get_adapter"]
