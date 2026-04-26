"""Ingest NESDC matched poll metadata into DuckDB raw_poll table.

Reads:
  _workspace/snapshots/validation/nesdc_list_raw.json (matches per region)
  Per-poll detail HTML (live-fetch on demand) for fieldwork window + sample size.

Writes:
  raw_poll table (DuckDB)
  _workspace/snapshots/validation/poll_fetch_<region_id>.json (evidence)

Schema:
  raw_poll(poll_id text PRIMARY KEY, contest_id text, region_id text,
           field_start date, field_end date, publish_ts timestamp,
           pollster text, sponsor text, source_url text,
           mode text, sample_size integer, population text,
           margin_error float, quality float, is_placeholder boolean)
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import duckdb
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "_workspace/db/politikast.duckdb"
LIST_JSON = ROOT / "_workspace/snapshots/validation/nesdc_list_raw.json"
EVIDENCE_DIR = ROOT / "_workspace/snapshots/validation"
HEADERS = {"User-Agent": "PolitiKAST-Hackathon/1.0", "Accept-Language": "ko-KR"}
VIEW_URL = "https://www.nesdc.go.kr/portal/bbs/B0000005/view.do"

REGION_TO_CONTEST = {
    "seoul_mayor":      "seoul_mayor_2026",
    "gwangju_mayor":    "gwangju_mayor_2026",
    "daegu_mayor":      "daegu_mayor_2026",
    "busan_buk_gap":    "busan_buk_gap_2026",
    "daegu_dalseo_gap": "daegu_dalseo_gap_2026",
}


def fetch_detail(session: requests.Session, nttid: str, gubuncd: str) -> str:
    params = {
        "nttId": nttid,
        "menuNo": "200467",
        "pollGubuncd": gubuncd,
        "searchTime": "3",
        "sdate": "2025-12-03",
        "edate": "2026-04-26",
    }
    r = session.get(VIEW_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text


def parse_detail(html: str) -> dict:
    """Extract fieldwork window + sample size + population from detail HTML."""
    soup = BeautifulSoup(html, "html.parser")
    out: dict = {}

    tables = soup.find_all("table")
    if not tables:
        return out

    # First table: meta. Iterate rows and pull by 라벨.
    text = tables[0].get_text(" ", strip=True)
    # 조사일시: e.g. "2026-04-22 ... 10시 30분 ~ 20시 40분 2026-04-23 ... 10시 30분 ~ 17시 00분"
    dates = re.findall(r"(20\d{2}-\d{2}-\d{2})", text)
    if dates:
        out["field_start"] = min(dates)
        out["field_end"] = max(dates)
    # 조사대상 line
    for tr in tables[0].find_all("tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all(["th", "td"])]
        if not cells:
            continue
        if any("조사대상" in c for c in cells):
            out["population"] = cells[-1][:200]
        if any("조사기간" in c or "조사일시" in c for c in cells):
            out["fielddesc"] = " ".join(cells)[:300]

    # Second/third table: 표본의 크기 — first row 전체 = sample_size
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

    return out


def ensure_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_poll (
            poll_id        TEXT PRIMARY KEY,
            contest_id     TEXT NOT NULL,
            region_id      TEXT NOT NULL,
            field_start    DATE,
            field_end      DATE,
            publish_ts     TIMESTAMP,
            pollster       TEXT,
            sponsor        TEXT,
            source_url     TEXT,
            mode           TEXT,
            sample_size    INTEGER,
            population     TEXT,
            margin_error   FLOAT,
            quality        FLOAT,
            is_placeholder BOOLEAN DEFAULT FALSE,
            ingested_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            title          TEXT,
            nesdc_reg_no   TEXT
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_poll_result (
            poll_id          TEXT,
            candidate_id     TEXT,
            share            FLOAT,
            undecided_share  FLOAT,
            PRIMARY KEY (poll_id, candidate_id)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS poll_consensus_daily (
            contest_id       TEXT,
            region_id        TEXT,
            as_of_date       DATE,
            candidate_id     TEXT,
            p_hat            FLOAT,
            variance         FLOAT,
            n_polls          INTEGER,
            method_version   TEXT,
            source_poll_ids  TEXT,
            PRIMARY KEY (contest_id, region_id, as_of_date, candidate_id)
        )
    """)


