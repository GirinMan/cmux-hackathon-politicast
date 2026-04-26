# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb", "pyarrow", "pandas"]
# ///
"""
schema_probe.py — Nemotron-Personas-Korea 스키마/카디널리티/카테고리 enum 조사 (shard 1개).

샘플 대상: data/train-00000-of-00009.parquet
실제 측정 결과는 schema_probe_output.json 로 보존.

실행: `uv run scripts/schema_probe.py`
(PEP 723 inline metadata로 의존성 자동 해결.)
"""
from __future__ import annotations
import duckdb
import json
import sys
from pathlib import Path

PARQUET = "/Users/girinman/datasets/Nemotron-Personas-Korea/data/train-00000-of-00009.parquet"
OUT_DIR = Path("/Users/girinman/repos/cmux-hackathon-politicast/_workspace/research/nemotron-personas-korea/scripts")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    con = duckdb.connect()
    con.execute(f"CREATE VIEW p AS SELECT * FROM read_parquet('{PARQUET}')")

    summary: dict = {}

    # 1) Schema (DESCRIBE)
    desc = con.execute("DESCRIBE p").fetchall()
    summary["schema"] = [
        {"column_name": r[0], "column_type": r[1], "null": r[2]} for r in desc
    ]

    # 2) row count
    row_count = con.execute("SELECT COUNT(*) FROM p").fetchone()[0]
    summary["row_count_shard0"] = row_count

    # 3) per-column null/cardinality (전수)
    cols = [r[0] for r in desc]
    col_stats = []
    for c in cols:
        q = f"""
            SELECT
                COUNT(*) - COUNT("{c}") AS n_null,
                COUNT(DISTINCT "{c}") AS n_distinct,
                MIN(LENGTH(CAST("{c}" AS VARCHAR))) AS min_len,
                AVG(LENGTH(CAST("{c}" AS VARCHAR))) AS avg_len,
                MAX(LENGTH(CAST("{c}" AS VARCHAR))) AS max_len
            FROM p
        """
        n_null, n_distinct, min_len, avg_len, max_len = con.execute(q).fetchone()
        col_stats.append({
            "column": c,
            "n_null": n_null,
            "n_distinct": n_distinct,
            "null_pct": round(n_null / row_count * 100, 4),
            "min_len": min_len,
            "avg_len": round(avg_len or 0, 2),
            "max_len": max_len,
        })
    summary["col_stats"] = col_stats

    # 4) categorical fields enum 전수 (cardinality < 100 가정)
    CATEGORICAL = [
        "sex", "marital_status", "military_status",
        "family_type", "housing_type", "education_level",
        "bachelors_field", "country", "province"
    ]
    enums = {}
    for c in CATEGORICAL:
        rows = con.execute(
            f'SELECT "{c}", COUNT(*) AS n FROM p GROUP BY 1 ORDER BY n DESC'
        ).fetchall()
        enums[c] = [{"value": v, "count": n} for v, n in rows]
    summary["enum_categorical"] = enums

    # 5) high-cardinality 표본 (district / occupation)
    for c in ["district", "occupation"]:
        rows = con.execute(
            f'SELECT "{c}", COUNT(*) AS n FROM p GROUP BY 1 ORDER BY n DESC LIMIT 30'
        ).fetchall()
        n_distinct = con.execute(f'SELECT COUNT(DISTINCT "{c}") FROM p').fetchone()[0]
        summary.setdefault("top30", {})[c] = {
            "n_distinct": n_distinct,
            "top30": [{"value": v, "count": n} for v, n in rows],
        }

    # 6) age 분포
    age_stats = con.execute(
        "SELECT MIN(age), MAX(age), AVG(age), MEDIAN(age) FROM p"
    ).fetchone()
    summary["age_stats"] = {
        "min": age_stats[0], "max": age_stats[1],
        "avg": round(age_stats[2], 2), "median": age_stats[3]
    }
    age_buckets = con.execute(
        """SELECT
            CASE
              WHEN age BETWEEN 19 AND 29 THEN '19-29'
              WHEN age BETWEEN 30 AND 39 THEN '30-39'
              WHEN age BETWEEN 40 AND 49 THEN '40-49'
              WHEN age BETWEEN 50 AND 59 THEN '50-59'
              WHEN age BETWEEN 60 AND 69 THEN '60-69'
              WHEN age BETWEEN 70 AND 79 THEN '70-79'
              WHEN age BETWEEN 80 AND 89 THEN '80-89'
              WHEN age >= 90 THEN '90+'
              ELSE 'other'
            END AS bucket,
            COUNT(*) AS n
        FROM p GROUP BY 1 ORDER BY 1"""
    ).fetchall()
    summary["age_buckets"] = [{"bucket": b, "count": n} for b, n in age_buckets]

    # 7) persona 텍스트 길이 통계 (7종 + persona attribute fields)
    PERSONA_TEXT_FIELDS = [
        "professional_persona", "sports_persona", "arts_persona",
        "travel_persona", "culinary_persona", "family_persona", "persona",
        "cultural_background", "skills_and_expertise",
        "skills_and_expertise_list", "hobbies_and_interests",
        "hobbies_and_interests_list", "career_goals_and_ambitions",
    ]
    text_stats = []
    for c in PERSONA_TEXT_FIELDS:
        row = con.execute(
            f"""SELECT
                AVG(LENGTH("{c}")) AS avg_chars,
                MIN(LENGTH("{c}")) AS min_chars,
                APPROX_QUANTILE(LENGTH("{c}"), 0.5) AS p50,
                APPROX_QUANTILE(LENGTH("{c}"), 0.9) AS p90,
                MAX(LENGTH("{c}")) AS max_chars
            FROM p"""
        ).fetchone()
        text_stats.append({
            "column": c,
            "avg_chars": round(row[0] or 0, 1),
            "min_chars": row[1],
            "p50_chars": row[2],
            "p90_chars": row[3],
            "max_chars": row[4],
        })
    summary["text_stats"] = text_stats

    # 8) sample 2 records (uuid 명시)
    sample = con.execute(
        f"""SELECT uuid, age, sex, province, district, occupation,
               professional_persona, sports_persona, arts_persona,
               travel_persona, culinary_persona, family_persona, persona,
               cultural_background, skills_and_expertise,
               hobbies_and_interests, career_goals_and_ambitions
        FROM p LIMIT 2"""
    ).fetchall()
    cols2 = [d[0] for d in con.description]
    summary["sample_records"] = [dict(zip(cols2, r)) for r in sample]

    out = OUT_DIR / "schema_probe_output.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"WROTE {out}")


if __name__ == "__main__":
    main()
