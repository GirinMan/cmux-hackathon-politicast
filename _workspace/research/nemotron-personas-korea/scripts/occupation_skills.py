#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["duckdb", "pandas", "matplotlib", "numpy", "pyarrow"]
# ///
"""
Task #14: occupation / skills_and_expertise_list / hobbies_and_interests_list 상위 30 분포.

실행: `uv run scripts/occupation_skills.py` (PEP 723 inline metadata 사용).

list 필드는 Python list-repr 문자열(single-quote): "['a', 'b', 'c']" 형식.
- 빠른 파싱: ast.literal_eval (1M 행 처리 시 ~30s)
- 빈도 집계: collections.Counter

산출:
- eda_charts/{occupation_top,skills_top,hobbies_top}.png
- eda_charts/_data/{occupation_top,skills_top,hobbies_top}.csv (top 100 저장)
- eda_charts/_data/{skills_token_count,hobbies_token_count}.json (per-row item count 통계)
"""
from __future__ import annotations

import ast
import json
import sys
from collections import Counter
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

DPI = 110
TOPN_CHART = 30
TOPN_CSV = 100


def parse_list(s):
    if not s:
        return []
    try:
        v = ast.literal_eval(s)
        if isinstance(v, list):
            return [str(x).strip() for x in v if x]
    except Exception:
        pass
    return []


def hbar(items_n_pairs, title: str, color: str, out_png: Path):
    items = [x[0] for x in items_n_pairs][::-1]
    ns = [x[1] for x in items_n_pairs][::-1]
    fig, ax = plt.subplots(figsize=(13, 9))
    ax.barh(range(len(items)), ns, color=color)
    ax.set_yticks(range(len(items)))
    # truncate long
    ax.set_yticklabels([(s[:42] + "…") if len(s) > 43 else s for s in items], fontsize=8)
    for i, v in enumerate(ns):
        ax.text(v, i, f" {v:,}", va="center", fontsize=8)
    ax.set_title(title)
    ax.set_xlabel("count")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_png, dpi=DPI)
    plt.close(fig)
    print(f"  saved: {out_png.name}")


# ---- 1) occupation ----
print("== occupation ==")
occ_df = con.execute(
    f"SELECT occupation, COUNT(*) AS n FROM read_parquet('{DATA_GLOB}') GROUP BY occupation ORDER BY n DESC"
).fetchdf()
print(f"  unique occupations: {len(occ_df):,}")
occ_df.head(TOPN_CSV).to_csv(DATA_DIR / "occupation_top.csv", index=False)
print(occ_df.head(15).to_string(index=False))
top = list(zip(occ_df["occupation"].head(TOPN_CHART).tolist(), occ_df["n"].head(TOPN_CHART).tolist()))
hbar(top, f"Occupation top {TOPN_CHART} (of {len(occ_df):,} unique)", "#3b78c0", CHART_DIR / "occupation_top.png")

# ---- 2) skills_and_expertise_list ----
print("\n== skills_and_expertise_list ==")
skills_strs = con.execute(
    f"SELECT skills_and_expertise_list FROM read_parquet('{DATA_GLOB}')"
).fetchdf()["skills_and_expertise_list"]
print(f"  rows fetched: {len(skills_strs):,}")
skill_counter = Counter()
skill_lengths = []
for s in skills_strs:
    items = parse_list(s)
    skill_lengths.append(len(items))
    skill_counter.update(items)
sk_df = pd.DataFrame(skill_counter.most_common(TOPN_CSV), columns=["skill", "n"])
sk_df.to_csv(DATA_DIR / "skills_top.csv", index=False)
sk_top = list(zip(sk_df["skill"].head(TOPN_CHART).tolist(), sk_df["n"].head(TOPN_CHART).tolist()))
print(sk_df.head(15).to_string(index=False))
print(f"  unique skills: {len(skill_counter):,}")
hbar(sk_top, f"Skills top {TOPN_CHART} (of {len(skill_counter):,} unique)", "#5a9c70", CHART_DIR / "skills_top.png")
sl_arr = np.asarray(skill_lengths)
skill_stats = {
    "rows": int(len(sl_arr)),
    "unique_items": int(len(skill_counter)),
    "items_per_row_mean": float(sl_arr.mean()),
    "items_per_row_median": float(np.median(sl_arr)),
    "items_per_row_min": int(sl_arr.min()),
    "items_per_row_max": int(sl_arr.max()),
    "rows_with_zero_items": int((sl_arr == 0).sum()),
}
with open(DATA_DIR / "skills_token_count.json", "w") as f:
    json.dump(skill_stats, f, ensure_ascii=False, indent=2)
print("  per-row item stats:", skill_stats)
del skills_strs, skill_counter, skill_lengths, sl_arr

# ---- 3) hobbies_and_interests_list ----
print("\n== hobbies_and_interests_list ==")
hobby_strs = con.execute(
    f"SELECT hobbies_and_interests_list FROM read_parquet('{DATA_GLOB}')"
).fetchdf()["hobbies_and_interests_list"]
print(f"  rows fetched: {len(hobby_strs):,}")
hobby_counter = Counter()
hobby_lengths = []
for s in hobby_strs:
    items = parse_list(s)
    hobby_lengths.append(len(items))
    hobby_counter.update(items)
hb_df = pd.DataFrame(hobby_counter.most_common(TOPN_CSV), columns=["hobby", "n"])
hb_df.to_csv(DATA_DIR / "hobbies_top.csv", index=False)
hb_top = list(zip(hb_df["hobby"].head(TOPN_CHART).tolist(), hb_df["n"].head(TOPN_CHART).tolist()))
print(hb_df.head(15).to_string(index=False))
print(f"  unique hobbies: {len(hobby_counter):,}")
hbar(hb_top, f"Hobbies top {TOPN_CHART} (of {len(hobby_counter):,} unique)", "#a06ec0", CHART_DIR / "hobbies_top.png")
hl_arr = np.asarray(hobby_lengths)
hobby_stats = {
    "rows": int(len(hl_arr)),
    "unique_items": int(len(hobby_counter)),
    "items_per_row_mean": float(hl_arr.mean()),
    "items_per_row_median": float(np.median(hl_arr)),
    "items_per_row_min": int(hl_arr.min()),
    "items_per_row_max": int(hl_arr.max()),
    "rows_with_zero_items": int((hl_arr == 0).sum()),
}
with open(DATA_DIR / "hobbies_token_count.json", "w") as f:
    json.dump(hobby_stats, f, ensure_ascii=False, indent=2)
print("  per-row item stats:", hobby_stats)

print("\nDONE: occupation_skills.py")
