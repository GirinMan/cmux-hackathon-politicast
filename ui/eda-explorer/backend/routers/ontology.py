"""/api/ontology/graph — categorical ontology graph for PolitiKAST frontend."""
from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter, HTTPException, Query

import db
from models import (
    OntologyCategory,
    OntologyEdge,
    OntologyGraphMeta,
    OntologyGraphResponse,
    OntologyNode,
)

router = APIRouter(tags=["ontology"])


DIMENSIONS = [
    "region",
    "province",
    "district",
    "age_group",
    "sex",
    "education_level",
    "occupation",
    "family_type",
    "housing_type",
]

CATEGORY_STYLE: dict[str, dict[str, str]] = {
    "region": {"label": "Region", "symbol": "roundRect", "color": "#059669"},
    "province": {"label": "Province", "symbol": "rect", "color": "#2563eb"},
    "district": {"label": "District", "symbol": "diamond", "color": "#0891b2"},
    "age_group": {"label": "AgeGroup", "symbol": "circle", "color": "#f59e0b"},
    "sex": {"label": "Sex", "symbol": "triangle", "color": "#ec4899"},
    "education_level": {
        "label": "EducationLevel",
        "symbol": "roundRect",
        "color": "#8b5cf6",
    },
    "occupation": {"label": "Occupation", "symbol": "pin", "color": "#ef4444"},
    "family_type": {"label": "FamilyType", "symbol": "circle", "color": "#14b8a6"},
    "housing_type": {"label": "HousingType", "symbol": "diamond", "color": "#64748b"},
}

AGE_BUCKET_SQL = """CASE
    WHEN age < 30 THEN '19-29'
    WHEN age < 40 THEN '30-39'
    WHEN age < 50 THEN '40-49'
    WHEN age < 60 THEN '50-59'
    WHEN age < 70 THEN '60-69'
    WHEN age < 80 THEN '70-79'
    WHEN age < 90 THEN '80-89'
    ELSE '90+'
END"""


def _clean_value(value: Any) -> str:
    text = "미상" if value is None else str(value).strip()
    return text or "미상"


def _node_id(kind: str, label: str) -> str:
    if kind == "region" and label == "root":
        return "root"
    digest = hashlib.sha1(label.encode("utf-8")).hexdigest()[:12]
    return f"{kind}:{digest}"


def _pct(count: int, total: int) -> float:
    return round((count / total) * 100, 3) if total > 0 else 0.0


class GraphBuilder:
    def __init__(self, total: int) -> None:
        self.total = total
        self.nodes: dict[str, OntologyNode] = {}
        self.edges: list[OntologyEdge] = []
        self._edge_keys: set[tuple[str, str, str]] = set()

    def add_node(
        self,
        kind: str,
        label: str,
        count: int,
        *,
        node_id: str | None = None,
    ) -> str:
        clean = _clean_value(label)
        style = CATEGORY_STYLE[kind]
        nid = node_id or _node_id(kind, clean)
        existing = self.nodes.get(nid)
        if existing is not None:
            if count > existing.count:
                existing.count = int(count)
                existing.pct = _pct(int(count), self.total)
            return nid
        self.nodes[nid] = OntologyNode(
            id=nid,
            label=clean,
            kind=kind,
            category=kind,
            count=int(count),
            pct=_pct(int(count), self.total),
            symbol=style["symbol"],
            color=style["color"],
        )
        return nid

    def add_edge(
        self,
        source: str,
        target: str,
        label: str,
        kind: str,
        count: int,
    ) -> None:
        if source == target or source not in self.nodes or target not in self.nodes:
            return
        key = (source, target, kind)
        if key in self._edge_keys:
            return
        self._edge_keys.add(key)
        self.edges.append(
            OntologyEdge(
                source=source,
                target=target,
                label=label,
                kind=kind,
                count=int(count),
                weight=round(int(count) / self.total, 6) if self.total > 0 else 0.0,
            )
        )


def _value_expr(column: str) -> str:
    return f"COALESCE(NULLIF(TRIM(CAST({column} AS VARCHAR)), ''), '미상')"


def _group_counts(
    source: db.RegionSource,
    expression: str,
    *,
    limit: int,
    min_count: int,
) -> list[tuple[str, int]]:
    rows = db.query(
        f"""
        SELECT {expression} AS value, COUNT(*) AS c
        FROM {source.table} {source.where_sql}
        GROUP BY value
        HAVING COUNT(*) >= ?
        ORDER BY c DESC
        LIMIT {int(limit)}
        """,
        [*source.params, min_count],
    )
    return [(_clean_value(value), int(count)) for value, count in rows]


