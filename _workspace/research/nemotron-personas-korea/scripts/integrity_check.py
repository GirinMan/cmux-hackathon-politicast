#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["duckdb", "pandas", "pyarrow"]
# ///
"""
Task #11: Nemotron-Personas-Korea 9 parquet shards 무결성 + schema consistency 검증.

실행: `uv run scripts/integrity_check.py` (PEP 723 inline metadata 사용).

검증 항목:
- shard별 row count + total
- column 이름/타입/순서 동일성 (DESCRIBE)
- uuid unique (전수)
- shard별 결측 비율 (컬럼별)
- shard별 파일 사이즈

산출:
- notes/20_integrity.md 작성용 데이터 → eda_charts/_data/integrity_*.csv
- stdout에 요약 출력
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import duckdb
import pandas as pd

DATA_GLOB = "/Users/girinman/datasets/Nemotron-Personas-Korea/data/train-*.parquet"
SHARDS = sorted(Path("/Users/girinman/datasets/Nemotron-Personas-Korea/data").glob("train-*.parquet"))
OUT_DIR = Path(__file__).resolve().parent.parent / "eda_charts" / "_data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

con = duckdb.connect()
con.execute("PRAGMA threads=4")
con.execute("PRAGMA memory_limit='8GB'")

# 1) Row count per shard
print("=== shard row counts ===")
rows = []
for sh in SHARDS:
    n = con.execute(f"SELECT COUNT(*) FROM read_parquet('{sh}')").fetchone()[0]
    sz = sh.stat().st_size
    rows.append({"shard": sh.name, "rows": n, "size_bytes": sz})
    print(f"  {sh.name}: rows={n:>8,}  size={sz/1e6:.1f} MB")
df_shards = pd.DataFrame(rows)
df_shards.loc[len(df_shards)] = {"shard": "TOTAL", "rows": int(df_shards["rows"].sum()), "size_bytes": int(df_shards["size_bytes"].sum())}
df_shards.to_csv(OUT_DIR / "integrity_shards.csv", index=False)
print(f"  TOTAL rows = {df_shards.iloc[-1]['rows']:,}")

# 2) Schema per shard
print("\n=== schema per shard (DESCRIBE) ===")
schemas = {}
for sh in SHARDS:
    desc = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{sh}')").fetchdf()
    sig = tuple(zip(desc["column_name"].tolist(), desc["column_type"].tolist()))
    schemas[sh.name] = sig

ref_name, ref_sig = next(iter(schemas.items()))
all_match = all(sig == ref_sig for sig in schemas.values())
print(f"  reference shard: {ref_name}  cols={len(ref_sig)}")
print(f"  all 9 shards identical schema? {all_match}")
if not all_match:
    for nm, sg in schemas.items():
        if sg != ref_sig:
            print(f"    MISMATCH {nm}")

# Save reference schema
schema_df = pd.DataFrame(ref_sig, columns=["column_name", "column_type"])
schema_df.to_csv(OUT_DIR / "integrity_schema.csv", index=False)
print(f"  schema saved: {len(schema_df)} columns")

# 3) UUID uniqueness across all shards
print("\n=== uuid uniqueness ===")
# Find a candidate id column
id_candidates = [c for c, t in ref_sig if c.lower() in {"uuid", "persona_id", "id"}]
print(f"  id candidates: {id_candidates}")
id_col = id_candidates[0] if id_candidates else None
uuid_stats = {}
if id_col:
    n_total = con.execute(f"SELECT COUNT(*) FROM read_parquet('{DATA_GLOB}')").fetchone()[0]
    n_distinct = con.execute(f"SELECT COUNT(DISTINCT {id_col}) FROM read_parquet('{DATA_GLOB}')").fetchone()[0]
    n_null = con.execute(f"SELECT COUNT(*) FROM read_parquet('{DATA_GLOB}') WHERE {id_col} IS NULL").fetchone()[0]
    uuid_stats = {"id_col": id_col, "rows": n_total, "distinct": n_distinct, "null": n_null, "unique": n_total == n_distinct and n_null == 0}
    print(f"  rows={n_total:,}  distinct={n_distinct:,}  null={n_null}  unique={uuid_stats['unique']}")
else:
    print("  WARN: no obvious id column.")
with open(OUT_DIR / "integrity_uuid.json", "w") as f:
    json.dump(uuid_stats, f, ensure_ascii=False, indent=2)

# 4) Per-column null ratio (full corpus)
print("\n=== column null ratio (full corpus) ===")
exprs = []
for c, t in ref_sig:
    safe = '"' + c.replace('"', '""') + '"'
    exprs.append(f"SUM(CASE WHEN {safe} IS NULL THEN 1 ELSE 0 END) AS {safe}")
sql = f"SELECT {', '.join(exprs)} FROM read_parquet('{DATA_GLOB}')"
nulls = con.execute(sql).fetchdf().iloc[0]
n_total_for_null = con.execute(f"SELECT COUNT(*) FROM read_parquet('{DATA_GLOB}')").fetchone()[0]
null_df = pd.DataFrame({
    "column": [c for c, _ in ref_sig],
    "type": [t for _, t in ref_sig],
    "null_count": [int(nulls[c]) for c, _ in ref_sig],
})
null_df["null_ratio"] = null_df["null_count"] / n_total_for_null
null_df = null_df.sort_values("null_ratio", ascending=False)
null_df.to_csv(OUT_DIR / "integrity_nulls.csv", index=False)
print(null_df.head(20).to_string(index=False))
print(f"  ... ({len(null_df)} columns)")

print("\nDONE: integrity_check.py")
