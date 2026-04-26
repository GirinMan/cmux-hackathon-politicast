"""/api/regions + /api/regions/five + /api/occupations."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

import db
from models import (
    FiveRegionItem,
    FiveRegionsResponse,
    OccupationMajorItem,
    OccupationMajorResponse,
    OccupationItem,
    OccupationsResponse,
    ProvinceCount,
    RegionsResponse,
)

router = APIRouter(tags=["regions"])


OCCUPATION_MAJOR_CASE = """
CASE
    WHEN occupation = '무직' OR occupation LIKE '%은퇴%' THEN '무직·은퇴·기타'
    WHEN occupation LIKE '%장교%' OR occupation LIKE '%부사관%' OR occupation LIKE '%군인%' THEN '군인'
    WHEN occupation LIKE '%관리자%' OR occupation LIKE '%고위 임원%' OR occupation LIKE '%경영자%' THEN '관리자'
    WHEN occupation LIKE '%전문가%' OR occupation LIKE '%기술자%' OR occupation LIKE '%연구원%'
      OR occupation LIKE '%교사%' OR occupation LIKE '%강사%' OR occupation LIKE '%간호사%'
      OR occupation LIKE '%간호조무사%' OR occupation LIKE '%사회복지사%' OR occupation LIKE '%프로그래머%'
      OR occupation LIKE '%데이터 분석가%' OR occupation LIKE '%변호사%' OR occupation LIKE '%디자이너%'
      OR occupation LIKE '%상담 전문가%' OR occupation LIKE '%컨설턴트%' OR occupation LIKE '%위생사%' THEN '전문가 및 관련 종사자'
    WHEN occupation LIKE '%사무원%' OR occupation LIKE '%비서%' OR occupation LIKE '%경리%'
      OR occupation LIKE '%회계%' OR occupation LIKE '%행정%' OR occupation LIKE '%편집 사무%' THEN '사무 종사자'
    WHEN occupation LIKE '%판매원%' OR occupation LIKE '%영업원%' OR occupation LIKE '%판매%'
      OR occupation LIKE '%영업 관리%' OR occupation LIKE '%상점%' OR occupation LIKE '%노점%' THEN '판매 종사자'
    WHEN occupation LIKE '%조리사%' OR occupation LIKE '%서비스 종사원%' OR occupation LIKE '%보육%'
      OR occupation LIKE '%돌봄%' OR occupation LIKE '%요양%' OR occupation LIKE '%음료 서비스%'
      OR occupation LIKE '%바텐더%' OR occupation LIKE '%119 구조대원%' OR occupation LIKE '%경찰관%' THEN '서비스 종사자'
    WHEN occupation LIKE '%농업%' OR occupation LIKE '%어업%' OR occupation LIKE '%축산%' OR occupation LIKE '%임업%' THEN '농림어업 숙련 종사자'
    WHEN occupation LIKE '%설치%' OR occupation LIKE '%정비%' OR occupation LIKE '%수리%'
      OR occupation LIKE '%용접%' OR occupation LIKE '%배관공%' OR occupation LIKE '%건립원%'
      OR occupation LIKE '%금형원%' OR occupation LIKE '%기능 관련%' THEN '기능원 및 관련 기능 종사자'
    WHEN occupation LIKE '%운전원%' OR occupation LIKE '%조작원%' OR occupation LIKE '%운송%'
      OR occupation LIKE '%지게차%' OR occupation LIKE '%장비 조작%' OR occupation LIKE '%택배원%'
      OR occupation LIKE '%우편집배원%' THEN '장치·기계조작 및 조립 종사자'
    WHEN occupation LIKE '%단순%' OR occupation LIKE '%청소원%' OR occupation LIKE '%경비원%'
      OR occupation LIKE '%하역%' OR occupation LIKE '%포장원%' OR occupation LIKE '%도우미%'
      OR occupation LIKE '%주방 보조원%' OR occupation LIKE '%매장 정리원%' THEN '단순노무 종사자'
    ELSE '무직·은퇴·기타'
END
"""


@router.get("/api/regions", response_model=RegionsResponse)
def regions() -> RegionsResponse:
    """17 시도(province) 분포."""
    total_row = db.query("SELECT COUNT(*) FROM persona_core")[0]
    total = int(total_row[0])
    rows = db.query(
        "SELECT province, COUNT(*) AS c FROM persona_core GROUP BY province ORDER BY c DESC"
    )
    provinces = [
        ProvinceCount(province=str(p), count=int(c), pct=round(c / total * 100, 3))
        for (p, c) in rows
    ]
    return RegionsResponse(total=total, provinces=provinces)


def _count_for_region(key: str, info: dict) -> tuple[int, bool]:
    """region key → (count, available)."""
    return db.count_region(key)


@router.get("/api/regions/five", response_model=FiveRegionsResponse)
def five_regions() -> FiveRegionsResponse:
    """PolitiKAST contract regions 매칭 행수."""
    items: list[FiveRegionItem] = []
    for key, info in db.FIVE_REGIONS.items():
        count, avail = _count_for_region(key, info)
        items.append(
            FiveRegionItem(
                key=key,
                label_ko=info["label_ko"],
                label_en=info["label_en"],
                province=info.get("province"),
                district=info.get("district"),
                table=info.get("table"),
                count=count,
                available=avail,
            )
        )
    return FiveRegionsResponse(regions=items)


@router.get("/api/occupations", response_model=OccupationsResponse)
def occupations(
    region: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=200),
) -> OccupationsResponse:
    """직업 top-N. region 필터 가능."""
    if region is None:
        src = "persona_core"
        where_sql, params = "", []
    else:
        if region not in db.FIVE_REGIONS:
            raise HTTPException(status_code=400, detail=f"unknown region key: {region}")
        source = db.resolve_region_source(region)
        src, where_sql, params = source.table, source.where_sql, source.params

    distinct = db.query(
        f"SELECT COUNT(DISTINCT occupation) FROM {src} {where_sql}", params
    )[0][0]
    rows = db.query(
        f"""
        SELECT occupation, COUNT(*) AS c
        FROM {src} {where_sql}
        GROUP BY occupation
        ORDER BY c DESC
        LIMIT {int(limit)}
        """,
        params,
    )
    top = [OccupationItem(occupation=str(o), count=int(c)) for (o, c) in rows]
    return OccupationsResponse(region=region, total_distinct=int(distinct), top=top)


@router.get("/api/occupations/major", response_model=OccupationMajorResponse)
def occupation_major(region: str | None = Query(default=None)) -> OccupationMajorResponse:
    """KSCO-like 11 major occupation groups using transparent string heuristics."""
    try:
        source = db.resolve_region_source(region)
    except db.UnknownRegionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    total = int(
        db.query(
            f"SELECT COUNT(*) FROM {source.table} {source.where_sql}",
            source.params,
        )[0][0]
    )
    rows = db.query(
        f"""
        SELECT major, COUNT(*) AS c
        FROM (
            SELECT {OCCUPATION_MAJOR_CASE} AS major
            FROM {source.table} {source.where_sql}
        )
        GROUP BY major
        ORDER BY c DESC
        """,
        source.params,
    )
    groups = [
        OccupationMajorItem(
            major=str(major),
            count=int(count),
            pct=round((int(count) / total) * 100, 3) if total > 0 else 0.0,
        )
        for major, count in rows
    ]
    return OccupationMajorResponse(
        region=region,
        total=total,
        groups=groups,
        meta={
            "source": "heuristic_string_rollup",
            "target_taxonomy": "KSCO major groups (11)",
            "note": "Raw occupation remains available at /api/occupations.",
        },
    )
