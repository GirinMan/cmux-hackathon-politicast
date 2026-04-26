"""/api/demographics — age/sex/marital/education 분포."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

import db
from models import AgeBucket, CountBucket, DemographicsResponse

router = APIRouter(tags=["demographics"])


# 학력 정렬 순서
_EDUCATION_ORDER = [
    "무학",
    "초등학교",
    "중학교",
    "고등학교",
    "2~3년제 전문대학",
    "4년제 대학교",
    "대학원",
]

# 결혼상태 정렬 (빈도순)
_MARITAL_ORDER = ["배우자있음", "미혼", "사별", "이혼"]


@router.get("/api/demographics", response_model=DemographicsResponse)
def demographics(
    region: str | None = Query(default=None, description="contract region id or omit"),
) -> DemographicsResponse:
    """region 옵션 필터 적용 후 age/sex/marital/education 분포 반환."""
    try:
        source = db.resolve_region_source(region)
    except db.UnknownRegionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    src = source.table
    where_sql, params = source.where_sql, source.params

    total_row = db.query(f"SELECT COUNT(*) FROM {src} {where_sql}", params)[0]
    total = int(total_row[0])
    if total == 0:
        return DemographicsResponse(
            region=region,
            total=0,
            age_buckets=[],
            age_stats={"min": 0.0, "avg": 0.0, "median": 0.0, "max": 0.0},
            sex=[],
            marital_status=[],
            education_level=[],
        )

    # age stats
    age_stats_row = db.query(
        f"SELECT MIN(age), AVG(age), MEDIAN(age), MAX(age) FROM {src} {where_sql}",
        params,
    )[0]
    age_stats = {
        "min": float(age_stats_row[0] or 0),
        "avg": float(age_stats_row[1] or 0),
        "median": float(age_stats_row[2] or 0),
        "max": float(age_stats_row[3] or 0),
    }

    # age buckets (10년 단위)
    age_bucket_rows = db.query(
        f"""
        SELECT bucket, COUNT(*) AS c
        FROM (
            SELECT CASE
                WHEN age < 30 THEN '19-29'
                WHEN age < 40 THEN '30-39'
                WHEN age < 50 THEN '40-49'
                WHEN age < 60 THEN '50-59'
                WHEN age < 70 THEN '60-69'
                WHEN age < 80 THEN '70-79'
                WHEN age < 90 THEN '80-89'
                ELSE '90+'
            END AS bucket
            FROM {src} {where_sql}
        )
        GROUP BY bucket
        ORDER BY bucket
        """,
        params,
    )
    age_buckets = [
        AgeBucket(bucket=str(b), count=int(c), pct=round(c / total * 100, 3))
        for (b, c) in age_bucket_rows
    ]

    # sex
    sex_rows = db.query(
        f"SELECT sex, COUNT(*) FROM {src} {where_sql} GROUP BY sex ORDER BY 2 DESC",
        params,
    )
    sex = [
        CountBucket(value=str(v), count=int(c), pct=round(c / total * 100, 3))
        for (v, c) in sex_rows
    ]

    # marital_status — enum 순서 고정
    marital_rows = dict(
        db.query(
            f"SELECT marital_status, COUNT(*) FROM {src} {where_sql} GROUP BY marital_status",
            params,
        )
    )
    marital = [
        CountBucket(
            value=k,
            count=int(marital_rows.get(k, 0)),
            pct=round(int(marital_rows.get(k, 0)) / total * 100, 3),
        )
        for k in _MARITAL_ORDER
        if k in marital_rows
    ]
    # 잔여 enum (변경 대비)
    for k, v in marital_rows.items():
        if k not in _MARITAL_ORDER:
            marital.append(
                CountBucket(value=str(k), count=int(v), pct=round(v / total * 100, 3))
            )

    # education — 학력 순서 강제
    edu_rows = dict(
        db.query(
            f"SELECT education_level, COUNT(*) FROM {src} {where_sql} GROUP BY education_level",
            params,
        )
    )
    education = [
        CountBucket(
            value=k,
            count=int(edu_rows.get(k, 0)),
            pct=round(int(edu_rows.get(k, 0)) / total * 100, 3),
        )
        for k in _EDUCATION_ORDER
        if k in edu_rows
    ]
    for k, v in edu_rows.items():
        if k not in _EDUCATION_ORDER:
            education.append(
                CountBucket(value=str(k), count=int(v), pct=round(v / total * 100, 3))
            )

    return DemographicsResponse(
        region=region,
        total=total,
        age_buckets=age_buckets,
        age_stats=age_stats,
        sex=sex,
        marital_status=marital,
        education_level=education,
    )
