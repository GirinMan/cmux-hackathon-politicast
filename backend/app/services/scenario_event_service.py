"""Phase 6 — ScenarioEvent service.

KG/LLM/custom 통합 이벤트 레지스트리. EventProposer.composite 가 DB 의 active row
들을 그대로 candidate event 로 emit. Admin UI 에서 custom row 만 사용자 등록 —
KG/LLM source 는 보통 build pipeline 이 채운다.
"""
from __future__ import annotations

import datetime as dt
import logging
import uuid
from typing import Any, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import ScenarioEvent as ScenarioEventORM
from ..schemas.admin_dto import (
    ScenarioEventCreateRequestDTO,
    ScenarioEventDTO,
    ScenarioEventListResponseDTO,
)

logger = logging.getLogger("backend.scenario_event")

VALID_SOURCES = {"kg_confirmed", "llm_hypothetical", "custom"}


def _orm_to_dto(orm: ScenarioEventORM) -> ScenarioEventDTO:
    return ScenarioEventDTO(
        id=str(orm.id),
        region_id=orm.region_id,
        source=orm.source,
        occurs_at=orm.occurs_at.isoformat() if orm.occurs_at else "",
        description=orm.description,
        candidate_patches=list(orm.candidate_patches or []),
        event_patches=list(orm.event_patches or []),
        prior_p=float(orm.prior_p),
        event_metadata=orm.event_metadata,
        created_at=orm.created_at.isoformat() if orm.created_at else "",
        created_by=orm.created_by,
        is_active=bool(orm.is_active),
    )


async def list_events(
    session: AsyncSession,
    *,
    region_id: Optional[str] = None,
    source: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    only_active: bool = True,
) -> ScenarioEventListResponseDTO:
    page = max(1, page)
    page_size = max(1, min(500, page_size))

    base = select(ScenarioEventORM)
    count = select(func.count(ScenarioEventORM.id))
    if region_id:
        base = base.where(ScenarioEventORM.region_id == region_id)
        count = count.where(ScenarioEventORM.region_id == region_id)
    if source:
        if source not in VALID_SOURCES:
            raise ValueError(f"invalid source: {source!r}")
        base = base.where(ScenarioEventORM.source == source)
        count = count.where(ScenarioEventORM.source == source)
    if only_active:
        base = base.where(ScenarioEventORM.is_active.is_(True))
        count = count.where(ScenarioEventORM.is_active.is_(True))

    total = int((await session.execute(count)).scalar() or 0)
    rows = (
        await session.execute(
            base.order_by(ScenarioEventORM.occurs_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return ScenarioEventListResponseDTO(
        data=[_orm_to_dto(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


async def create_event(
    session: AsyncSession,
    payload: ScenarioEventCreateRequestDTO,
    *,
    created_by: Optional[str] = None,
) -> ScenarioEventDTO:
    if payload.source not in VALID_SOURCES:
        raise ValueError(f"invalid source: {payload.source!r}")
    occurs_at = dt.datetime.fromisoformat(payload.occurs_at)
    if occurs_at.tzinfo is None:
        occurs_at = occurs_at.replace(tzinfo=dt.timezone.utc)
    orm = ScenarioEventORM(
        id=uuid.uuid4(),
        region_id=payload.region_id,
        source=payload.source,
        occurs_at=occurs_at,
        description=payload.description,
        candidate_patches=list(payload.candidate_patches),
        event_patches=list(payload.event_patches),
        prior_p=float(payload.prior_p),
        event_metadata=payload.event_metadata,
        created_by=created_by,
        is_active=True,
    )
    session.add(orm)
    await session.commit()
    await session.refresh(orm)
    return _orm_to_dto(orm)


async def delete_event(session: AsyncSession, event_id: str) -> bool:
    try:
        eid = uuid.UUID(event_id)
    except ValueError:
        return False
    res = await session.execute(
        delete(ScenarioEventORM).where(ScenarioEventORM.id == eid)
    )
    await session.commit()
    return (res.rowcount or 0) > 0


__all__ = ["create_event", "delete_event", "list_events"]
