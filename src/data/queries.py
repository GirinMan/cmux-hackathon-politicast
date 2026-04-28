"""Read-only 쿼리 API — Phase 4 dual backend (Postgres primary / DuckDB legacy).

원칙
----
- 본 모듈은 read-only. 인제션은 `src.data.ingest`.
- region_id 는 `_workspace/contracts/data_paths.json` 의 `regions[].id` 매칭.
- 페르소나 sample 추출은 reproducible (`seed`).
- 함수 시그니처는 cutover 전과 동일. 내부적으로 `is_postgres_enabled()` 가 True
  일 때 SQLAlchemy 동기 엔진으로 PG 쿼리, 아니면 DuckDB legacy.
"""
from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional

logger = logging.getLogger("data.queries")

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_PATH = REPO_ROOT / "_workspace" / "contracts" / "data_paths.json"


def load_contracts() -> dict[str, Any]:
    with CONTRACTS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def default_db_path() -> Path:
    return REPO_ROOT / load_contracts()["duckdb_path"]


# ---------------------------------------------------------------------------
# Backend resolution
# ---------------------------------------------------------------------------
def _use_postgres() -> bool:
    try:
        from backend.app.db.session import is_postgres_enabled

        return is_postgres_enabled()
    except Exception:
        return False


@contextmanager
def connect(db_path: Path | None = None, read_only: bool = True) -> Iterator[Any]:
    """Backend-aware read-only connection.

    PG 모드: SQLAlchemy 동기 engine.connect() 반환 — `con.execute(text(sql))`.
    DuckDB 모드: legacy duckdb connection.

    호출부는 ``con.execute(sql).fetchall()`` 만 쓰면 둘 다 동작 (compat shim).
    """
    if _use_postgres():
        from sqlalchemy import create_engine

        from backend.app.db.session import resolve_dsn

        engine = create_engine(resolve_dsn(async_=False), future=True)
        con = engine.connect()
        try:
            yield _SAConCompat(con)
        finally:
            con.close()
            engine.dispose()
        return

    import duckdb

    if db_path is None:
        db_path = default_db_path()
    con = duckdb.connect(str(db_path), read_only=read_only)
    try:
        yield con
    finally:
        con.close()


class _SAConCompat:
    """DuckDB-style ``con.execute(sql).fetchall()`` 인터페이스 SQLAlchemy 래퍼."""

    def __init__(self, sa_con: Any) -> None:
        self._con = sa_con
        self.description: list[Any] = []

    def execute(self, sql: str, params: Any = None) -> "_SAConCompat":
        from sqlalchemy import text as _text

        # DuckDB-style `?` placeholder → SQLAlchemy named bind.
        if params is not None and "?" in sql:
            named: dict[str, Any] = {}
            parts = sql.split("?")
            new_sql = parts[0]
            for i, p in enumerate(parts[1:], start=1):
                key = f"p{i}"
                named[key] = (params[i - 1] if isinstance(params, (list, tuple)) else params)
                new_sql += f":{key}" + p
            self._result = self._con.execute(_text(new_sql), named)
        else:
            self._result = self._con.execute(_text(sql))
        # description (DuckDB 와 호환)
        try:
            self.description = [(c, None) for c in self._result.keys()]
        except Exception:
            self.description = []
        return self

    def fetchall(self) -> list[tuple]:
        return [tuple(r) for r in self._result.fetchall()]

    def fetchone(self) -> Optional[tuple]:
        row = self._result.fetchone()
        return tuple(row) if row is not None else None

    def executemany(self, sql: str, seq: Any) -> None:
        for params in seq:
            self.execute(sql, params)


# ---------------------------------------------------------------------------
# Region helpers
# ---------------------------------------------------------------------------
def region_view_name(region_id: str) -> str:
    return f"personas_{region_id}"


def region_size(region_id: str, db_path: Path | None = None) -> int:
    view = region_view_name(region_id)
    with connect(db_path) as con:
        row = con.execute(f'SELECT COUNT(*) FROM "{view}"').fetchone()
        return int(row[0]) if row else 0


