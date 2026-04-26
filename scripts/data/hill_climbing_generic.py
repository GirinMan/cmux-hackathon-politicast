"""Generic hill-climbing target n=10 builder.

Same axes spec as Seoul/Busan (sim-engineer 15:08 ack):
- 5 age bins × 2 sex (5M / 5F)
- 5 학사+ / 5 학사 미만
- occupation diversity (white_collar/blue_collar/self_employed/student-equiv/homemaker-equiv)
- district preference (multi-district regions only) — single-district regions get axis N/A

Usage:
  python -m scripts.data.hill_climbing_generic <region_id>

Supported region_id: daegu_mayor, gwangju_mayor, daegu_dalseo_gap

ground_truth:
- If region has poll_consensus_daily rows for as_of_date 2026-04-26, the JSON
  contains consensus_raw + consensus_renorm_intersection.
- Otherwise the JSON contains a "missing" stub with reason.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "_workspace/db/politikast.duckdb"

EDU_BACHELOR_PLUS = ("4년제 대학교", "대학원")
EDU_SUB_BACHELOR = ("2~3년제 전문대학", "고등학교", "중학교", "초등학교", "무학")

REGION_CONFIG = {
    "daegu_mayor": {
        "table": "personas_daegu_mayor",
        "districts_preferred": [
            "대구-수성구", "대구-북구", "대구-달성군", "대구-동구",
            "대구-남구", "대구-서구", "대구-중구", "대구-달서구", "대구-군위군",
        ],
        "single_district": False,
        "ground_truth_missing_reason": None,  # will be filled at runtime if missing
    },
    "gwangju_mayor": {
        "table": "personas_gwangju_mayor",
        "districts_preferred": [
            "광주-북구", "광주-광산구", "광주-서구", "광주-남구", "광주-동구",
        ],
        "single_district": False,
        "ground_truth_missing_reason": (
            "현장 후보 reshuffle 이후 NESDC 등록 폴(2026-04 기준 25건)의 후보 set이 "
            "scenario gwangju_mayor.json (강기정/민형배/주기환/안철수)와 일치하지 않음 "
            "(2026-01 이후 광주·전남 통합단체장 후보 김영록 등 신규 인물 등장). "
            "raw_poll_result 미박제 → poll_consensus_daily 0 rows."
        ),
    },
    "daegu_dalseo_gap": {
        "table": "personas_daegu_dalseo_gap",
        "districts_preferred": ["대구-달서구"],
        "single_district": True,
        "ground_truth_missing_reason": (
            "VT039(2026년 재·보궐선거) NESDC 등록 폴 12건 전수 스캔 결과 "
            "대구 달서구갑 선거구 폴 0건. ground truth 없음 — paper Limitations에 "
            "'NESDC 등록 부재 region — validation gate available=false' 박제 권고."
        ),
    },
}

SLOT_TEMPLATE = [
    {
        "slot_id": "20s_male_bachelor_marketing",
        "age_lo": 20, "age_hi": 29, "sex": "남자", "edu_in": EDU_BACHELOR_PLUS,
        "occupations": ["마케팅 전문가", "사무 보조원", "경영 기획 사무원", "조사 전문가"],
        "occ_kind": "white_collar_entry",
    },
    {
        "slot_id": "20s_female_subbach_unemployed",
        "age_lo": 20, "age_hi": 29, "sex": "여자", "edu_in": EDU_SUB_BACHELOR,
        "occupations": ["무직"],
        "occ_kind": "unemployed_student_equiv",
    },
    {
        "slot_id": "30s_male_bachelor_office",
        "age_lo": 30, "age_hi": 39, "sex": "남자", "edu_in": EDU_BACHELOR_PLUS,
        "occupations": ["경영 기획 사무원", "사무 보조원", "경리 사무원",
                        "교육 및 훈련 사무원", "마케팅 전문가"],
        "occ_kind": "white_collar_office",
    },
    {
        "slot_id": "30s_female_bachelor_specialist",
        "age_lo": 30, "age_hi": 39, "sex": "여자", "edu_in": EDU_BACHELOR_PLUS,
        "occupations": ["마케팅 전문가", "보육교사", "산업 안전원",
                        "조사 전문가", "교육 및 훈련 사무원"],
        "occ_kind": "white_collar_specialist",
    },
    {
        "slot_id": "40s_male_subbach_blue_collar",
        "age_lo": 40, "age_hi": 49, "sex": "남자", "edu_in": EDU_SUB_BACHELOR,
        "occupations": [
            "건물 경비원", "시설 경비원", "한식 조리사",
            "하역 및 적재 관련 단순 종사원", "철도운송 관련 종사원",
            "지게차 운전원", "경·소형 화물차 운전원", "승용차 및 승합차 운전원",
        ],
        "occ_kind": "blue_collar",
    },
    {
        "slot_id": "40s_female_bachelor_office",
        "age_lo": 40, "age_hi": 49, "sex": "여자", "edu_in": EDU_BACHELOR_PLUS,
        "occupations": ["회계 사무원", "경리 사무원", "마케팅 전문가",
                        "보육교사", "교육 및 훈련 사무원"],
        "occ_kind": "white_collar_office",
    },
    {
        "slot_id": "50s_male_subbach_self_employed",
        "age_lo": 50, "age_hi": 59, "sex": "남자", "edu_in": EDU_SUB_BACHELOR,
        "occupations": ["소규모 상점 경영자", "그 외 일반 영업원",
                        "소규모 상점 일선 관리 종사원"],
        "occ_kind": "self_employed",
    },
    {
        "slot_id": "50s_female_bachelor_finance",
        "age_lo": 50, "age_hi": 59, "sex": "여자", "edu_in": EDU_BACHELOR_PLUS,
        "occupations": ["회계 사무원", "경리 사무원", "일반 비서", "기업 고위 임원"],
        "occ_kind": "white_collar_office",
    },
    {
        "slot_id": "60p_male_subbach_security",
        "age_lo": 60, "age_hi": 99, "sex": "남자", "edu_in": EDU_SUB_BACHELOR,
        "occupations": ["건물 경비원", "시설 경비원", "건물 청소원", "무직"],
        "occ_kind": "blue_collar_or_unemployed",
    },
    {
        "slot_id": "60p_female_subbach_homemaker",
        "age_lo": 60, "age_hi": 99, "sex": "여자", "edu_in": EDU_SUB_BACHELOR,
        "occupations": ["무직"],
        "occ_kind": "homemaker_equiv",
    },
]


def pick_slot(con, table, slot, used_uuids, used_districts, single_district, district_pool):
    base_filter = "age BETWEEN ? AND ? AND sex = ? AND education_level = ANY(?)"
    base_params = [slot["age_lo"], slot["age_hi"], slot["sex"], list(slot["edu_in"])]

    if single_district:
        # No district fan-out; only occupation tiers
        candidates = [
            ("tier1_occ_in_list",
             f"{base_filter} AND occupation = ANY(?)",
             base_params + [list(slot["occupations"])]),
            ("tier2_drop_occupation",
             base_filter,
             base_params),
        ]
    else:
        unused_districts = [d for d in district_pool if d not in used_districts] or district_pool
        candidates = [
            ("tier1_unused_district",
             f"{base_filter} AND occupation = ANY(?) AND district = ANY(?)",
             base_params + [list(slot["occupations"]), unused_districts]),
            ("tier2_any_district_in_pool",
             f"{base_filter} AND occupation = ANY(?) AND district = ANY(?)",
             base_params + [list(slot["occupations"]), district_pool]),
            ("tier3_drop_district",
             f"{base_filter} AND occupation = ANY(?)",
             base_params + [list(slot["occupations"])]),
            ("tier4_drop_occupation_keep_district",
             f"{base_filter} AND district = ANY(?)",
             base_params + [district_pool]),
            ("tier5_only_age_sex_edu",
             base_filter,
             base_params),
        ]

    for tier_label, where, params in candidates:
        sql = f"SELECT * FROM {table} WHERE {where} ORDER BY uuid LIMIT 32"
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


def edu_class(edu):
    return "bachelor_plus" if edu in EDU_BACHELOR_PLUS else "sub_bachelor"


def age_bin(age):
    if age < 30: return "20s"
    if age < 40: return "30s"
    if age < 50: return "40s"
    if age < 60: return "50s"
    return "60p"


def build_ground_truth(con, region_id, missing_reason):
    rows = con.execute(
        """SELECT candidate_id, p_hat, variance, n_polls, source_poll_ids
           FROM poll_consensus_daily
           WHERE region_id = ? AND as_of_date = DATE '2026-04-26'
           ORDER BY p_hat DESC""", [region_id]
    ).fetchall()
    if not rows:
        return {
            "available": False,
            "source": f"DuckDB.poll_consensus_daily as_of=2026-04-26 region_id={region_id}",
            "method_version": "weighted_v1",
            "consensus_raw": [],
            "consensus_renorm_intersection": [],
            "missing_reason": missing_reason or "ground truth not available",
        }
    raw = [{"candidate_id": r[0], "p_hat": r[1], "variance": r[2],
            "n_polls": r[3], "source_poll_ids": r[4]} for r in rows]
    s = sum(r["p_hat"] for r in raw)
    renorm = [{"candidate_id": r["candidate_id"], "p_hat_renorm": r["p_hat"] / s} for r in raw]
    return {
        "available": True,
        "source": f"DuckDB.poll_consensus_daily as_of=2026-04-26 region_id={region_id}",
        "method_version": "weighted_v1",
        "consensus_raw": raw,
        "consensus_renorm_intersection": renorm,
    }


def main(region_id):
    cfg = REGION_CONFIG[region_id]
    con = duckdb.connect(str(DB), read_only=True)

    out_personas = ROOT / f"_workspace/data/scenarios/hill_climbing_target_{region_id}_n10.json"
    out_dist = ROOT / f"_workspace/snapshots/hill_climbing_target_{region_id}_n10_distribution.json"

    used_uuids: set[str] = set()
    used_districts: set[str] = set()
    picks: list[dict] = []

    print(f"\n[REGION {region_id}] table={cfg['table']} single_district={cfg['single_district']}", file=sys.stderr)

    for slot in SLOT_TEMPLATE:
        p = pick_slot(con, cfg["table"], slot, used_uuids, used_districts,
                      cfg["single_district"], cfg["districts_preferred"])
        if not p:
            print(f"  FAIL: no candidate for {slot['slot_id']}", file=sys.stderr)
            continue
        used_uuids.add(p["uuid"])
        used_districts.add(p["district"])
        picks.append({"slot": slot["slot_id"], "occ_kind": slot["occ_kind"], "persona": p})
        print(f"  {slot['slot_id']:<40}  {p['_picked_tier']:<32}  uuid={p['uuid'][:8]}  age={p['age']}  sex={p['sex']}  edu={p['education_level']}  occ={p['occupation']}  district={p['district']}", file=sys.stderr)

    personas_out = []
    for entry in picks:
        p = entry["persona"]
        personas_out.append({
            "uuid": p["uuid"], "region_id": region_id,
            "slot_id": entry["slot"], "occ_kind": entry["occ_kind"],
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
            "district_note": "single 시군구 (axis N/A)" if cfg["single_district"]
                             else f"multi-district pool ({len(cfg['districts_preferred'])})",
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

    gt = build_ground_truth(con, region_id, cfg.get("ground_truth_missing_reason"))

    out_personas.parent.mkdir(parents=True, exist_ok=True)
    out_personas.write_text(json.dumps({
        "_doc": f"Hill-climbing target — 10 stratified personas for {region_id}. team-lead 15:20 spec.",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
        "region_id": region_id,
        "n": len(personas_out),
        "stratification_axes": [
            "age_bin(20s/30s/40s/50s/60+ × 2)",
            "sex(5M/5F)",
            "education_class(5 bachelor+/5 sub_bachelor)",
            "occupation(white_collar/blue_collar/self_employed/student_equiv/homemaker_equiv)",
            ("district N/A (single 시군구)" if cfg["single_district"]
             else f"district({len(cfg['districts_preferred'])} 자치구 pool)"),
        ],
        "ground_truth": gt,
        "personas": personas_out,
    }, ensure_ascii=False, indent=2))

    out_dist.parent.mkdir(parents=True, exist_ok=True)
    out_dist.write_text(json.dumps({
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
        "source_file": str(out_personas.relative_to(ROOT)),
        "distribution": dist,
        "ground_truth": gt,
    }, ensure_ascii=False, indent=2))

    print(f"\n  WROTE {out_personas}", file=sys.stderr)
    print(f"  WROTE {out_dist}", file=sys.stderr)
    print(f"  Balance: {json.dumps(dist['balance_checks'], ensure_ascii=False)}", file=sys.stderr)
    print(f"  Ground truth available: {gt['available']}", file=sys.stderr)
    if gt["available"]:
        for r in gt["consensus_renorm_intersection"]:
            print(f"    - {r['candidate_id']:<22} renorm={r['p_hat_renorm']:.4f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    region_ids = sys.argv[1:] if len(sys.argv) > 1 else list(REGION_CONFIG.keys())
    for rid in region_ids:
        if rid not in REGION_CONFIG:
            print(f"unknown region: {rid}", file=sys.stderr)
            sys.exit(2)
        main(rid)
