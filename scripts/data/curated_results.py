"""Curated raw_poll_result inserts (V2) + poll_consensus_daily compute (V3).

Sources hand-curated from published media reports for NESDC-registered polls
(see _workspace/snapshots/validation/nesdc_list_raw.json metadata + curated
share data from Korean news outlets cited in source_notes).

V2: For polls with verified published candidate shares, insert into
    raw_poll_result(poll_id, candidate_id, share, undecided_share).

V3: Compute poll_consensus_daily(contest_id, region_id, as_of_date,
    candidate_id, p_hat, variance, n_polls, method_version="weighted_v1",
    source_poll_ids) using exponential time-decay + sample-size weighting:
        w_i = sample_size_i * exp(-ln(2) * (as_of_date - field_end_i) / half_life_days)
    Half-life = 7 days. Variance from weighted sample variance across polls.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "_workspace/db/politikast.duckdb"
EVIDENCE = ROOT / "_workspace/snapshots/validation"

# ---- Curated direct-label results (V2) ----
# Each entry: {poll_id, region_id, by_candidate: {cand_id: share}, undecided, source_note}
CURATED_RESULTS = [
    # SEOUL ===========================================================
    {
        "poll_id": "nesdc-16200",
        "region_id": "seoul_mayor",
        "shares": {
            "c_seoul_dpk": 0.456,
            "c_seoul_ppp": 0.354,
        },
        "undecided": 0.19,
        "source_note": "KSOI/CBS 2026-04-22~23 n=1001; 정원오 45.6 / 오세훈 35.4 (digitaltimes/munhwa/hankookilbo coverage)",
    },
    {
        "poll_id": "nesdc-16198",
        "region_id": "seoul_mayor",
        "shares": {
            "c_seoul_dpk": 0.497,
            "c_seoul_ppp": 0.359,
        },
        "undecided": 0.144,
        "source_note": "조원씨앤아이/스트레이트뉴스 2026-04-20~21 n=802; 양자대결 정원오 49.7 / 오세훈 35.9 (munhwa)",
    },
    # DAEGU MAYOR =====================================================
    {
        "poll_id": "nesdc-16158",
        "region_id": "daegu_mayor",
        "shares": {
            # 이진숙(0.172) and 주호영(0.074) are NOT in the scenario candidate set;
            # we drop them and renormalize-aware downstream consumers should know undecided
            # absorbs the unmapped 24.6%.
            "c_daegu_dpk":      0.453,
            "c_daegu_ppp_choo": 0.162,
            "c_daegu_ppp_yoo":  0.054,
        },
        "undecided": 0.331,  # = 1 - (0.453 + 0.162 + 0.054) ≈ residual + 이진숙 + 주호영 + 미상
        "source_note": "Ace Research/대구MBC 2026-04-18~19 n=1002; 김부겸 45.3 / 이진숙 17.2 / 추경호 16.2 / 주호영 7.4 / 유영하 5.4. 이진숙·주호영 unmapped to scenario.",
    },
    # BUSAN BUK-GAP ====================================================
    {
        "poll_id": "nesdc-16169",
        "region_id": "busan_buk_gap",
        "shares": {
            "c_busan_dpk":       0.31,
            "c_busan_indep_han": 0.26,
            "c_busan_ppp":       0.21,
        },
        "undecided": 0.22,  # = 1 - 0.78 (이영풍 0.05 + 미상 0.17)
        "source_note": "KOPRA/인싸잇 2026-04-19~20 n=505; 하정우 31 / 한동훈 26 / 박민식 21 / 이영풍 5. ±4.4pp. (mediawatch/dt/daum)",
    },
    # GWANGJU MAYOR ===================================================
    # No NESDC poll in our top-25 has a published candidate share map that
    # uses scenario candidate_ids cleanly (current field reshuffled around
    # 광주·전남 통합 후보). Marked deferred; raw_poll metadata still ingested.
]

# ---- Consensus computation (V3) ----
HALF_LIFE_DAYS = 7
METHOD_VERSION = "weighted_v1"


def daterange(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def parse_date(s: str | date) -> date:
    if isinstance(s, date):
        return s
    return date.fromisoformat(s)


def compute_consensus(
    polls: list[dict],
    as_of: date,
    candidate_id: str,
) -> tuple[float, float, int, list[str]] | None:
    """polls: list of {poll_id, field_end (date), sample_size, share}. Returns (p_hat, variance, n_polls, ids)."""
    cands = [p for p in polls if p.get("share") is not None]
    cands = [p for p in cands if parse_date(p["field_end"]) <= as_of]
    if not cands:
        return None
    weights = []
    shares = []
    ids = []
    for p in cands:
        age = max((as_of - parse_date(p["field_end"])).days, 0)
        sample = p.get("sample_size") or 500
        w = sample * math.exp(-math.log(2) * age / HALF_LIFE_DAYS)
        if w <= 0:
            continue
        weights.append(w)
        shares.append(float(p["share"]))
        ids.append(p["poll_id"])
    if not weights:
        return None
    sw = sum(weights)
    p_hat = sum(w * s for w, s in zip(weights, shares)) / sw
    if len(weights) > 1:
        var = sum(w * (s - p_hat) ** 2 for w, s in zip(weights, shares)) / sw
    else:
        # Single-poll variance ≈ p(1-p)/n_eff
        n_eff = sum(weights)
        var = max(p_hat * (1 - p_hat) / max(n_eff, 1), 1e-6)
    return p_hat, var, len(weights), ids


def main() -> int:
    con = duckdb.connect(str(DB))

    # ---- V2: insert curated results ----
    inserted_results = 0
    for entry in CURATED_RESULTS:
        # Verify poll exists
        row = con.execute("SELECT poll_id, region_id FROM raw_poll WHERE poll_id = ?", [entry["poll_id"]]).fetchone()
        if not row:
            print(f"WARN: poll {entry['poll_id']} not in raw_poll; skipping", file=sys.stderr)
            continue
        if row[1] != entry["region_id"]:
            print(f"WARN: poll {entry['poll_id']} region mismatch ({row[1]} vs {entry['region_id']})", file=sys.stderr)
            continue
        for cand_id, share in entry["shares"].items():
            con.execute(
                "DELETE FROM raw_poll_result WHERE poll_id = ? AND candidate_id = ?",
                [entry["poll_id"], cand_id],
            )
            con.execute(
                "INSERT INTO raw_poll_result(poll_id, candidate_id, share, undecided_share) VALUES (?,?,?,?)",
                [entry["poll_id"], cand_id, float(share), float(entry["undecided"])],
            )
            inserted_results += 1
    print(f"raw_poll_result rows inserted: {inserted_results}", file=sys.stderr)

    # ---- V3: poll_consensus_daily ----
    # For each region with results, build {candidate_id: [poll dicts]} then
    # iterate over a sensible as_of_date grid (region-specific window).
    region_grid = {
        "seoul_mayor":      (date(2026, 4, 12), date(2026, 4, 26)),
        "daegu_mayor":      (date(2026, 4, 12), date(2026, 4, 26)),
        "busan_buk_gap":    (date(2026, 4, 12), date(2026, 4, 26)),
        "gwangju_mayor":    (date(2026, 4, 12), date(2026, 4, 26)),  # no shares yet → empty
        "daegu_dalseo_gap": (date(2026, 4, 12), date(2026, 4, 26)),  # no polls
    }

    consensus_rows = 0
    grid_summary: dict[str, dict] = {}

    for region_id, (start, end) in region_grid.items():
        # Pull all (poll_id, field_end, sample_size, candidate_id, share) for region
        rows = con.execute(
            """
            SELECT rp.poll_id, rp.field_end, rp.sample_size, rpr.candidate_id, rpr.share, rp.contest_id
            FROM raw_poll rp
            JOIN raw_poll_result rpr ON rp.poll_id = rpr.poll_id
            WHERE rp.region_id = ? AND rp.field_end IS NOT NULL
            """,
            [region_id],
        ).fetchall()
        if not rows:
            grid_summary[region_id] = {"n_polls_with_shares": 0, "as_of_dates": 0}
            continue
        contest_id = rows[0][5]
        per_cand: dict[str, list[dict]] = {}
        for poll_id, field_end, sample_size, candidate_id, share, _cid in rows:
            per_cand.setdefault(candidate_id, []).append({
                "poll_id": poll_id, "field_end": field_end,
                "sample_size": sample_size, "share": share,
            })

        # Delete existing region rows in window for idempotency
        con.execute(
            "DELETE FROM poll_consensus_daily WHERE region_id = ? AND as_of_date BETWEEN ? AND ?",
            [region_id, start, end],
        )
        as_of_count = 0
        for as_of in daterange(start, end):
            for cand_id, polls in per_cand.items():
                result = compute_consensus(polls, as_of, cand_id)
                if not result:
                    continue
                p_hat, var, n_polls, ids = result
                con.execute(
                    """
                    INSERT INTO poll_consensus_daily(contest_id, region_id, as_of_date, candidate_id,
                                                     p_hat, variance, n_polls, method_version, source_poll_ids)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    """,
                    [contest_id, region_id, as_of, cand_id,
                     p_hat, var, n_polls, METHOD_VERSION, json.dumps(sorted(set(ids)))],
                )
                consensus_rows += 1
            as_of_count += 1
        grid_summary[region_id] = {
            "contest_id": contest_id,
            "n_polls_with_shares": len(rows),
            "n_candidates_with_shares": len(per_cand),
            "as_of_window": [start.isoformat(), end.isoformat()],
            "as_of_dates": as_of_count,
        }

    print(f"poll_consensus_daily rows inserted: {consensus_rows}", file=sys.stderr)
    for region_id, summ in grid_summary.items():
        print(f"  {region_id}: {summ}", file=sys.stderr)

    # Verify
    counts = con.execute(
        "SELECT region_id, COUNT(*) FROM poll_consensus_daily GROUP BY region_id ORDER BY region_id"
    ).fetchall()
    print("poll_consensus_daily counts:", counts, file=sys.stderr)

    # Write evidence summary
    summary = {
        "generated_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S+09:00"),
        "method_version": METHOD_VERSION,
        "half_life_days": HALF_LIFE_DAYS,
        "raw_poll_result_inserts": inserted_results,
        "consensus_rows": consensus_rows,
        "regions": grid_summary,
        "curated_sources": [
            {"poll_id": e["poll_id"], "region_id": e["region_id"], "source_note": e["source_note"]}
            for e in CURATED_RESULTS
        ],
    }
    out = EVIDENCE / "consensus_v1.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"WROTE {out}", file=sys.stderr)
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
