"""Build a deterministic 10-persona stratified sample for busan_buk_gap (R3 hill-climbing).

Same axes spec as Seoul n=10 (sim-engineer 15:08 ack), adapted for the
single-district reality of personas_busan_buk_gap (5,421 rows, 1 district):

- 5 age bins × 2 sex (5M / 5F)
- 5 학사+ / 5 학사 미만
- occupation: white_collar + blue_collar + self_employed + 학생-equiv + 무직/주부
- district axis N/A (only 부산-북구) — replaced by occupation diversity emphasis

Determinism: ORDER BY uuid LIMIT 1 per slot, used_uuid dedup.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "_workspace/db/politikast.duckdb"
REGION = "busan_buk_gap"
TABLE = "personas_busan_buk_gap"
OUT_PERSONAS = ROOT / f"_workspace/data/scenarios/hill_climbing_target_{REGION}_n10.json"
OUT_DIST = ROOT / f"_workspace/snapshots/hill_climbing_target_{REGION}_n10_distribution.json"

EDU_BACHELOR_PLUS = ("4년제 대학교", "대학원")
EDU_SUB_BACHELOR = ("2~3년제 전문대학", "고등학교", "중학교", "초등학교", "무학")

SLOTS = [
    {
        "slot_id": "20s_male_bachelor_marketing",
        "age_lo": 20, "age_hi": 29, "sex": "남자",
        "edu_in": EDU_BACHELOR_PLUS,
        "occupations": ["마케팅 전문가", "사무 보조원", "경영 기획 사무원"],
        "occ_kind": "white_collar_entry",
    },
    {
        "slot_id": "20s_female_subbach_unemployed",
        "age_lo": 20, "age_hi": 29, "sex": "여자",
        "edu_in": EDU_SUB_BACHELOR,
        "occupations": ["무직"],
        "occ_kind": "unemployed_student_equiv",
    },
    {
        "slot_id": "30s_male_bachelor_office",
        "age_lo": 30, "age_hi": 39, "sex": "남자",
        "edu_in": EDU_BACHELOR_PLUS,
        "occupations": ["경영 기획 사무원", "사무 보조원", "경리 사무원"],
        "occ_kind": "white_collar_office",
    },
    {
        "slot_id": "30s_female_bachelor_specialist",
        "age_lo": 30, "age_hi": 39, "sex": "여자",
        "edu_in": EDU_BACHELOR_PLUS,
        "occupations": ["마케팅 전문가", "보육교사", "산업 안전원"],
        "occ_kind": "white_collar_specialist",
    },
    {
        "slot_id": "40s_male_subbach_blue_collar",
        "age_lo": 40, "age_hi": 49, "sex": "남자",
        "edu_in": EDU_SUB_BACHELOR,
        "occupations": [
            "건물 경비원", "시설 경비원", "한식 조리사",
            "하역 및 적재 관련 단순 종사원", "철도운송 관련 종사원",
            "지게차 운전원", "경·소형 화물차 운전원", "승용차 및 승합차 운전원",
        ],
        "occ_kind": "blue_collar",
    },
    {
        "slot_id": "40s_female_bachelor_office",
        "age_lo": 40, "age_hi": 49, "sex": "여자",
        "edu_in": EDU_BACHELOR_PLUS,
        "occupations": ["회계 사무원", "경리 사무원", "마케팅 전문가", "보육교사"],
        "occ_kind": "white_collar_office",
    },
    {
        "slot_id": "50s_male_subbach_self_employed",
        "age_lo": 50, "age_hi": 59, "sex": "남자",
        "edu_in": EDU_SUB_BACHELOR,
        "occupations": ["소규모 상점 경영자", "그 외 일반 영업원"],
        "occ_kind": "self_employed",
    },
    {
        "slot_id": "50s_female_bachelor_finance",
        "age_lo": 50, "age_hi": 59, "sex": "여자",
        "edu_in": EDU_BACHELOR_PLUS,
        "occupations": ["회계 사무원", "경리 사무원", "일반 비서"],
        "occ_kind": "white_collar_office",
    },
    {
        "slot_id": "60p_male_subbach_security",
        "age_lo": 60, "age_hi": 99, "sex": "남자",
        "edu_in": EDU_SUB_BACHELOR,
        "occupations": ["건물 경비원", "시설 경비원", "건물 청소원", "무직"],
        "occ_kind": "blue_collar_or_unemployed",
    },
    {
        "slot_id": "60p_female_subbach_homemaker",
        "age_lo": 60, "age_hi": 99, "sex": "여자",
        "edu_in": EDU_SUB_BACHELOR,
        "occupations": ["무직"],
        "occ_kind": "homemaker_equiv",
    },
]


def pick_slot(con: duckdb.DuckDBPyConnection, slot: dict, used_uuids: set[str]) -> dict | None:
    base_filter = "age BETWEEN ? AND ? AND sex = ? AND education_level = ANY(?)"
    base_params = [slot["age_lo"], slot["age_hi"], slot["sex"], list(slot["edu_in"])]

    candidates = [
        ("tier1_occ_in_list",
         f"{base_filter} AND occupation = ANY(?)",
         base_params + [list(slot["occupations"])]),
        ("tier2_drop_occupation",
         base_filter,
         base_params),
    ]

    for tier_label, where, params in candidates:
        sql = f"SELECT * FROM {TABLE} WHERE {where} ORDER BY uuid LIMIT 32"
        con.execute(sql, params)
        cols = [d[0] for d in con.description]
        rows = con.fetchall()
        for r in rows:
            d = dict(zip(cols, r))
            if d["uuid"] in used_uuids:
                continue
            d["_picked_tier"] = tier_label
            return d
    return None


def edu_class(edu: str) -> str:
    return "bachelor_plus" if edu in EDU_BACHELOR_PLUS else "sub_bachelor"


def age_bin(age: int) -> str:
    if age < 30: return "20s"
    if age < 40: return "30s"
    if age < 50: return "40s"
    if age < 60: return "50s"
    return "60p"


def main() -> int:
    con = duckdb.connect(str(DB), read_only=True)
    used_uuids: set[str] = set()
    picks: list[dict] = []

    for slot in SLOTS:
        p = pick_slot(con, slot, used_uuids)
        if not p:
            print(f"FAIL: no candidate for {slot['slot_id']}", file=sys.stderr)
            continue
        used_uuids.add(p["uuid"])
        picks.append({"slot": slot["slot_id"], "occ_kind": slot["occ_kind"], "persona": p})
        print(f"  {slot['slot_id']:<40}  {p['_picked_tier']:<24}  uuid={p['uuid'][:8]}  age={p['age']}  sex={p['sex']}  edu={p['education_level']}  occ={p['occupation']}", file=sys.stderr)

    personas_out = []
    for entry in picks:
        p = entry["persona"]
        personas_out.append({
            "uuid": p["uuid"],
            "region_id": REGION,
            "slot_id": entry["slot"],
            "occ_kind": entry["occ_kind"],
            "_picked_tier": p.get("_picked_tier"),
            "age": p["age"], "sex": p["sex"],
            "marital_status": p.get("marital_status"),
            "military_status": p.get("military_status"),
            "family_type": p.get("family_type"),
            "housing_type": p.get("housing_type"),
            "education_level": p["education_level"],
            "education_class": edu_class(p["education_level"]),
            "bachelors_field": p.get("bachelors_field"),
            "occupation": p["occupation"],
            "district": p["district"],
            "province": p.get("province"),
            "country": p.get("country"),
            "persona": p.get("persona"),
            "cultural_background": p.get("cultural_background"),
            "skills_and_expertise": p.get("skills_and_expertise"),
            "skills_and_expertise_list": p.get("skills_and_expertise_list"),
            "hobbies_and_interests": p.get("hobbies_and_interests"),
            "hobbies_and_interests_list": p.get("hobbies_and_interests_list"),
            "career_goals_and_ambitions": p.get("career_goals_and_ambitions"),
        })

    dist = {
        "n": len(personas_out),
        "by_age_bin": {}, "by_sex": {}, "by_education_class": {},
        "by_education_level": {}, "by_occupation": {}, "by_occ_kind": {},
        "by_district": {},
        "axes_coverage": {
            "age_bins": sorted({age_bin(p["age"]) for p in personas_out}),
            "sex": sorted({p["sex"] for p in personas_out}),
            "education_classes": sorted({p["education_class"] for p in personas_out}),
            "districts_unique": sorted({p["district"] for p in personas_out}),
            "occ_kinds": sorted({p["occ_kind"] for p in personas_out}),
        },
        "balance_checks": {
            "sex_balance_5_5": (sum(1 for p in personas_out if p["sex"] == "남자"),
                                sum(1 for p in personas_out if p["sex"] == "여자")),
            "edu_balance_5_5": (sum(1 for p in personas_out if p["education_class"] == "bachelor_plus"),
                                sum(1 for p in personas_out if p["education_class"] == "sub_bachelor")),
            "age_bin_counts": {b: sum(1 for p in personas_out if age_bin(p["age"]) == b)
                               for b in ("20s","30s","40s","50s","60p")},
            "district_unique_count": len({p["district"] for p in personas_out}),
            "district_note": "busan_buk_gap personas table has only 1 district (부산-북구) — N/A axis, replaced by occupation diversity",
        },
    }
    def bump(d, k):
        d[k] = d.get(k, 0) + 1
    for p in personas_out:
        bump(dist["by_age_bin"], age_bin(p["age"]))
        bump(dist["by_sex"], p["sex"])
        bump(dist["by_education_class"], p["education_class"])
        bump(dist["by_education_level"], p["education_level"])
        bump(dist["by_occupation"], p["occupation"])
        bump(dist["by_occ_kind"], p["occ_kind"])
        bump(dist["by_district"], p["district"])

    con2 = duckdb.connect(str(DB), read_only=True)
    consensus_rows = con2.execute(
        """SELECT candidate_id, p_hat, variance, n_polls, source_poll_ids
           FROM poll_consensus_daily
           WHERE region_id = ? AND as_of_date = DATE '2026-04-26'
           ORDER BY p_hat DESC""", [REGION]
    ).fetchall()
    con2.close()
    consensus_pretty = [{"candidate_id": r[0], "p_hat": r[1], "variance": r[2],
                         "n_polls": r[3], "source_poll_ids": r[4]} for r in consensus_rows]
    if consensus_rows:
        s = sum(r[1] for r in consensus_rows)
        renorm = [{"candidate_id": r[0], "p_hat_renorm": r[1] / s} for r in consensus_rows]
    else:
        renorm = []

    OUT_PERSONAS.parent.mkdir(parents=True, exist_ok=True)
    OUT_PERSONAS.write_text(json.dumps({
        "_doc": "Hill-climbing target — 10 stratified busan_buk_gap personas (R3). Same spec as Seoul, district axis N/A (single 시군구).",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
        "region_id": REGION,
        "n": len(personas_out),
        "stratification_axes": [
            "age_bin(20s/30s/40s/50s/60+ × 2)",
            "sex(5M/5F)",
            "education_class(5 bachelor+/5 sub_bachelor)",
            "occupation(white_collar/blue_collar/self_employed/student_equiv/homemaker_equiv)",
            "district N/A (single 부산-북구 in personas table)",
        ],
        "ground_truth": {
            "source": "DuckDB.poll_consensus_daily as_of=2026-04-26 region_id=busan_buk_gap",
            "method_version": "weighted_v1",
            "consensus_raw": consensus_pretty,
            "consensus_renorm_intersection": renorm,
        },
        "personas": personas_out,
    }, ensure_ascii=False, indent=2))

    OUT_DIST.parent.mkdir(parents=True, exist_ok=True)
    OUT_DIST.write_text(json.dumps({
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
        "source_file": str(OUT_PERSONAS.relative_to(ROOT)),
        "distribution": dist,
        "ground_truth_consensus": consensus_pretty,
        "ground_truth_renorm": renorm,
    }, ensure_ascii=False, indent=2))

    print(f"\nWROTE {OUT_PERSONAS}", file=sys.stderr)
    print(f"WROTE {OUT_DIST}", file=sys.stderr)
    print(f"\nDistribution sanity:", file=sys.stderr)
    print(json.dumps(dist["balance_checks"], ensure_ascii=False, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
