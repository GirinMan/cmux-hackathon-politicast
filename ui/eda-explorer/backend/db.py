"""DuckDB 연결 레이어 — 영속 DB 우선, parquet glob fallback."""
from __future__ import annotations

import ast
import json
import os
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import duckdb

# 데이터 소스 우선순위. 경로의 source of truth 는 프로젝트 계약 파일이다.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_PATHS_PATH = PROJECT_ROOT / "_workspace" / "contracts" / "data_paths.json"


def _project_path(path_value: str | os.PathLike[str]) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else PROJECT_ROOT / path


@lru_cache(maxsize=1)
def data_paths_contract() -> dict[str, Any]:
    """Load `_workspace/contracts/data_paths.json` once per process."""
    with DATA_PATHS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


_CONTRACT = data_paths_contract()
DUCKDB_PATH = _project_path(str(_CONTRACT.get("duckdb_path", "_workspace/db/politikast.duckdb")))
PARQUET_DIR = Path(
    str(
        _CONTRACT.get(
            "nemotron_parquet_dir",
            "/Users/girinman/datasets/Nemotron-Personas-Korea/data",
        )
    )
)
PARQUET_GLOB = str(PARQUET_DIR / "*.parquet")
PERSONA_TABLE = str(_CONTRACT.get("persona_table", "persona_core"))
PERSONA_TEXT_TABLE = str(_CONTRACT.get("persona_text_table", "persona_text"))

# Persistent vs fallback 모드 분기
_lock = threading.Lock()
_query_lock = threading.RLock()
_con: duckdb.DuckDBPyConnection | None = None
_mode: str = "uninitialized"  # "duckdb" | "parquet" | "uninitialized"


def _build_connection() -> tuple[duckdb.DuckDBPyConnection, str]:
    """DuckDB 영속 파일이 있고 persona_core 테이블이 있으면 사용, 아니면 parquet view fallback."""
    if DUCKDB_PATH.exists():
        try:
            con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
            tables = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
            if {PERSONA_TABLE, PERSONA_TEXT_TABLE}.issubset(tables):
                return con, "duckdb"
            con.close()
        except Exception:
            pass

    # Fallback: in-memory connection wrapping parquet glob
    con = duckdb.connect(":memory:")
    # persona_core 와 persona_text 를 view 로 만들어 동일한 SQL 사용 가능하게
    con.execute(
        f"""
        CREATE VIEW {PERSONA_TABLE} AS
        SELECT uuid, persona, cultural_background, skills_and_expertise,
               skills_and_expertise_list, hobbies_and_interests,
               hobbies_and_interests_list, career_goals_and_ambitions,
               sex, age, marital_status, military_status, family_type,
               housing_type, education_level, bachelors_field, occupation,
               district, province, country
        FROM read_parquet('{PARQUET_GLOB}')
        """
    )
    con.execute(
        f"""
        CREATE VIEW {PERSONA_TEXT_TABLE} AS
        SELECT uuid, professional_persona, sports_persona, arts_persona,
               travel_persona, culinary_persona, family_persona
        FROM read_parquet('{PARQUET_GLOB}')
        """
    )
    return con, "parquet"


def get_connection() -> duckdb.DuckDBPyConnection:
    """프로세스 단일 read-only 연결 반환. 첫 호출 시 mode 결정."""
    global _con, _mode
    if _con is not None:
        return _con
    with _lock:
        if _con is None:
            _con, _mode = _build_connection()
    return _con


def get_mode() -> str:
    """현재 데이터 소스 모드 반환 ('duckdb' / 'parquet')."""
    if _mode == "uninitialized":
        get_connection()
    return _mode


def get_source_path() -> str:
    """현재 데이터 소스 경로(또는 glob) 반환."""
    return str(DUCKDB_PATH) if get_mode() == "duckdb" else PARQUET_GLOB


def query(sql: str, params: Iterable[Any] | None = None) -> list[tuple[Any, ...]]:
    """Prepared statement 실행. f-string SQL injection 금지."""
    con = get_connection()
    with _query_lock:
        cur = con.execute(sql, list(params) if params else [])
        return cur.fetchall()


def query_dicts(sql: str, params: Iterable[Any] | None = None) -> list[dict[str, Any]]:
    """결과를 dict 리스트로 변환."""
    con = get_connection()
    with _query_lock:
        cur = con.execute(sql, list(params) if params else [])
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def parse_list_field(value: str | None) -> list[str]:
    """`*_list` 컬럼 (Python list repr) 안전 파싱."""
    if not value:
        return []
    try:
        out = ast.literal_eval(value)
        if isinstance(out, list):
            return [str(x) for x in out]
    except (ValueError, SyntaxError):
        pass
    return []


def list_region_tables() -> list[str]:
    """현재 DB 에 존재하는 personas_* region 테이블 목록."""
    if get_mode() != "duckdb":
        return []
    rows = query("SHOW TABLES")
    return sorted(t for (t,) in rows if t.startswith("personas_"))


