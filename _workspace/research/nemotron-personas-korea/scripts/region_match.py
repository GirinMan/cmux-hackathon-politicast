#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["duckdb", "pandas", "matplotlib", "pyarrow"]
# ///
"""
Task #13: 5 region 매칭 행수 (서울/광주/대구/부산 북구 갑/대구 달서구 갑).

실행: `uv run scripts/region_match.py` (PEP 723 inline metadata 사용).

`province` + `district` 컬럼이 모든 행에 존재(integrity_check 결과) → 정확 GROUP BY.

5 region 정의는 `_workspace/contracts/data_paths.json` 기준:
- seoul_mayor (province == '서울')
- gwangju_mayor (province == '광주')
- daegu_mayor (province == '대구')
- busan_buk_gap (province == '부산', district == '부산-북구')
- daegu_dalseo_gap (province == '대구', district == '대구-달서구')

산출:
- eda_charts/_data/region_match.csv  (5 region rowcount)
- eda_charts/_data/province_breakdown.csv  (전체 province 분포)
- eda_charts/_data/by_election_districts.csv  (부산 북구/대구 달서구 검증용)
- eda_charts/region_match_bar.png
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys
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

# 1) Province 분포 (전수)
print("== province distribution (top 20) ==")
prov = con.execute(
    f"SELECT province, COUNT(*) AS n FROM read_parquet('{DATA_GLOB}') GROUP BY province ORDER BY n DESC"
).fetchdf()
prov["pct"] = prov["n"] / prov["n"].sum() * 100
prov.to_csv(DATA_DIR / "province_breakdown.csv", index=False)
print(prov.to_string(index=False))

# 2) 5 region matching
print("\n== 5 region matching ==")
sql = f"""
WITH src AS (
  SELECT province, district FROM read_parquet('{DATA_GLOB}')
)
SELECT 'seoul_mayor' AS region, COUNT(*) AS n FROM src WHERE province = '서울'
UNION ALL
SELECT 'gwangju_mayor' AS region, COUNT(*) AS n FROM src WHERE province = '광주'
UNION ALL
SELECT 'daegu_mayor' AS region, COUNT(*) AS n FROM src WHERE province = '대구'
UNION ALL
SELECT 'busan_buk_gap' AS region, COUNT(*) AS n FROM src WHERE province = '부산' AND district = '부산-북구'
UNION ALL
SELECT 'daegu_dalseo_gap' AS region, COUNT(*) AS n FROM src WHERE province = '대구' AND district = '대구-달서구'
"""
region = con.execute(sql).fetchdf()
region["pct"] = (region["n"] / 1_000_000 * 100).round(4)
region = region.sort_values("n", ascending=False)
print(region.to_string(index=False))
region.to_csv(DATA_DIR / "region_match.csv", index=False)

# 3) 보궐 지역 검증: 부산/대구 district 분포
print("\n== by-election district sanity ==")
districts = con.execute(
    f"""SELECT province, district, COUNT(*) AS n
        FROM read_parquet('{DATA_GLOB}')
        WHERE province IN ('부산', '대구')
        GROUP BY province, district ORDER BY province, n DESC"""
).fetchdf()
districts.to_csv(DATA_DIR / "by_election_districts.csv", index=False)
print(districts.to_string(index=False))

# 4) chart
print("\n== chart ==")
fig, ax = plt.subplots(figsize=(12, 8))
labels_en = {
    "seoul_mayor": "Seoul Mayor",
    "gwangju_mayor": "Gwangju Mayor",
    "daegu_mayor": "Daegu Mayor",
    "busan_buk_gap": "Busan Buk Gap",
    "daegu_dalseo_gap": "Daegu Dalseo Gap",
    "other": "Other",
}
xs = [labels_en.get(r, r) for r in region["region"]]
ys = region["n"].tolist()
colors = ["#3b78c0", "#e6749b", "#5a9c70", "#a06ec0", "#bbbbbb"]
ax.bar(xs, ys, color=colors[: len(xs)])
for i, (v, p) in enumerate(zip(region["n"], region["pct"])):
    ax.text(i, v, f"{v:,}\n({p:.2f}%)", ha="center", va="bottom")
ax.set_yscale("log")
ax.set_title("PolitiKAST 5 region row counts (log scale)")
ax.set_ylabel("rows (log)")
ax.grid(axis="y", which="both", alpha=0.3)
fig.tight_layout()
fig.savefig(CHART_DIR / "region_match_bar.png", dpi=110)
plt.close(fig)
print(f"  saved: region_match_bar.png")

print("\nDONE: region_match.py")
