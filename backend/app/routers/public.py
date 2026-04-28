"""Public read-only API + community write. 인증 없음 (cookie 기반 익명).

write (POST/PUT/DELETE) 는 cookie 동의 필요 → 401 'consent required'.
banned user 는 모든 write 401.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, status

from ..deps import (
    ANON_COOKIE_NAME,
    get_blackout_status,
    get_current_user,
    limiter,
    require_active_user,
)
from ..schemas.public_dto import (
    AnonUserDTO,
    BlackoutMetaDTO,
    BoardTopicDetailDTO,
    BoardTopicDTO,
    BoardTopicListResponseDTO,
    CommentCreateRequestDTO,
    CommentDTO,
    CommentListResponseDTO,
    CommentUpdateRequestDTO,
    CreateTopicRequestDTO,
    KGSubgraphDTO,
    PersonaSampleDTO,
    PollPointDTO,
    PollTrajectoryResponseDTO,
    PredictionPointDTO,
    PredictionTrajectoryResponseDTO,
    RegionDTO,
    RegionSummaryDTO,
    ReportRequestDTO,
    ScenarioDTO,
    ScenarioOutcomeDTO,
    ScenarioOutcomeResponseDTO,
    UpdateNicknameRequestDTO,
    UpdateTopicRequestDTO,
)
from ..services import (
    anon_user_service,
    blackout_service,
    board_service,
    comment_service,
    kg_service,
    persona_service,
    poll_service,
    prediction_service,
    region_service,
    scenario_service,
)

logger = logging.getLogger("backend.public")

router = APIRouter(prefix="/api/v1", tags=["public"])


# ---------------------------------------------------------------------------
# Regions
# ---------------------------------------------------------------------------
@router.get("/regions", response_model=list[RegionDTO])
@limiter.limit("120/minute")
def list_regions(request: Request) -> list[RegionDTO]:
    return region_service.list_regions()


@router.get("/regions/{region_id}", response_model=RegionDTO)
@limiter.limit("120/minute")
def get_region(request: Request, region_id: str) -> RegionDTO:
    try:
        return region_service.get_region(region_id)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown region_id={region_id!r}")


@router.get("/regions/{region_id}/summary", response_model=RegionSummaryDTO)
@limiter.limit("60/minute")
def get_region_summary(request: Request, region_id: str) -> RegionSummaryDTO:
    try:
        return region_service.get_summary(region_id)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown region_id={region_id!r}")


# ---------------------------------------------------------------------------
# Personas
# ---------------------------------------------------------------------------
@router.get("/regions/{region_id}/personas", response_model=list[PersonaSampleDTO])
@limiter.limit("30/minute")
def sample_personas(
    request: Request,
    region_id: str,
    n: int = Query(default=30, ge=1, le=200),
    seed: Optional[int] = Query(default=None),
) -> list[PersonaSampleDTO]:
    return persona_service.sample(region_id=region_id, n=n, seed=seed)


# ---------------------------------------------------------------------------
# Polls + Predictions (region-level latest) — wrapped with blackout meta
# ---------------------------------------------------------------------------
def _blackout_meta(region_id: str) -> BlackoutMetaDTO:
    m = get_blackout_status(region_id)
    return BlackoutMetaDTO(
        in_blackout=m.in_blackout,
        end_date=m.end_date,
        hides_ai=m.hides_ai,
        region_id=m.region_id,
    )


@router.get(
    "/regions/{region_id}/poll-trajectory",
    response_model=PollTrajectoryResponseDTO,
)
@limiter.limit("60/minute")
def region_poll_trajectory(
    request: Request,
    region_id: str,
    scenario_id: Optional[str] = Query(default=None),
) -> PollTrajectoryResponseDTO:
    meta = _blackout_meta(region_id)
    if meta.in_blackout and meta.hides_ai:
        return PollTrajectoryResponseDTO(data=[], blackout=meta)
    return PollTrajectoryResponseDTO(
        data=poll_service.get_trajectory(region_id, scenario_id),
        blackout=meta,
    )


@router.get(
    "/regions/{region_id}/prediction-trajectory",
    response_model=PredictionTrajectoryResponseDTO,
)
@limiter.limit("60/minute")
def region_prediction_trajectory(
    request: Request,
    region_id: str,
    scenario_id: Optional[str] = Query(default=None),
) -> PredictionTrajectoryResponseDTO:
    meta = _blackout_meta(region_id)
    if meta.in_blackout and meta.hides_ai:
        return PredictionTrajectoryResponseDTO(data=[], blackout=meta)
    return PredictionTrajectoryResponseDTO(
        data=prediction_service.get_trajectory(region_id, scenario_id),
        blackout=meta,
    )


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------
@router.get("/scenarios", response_model=list[ScenarioDTO])
@limiter.limit("60/minute")
def list_scenarios(request: Request) -> list[ScenarioDTO]:
    return scenario_service.list_scenarios()


@router.get("/scenarios/{scenario_id}", response_model=ScenarioDTO)
@limiter.limit("120/minute")
def get_scenario(request: Request, scenario_id: str) -> ScenarioDTO:
    try:
        return scenario_service.get_scenario(scenario_id)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown scenario_id={scenario_id!r}")


@router.get(
    "/scenarios/{scenario_id}/outcome",
    response_model=ScenarioOutcomeResponseDTO,
)
@limiter.limit("120/minute")
def get_scenario_outcome(request: Request, scenario_id: str) -> ScenarioOutcomeResponseDTO:
    try:
        outcome = scenario_service.get_outcome(scenario_id)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown scenario_id={scenario_id!r}")
    meta = _blackout_meta(outcome.region_id)
    if meta.in_blackout and meta.hides_ai:
        return ScenarioOutcomeResponseDTO(data=None, blackout=meta)
    return ScenarioOutcomeResponseDTO(data=outcome, blackout=meta)


# ---------------------------------------------------------------------------
# KG subgraph
# ---------------------------------------------------------------------------
@router.get("/regions/{region_id}/kg-subgraph", response_model=KGSubgraphDTO)
@limiter.limit("30/minute")
def get_kg_subgraph(
    request: Request,
    region_id: str,
    cutoff: Optional[str] = Query(default=None, description="ISO datetime cutoff"),
    k: int = Query(default=25, ge=1, le=200),
) -> KGSubgraphDTO:
    return kg_service.get_subgraph(region_id=region_id, cutoff=cutoff, k=k)


# ===========================================================================
# Phase 5 — Anonymous user / Comments / Board
# ===========================================================================
def _anon_to_dto(u) -> AnonUserDTO:
    return AnonUserDTO(
        id=u.id, display_name=u.display_name, created_at=u.created_at,
        banned=u.banned,
    )


def _comment_to_dto(c, *, user_display_name: str) -> CommentDTO:
    return CommentDTO(
        id=c.id, scope_type=c.scope_type, scope_id=c.scope_id,
        parent_id=c.parent_id, user_id=c.user_id,
        user_display_name=user_display_name,
        body="" if c.deleted_at else c.body,
        created_at=c.created_at, updated_at=c.updated_at,
        edited_count=c.edited_count, deleted_at=c.deleted_at,
    )


def _topic_to_dto(t, *, user_display_name: str) -> BoardTopicDTO:
    return BoardTopicDTO(
        id=t.id, region_id=t.region_id, user_id=t.user_id,
        user_display_name=user_display_name,
        title=t.title, body="" if t.deleted_at else t.body,
        created_at=t.created_at, updated_at=t.updated_at,
        pinned=t.pinned, comment_count=t.comment_count,
        deleted_at=t.deleted_at,
    )


def _resolve_user_name(user_id: str) -> str:
    u = anon_user_service.get_user(user_id)
    return u.display_name if u else "(deleted)"


# ---- Anonymous user ----
@router.post("/users/anonymous", response_model=AnonUserDTO)
@limiter.limit("10/minute")
def create_anonymous_user(
    request: Request,
    response: Response,
    politikast_uid: Optional[str] = Cookie(default=None, alias=ANON_COOKIE_NAME),
) -> AnonUserDTO:
    user = anon_user_service.get_or_create_user(politikast_uid)
    response.set_cookie(
        key=ANON_COOKIE_NAME,
        value=user.id,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 365,  # 1 year
    )
    return _anon_to_dto(user)


@router.get("/users/me", response_model=Optional[AnonUserDTO])
def get_me(user=Depends(get_current_user)) -> Optional[AnonUserDTO]:
    if user is None:
        return None
    return _anon_to_dto(user)


@router.put("/users/me", response_model=AnonUserDTO)
@limiter.limit("10/minute")
def update_me(
    request: Request,
    payload: UpdateNicknameRequestDTO,
    user=Depends(require_active_user),
) -> AnonUserDTO:
    try:
        updated = anon_user_service.update_nickname(user.id, payload.display_name)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return _anon_to_dto(updated)


# ---- Comments ----
@router.get("/comments", response_model=CommentListResponseDTO)
@limiter.limit("60/minute")
def list_comments(
    request: Request,
    scope_type: str = Query(...),
    scope_id: str = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> CommentListResponseDTO:
    try:
        rows, total = comment_service.list_for_scope(
            scope_type, scope_id, page=page, page_size=page_size,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return CommentListResponseDTO(
        data=[_comment_to_dto(c, user_display_name=_resolve_user_name(c.user_id))
              for c in rows],
        page=page, page_size=page_size, total=total,
    )


@router.post(
    "/comments",
    response_model=CommentDTO,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
def create_comment(
    request: Request,
    payload: CommentCreateRequestDTO,
    user=Depends(require_active_user),
) -> CommentDTO:
    try:
        c = comment_service.create(
            user, scope_type=payload.scope_type, scope_id=payload.scope_id,
            body=payload.body, parent_id=payload.parent_id,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return _comment_to_dto(c, user_display_name=user.display_name)


@router.put("/comments/{comment_id}", response_model=CommentDTO)
@limiter.limit("5/minute")
def update_comment(
    request: Request,
    comment_id: str,
    payload: CommentUpdateRequestDTO,
    user=Depends(require_active_user),
) -> CommentDTO:
    try:
        c = comment_service.update(user, comment_id, payload.body)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "comment not found")
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return _comment_to_dto(c, user_display_name=user.display_name)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
def delete_comment(
    request: Request,
    comment_id: str,
    user=Depends(require_active_user),
):
    try:
        comment_service.soft_delete(user, comment_id)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "comment not found")
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/comments/{comment_id}/report",
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
def report_comment(
    request: Request,
    comment_id: str,
    payload: ReportRequestDTO,
    user=Depends(require_active_user),
):
    try:
        r = comment_service.report(user, comment_id, payload.reason)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "comment not found")
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return {"id": r.id, "status": r.status}


# ---- Board ----
@router.get("/board/topics", response_model=BoardTopicListResponseDTO)
@limiter.limit("60/minute")
def list_board_topics(
    request: Request,
    region_id: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> BoardTopicListResponseDTO:
    rows, total = board_service.list_topics(region_id, page=page, page_size=page_size)
    return BoardTopicListResponseDTO(
        data=[_topic_to_dto(t, user_display_name=_resolve_user_name(t.user_id))
              for t in rows],
        page=page, page_size=page_size, total=total,
    )


@router.post(
    "/board/topics",
    response_model=BoardTopicDTO,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("2/hour")
def create_board_topic(
    request: Request,
    payload: CreateTopicRequestDTO,
    user=Depends(require_active_user),
) -> BoardTopicDTO:
    try:
        t = board_service.create_topic(
            user, region_id=payload.region_id, title=payload.title, body=payload.body,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return _topic_to_dto(t, user_display_name=user.display_name)


@router.get(
    "/board/topics/{topic_id}",
    response_model=BoardTopicDetailDTO,
)
@limiter.limit("60/minute")
def get_board_topic(request: Request, topic_id: str) -> BoardTopicDetailDTO:
    t, comments = board_service.get_topic_with_first_comments(topic_id, n=20)
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "topic not found")
    return BoardTopicDetailDTO(
        topic=_topic_to_dto(t, user_display_name=_resolve_user_name(t.user_id)),
        first_comments=[
            _comment_to_dto(c, user_display_name=_resolve_user_name(c.user_id))
            for c in comments
        ],
    )


@router.put("/board/topics/{topic_id}", response_model=BoardTopicDTO)
@limiter.limit("5/minute")
def update_board_topic(
    request: Request,
    topic_id: str,
    payload: UpdateTopicRequestDTO,
    user=Depends(require_active_user),
) -> BoardTopicDTO:
    try:
        t = board_service.update_topic(user, topic_id, title=payload.title, body=payload.body)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "topic not found")
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return _topic_to_dto(t, user_display_name=user.display_name)


@router.delete("/board/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
def delete_board_topic(
    request: Request,
    topic_id: str,
    user=Depends(require_active_user),
):
    try:
        board_service.soft_delete_topic(user, topic_id)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "topic not found")
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/board/topics/{topic_id}/report",
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
def report_board_topic(
    request: Request,
    topic_id: str,
    payload: ReportRequestDTO,
    user=Depends(require_active_user),
):
    try:
        r = board_service.report_topic(user, topic_id, payload.reason)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "topic not found")
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return {"id": r.id, "status": r.status}


# ---------------------------------------------------------------------------
# Phase 6 — Scenario tree (Vertical Sankey)
# ---------------------------------------------------------------------------
import datetime as _dt  # noqa: E402

from ..schemas.public_dto import (  # noqa: E402
    BeamNodeDetailDTO,
    ScenarioTreeResponseDTO,
)

# DB session is optional — sqlalchemy may not be installed in slim dev envs.
try:  # pragma: no cover - import-side
    from ..db.session import get_session as _get_session  # type: ignore
    from ..services import scenario_tree_service as _scenario_tree_service  # type: ignore

    _SCENARIO_TREE_AVAILABLE = True
except Exception:  # noqa: BLE001
    _SCENARIO_TREE_AVAILABLE = False
    _get_session = None  # type: ignore
    _scenario_tree_service = None  # type: ignore


@router.get(
    "/regions/{region_id}/scenario-tree",
    response_model=ScenarioTreeResponseDTO,
)
@limiter.limit("60/minute")
async def get_scenario_tree(
    request: Request,
    region_id: str,
    as_of: Optional[str] = Query(default=None, description="ISO date (cutoff)"),
):
    if not _SCENARIO_TREE_AVAILABLE:
        return ScenarioTreeResponseDTO(
            data=None, blackout=BlackoutMetaDTO(region_id=region_id)
        )
    as_of_date: Optional[_dt.date] = None
    if as_of:
        try:
            as_of_date = _dt.date.fromisoformat(as_of)
        except ValueError:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"invalid as_of: {as_of!r}"
            )
    blackout = _blackout_meta(region_id)
    async for session in _get_session():  # type: ignore[union-attr]
        dto = await _scenario_tree_service.get_scenario_tree(  # type: ignore[union-attr]
            session, region_id, as_of=as_of_date
        )
        break
    return ScenarioTreeResponseDTO(data=dto, blackout=blackout)


@router.get(
    "/regions/{region_id}/scenario-tree/{tree_id}/nodes/{node_id}",
    response_model=BeamNodeDetailDTO,
)
@limiter.limit("120/minute")
async def get_scenario_tree_node(
    request: Request,
    region_id: str,
    tree_id: str,
    node_id: str,
):
    if not _SCENARIO_TREE_AVAILABLE:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "scenario tree service unavailable",
        )
    async for session in _get_session():  # type: ignore[union-attr]
        detail = await _scenario_tree_service.get_node_detail(  # type: ignore[union-attr]
            session, region_id, tree_id, node_id
        )
        break
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "node not found")
    return detail


__all__ = ["router"]
