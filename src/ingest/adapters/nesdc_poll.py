"""NESDC 정형 어댑터 (raw_poll target).

scripts/data/nesdc_scrape.py + nesdc_ingest.py 의 fetch/parse 로직을
`SourceAdapter` Protocol 로 재포장. PipelineRunner 가 이 어댑터를 호출하면
``stg_raw_poll`` 테이블에 멱등 INSERT 가능한 row 들이 생성된다.

기존 동작과의 동등성 (회귀 게이트):
- per-region 캡 25 (newest reg_no 우선) — `legacy_per_region_cap` config.
- raw_poll 77 row (legacy snapshot) 와 동일 매핑.
- ``poll_id = f"nesdc-{reg_no}"`` PK.

Test/CI 환경에선 외부 HTTP 가 불가하므로 ``config["list_json_path"]`` 를
받아 cached `_workspace/snapshots/validation/nesdc_list_raw.json` 으로
대체 재생할 수 있다 (회귀 게이트 #49 가 이 경로를 사용).
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from src.ingest.base import (
    FetchPayload,
    IngestRunContext,
    ParseResult,
    SourceAdapter,
)


logger = logging.getLogger("ingest.nesdc_poll")

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LIST_JSON = (
    REPO_ROOT / "_workspace" / "snapshots" / "validation" / "nesdc_list_raw.json"
)
DEFAULT_PER_REGION_CAP = 25

LIST_URL = "https://www.nesdc.go.kr/portal/bbs/B0000005/list.do"
VIEW_URL = "https://www.nesdc.go.kr/portal/bbs/B0000005/view.do"
HEADERS = {
    "User-Agent": "PolitiKAST-Hackathon/1.0 (+research; contact: sjlee@bhsn.ai)",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# region_id -> contest_id 매핑 (legacy nesdc_ingest.py 의 REGION_TO_CONTEST 와 동일).
REGION_TO_CONTEST = {
    "seoul_mayor": "seoul_mayor_2026",
    "gwangju_mayor": "gwangju_mayor_2026",
    "daegu_mayor": "daegu_mayor_2026",
    "busan_buk_gap": "busan_buk_gap_2026",
    "daegu_dalseo_gap": "daegu_dalseo_gap_2026",
}


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------
@dataclass
class NESDCPollAdapter:
    """NESDC 등록 여론조사 → ``stg_raw_poll`` 어댑터."""

    source_id: str = "nesdc_poll"
    kind: str = "structured"
    target_kind: str = "raw_poll"
    list_json_path: Optional[Path] = None
    per_region_cap: int = DEFAULT_PER_REGION_CAP
    fetch_details: bool = False  # CI 회귀 모드에선 False (HTTP 차단)

    # ------------------------------------------------------------------
    # SourceAdapter.fetch
    # ------------------------------------------------------------------
    def fetch(self, ctx: IngestRunContext) -> FetchPayload:
        """List 페이지 → 매칭 row 수집.

        ``ctx.config`` 로 다음을 override 가능:
          - list_json_path : 캐시된 ``nesdc_list_raw.json`` 경로 (HTTP 우회)
          - per_region_cap : 정수 (default 25)
          - fetch_details  : bool (default False)
        """
        cfg = dict(ctx.config or {})
        list_path = Path(
            cfg.get("list_json_path") or self.list_json_path or DEFAULT_LIST_JSON
        )
        per_region_cap = int(cfg.get("per_region_cap", self.per_region_cap))

        if not list_path.exists():
            raise FileNotFoundError(
                f"NESDC list snapshot not found: {list_path}. "
                "scripts/data/nesdc_scrape.py 로 먼저 캐시를 만들거나 "
                "config['list_json_path'] 로 명시 필요."
            )
        with list_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        matches = payload.get("matches") or {}

        # per-region cap (legacy nesdc_ingest 와 동일: newest reg_no 우선).
        items: list[dict[str, Any]] = []
        for region_id, rows in matches.items():
            sorted_rows = sorted(
                rows,
                key=lambda x: int(x.get("reg_no") or 0),
                reverse=True,
            )[:per_region_cap]
            for r in sorted_rows:
                items.append({**r, "_region_id": region_id})

        return FetchPayload(
            source_id=self.source_id,
            items=items,
            fetched_at=payload.get("fetched_at"),
            cursor=None,
            notes={
                "list_json_path": str(list_path),
                "per_region_cap": per_region_cap,
                "n_total_list_rows": sum(len(v) for v in matches.values()),
            },
        )

    # ------------------------------------------------------------------
    # SourceAdapter.parse
    # ------------------------------------------------------------------
    def parse(self, payload: FetchPayload, ctx: IngestRunContext) -> ParseResult:
        """List item → ``stg_raw_poll`` row.

        Detail HTML fetch 는 default off (CI/회귀 모드). ``fetch_details=True``
        + ctx.config 에서 활성 시 sample_size/population/field_window 보강.
        """
        cfg = dict(ctx.config or {})
        fetch_details = bool(cfg.get("fetch_details", self.fetch_details))

        rows: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []
        for item in payload.items:
            try:
                row = self._item_to_row(item, fetch_details=fetch_details)
                if row is None:
                    unresolved.append(item)
                else:
                    rows.append(row)
            except Exception as e:  # pragma: no cover — defensive
                logger.warning("nesdc_poll parse 실패: %s", e)
                unresolved.append({**item, "_error": str(e)})

        return ParseResult(
            table="stg_raw_poll",
            rows=rows,
            unresolved=unresolved,
            extras={
                "n_in": len(payload.items),
                "n_out": len(rows),
                "fetched_at": payload.fetched_at,
            },
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _item_to_row(item: dict[str, Any], *, fetch_details: bool) -> Optional[dict[str, Any]]:
        region_id = item.get("_region_id")
        contest_id = REGION_TO_CONTEST.get(region_id)
        nttid = item.get("nttid")
        reg_no = item.get("reg_no")
        if not (region_id and contest_id and nttid and reg_no):
            return None
        gubuncd = item.get("pollGubuncd") or "VT026"
        # field_date 는 legacy 가 list cell 에서 ISO 날짜를 추출
        field_date = item.get("field_date") or ""
        f_dates = re.findall(r"(20\d{2}-\d{2}-\d{2})", field_date)
        field_start = min(f_dates) if f_dates else None
        field_end = max(f_dates) if f_dates else None

        sample_size: Optional[int] = None
        population: Optional[str] = None
        if fetch_details:  # pragma: no cover — CI 모드에서는 호출 안 됨
            try:
                detail = NESDCPollAdapter._fetch_detail(nttid, gubuncd)
                if detail:
                    field_start = detail.get("field_start") or field_start
                    field_end = detail.get("field_end") or field_end
                    sample_size = detail.get("sample_size")
                    population = detail.get("population")
            except Exception as e:
                logger.warning("nesdc_poll detail fetch 실패 nttid=%s: %s", nttid, e)

        source_url = (
            f"{VIEW_URL}?nttId={nttid}&menuNo=200467&pollGubuncd={gubuncd}&searchTime=3"
        )
        return {
            "poll_id": f"nesdc-{reg_no}",
            "contest_id": contest_id,
            "region_id": region_id,
            "field_start": field_start,
            "field_end": field_end,
            "publish_ts": None,
            "pollster": item.get("pollster"),
            "sponsor": item.get("sponsor"),
            "source_url": source_url,
            "mode": item.get("method"),
            "sample_size": sample_size,
            "population": population,
            "margin_error": None,
            "quality": 0.6,  # legacy default
            "is_placeholder": False,
            "title": item.get("title"),
            "nesdc_reg_no": reg_no,
        }

    @staticmethod
    def _fetch_detail(nttid: str, gubuncd: str) -> Optional[dict[str, Any]]:  # pragma: no cover - HTTP
        try:
            import requests  # type: ignore
            from bs4 import BeautifulSoup  # type: ignore
        except Exception as e:
            logger.warning("requests/bs4 미설치 — detail fetch skip: %s", e)
            return None
        params = {
            "nttId": nttid,
            "menuNo": "200467",
            "pollGubuncd": gubuncd,
            "searchTime": "3",
        }
        r = requests.get(VIEW_URL, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        out: dict[str, Any] = {}
        tables = soup.find_all("table")
        if not tables:
            return out
        text = tables[0].get_text(" ", strip=True)
        dates = re.findall(r"(20\d{2}-\d{2}-\d{2})", text)
        if dates:
            out["field_start"] = min(dates)
            out["field_end"] = max(dates)
        for tr in tables[0].find_all("tr"):
            cells = [td.get_text(" ", strip=True) for td in tr.find_all(["th", "td"])]
            if not cells:
                continue
            if any("조사대상" in c for c in cells):
                out["population"] = cells[-1][:200]
        for t in tables[1:6]:
            cap = t.get_text(" ", strip=True)
            if "표본의 크기" in cap or "표본 크기" in cap:
                for tr in t.find_all("tr"):
                    cells = [td.get_text(" ", strip=True) for td in tr.find_all(["th", "td"])]
                    if len(cells) >= 2 and cells[0].strip() == "전체":
                        try:
                            out["sample_size"] = int(re.sub(r"[^\d]", "", cells[1]))
                        except ValueError:
                            pass
                        break
                break
        time.sleep(0.05)  # gentle
        return out


def get_adapter() -> SourceAdapter:
    """PipelineRunner 가 importlib.import_module(...).get_adapter() 로 호출."""
    return NESDCPollAdapter()  # type: ignore[return-value]


__all__ = ["NESDCPollAdapter", "REGION_TO_CONTEST", "get_adapter"]