def region_summary(region_id: str, db_path: Path | None = None) -> dict[str, Any]:
    """간단한 demographic 요약 — paper / dashboard."""
    view = region_view_name(region_id)
    with connect(db_path) as con:
        n = con.execute(f'SELECT COUNT(*) FROM "{view}"').fetchone()[0]
        if not n:
            return {"region_id": region_id, "n": 0}
        avg_age = con.execute(f'SELECT AVG(age) FROM "{view}"').fetchone()[0]
        sex = dict(
            con.execute(f'SELECT sex, COUNT(*) FROM "{view}" GROUP BY 1').fetchall()
        )
        edu = dict(
            con.execute(
                f'SELECT education_level, COUNT(*) FROM "{view}" '
                f"GROUP BY 1 ORDER BY 2 DESC LIMIT 6"
            ).fetchall()
        )
        return {
            "region_id": region_id,
            "n": int(n),
            "avg_age": round(float(avg_age), 2),
            "sex_dist": sex,
            "edu_top6": edu,
        }


# ---------------------------------------------------------------------------
# Persona sampling
# ---------------------------------------------------------------------------
@dataclass
class PersonaRecord:
    """Voter agent prompt 에 들어갈 페르소나 단일 레코드."""

    uuid: str
    sex: str | None
    age: int | None
    province: str | None
    district: str | None
    education_level: str | None
    occupation: str | None
    persona: str | None
    cultural_background: str | None
    professional_persona: str | None
    family_persona: str | None

    def to_block(self) -> str:
        parts: list[str] = []
        head_bits = [
            f"{self.age}세" if self.age is not None else None,
            self.sex,
            self.district or self.province,
        ]
        head = " · ".join([b for b in head_bits if b])
        if head:
            parts.append(f"[프로필] {head}")
        if self.occupation:
            parts.append(f"[직업] {self.occupation}")
        if self.education_level:
            parts.append(f"[학력] {self.education_level}")
        if self.persona:
            parts.append(f"[요약] {self.persona}")
        if self.cultural_background:
            parts.append(f"[문화 배경] {self.cultural_background}")
        if self.professional_persona:
            parts.append(f"[직업 페르소나] {self.professional_persona}")
        if self.family_persona:
            parts.append(f"[가족 페르소나] {self.family_persona}")
        return "\n".join(parts)


_PERSONA_SELECT = """
SELECT
    p.uuid,
    p.sex,
    p.age,
    p.province,
    p.district,
    p.education_level,
    p.occupation,
    p.persona,
    p.cultural_background,
    t.professional_persona,
    t.family_persona
FROM "{view}" p
LEFT JOIN persona_text t USING (uuid)
"""


def sample_personas(
    region_id: str,
    n: int,
    *,
    seed: int = 42,
    db_path: Path | None = None,
    min_age: int | None = None,
) -> list[PersonaRecord]:
    """region 에서 n명 reproducible sample.

    Postgres: ``ORDER BY md5(uuid::text || :seed)`` (deterministic 해싱).
    DuckDB:   ``ORDER BY hash(uuid::VARCHAR || '<seed>')`` legacy.
    """
    view = region_view_name(region_id)
    where = ""
    if min_age is not None:
        where = f" WHERE p.age >= {int(min_age)}"

    if _use_postgres():
        order_by = f" ORDER BY md5(p.uuid::text || '{int(seed)}')"
    else:
        order_by = f" ORDER BY hash(p.uuid::VARCHAR || '{int(seed)}')"

    sql = (
        _PERSONA_SELECT.format(view=view)
        + where
        + order_by
        + f" LIMIT {int(n)}"
    )
    with connect(db_path) as con:
        rows = con.execute(sql).fetchall()
        cols = [d[0] for d in con.description] if con.description else (
            "uuid sex age province district education_level occupation "
            "persona cultural_background professional_persona family_persona"
        ).split()
    out: list[PersonaRecord] = []
    for r in rows:
        d = dict(zip(cols, r))
        out.append(
            PersonaRecord(
                uuid=str(d["uuid"]),
                sex=d.get("sex"),
                age=int(d["age"]) if d.get("age") is not None else None,
                province=d.get("province"),
                district=d.get("district"),
                education_level=d.get("education_level"),
                occupation=d.get("occupation"),
                persona=d.get("persona"),
                cultural_background=d.get("cultural_background"),
                professional_persona=d.get("professional_persona"),
                family_persona=d.get("family_persona"),
            )
        )
    return out


# ---------------------------------------------------------------------------
# CLI helper
# ---------------------------------------------------------------------------
def main() -> int:
    contracts = load_contracts()
    for r in contracts["regions"]:
        rid = r["id"]
        if r.get("province") in (None, "TBD"):
            print(f"{rid}: skipped (TBD)")
            continue
        try:
            summary = region_summary(rid)
            print(f"{rid}: n={summary['n']:,}  avg_age={summary.get('avg_age')}")
        except Exception as e:
            print(f"{rid}: error {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