def _pair_counts(
    source: db.RegionSource,
    left_expr: str,
    right_expr: str,
    *,
    limit: int,
    min_count: int,
) -> list[tuple[str, str, int]]:
    rows = db.query(
        f"""
        SELECT {left_expr} AS left_value, {right_expr} AS right_value, COUNT(*) AS c
        FROM {source.table} {source.where_sql}
        GROUP BY left_value, right_value
        HAVING COUNT(*) >= ?
        ORDER BY c DESC
        LIMIT {int(limit)}
        """,
        [*source.params, min_count],
    )
    return [
        (_clean_value(left), _clean_value(right), int(count))
        for left, right, count in rows
    ]


def _categories() -> list[OntologyCategory]:
    return [
        OntologyCategory(name=key, label=style["label"], symbol=style["symbol"], color=style["color"])
        for key, style in CATEGORY_STYLE.items()
    ]


@router.get("/api/ontology/graph", response_model=OntologyGraphResponse)
def ontology_graph(
    region: str | None = Query(
        default=None,
        description="contract region id, province:<id>, or omit",
    ),
    cluster_limit: int = Query(default=12, ge=3, le=50),
    occupation_limit: int = Query(default=12, ge=3, le=50),
    min_count: int = Query(default=1, ge=1),
) -> OntologyGraphResponse:
    """Return a SQL-aggregated categorical ontology graph."""
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
    builder = GraphBuilder(total)
    root_label = "All Personas" if region is None else "Selected Region"
    root = builder.add_node("region", root_label, total, node_id="root")

    if total == 0:
        return OntologyGraphResponse(
            region=region,
            total=0,
            categories=_categories(),
            nodes=list(builder.nodes.values()),
            edges=[],
            meta=OntologyGraphMeta(
                cluster_source="raw_categorical_sql",
                dimensions=DIMENSIONS,
            ),
        )

    if region is not None and source.info is not None:
        label = str(source.info.get("label_ko") or source.info.get("label") or region)
        anchor = builder.add_node("region", label, total, node_id=f"region:{region}")
        builder.add_edge(root, anchor, "contains", "membership", total)
    else:
        anchor = root
        for key, info in db.FIVE_REGIONS.items():
            count, available = db.count_region(key)
            if not available or count < min_count:
                continue
            label = str(info.get("label_ko") or key)
            region_node = builder.add_node("region", label, count, node_id=f"region:{key}")
            builder.add_edge(root, region_node, "contains", "membership", count)

    node_lookup: dict[tuple[str, str], str] = {}

    def add_dimension(kind: str, expression: str, limit: int) -> None:
        for label, count in _group_counts(
            source,
            expression,
            limit=limit,
            min_count=min_count,
        ):
            node_id = builder.add_node(kind, label, count)
            node_lookup[(kind, label)] = node_id
            builder.add_edge(anchor, node_id, kind, "membership", count)

    add_dimension("province", _value_expr("province"), cluster_limit)
    add_dimension("age_group", AGE_BUCKET_SQL, cluster_limit)
    add_dimension("sex", _value_expr("sex"), cluster_limit)
    add_dimension("education_level", _value_expr("education_level"), cluster_limit)
    add_dimension("occupation", _value_expr("occupation"), occupation_limit)
    add_dimension("family_type", _value_expr("family_type"), cluster_limit)
    add_dimension("housing_type", _value_expr("housing_type"), cluster_limit)

    province_district = _pair_counts(
        source,
        _value_expr("province"),
        _value_expr("district"),
        limit=cluster_limit,
        min_count=min_count,
    )
    for province, district, count in province_district:
        province_id = node_lookup.get(("province", province))
        district_id = builder.add_node("district", district, count)
        node_lookup[("district", district)] = district_id
        builder.add_edge(province_id or anchor, district_id, "contains", "membership", count)

    co_occurrence_specs = [
        ("sex", _value_expr("sex"), "age_group", AGE_BUCKET_SQL, "age mix"),
        (
            "education_level",
            _value_expr("education_level"),
            "occupation",
            _value_expr("occupation"),
            "work mix",
        ),
        (
            "family_type",
            _value_expr("family_type"),
            "housing_type",
            _value_expr("housing_type"),
            "household mix",
        ),
    ]
    for left_kind, left_expr, right_kind, right_expr, label in co_occurrence_specs:
        for left, right, count in _pair_counts(
            source,
            left_expr,
            right_expr,
            limit=max(cluster_limit, occupation_limit) * 4,
            min_count=min_count,
        ):
            left_id = node_lookup.get((left_kind, left))
            right_id = node_lookup.get((right_kind, right))
            if left_id and right_id:
                builder.add_edge(left_id, right_id, label, "co_occurrence", count)

    return OntologyGraphResponse(
        region=region,
        total=total,
        categories=_categories(),
        nodes=list(builder.nodes.values()),
        edges=builder.edges,
        meta=OntologyGraphMeta(
            cluster_source="raw_categorical_sql",
            dimensions=DIMENSIONS,
        ),
    )
