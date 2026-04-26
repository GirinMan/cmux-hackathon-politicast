"""Build a deterministic 10-persona stratified sample for hill-climbing target.

Spec from team-lead 14:55 KST:
- 10 personas from personas_seoul_mayor
- Age: 20s/30s/40s/50s/60+ × 2 each = 10
- Sex: 5 male / 5 female (one per age bin)
- Education: 5 학사+ (4년제 대학교 or 대학원) / 5 학사 미만
- Occupation: 화이트칼라 + 블루칼라 + 자영업 + 학생-equivalent + 무직/주부 골고루
- District: 10 distinct 자치구 across Seoul

Determinism: ORDER BY uuid LIMIT 1 per slot, with explicit slot constraints.
If a slot's tight predicate has no match we fall back by progressively dropping
district → occupation; we never fall back across age × sex × education buckets.

Outputs:
  _workspace/data/scenarios/hill_climbing_target_seoul_n10.json
  _workspace/snapshots/hill_climbing_target_seoul_n10_distribution.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "_workspace/db/politikast.duckdb"
OUT_PERSONAS = ROOT / "_workspace/data/scenarios/hill_climbing_target_seoul_n10.json"
OUT_DIST = ROOT / "_workspace/snapshots/hill_climbing_target_seoul_n10_distribution.json"

EDU_BACHELOR_PLUS = ("4년제 대학교", "대학원")
EDU_SUB_BACHELOR = ("2~3년제 전문대학", "고등학교", "중학교", "초등학교", "무학")

# Slot spec: explicit WHERE-fragment + intent label
SLOTS = [
    # 20s — student-age cohort
    {
        "slot_id": "20s_male_bachelor_marketing",
        "age_lo": 20, "age_hi": 29, "sex": "남자",
        "edu_in": EDU_BACHELOR_PLUS,
        "occupations": ["마케팅 전문가", "조사 전문가", "사무 보조원"],
        "districts": ["서울-관악구", "서울-동작구", "서울-마포구"],
        "occ_kind": "white_collar_entry",
    },
    {
        "slot_id": "20s_female_subbach_unemployed",
        "age_lo": 20, "age_hi": 29, "sex": "여자",
        "edu_in": EDU_SUB_BACHELOR,
        "occupations": ["무직"],
        "districts": ["서울-노원구", "서울-도봉구", "서울-중랑구"],
        "occ_kind": "unemployed_student_equiv",
    },
    # 30s
    {
        "slot_id": "30s_male_bachelor_office",
        "age_lo": 30, "age_hi": 39, "sex": "남자",
        "edu_in": EDU_BACHELOR_PLUS,
        "occupations": ["경영 기획 사무원", "경리 사무원", "교육 및 훈련 사무원", "사무 보조원"],
        "districts": ["서울-마포구", "서울-영등포구", "서울-성동구"],
        "occ_kind": "white_collar_office",
    },
    {
        "slot_id": "30s_female_grad_specialist",
        "age_lo": 30, "age_hi": 39, "sex": "여자",
        "edu_in": ("대학원", "4년제 대학교"),
        "occupations": ["경영 컨설턴트", "조사 전문가", "마케팅 전문가"],
        "districts": ["서울-강남구", "서울-서초구", "서울-송파구"],
        "occ_kind": "white_collar_specialist",
    },
    # 40s
    {
        "slot_id": "40s_male_subbach_blue_collar",
        "age_lo": 40, "age_hi": 49, "sex": "남자",
        "edu_in": EDU_SUB_BACHELOR,
        "occupations": [
            "건물 경비원", "시설 경비원",
            "하역 및 적재 관련 단순 종사원", "한식 조리사",
            "철도운송 관련 종사원",
        ],
        "districts": ["서울-영등포구", "서울-구로구", "서울-금천구"],
        "occ_kind": "blue_collar",
    },
    {
        "slot_id": "40s_female_bachelor_office",
        "age_lo": 40, "age_hi": 49, "sex": "여자",
        "edu_in": EDU_BACHELOR_PLUS,
        "occupations": ["회계 사무원", "교육 및 훈련 사무원", "마케팅 전문가", "보육교사"],
        "districts": ["서울-송파구", "서울-강서구", "서울-양천구"],
        "occ_kind": "white_collar_office",
    },
    # 50s
    {
        "slot_id": "50s_male_subbach_self_employed",
        "age_lo": 50, "age_hi": 59, "sex": "남자",
        "edu_in": EDU_SUB_BACHELOR,
        "occupations": ["소규모 상점 경영자", "소규모 상점 일선 관리 종사원"],
        "districts": ["서울-강북구", "서울-성북구", "서울-동대문구"],
        "occ_kind": "self_employed",
    },
    {
        "slot_id": "50s_female_bachelor_finance",
        "age_lo": 50, "age_hi": 59, "sex": "여자",
        "edu_in": EDU_BACHELOR_PLUS,
        "occupations": ["회계 사무원", "경리 사무원", "기업 고위 임원"],
        "districts": ["서울-서초구", "서울-용산구", "서울-광진구"],
        "occ_kind": "white_collar_office",
    },
    # 60+
    {
        "slot_id": "60p_male_subbach_security",
        "age_lo": 60, "age_hi": 99, "sex": "남자",
        "edu_in": EDU_SUB_BACHELOR,
        "occupations": ["건물 경비원", "시설 경비원", "건물 청소원", "무직"],
        "districts": ["서울-종로구", "서울-중구", "서울-서대문구"],
        "occ_kind": "blue_collar_or_unemployed",
    },
    {
        "slot_id": "60p_female_subbach_homemaker",
        "age_lo": 60, "age_hi": 99, "sex": "여자",
        "edu_in": EDU_SUB_BACHELOR,
        "occupations": ["무직"],
        "districts": ["서울-중랑구", "서울-은평구", "서울-강동구"],
        "occ_kind": "homemaker_equiv",
    },
]


def pick_slot(con: duckdb.DuckDBPyConnection, slot: dict, used_uuids: set[str], used_districts: set[str]) -> dict | None:
    """Try predicates in decreasing tightness; return first persona row not yet used."""
    base_filter = (
        "age BETWEEN ? AND ? AND sex = ? AND education_level = ANY(?)"
    )
    base_params = [slot["age_lo"], slot["age_hi"], slot["sex"], list(slot["edu_in"])]

    # Tier 1: exact slot (occupation IN, district IN, prefer unused district)
    tier_1_districts = [d for d in slot["districts"] if d not in used_districts] or slot["districts"]
    candidates = [
        ("tier1_unused_district",
         f"{base_filter} AND occupation = ANY(?) AND district = ANY(?)",
         base_params + [list(slot["occupations"]), tier_1_districts]),
        ("tier2_any_listed_district",
         f"{base_filter} AND occupation = ANY(?) AND district = ANY(?)",
         base_params + [list(slot["occupations"]), slot["districts"]]),
        ("tier3_drop_district",
         f"{base_filter} AND occupation = ANY(?)",
         base_params + [list(slot["occupations"])]),
        ("tier4_drop_occupation_keep_district",
         f"{base_filter} AND district = ANY(?)",
         base_params + [slot["districts"]]),
        ("tier5_only_age_sex_edu",
         base_filter,
         base_params),
    ]

    for tier_label, where, params in candidates:
        # Pull a small window to skip used uuids deterministically
        sql = (
            f"SELECT * FROM personas_seoul_mayor WHERE {where} "
            f"ORDER BY uuid LIMIT 32"
        )
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
    used_districts: set[str] = set()
    picks: list[dict] = []

    for slot in SLOTS:
        p = pick_slot(con, slot, used_uuids, used_districts)
        if not p:
            print(f"FAIL: no candidate for {slot['slot_id']}", file=sys.stderr)
            continue
        used_uuids.add(p["uuid"])
        used_districts.add(p["district"])
        picks.append({"slot": slot["slot_id"], "occ_kind": slot["occ_kind"], "persona": p})
        print(f"  {slot['slot_id']:<40}  {p['_picked_tier']:<32}  uuid={p['uuid'][:8]}  age={p['age']}  sex={p['sex']}  edu={p['education_level']}  occ={p['occupation']}  district={p['district']}", file=sys.stderr)

    if len(picks) != 10:
        print(f"WARN: only {len(picks)}/10 slots filled", file=sys.stderr)

    # Build persona dicts (only fields needed by sim — keep all string fields)
    personas_out = []
    for entry in picks:
        p = entry["persona"]
        personas_out.append({
            "uuid": p["uuid"],
            "region_id": "seoul_mayor",
            "slot_id": entry["slot"],
            "occ_kind": entry["occ_kind"],
            "_picked_tier": p.get("_picked_tier"),
            # Demographics
            "age": p["age"],
            "sex": p["sex"],
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
            # Persona text fields (4 required by sim)
            "persona": p.get("persona"),
            "cultural_background": p.get("cultural_background"),
            "skills_and_expertise": p.get("skills_and_expertise"),
            "skills_and_expertise_list": p.get("skills_and_expertise_list"),
            "hobbies_and_interests": p.get("hobbies_and_interests"),
            "hobbies_and_interests_list": p.get("hobbies_and_interests_list"),
            "career_goals_and_ambitions": p.get("career_goals_and_ambitions"),
        })

    # Distribution stats
    dist = {
        "n": len(personas_out),
        "by_age_bin": {},
        "by_sex": {},
        "by_education_class": {},
        "by_education_level": {},
        "by_occupation": {},
        "by_occ_kind": {},
        "by_district": {},
        "axes_coverage": {
            "age_bins": sorted({age_bin(p["age"]) for p in personas_out}),
            "sex": sorted({p["sex"] for p in personas_out}),
            "education_classes": sorted({p["education_class"] for p in personas_out}),
            "districts_unique": sorted({p["district"] for p in personas_out}),
            "occ_kinds": sorted({p["occ_kind"] for p in personas_out}),
        },
        "balance_checks": {
            "sex_balance_5_5": (sum(1 for p in personas_out if p["sex"] == "남자"), sum(1 for p in personas_out if p["sex"] == "여자")),
            "edu_balance_5_5": (sum(1 for p in personas_out if p["education_class"] == "bachelor_plus"),
                                sum(1 for p in personas_out if p["education_class"] == "sub_bachelor")),
            "age_bin_counts": {b: sum(1 for p in personas_out if age_bin(p["age"]) == b)
                               for b in ("20s","30s","40s","50s","60p")},
            "district_unique_count": len({p["district"] for p in personas_out}),
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

    # Validation target consensus from data-engineer V3
    con2 = duckdb.connect(str(DB), read_only=True)
    consensus_rows = con2.execute(
        """SELECT candidate_id, p_hat, variance, n_polls, source_poll_ids
           FROM poll_consensus_daily
           WHERE region_id = 'seoul_mayor' AND as_of_date = DATE '2026-04-26'
           ORDER BY p_hat DESC"""
    ).fetchall()
    con2.close()
    consensus_pretty = [{"candidate_id": r[0], "p_hat": r[1], "variance": r[2],
                         "n_polls": r[3], "source_poll_ids": r[4]} for r in consensus_rows]

    # Renormalized to intersection (sim-engineer V6 path):
    if consensus_rows:
        s = sum(r[1] for r in consensus_rows)
        renorm = [{"candidate_id": r[0], "p_hat_renorm": r[1] / s} for r in consensus_rows]
    else:
        renorm = []

    OUT_PERSONAS.parent.mkdir(parents=True, exist_ok=True)
    OUT_PERSONAS.write_text(json.dumps({
        "_doc": "Hill-climbing target — 10 stratified Seoul personas. team-lead spec 14:55 KST. Deterministic ORDER BY uuid pick.",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
        "region_id": "seoul_mayor",
        "n": len(personas_out),
        "stratification_axes": [
            "age_bin(20s/30s/40s/50s/60+ × 2)",
            "sex(5M/5F)",
            "education_class(5 bachelor+/5 sub_bachelor)",
            "occupation(white_collar/blue_collar/self_employed/student_equiv/homemaker_equiv)",
            "district(10 distinct 자치구)",
        ],
        "ground_truth": {
            "source": "DuckDB.poll_consensus_daily as_of=2026-04-26 region_id=seoul_mayor",
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
