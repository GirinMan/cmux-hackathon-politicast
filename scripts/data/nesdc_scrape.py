"""[DEPRECATED 2026-04-26 — Phase 3 정형 어댑터 전환]

NESDC list scraper for PolitiKAST validation gate.

Iterates list pages for VT026 (제9회 전국동시지방선거) + VT039 (2026년 재·보궐선거)
and collects rows whose 지역 column matches our 5 regions.

Output: _workspace/snapshots/validation/nesdc_list_raw.json (all matches with metadata)

NOTE
----
이 스크립트는 ``src/ingest/adapters/nesdc_poll.py::NESDCPollAdapter`` 로
대체되었다. 신규 코드는 PipelineRunner 경유로 어댑터를 호출해야 한다.
본 파일은 ``nesdc_list_raw.json`` 캐시 갱신용으로만 유지된다 (상대 시점:
hackathon Phase 3+ 에서는 어댑터 정식 채널 사용).
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "_workspace/snapshots/validation/nesdc_list_raw.json"

LIST_URL = "https://www.nesdc.go.kr/portal/bbs/B0000005/list.do"
HEADERS = {
    "User-Agent": "PolitiKAST-Hackathon/1.0 (+research; contact: sjlee@bhsn.ai)",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# region_id -> {area_match: predicate on 지역 cell, title_match: predicate on title cell}
REGION_FILTERS = {
    "seoul_mayor": {
        "areas": ["서울특별시"],
        "title_kw": ["서울특별시", "서울시장", "광역단체장"],
    },
    "gwangju_mayor": {
        "areas": ["광주광역시"],
        "title_kw": ["광주광역시", "광주시장", "광역단체장"],
    },
    "daegu_mayor": {
        "areas": ["대구광역시"],
        "title_kw": ["대구광역시", "대구시장", "광역단체장"],
    },
    "busan_buk_gap": {
        # By-election: title typically includes 부산 북구갑 / 부산광역시 북구
        "areas": ["부산광역시"],
        "title_kw": ["북구갑", "북구 갑", "북구甲", "북구"],
    },
    "daegu_dalseo_gap": {
        "areas": ["대구광역시"],
        "title_kw": ["달서구갑", "달서구 갑", "달서구甲", "달서구"],
    },
}

ELECTION_FILTERS = [
    {"pollGubuncd": "VT026", "label": "제9회 전국동시지방선거"},
    {"pollGubuncd": "VT039", "label": "2026년 재·보궐선거"},
]

DATE_RANGE = {"sdate": "2025-12-03", "edate": "2026-04-26", "searchTime": "3"}
PAGE_SIZE = 10


def fetch_list_page(session: requests.Session, gubuncd: str, page: int) -> str:
    params = {
        "menuNo": "200467",
        "pollGubuncd": gubuncd,
        "pageIndex": page,
        **DATE_RANGE,
    }
    r = session.get(LIST_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text


def parse_list(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for a in soup.select("a.row.tr"):
        m = re.search(r"nttId=(\d+)", a.get("href", ""))
        nttid = m.group(1) if m else None
        cols = [c.get_text(" ", strip=True).replace("\n", " ").strip() for c in a.select("span.col")]
        if len(cols) < 8:
            continue
        rows.append({
            "nttid": nttid,
            "reg_no": cols[0],            # 등록번호
            "pollster": cols[1],          # 조사기관명
            "sponsor": cols[2],           # 의뢰자
            "method": cols[3],            # 조사방법
            "frame": cols[4],             # 표본추출틀
            "title": cols[5],             # 여론조사 명칭
            "field_date": cols[6],        # 조사일시
            "area": cols[7],              # 지역
        })
    return rows


def total_pages(html: str) -> int:
    """Best-effort: pull pagination 'last' link or count rows."""
    soup = BeautifulSoup(html, "html.parser")
    # Pagination is rendered as <button class="page cont last" onclick="location.href='...pageIndex=N'">
    # Scan all onclick href targets for the maximum pageIndex.
    max_idx = 1
    for btn in soup.select("button.page"):
        oc = btn.get("onclick") or ""
        m = re.search(r"pageIndex=(\d+)", oc)
        if m:
            max_idx = max(max_idx, int(m.group(1)))
    return max_idx


def matches_region(row: dict, filt: dict) -> bool:
    if row.get("area") in filt["areas"]:
        title = row.get("title", "")
        for kw in filt["title_kw"]:
            if kw in title:
                return True
    return False


def main() -> int:
    session = requests.Session()
    matches: dict[str, list[dict]] = {rid: [] for rid in REGION_FILTERS}
    summary = {"election_filters": [], "pages_scanned": 0, "rows_seen": 0}
    seen_nttids: set[str] = set()

    for ef in ELECTION_FILTERS:
        gubuncd = ef["pollGubuncd"]
        first = fetch_list_page(session, gubuncd, 1)
        total = total_pages(first)
        # Be conservative: cap at 200 pages per filter
        total = min(total, 200)
        summary["election_filters"].append({"pollGubuncd": gubuncd, "label": ef["label"], "total_pages": total})
        print(f"[{gubuncd}] total_pages={total}", file=sys.stderr)

        # parse the first page we already fetched
        for page in range(1, total + 1):
            try:
                html = first if page == 1 else fetch_list_page(session, gubuncd, page)
            except requests.RequestException as e:
                print(f"[{gubuncd}] page {page} err: {e}", file=sys.stderr)
                continue
            rows = parse_list(html)
            summary["rows_seen"] += len(rows)
            summary["pages_scanned"] += 1
            for row in rows:
                row["pollGubuncd"] = gubuncd
                if not row["nttid"] or row["nttid"] in seen_nttids:
                    continue
                seen_nttids.add(row["nttid"])
                for rid, filt in REGION_FILTERS.items():
                    if matches_region(row, filt):
                        matches[rid].append(row)
                        break  # 1 row → 1 region
            if page % 25 == 0:
                print(f"[{gubuncd}] page {page} processed; matches counts: " +
                      ", ".join(f"{k}={len(v)}" for k, v in matches.items()), file=sys.stderr)
            time.sleep(0.05)  # gentle

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
        "summary": summary,
        "matches": matches,
    }, ensure_ascii=False, indent=2))
    print(f"WROTE {OUT}", file=sys.stderr)
    for rid, lst in matches.items():
        print(f"  {rid}: {len(lst)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
