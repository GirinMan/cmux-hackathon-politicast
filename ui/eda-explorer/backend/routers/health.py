"""/api/health + /api/schema 엔드포인트."""
from __future__ import annotations

from fastapi import APIRouter

import db
from models import (
    ColumnDescriptor,
    HealthResponse,
    SchemaResponse,
    TableDescriptor,
)

router = APIRouter(tags=["meta"])


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """DB 연결·테이블 존재 여부 확인."""
    try:
        core_rows = db.query("SELECT COUNT(*) FROM persona_core")[0][0]
        text_rows = db.query("SELECT COUNT(*) FROM persona_text")[0][0]
        regions = db.list_region_tables()
        status = "ok" if core_rows > 0 and text_rows > 0 else "degraded"
    except Exception:
        return HealthResponse(
            status="degraded",
            mode=db.get_mode(),
            source=db.get_source_path(),
            persona_core_rows=0,
            persona_text_rows=0,
            region_tables=[],
        )
    return HealthResponse(
        status=status,
        mode=db.get_mode(),
        source=db.get_source_path(),
        persona_core_rows=int(core_rows),
        persona_text_rows=int(text_rows),
        region_tables=regions,
    )


def _describe_table(name: str) -> TableDescriptor | None:
    """단일 테이블 schema + row count. 없으면 None."""
    try:
        cols = db.query(f"DESCRIBE {name}")
        rows = db.query(f"SELECT COUNT(*) FROM {name}")[0][0]
    except Exception:
        return None
    return TableDescriptor(
        name=name,
        rows=int(rows),
        columns=[
            ColumnDescriptor(
                name=str(r[0]),
                dtype=str(r[1]),
                nullable=str(r[2]).upper() != "NO",
            )
            for r in cols
        ],
    )


@router.get("/api/schema", response_model=SchemaResponse)
def schema() -> SchemaResponse:
    """등록된 모든 테이블의 schema + row count 반환."""
    table_names = ["persona_core", "persona_text", *db.list_region_tables()]
    tables: list[TableDescriptor] = []
    for n in table_names:
        td = _describe_table(n)
        if td is not None:
            tables.append(td)
    notes = [
        "persona_core(uuid PK) + persona_text(uuid PK) join on uuid (1:1, 1M rows).",
        "persona = concise summary in persona_core; long text fields live in persona_text.",
        "*_list columns are Python list repr strings — use ast.literal_eval before list ops.",
        "province uses short form (서울, 경기, 경상남, 전북). KOSIS-style join requires normalization.",
    ]
    return SchemaResponse(tables=tables, notes=notes)
