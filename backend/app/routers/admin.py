"""Admin router — JWT bearer auth + 관리자 엔드포인트.

엔드포인트:
  POST /admin/api/auth/login              — 사용자/비밀번호 → JWT
  GET  /admin/api/auth/me                 — 토큰 검증
  GET  /admin/api/sim-runs                — 최근 sim 실행 요약
  GET  /admin/api/data-sources            — data_sources.json registry
  GET  /admin/api/unresolved-entities     — 미해결 엔티티 큐
  POST /admin/api/unresolved-entities/resolve — 수동 매핑 적용 (entity_alias INSERT)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from ..settings import Settings, get_settings
from ..services import auth_service
from ..schemas.admin_dto import AdminScenarioStatusDTO  # noqa: F401 — re-used by future endpoints

logger = logging.getLogger("backend.admin")

router = APIRouter(prefix="/admin/api", tags=["admin"])


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    username: str


class MeResponse(BaseModel):
    username: str
    role: str = "admin"
    exp: int


class SimRunSummaryDTO(BaseModel):
    run_id: str
    region_id: str
    scenario_id: Optional[str] = None
    status: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    mae: Optional[float] = None


class UnresolvedEntityDTO(BaseModel):
    run_id: str
    alias: str
    kind: str
    context: Optional[str] = None
    suggested_id: Optional[str] = None
    status: str = "pending"


class ResolveEntityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    alias: str
    kind: str
    canonical_id: str


class ResolveEntityResponse(BaseModel):
    ok: bool
    alias: str
    kind: str
    canonical_id: str


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------
def get_current_admin(
    authorization: Optional[str] = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization[7:].strip()
    try:
        payload = auth_service.verify_token(token, settings)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token expired",
                            headers={"WWW-Authenticate": "Bearer"})
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"invalid token: {exc}",
                            headers={"WWW-Authenticate": "Bearer"})
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="not an admin")
    return payload


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
@router.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest, settings: Settings = Depends(get_settings)) -> LoginResponse:
    user = auth_service.authenticate(req.username, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid credentials")
    token, ttl = auth_service.issue_token(user.username, settings)
    return LoginResponse(
        access_token=token, expires_in=ttl, username=user.username,
    )


@router.get("/auth/me", response_model=MeResponse)
def me(payload: dict = Depends(get_current_admin)) -> MeResponse:
    return MeResponse(
        username=str(payload.get("sub") or ""),
        role=str(payload.get("role") or "admin"),
        exp=int(payload.get("exp") or 0),
    )


# ---------------------------------------------------------------------------
# Read-only admin endpoints (DuckDB / registry 기반)
# ---------------------------------------------------------------------------
def _duckdb(settings: Settings):
    import duckdb  # local import — backend test 시 무거운 의존성 회피.
    return duckdb.connect(str(settings.duckdb_path), read_only=False)


@router.get("/sim-runs", response_model=list[SimRunSummaryDTO])
def list_sim_runs(
    _: dict = Depends(get_current_admin),
    settings: Settings = Depends(get_settings),
    limit: int = 50,
) -> list[SimRunSummaryDTO]:
    """결과 스냅샷 디렉토리 + ingest_run 테이블에서 가장 최근 실행 모음."""
    rows: list[SimRunSummaryDTO] = []
    snap_dir: Path = settings.snapshots_dir
    if snap_dir.exists():
        for p in sorted(snap_dir.glob("*.json"))[-limit:]:
            try:
                blob = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            mae = (
                ((blob.get("meta") or {}).get("official_poll_validation") or {}).get("metrics") or {}
            ).get("mae")
            rows.append(
                SimRunSummaryDTO(
                    run_id=p.stem,
                    region_id=blob.get("region_id") or "?",
                    scenario_id=blob.get("scenario_id"),
                    status="completed",
                    started_at=(blob.get("meta") or {}).get("started_at"),
                    finished_at=(blob.get("meta") or {}).get("finished_at"),
                    mae=mae,
                )
            )
    return rows


@router.get("/data-sources")
def list_data_sources(
    _: dict = Depends(get_current_admin),
) -> dict[str, Any]:
    path = Path(__file__).resolve().parents[3] / "_workspace" / "data" / "registries" / "data_sources.json"
    if not path.exists():
        return {"version": "v1", "sources": {}}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/unresolved-entities", response_model=list[UnresolvedEntityDTO])
def list_unresolved(
    _: dict = Depends(get_current_admin),
    settings: Settings = Depends(get_settings),
    limit: int = 200,
) -> list[UnresolvedEntityDTO]:
    if not settings.duckdb_path.exists():
        return []
    con = _duckdb(settings)
    try:
        rs = con.execute(
            "SELECT run_id, alias, kind, context, suggested_id, status "
            "FROM unresolved_entity WHERE status = 'pending' LIMIT ?",
            (limit,),
        ).fetchall()
    except Exception:
        return []
    finally:
        con.close()
    return [
        UnresolvedEntityDTO(
            run_id=r[0], alias=r[1], kind=r[2], context=r[3], suggested_id=r[4],
            status=r[5] or "pending",
        )
        for r in rs
    ]


@router.post("/unresolved-entities/resolve", response_model=ResolveEntityResponse)
def resolve_unresolved(
    req: ResolveEntityRequest,
    _: dict = Depends(get_current_admin),
    settings: Settings = Depends(get_settings),
) -> ResolveEntityResponse:
    if not settings.duckdb_path.exists():
        raise HTTPException(status_code=404, detail="duckdb missing")
    con = _duckdb(settings)
    try:
        con.execute(
            "INSERT OR REPLACE INTO entity_alias "
            "(alias, kind, canonical_id, confidence, source, created_at) "
            "VALUES (?, ?, ?, 1.0, 'admin', CURRENT_TIMESTAMP::VARCHAR)",
            (req.alias, req.kind, req.canonical_id),
        )
        con.execute(
            "UPDATE unresolved_entity SET status = 'resolved' "
            "WHERE run_id = ? AND alias = ? AND kind = ?",
            (req.run_id, req.alias, req.kind),
        )
    finally:
        con.close()
    return ResolveEntityResponse(
        ok=True, alias=req.alias, kind=req.kind, canonical_id=req.canonical_id,
    )


# ===========================================================================
# Phase 5 — Community moderation endpoints
# ===========================================================================
from ..schemas.admin_dto import (  # noqa: E402
    AdminBoardTopicDTO,
    AdminCommentDTO,
    BanUserRequestDTO,
    ReportDTO,
    ResolveReportRequestDTO,
)
from ..services import board_service as _board_svc  # noqa: E402
from ..services import comment_service as _cmt_svc  # noqa: E402
from ..services import report_service as _rpt_svc  # noqa: E402


def _admin_comment(c) -> AdminCommentDTO:
    from ..services import anon_user_service as _au
    u = _au.get_user(c.user_id)
    return AdminCommentDTO(
        id=c.id, scope_type=c.scope_type, scope_id=c.scope_id,
        user_id=c.user_id,
        user_display_name=u.display_name if u else "(deleted)",
        body=c.body, created_at=c.created_at, edited_count=c.edited_count,
        deleted_at=c.deleted_at, deleted_by=c.deleted_by,
    )


def _admin_topic(t) -> AdminBoardTopicDTO:
    from ..services import anon_user_service as _au
    u = _au.get_user(t.user_id)
    return AdminBoardTopicDTO(
        id=t.id, region_id=t.region_id, user_id=t.user_id,
        user_display_name=u.display_name if u else "(deleted)",
        title=t.title, pinned=t.pinned, comment_count=t.comment_count,
        created_at=t.created_at, deleted_at=t.deleted_at, deleted_by=t.deleted_by,
    )


def _report_to_dto(r) -> ReportDTO:
    return ReportDTO(
        id=r.id, target_kind=r.target_kind, target_id=r.target_id,
        reporter_user_id=r.reporter_user_id, reason=r.reason,
        status=r.status, resolution=r.resolution,
        resolved_at=r.resolved_at, resolved_by=r.resolved_by,
        created_at=r.created_at,
    )


@router.get("/comments", response_model=list[AdminCommentDTO])
def admin_list_comments(
    _: dict = Depends(get_current_admin),
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
    limit: int = 100,
) -> list[AdminCommentDTO]:
    from ..services._community_store import get_store
    rows = list(get_store().comments.values())
    if scope_type:
        rows = [c for c in rows if c.scope_type == scope_type]
    if scope_id:
        rows = [c for c in rows if c.scope_id == scope_id]
    rows.sort(key=lambda c: c.created_at, reverse=True)
    return [_admin_comment(c) for c in rows[:limit]]


@router.delete("/comments/{comment_id}", status_code=204)
def admin_delete_comment(
    comment_id: str,
    _: dict = Depends(get_current_admin),
):
    try:
        _cmt_svc.admin_soft_delete(comment_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="comment not found")
    return None


@router.post("/board/topics/{topic_id}/pin", response_model=AdminBoardTopicDTO)
def admin_pin_topic(
    topic_id: str,
    pinned: bool = True,
    _: dict = Depends(get_current_admin),
) -> AdminBoardTopicDTO:
    try:
        t = _board_svc.pin_topic(topic_id, pinned=pinned)
    except KeyError:
        raise HTTPException(status_code=404, detail="topic not found")
    return _admin_topic(t)


@router.delete("/board/topics/{topic_id}", status_code=204)
def admin_delete_topic(
    topic_id: str,
    payload: dict = Depends(get_current_admin),
):
    from ..services._community_store import get_store
    store = get_store()
    if topic_id not in store.topics:
        raise HTTPException(status_code=404, detail="topic not found")
    store.soft_delete_topic(topic_id, by="admin")
    return None


@router.get("/reports", response_model=list[ReportDTO])
def admin_list_reports(
    _: dict = Depends(get_current_admin),
    status: Optional[str] = None,
) -> list[ReportDTO]:
    try:
        rows = _rpt_svc.list_reports(status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return [_report_to_dto(r) for r in rows]


@router.post("/reports/{report_id}/resolve", response_model=ReportDTO)
def admin_resolve_report(
    report_id: str,
    req: ResolveReportRequestDTO,
    payload: dict = Depends(get_current_admin),
) -> ReportDTO:
    admin_username = str(payload.get("sub") or "admin")
    try:
        r = _rpt_svc.resolve(
            report_id, resolution=req.resolution, admin_username=admin_username,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="report not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _report_to_dto(r)


@router.post("/users/{user_id}/ban")
def admin_ban_user(
    user_id: str,
    req: BanUserRequestDTO,
    payload: dict = Depends(get_current_admin),
):
    from ..services import anon_user_service as _au
    if _au.get_user(user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")
    admin_username = str(payload.get("sub") or "admin")
    u = _rpt_svc.ban_user_directly(
        user_id, admin_username=admin_username, reason=req.reason,
    )
    return {"id": u.id, "banned": u.banned, "banned_at": u.banned_at}


# ---------------------------------------------------------------------------
# Phase 6 — scenario tree / calibration / scenario_event
# ---------------------------------------------------------------------------
from fastapi import BackgroundTasks, Query  # noqa: E402

from ..schemas.admin_dto import (  # noqa: E402
    CalibrationStartRequestDTO,
    CalibrationStartResponseDTO,
    MLflowRunListResponseDTO,
    ScenarioEventCreateRequestDTO,
    ScenarioEventDTO,
    ScenarioEventListResponseDTO,
    ScenarioTreeBuildRequestDTO,
    ScenarioTreeBuildResponseDTO,
    ScenarioTreeListResponseDTO,
)

try:  # pragma: no cover - import-side
    from ..db.session import get_session as _phase6_get_session  # type: ignore
    from ..services import calibration_service as _phase6_calibration  # type: ignore
    from ..services import scenario_event_service as _phase6_event  # type: ignore
    from ..services import scenario_tree_service as _phase6_tree  # type: ignore

    _PHASE6_AVAILABLE = True
except Exception as _phase6_exc:  # noqa: BLE001
    logger.warning("Phase 6 admin endpoints unavailable: %s", _phase6_exc)
    _PHASE6_AVAILABLE = False


def _phase6_guard() -> None:
    if not _PHASE6_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="phase6 admin endpoints require sqlalchemy + ORM stack",
        )


# --- scenario_tree ----------------------------------------------------------
@router.get("/scenario-trees", response_model=ScenarioTreeListResponseDTO)
async def admin_list_scenario_trees(
    region_id: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    _: dict = Depends(get_current_admin),
) -> ScenarioTreeListResponseDTO:
    _phase6_guard()
    async for session in _phase6_get_session():  # type: ignore[misc]
        return await _phase6_tree.list_trees(
            session, region_id=region_id, page=page, page_size=page_size
        )


@router.post(
    "/scenario-trees/build",
    response_model=ScenarioTreeBuildResponseDTO,
    status_code=status.HTTP_202_ACCEPTED,
)
async def admin_build_scenario_tree(
    payload: ScenarioTreeBuildRequestDTO,
    background: BackgroundTasks,
    admin_payload: dict = Depends(get_current_admin),
) -> ScenarioTreeBuildResponseDTO:
    _phase6_guard()
    requested_by = str(admin_payload.get("sub") or "admin")
    async for session in _phase6_get_session():  # type: ignore[misc]
        return await _phase6_tree.request_build(
            session, payload, requested_by=requested_by
        )


@router.delete(
    "/scenario-trees/{tree_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def admin_delete_scenario_tree(
    tree_id: str,
    _: dict = Depends(get_current_admin),
):
    _phase6_guard()
    async for session in _phase6_get_session():  # type: ignore[misc]
        ok = await _phase6_tree.delete_tree(session, tree_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "tree not found")
    return None


# --- calibration ------------------------------------------------------------
@router.get("/calibration/runs", response_model=MLflowRunListResponseDTO)
def admin_list_calibration_runs(
    region_id: Optional[str] = None,
    stage: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    _: dict = Depends(get_current_admin),
) -> MLflowRunListResponseDTO:
    _phase6_guard()
    return _phase6_calibration.list_runs(
        region_id=region_id, stage=stage, page=page, page_size=page_size
    )


@router.post(
    "/calibration/start",
    response_model=CalibrationStartResponseDTO,
    status_code=status.HTTP_202_ACCEPTED,
)
def admin_start_calibration(
    payload: CalibrationStartRequestDTO,
    _: dict = Depends(get_current_admin),
) -> CalibrationStartResponseDTO:
    _phase6_guard()
    return _phase6_calibration.start_calibration(payload)


# --- scenario_event ---------------------------------------------------------
@router.get("/scenario-events", response_model=ScenarioEventListResponseDTO)
async def admin_list_scenario_events(
    region_id: Optional[str] = None,
    source: Optional[str] = None,
    only_active: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    _: dict = Depends(get_current_admin),
) -> ScenarioEventListResponseDTO:
    _phase6_guard()
    async for session in _phase6_get_session():  # type: ignore[misc]
        try:
            return await _phase6_event.list_events(
                session,
                region_id=region_id,
                source=source,
                only_active=only_active,
                page=page,
                page_size=page_size,
            )
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


@router.post(
    "/scenario-events",
    response_model=ScenarioEventDTO,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_scenario_event(
    payload: ScenarioEventCreateRequestDTO,
    admin_payload: dict = Depends(get_current_admin),
) -> ScenarioEventDTO:
    _phase6_guard()
    created_by = str(admin_payload.get("sub") or "admin")
    async for session in _phase6_get_session():  # type: ignore[misc]
        try:
            return await _phase6_event.create_event(
                session, payload, created_by=created_by
            )
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


@router.delete(
    "/scenario-events/{event_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def admin_delete_scenario_event(
    event_id: str,
    _: dict = Depends(get_current_admin),
):
    _phase6_guard()
    async for session in _phase6_get_session():  # type: ignore[misc]
        ok = await _phase6_event.delete_event(session, event_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "event not found")
    return None


__all__ = ["router", "get_current_admin"]