def _assert_identifier(value: str) -> str:
    """Allow only simple DuckDB identifiers derived from project contracts."""
    if not value.replace("_", "").isalnum():
        raise ValueError(f"unsafe SQL identifier: {value}")
    return value


def _region_label_en(region_id: str) -> str:
    return region_id.replace("_", " ").title()


def _load_regions() -> dict[str, dict[str, Any]]:
    regions: dict[str, dict[str, Any]] = {}
    for raw in data_paths_contract().get("regions", []):
        region_id = str(raw["id"])
        table = _assert_identifier(f"personas_{region_id}")
        regions[region_id] = {
            "key": region_id,
            "id": region_id,
            "label_ko": raw.get("label", region_id),
            "label_en": raw.get("label_en", _region_label_en(region_id)),
            "type": raw.get("type"),
            "province": raw.get("province"),
            "district": raw.get("district"),
            "table": table,
            "rationale": raw.get("rationale"),
        }
    return regions


# 5 region 정규화 — `_workspace/contracts/data_paths.json` 기반.
FIVE_REGIONS: dict[str, dict[str, Any]] = _load_regions()

# Province-level scopes used by the frontend population map. The source data
# uses a mix of short and long Korean province names, so keep the mapping here
# instead of duplicating SQL filters in routers.
PROVINCE_REGION_ALIASES: dict[str, tuple[str, str]] = {
    "seoul": ("서울", "Seoul"),
    "incheon": ("인천", "Incheon"),
    "gyeonggi": ("경기", "Gyeonggi"),
    "gangwon": ("강원", "Gangwon"),
    "chungbuk": ("충청북", "Chungbuk"),
    "chungnam": ("충청남", "Chungnam"),
    "sejong": ("세종", "Sejong"),
    "daejeon": ("대전", "Daejeon"),
    "jeonbuk": ("전북", "Jeonbuk"),
    "jeonnam": ("전라남", "Jeonnam"),
    "gwangju": ("광주", "Gwangju"),
    "gyeongbuk": ("경상북", "Gyeongbuk"),
    "daegu": ("대구", "Daegu"),
    "ulsan": ("울산", "Ulsan"),
    "gyeongnam": ("경상남", "Gyeongnam"),
    "busan": ("부산", "Busan"),
    "jeju": ("제주", "Jeju"),
}


class UnknownRegionError(ValueError):
    """Raised when a region id is not present in `data_paths.json`."""


@dataclass(frozen=True)
class RegionSource:
    """Resolved SQL source for a global or contract region query."""

    region: str | None
    table: str
    where_sql: str
    params: list[Any]
    info: dict[str, Any] | None
    uses_region_table: bool


def resolve_region_source(region: str | None) -> RegionSource:
    """Return `(table, where, params)` for a region, using contract tables first."""
    if region is None:
        return RegionSource(
            region=None,
            table=PERSONA_TABLE,
            where_sql="",
            params=[],
            info=None,
            uses_region_table=False,
        )
    if region.startswith("province:"):
        province_key = region.split(":", 1)[1]
        province_info = PROVINCE_REGION_ALIASES.get(province_key)
        if province_info is None:
            raise UnknownRegionError(f"unknown province region key: {region}")
        province, label_en = province_info
        return RegionSource(
            region=region,
            table=PERSONA_TABLE,
            where_sql="WHERE province = ?",
            params=[province],
            info={
                "key": region,
                "id": region,
                "label_ko": province,
                "label_en": label_en,
                "type": "province_scope",
                "province": province,
                "district": None,
                "table": None,
            },
            uses_region_table=False,
        )
    if region not in FIVE_REGIONS:
        raise UnknownRegionError(f"unknown region key: {region}")

    info = FIVE_REGIONS[region]
    table = str(info.get("table") or "")
    if table and table in list_region_tables():
        return RegionSource(
            region=region,
            table=table,
            where_sql="",
            params=[],
            info=info,
            uses_region_table=True,
        )

    province = info.get("province")
    district = info.get("district")
    if district:
        return RegionSource(
            region=region,
            table=PERSONA_TABLE,
            where_sql="WHERE district = ?",
            params=[district],
            info=info,
            uses_region_table=False,
        )
    if province:
        return RegionSource(
            region=region,
            table=PERSONA_TABLE,
            where_sql="WHERE province = ?",
            params=[province],
            info=info,
            uses_region_table=False,
        )

    return RegionSource(
        region=region,
        table=PERSONA_TABLE,
        where_sql="WHERE 1 = 0",
        params=[],
        info=info,
        uses_region_table=False,
    )


def count_region(region: str) -> tuple[int, bool]:
    """Return `(count, available)` for a contract region."""
    src = resolve_region_source(region)
    count = int(query(f"SELECT COUNT(*) FROM {src.table} {src.where_sql}", src.params)[0][0])
    return count, count > 0
