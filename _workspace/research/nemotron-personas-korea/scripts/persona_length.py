#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["duckdb", "pandas", "matplotlib", "numpy", "pyarrow"]
# ///
"""
Task #15: 페르소나 텍스트 7종 (professional/sports/arts/travel/culinary/family/persona)
   + cultural_background + career_goals_and_ambitions
의 길이(문자 수) 분포 + 결측(빈 문자열 / NULL) 통계.

실행: `uv run scripts/persona_length.py` (PEP 723 inline metadata 사용).

DuckDB SQL로 전수 길이 통계 + 결측 카운트 산출.

산출:
- eda_charts/persona_length.png  (boxplot of 7 persona fields, char count)
- eda_charts/_data/persona_length_summary.csv  (per-field describe)
- eda_charts/_data/persona_length_missing.csv  (NULL + empty count per field)
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _font import setup_korean_font  # noqa: E402

setup_korean_font()

DATA_GLOB = "/Users/girinman/datasets/Nemotron-Personas-Korea/data/train-*.parquet"
ROOT = Path(__file__).resolve().parent.parent
CHART_DIR = ROOT / "eda_charts"
DATA_DIR = CHART_DIR / "_data"

con = duckdb.connect()
con.execute("PRAGMA threads=4")
con.execute("PRAGMA memory_limit='8GB'")

FIELDS = [
    "professional_persona",
    "sports_persona",
    "arts_persona",
    "travel_persona",
    "culinary_persona",
    "family_persona",
    "persona",
    "cultural_background",
    "career_goals_and_ambitions",
]

# 1) Length describe per field
print("== length per field (DuckDB) ==")
sel = ", ".join([f"LENGTH({f}) AS len_{f}" for f in FIELDS])
empty_sel = ", ".join([
    f"SUM(CASE WHEN {f} IS NULL THEN 1 ELSE 0 END) AS null_{f}, "
    f"SUM(CASE WHEN {f} IS NOT NULL AND LENGTH(TRIM({f})) = 0 THEN 1 ELSE 0 END) AS empty_{f}"
    for f in FIELDS
])
miss_df = con.execute(f"SELECT {empty_sel} FROM read_parquet('{DATA_GLOB}')").fetchdf().iloc[0]
miss_rows = []
n_total = con.execute(f"SELECT COUNT(*) FROM read_parquet('{DATA_GLOB}')").fetchone()[0]
for f in FIELDS:
    miss_rows.append({
        "field": f,
        "null_count": int(miss_df[f"null_{f}"]),
        "empty_count": int(miss_df[f"empty_{f}"]),
        "missing_total": int(miss_df[f"null_{f}"] + miss_df[f"empty_{f}"]),
        "missing_ratio": float((miss_df[f"null_{f}"] + miss_df[f"empty_{f}"]) / n_total),
    })
miss_out = pd.DataFrame(miss_rows)
miss_out.to_csv(DATA_DIR / "persona_length_missing.csv", index=False)
print(miss_out.to_string(index=False))

# Length stats per field via DuckDB approx_quantile (avoid loading 1M*9 strings)
stat_rows = []
for f in FIELDS:
    row = con.execute(
        f"""
        SELECT
          MIN(LENGTH({f})) AS min_len,
          MAX(LENGTH({f})) AS max_len,
          AVG(LENGTH({f}))::DOUBLE AS mean_len,
          STDDEV(LENGTH({f}))::DOUBLE AS std_len,
          QUANTILE_CONT(LENGTH({f}), 0.05)::DOUBLE AS p05,
          QUANTILE_CONT(LENGTH({f}), 0.25)::DOUBLE AS p25,
          QUANTILE_CONT(LENGTH({f}), 0.50)::DOUBLE AS p50,
          QUANTILE_CONT(LENGTH({f}), 0.75)::DOUBLE AS p75,
          QUANTILE_CONT(LENGTH({f}), 0.95)::DOUBLE AS p95
        FROM read_parquet('{DATA_GLOB}')
        WHERE {f} IS NOT NULL
        """
    ).fetchone()
    stat_rows.append(dict(field=f, min=row[0], max=row[1], mean=row[2], std=row[3],
                          p05=row[4], p25=row[5], p50=row[6], p75=row[7], p95=row[8]))
stats_df = pd.DataFrame(stat_rows)
stats_df.to_csv(DATA_DIR / "persona_length_summary.csv", index=False)
print("\n== length summary ==")
print(stats_df.to_string(index=False))

# 2) Boxplot from a sample (1% = 10k rows) — boxplot data only, full describe above
print("\n== sampling 10k for boxplot ==")
sample = con.execute(
    f"""
    SELECT {sel}
    FROM read_parquet('{DATA_GLOB}')
    USING SAMPLE 10000 ROWS (RESERVOIR, 42)
    """
).fetchdf()

fig, ax = plt.subplots(figsize=(13, 8))
data = [sample[f"len_{f}"].dropna().values for f in FIELDS]
labels = [f.replace("_persona", "_p.").replace("_and_ambitions", "") for f in FIELDS]
bp = ax.boxplot(data, labels=labels, showfliers=False, patch_artist=True)
for patch, color in zip(bp["boxes"], plt.cm.tab10.colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.6)
ax.set_title("Persona text length (chars) — 10k reservoir sample, full stats in CSV")
ax.set_ylabel("character length")
ax.grid(axis="y", alpha=0.3)
ax.tick_params(axis="x", rotation=20)
fig.tight_layout()
fig.savefig(CHART_DIR / "persona_length.png", dpi=110)
plt.close(fig)
print("  saved: persona_length.png")

print("\nDONE: persona_length.py")
