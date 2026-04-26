#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["duckdb", "pandas", "matplotlib", "pyarrow"]
# ///
"""
Task #12: age / sex / marital_status / education_level 분포 차트.

실행: `uv run scripts/demographics.py` (PEP 723 inline metadata 사용).

산출:
- eda_charts/age_hist.png
- eda_charts/sex_pie.png
- eda_charts/marital_bar.png
- eda_charts/education_bar.png
- eda_charts/_data/{age_hist,sex_pie,marital_bar,education_bar}.csv
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _font import setup_korean_font  # noqa: E402
setup_korean_font()

DATA_GLOB = "/Users/girinman/datasets/Nemotron-Personas-Korea/data/train-*.parquet"
ROOT = Path(__file__).resolve().parent.parent
CHART_DIR = ROOT / "eda_charts"
DATA_DIR = CHART_DIR / "_data"
CHART_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

con = duckdb.connect()
con.execute("PRAGMA threads=4")
con.execute("PRAGMA memory_limit='8GB'")

DPI = 110
FIGSIZE = (12, 8)

# Korean -> English label maps (한글 폰트 부재로 차트는 영문, 노트엔 한글 병기)
SEX_MAP = {"남자": "Male", "여자": "Female"}
MARITAL_MAP = {
    "미혼": "Never married",
    "배우자있음": "Married",
    "이혼": "Divorced",
    "사별": "Widowed",
}
EDU_MAP = {
    "무학": "None",
    "초등학교": "Elementary",
    "중학교": "Middle school",
    "고등학교": "High school",
    "2~3년제 전문대학": "2-3yr college",
    "4년제 대학교": "4yr university",
    "대학원": "Graduate",
}


def save(fig, path: Path):
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    print(f"  saved: {path.name}")


# ---- 1) AGE histogram + summary ----
print("== age ==")
age_df = con.execute(f"SELECT age FROM read_parquet('{DATA_GLOB}')").fetchdf()
age_summary = age_df["age"].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).to_frame("age").T
print(age_summary.to_string())
age_summary.to_csv(DATA_DIR / "age_summary.csv")

# bin into 5-year buckets for storage; histogram from raw
bins = list(range(0, 101, 5))
hist, edges = pd.cut(age_df["age"], bins=bins, right=False, include_lowest=True).value_counts(sort=False), bins
hist_df = pd.DataFrame({"bucket": [str(b) for b in hist.index], "count": hist.values})
hist_df.to_csv(DATA_DIR / "age_hist.csv", index=False)

fig, ax = plt.subplots(figsize=FIGSIZE)
ax.hist(age_df["age"], bins=bins, color="#3b78c0", edgecolor="white")
median = float(age_df["age"].median())
mean = float(age_df["age"].mean())
ax.axvline(median, color="crimson", linestyle="--", label=f"median={median:.0f}")
ax.axvline(mean, color="darkorange", linestyle=":", label=f"mean={mean:.1f}")
ax.set_title(f"Nemotron-Personas-Korea: age distribution (N={len(age_df):,})")
ax.set_xlabel("age (5yr bins)")
ax.set_ylabel("count")
ax.legend()
ax.grid(axis="y", alpha=0.3)
save(fig, CHART_DIR / "age_hist.png")
del age_df

# ---- 2) SEX pie ----
print("\n== sex ==")
sex_df = con.execute(
    f"SELECT sex, COUNT(*) AS n FROM read_parquet('{DATA_GLOB}') GROUP BY sex ORDER BY n DESC"
).fetchdf()
sex_df["pct"] = sex_df["n"] / sex_df["n"].sum() * 100
print(sex_df.to_string(index=False))
sex_df.to_csv(DATA_DIR / "sex_pie.csv", index=False)

fig, ax = plt.subplots(figsize=(8, 8))
colors = ["#e6749b", "#4f9bd9", "#888"][: len(sex_df)]
wedges, texts, autotexts = ax.pie(
    sex_df["n"],
    labels=[f"{SEX_MAP.get(s, s)} (n={n:,})" for s, n in zip(sex_df["sex"], sex_df["n"])],
    autopct="%1.1f%%",
    colors=colors,
    startangle=90,
)
ax.set_title(f"Sex distribution (N={int(sex_df['n'].sum()):,})")
save(fig, CHART_DIR / "sex_pie.png")

# ---- 3) MARITAL status bar ----
print("\n== marital_status ==")
mar_df = con.execute(
    f"SELECT marital_status, COUNT(*) AS n FROM read_parquet('{DATA_GLOB}') GROUP BY marital_status ORDER BY n DESC"
).fetchdf()
mar_df["pct"] = mar_df["n"] / mar_df["n"].sum() * 100
print(mar_df.to_string(index=False))
mar_df.to_csv(DATA_DIR / "marital_bar.csv", index=False)

mar_df_en = mar_df.copy()
mar_df_en["label"] = mar_df_en["marital_status"].map(lambda s: MARITAL_MAP.get(s, s))
fig, ax = plt.subplots(figsize=FIGSIZE)
ax.barh(mar_df_en["label"][::-1], mar_df_en["n"][::-1], color="#5a9c70")
for i, (val, pct) in enumerate(zip(mar_df["n"][::-1], mar_df["pct"][::-1])):
    ax.text(val, i, f" {val:,} ({pct:.1f}%)", va="center")
ax.set_title("Marital status distribution")
ax.set_xlabel("count")
ax.grid(axis="x", alpha=0.3)
save(fig, CHART_DIR / "marital_bar.png")

# ---- 4) EDUCATION level bar ----
print("\n== education_level ==")
edu_df = con.execute(
    f"SELECT education_level, COUNT(*) AS n FROM read_parquet('{DATA_GLOB}') GROUP BY education_level ORDER BY n DESC"
).fetchdf()
edu_df["pct"] = edu_df["n"] / edu_df["n"].sum() * 100
print(edu_df.to_string(index=False))
edu_df.to_csv(DATA_DIR / "education_bar.csv", index=False)

edu_df_en = edu_df.copy()
edu_df_en["label"] = edu_df_en["education_level"].map(lambda s: EDU_MAP.get(s, s))
fig, ax = plt.subplots(figsize=FIGSIZE)
ax.barh(edu_df_en["label"][::-1], edu_df_en["n"][::-1], color="#a06ec0")
for i, (val, pct) in enumerate(zip(edu_df["n"][::-1], edu_df["pct"][::-1])):
    ax.text(val, i, f" {val:,} ({pct:.1f}%)", va="center")
ax.set_title("Education level distribution")
ax.set_xlabel("count")
ax.grid(axis="x", alpha=0.3)
save(fig, CHART_DIR / "education_bar.png")

print("\nDONE: demographics.py")