def upsert_raw_poll(con: duckdb.DuckDBPyConnection, row: dict) -> None:
    con.execute("DELETE FROM raw_poll WHERE poll_id = ?", [row["poll_id"]])
    con.execute(
        """
        INSERT INTO raw_poll(
            poll_id, contest_id, region_id, field_start, field_end, publish_ts,
            pollster, sponsor, source_url, mode, sample_size, population,
            margin_error, quality, is_placeholder, title, nesdc_reg_no
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        [
            row["poll_id"], row["contest_id"], row["region_id"],
            row.get("field_start"), row.get("field_end"), row.get("publish_ts"),
            row.get("pollster"), row.get("sponsor"), row.get("source_url"),
            row.get("mode"), row.get("sample_size"), row.get("population"),
            row.get("margin_error"), row.get("quality"),
            row.get("is_placeholder", False),
            row.get("title"), row.get("nesdc_reg_no"),
        ],
    )


def main() -> int:
    payload = json.loads(LIST_JSON.read_text())
    matches = payload["matches"]
    session = requests.Session()
    con = duckdb.connect(str(DB))
    ensure_schema(con)

    rows_inserted = 0
    evidence_per_region: dict[str, dict] = {}

    # Cap per-region detail fetch to most recent N polls (newest reg_no first)
    PER_REGION_CAP = 25
    for region_id, rows in matches.items():
        rows_sorted = sorted(rows, key=lambda x: int(x.get("reg_no") or 0), reverse=True)[:PER_REGION_CAP]
        per = []
        for r in rows_sorted:
            nttid = r["nttid"]
            gubuncd = r["pollGubuncd"]
            poll_id = f"nesdc-{r['reg_no']}"
            # Determine field_date(s) from list 'field_date' col first
            field_date = r.get("field_date") or ""
            f_dates = re.findall(r"(20\d{2}-\d{2}-\d{2})", field_date)
            field_start = min(f_dates) if f_dates else None
            field_end = max(f_dates) if f_dates else None

            # Fetch detail for sample_size + canonical fieldwork
            try:
                html = fetch_detail(session, nttid, gubuncd)
                detail = parse_detail(html)
                time.sleep(0.05)
            except Exception as e:
                detail = {"_err": str(e)}

            field_start = detail.get("field_start") or field_start
            field_end = detail.get("field_end") or field_end

            source_url = (
                f"https://www.nesdc.go.kr/portal/bbs/B0000005/view.do?nttId={nttid}"
                f"&menuNo=200467&pollGubuncd={gubuncd}&searchTime=3"
            )

            row_db = {
                "poll_id":      poll_id,
                "contest_id":   REGION_TO_CONTEST[region_id],
                "region_id":    region_id,
                "field_start":  field_start,
                "field_end":    field_end,
                "publish_ts":   None,
                "pollster":     r.get("pollster"),
                "sponsor":      r.get("sponsor"),
                "source_url":   source_url,
                "mode":         r.get("method"),
                "sample_size":  detail.get("sample_size"),
                "population":   detail.get("population"),
                "margin_error": None,
                "quality":      0.6,
                "is_placeholder": False,
                "title":        r.get("title"),
                "nesdc_reg_no": r.get("reg_no"),
            }
            upsert_raw_poll(con, row_db)
            rows_inserted += 1
            per.append({**row_db, "raw_list_row": r, "detail_summary": {
                "fielddesc": detail.get("fielddesc"),
                "sample_size": detail.get("sample_size"),
                "population": detail.get("population"),
            }})

        evidence_per_region[region_id] = {
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
            "n": len(per),
            "polls": per,
        }
        out = EVIDENCE_DIR / f"poll_fetch_{region_id}.json"
        out.write_text(json.dumps(evidence_per_region[region_id], ensure_ascii=False, indent=2))
        print(f"WROTE {out}: {len(per)} polls", file=sys.stderr)

    print(f"raw_poll rows inserted: {rows_inserted}", file=sys.stderr)
    counts = con.execute("SELECT region_id, COUNT(*) FROM raw_poll GROUP BY region_id ORDER BY region_id").fetchall()
    print("raw_poll counts per region:", counts, file=sys.stderr)
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
