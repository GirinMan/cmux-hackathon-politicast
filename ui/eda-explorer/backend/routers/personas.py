"""/api/personas/sample + /api/personas/{uuid} + /api/personas/text-stats."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

import db
from models import (
    PersonaDetail,
    PersonaSampleResponse,
    PersonaSummary,
    PersonaTextStatsResponse,
    TextStat,
)

router = APIRouter(tags=["personas"])


_TEXT_FIELDS_CORE = ["persona", "cultural_background", "skills_and_expertise"]
_TEXT_FIELDS_LONG = [
    "professional_persona",
    "sports_persona",
    "arts_persona",
    "travel_persona",
    "culinary_persona",
    "family_persona",
]


def _resolve_region(region: str | None) -> tuple[str, str, list]:
    """(src_table, where_sql, params) 반환. region 미지정 → persona_core."""
    try:
        source = db.resolve_region_source(region)
    except db.UnknownRegionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return source.table, source.where_sql, source.params


@router.get("/api/personas/sample", response_model=PersonaSampleResponse)
def sample(
    region: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    seed: int | None = Query(default=None, description="재현 가능한 random seed"),
) -> PersonaSampleResponse:
    """region 옵션 + N 랜덤 샘플."""
    src, where_sql, params = _resolve_region(region)
    total = int(db.query(f"SELECT COUNT(*) FROM {src} {where_sql}", params)[0][0])
    if total == 0:
        return PersonaSampleResponse(region=region, total=0, samples=[])

    # DuckDB 의 setseed 는 -1.0 ~ 1.0
    if seed is not None:
        try:
            db.query("SELECT setseed(?)", [(seed % 1000) / 1000.0])
        except Exception:
            pass

    rows = db.query_dicts(
        f"""
        SELECT uuid, persona, sex, age, marital_status, education_level,
               occupation, province, district
        FROM {src} {where_sql}
        USING SAMPLE {int(limit)} ROWS
        """,
        params,
    )
    samples = [PersonaSummary(**r) for r in rows]
    return PersonaSampleResponse(region=region, total=total, samples=samples)


@router.get("/api/personas/text-stats", response_model=PersonaTextStatsResponse)
def text_stats(
    region: str | None = Query(default=None),
    sample_size: int = Query(default=5000, ge=100, le=50000, description="LIMIT N (성능 보호)"),
) -> PersonaTextStatsResponse:
    """페르소나 텍스트 13종 길이 통계 (sample_size 행 기준)."""
    src, where_sql, params = _resolve_region(region)
    # uuid 기반 join — region 테이블도 uuid 컬럼 보유
    sub_sql = f"SELECT uuid FROM {src} {where_sql} LIMIT {int(sample_size)}"
    sub_rows = db.query(sub_sql, params)
    if not sub_rows:
        return PersonaTextStatsResponse(region=region, sample_size=0, stats=[])

    # core text fields
    core_aggs = ", ".join(
        f"MIN(LENGTH({f})) AS {f}_min, "
        f"AVG(LENGTH({f})) AS {f}_avg, "
        f"QUANTILE_CONT(LENGTH({f}), 0.5) AS {f}_p50, "
        f"QUANTILE_CONT(LENGTH({f}), 0.9) AS {f}_p90, "
        f"MAX(LENGTH({f})) AS {f}_max"
        for f in _TEXT_FIELDS_CORE
    )
    core_row = db.query_dicts(
        f"""
        WITH s AS ({sub_sql})
        SELECT {core_aggs}
        FROM persona_core c JOIN s USING (uuid)
        """,
        params,
    )[0]

    # long text fields (persona_text)
    long_aggs = ", ".join(
        f"MIN(LENGTH({f})) AS {f}_min, "
        f"AVG(LENGTH({f})) AS {f}_avg, "
        f"QUANTILE_CONT(LENGTH({f}), 0.5) AS {f}_p50, "
        f"QUANTILE_CONT(LENGTH({f}), 0.9) AS {f}_p90, "
        f"MAX(LENGTH({f})) AS {f}_max"
        for f in _TEXT_FIELDS_LONG
    )
    long_row = db.query_dicts(
        f"""
        WITH s AS ({sub_sql})
        SELECT {long_aggs}
        FROM persona_text t JOIN s USING (uuid)
        """,
        params,
    )[0]

    stats: list[TextStat] = []
    for f in _TEXT_FIELDS_CORE:
        stats.append(
            TextStat(
                field=f,
                min=int(core_row[f"{f}_min"] or 0),
                avg=round(float(core_row[f"{f}_avg"] or 0), 2),
                p50=int(core_row[f"{f}_p50"] or 0),
                p90=int(core_row[f"{f}_p90"] or 0),
                max=int(core_row[f"{f}_max"] or 0),
            )
        )
    for f in _TEXT_FIELDS_LONG:
        stats.append(
            TextStat(
                field=f,
                min=int(long_row[f"{f}_min"] or 0),
                avg=round(float(long_row[f"{f}_avg"] or 0), 2),
                p50=int(long_row[f"{f}_p50"] or 0),
                p90=int(long_row[f"{f}_p90"] or 0),
                max=int(long_row[f"{f}_max"] or 0),
            )
        )
    return PersonaTextStatsResponse(
        region=region, sample_size=len(sub_rows), stats=stats
    )


@router.get("/api/personas/{uuid}", response_model=PersonaDetail)
def detail(uuid: str) -> PersonaDetail:
    """단일 페르소나 전체 필드 (core + text 조인)."""
    if len(uuid) != 32 or not all(c in "0123456789abcdef" for c in uuid.lower()):
        raise HTTPException(status_code=400, detail="uuid must be 32-char hex")

    rows = db.query_dicts(
        """
        SELECT
            c.uuid,
            c.persona, c.cultural_background, c.skills_and_expertise,
            c.skills_and_expertise_list, c.hobbies_and_interests,
            c.hobbies_and_interests_list, c.career_goals_and_ambitions,
            c.sex, c.age, c.marital_status, c.military_status, c.family_type,
            c.housing_type, c.education_level, c.bachelors_field, c.occupation,
            c.district, c.province, c.country,
            t.professional_persona, t.sports_persona, t.arts_persona,
            t.travel_persona, t.culinary_persona, t.family_persona
        FROM persona_core c
        LEFT JOIN persona_text t USING (uuid)
        WHERE c.uuid = ?
        """,
        [uuid],
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"persona not found: {uuid}")
    r = rows[0]
    # *_list 필드 파싱 (Python list repr 문자열 → list[str])
    r["skills_and_expertise_list"] = db.parse_list_field(r.get("skills_and_expertise_list"))
    r["hobbies_and_interests_list"] = db.parse_list_field(r.get("hobbies_and_interests_list"))
    return PersonaDetail(**r)
