"""Internal API — 정적 service token 인증, 외부 sim 결과 업로드."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import require_internal_token
from ..schemas.admin_dto import SimResultUploadDTO, SimResultUploadResponseDTO
from ..services import sim_service

logger = logging.getLogger("backend.internal")

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
    dependencies=[Depends(require_internal_token)],
)


@router.post(
    "/sim-results",
    response_model=SimResultUploadResponseDTO,
    status_code=status.HTTP_201_CREATED,
)
def upload_sim_result(payload: SimResultUploadDTO) -> SimResultUploadResponseDTO:
    try:
        return sim_service.store_upload(payload)
    except Exception as e:
        logger.exception("sim upload failed")
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"sim result rejected: {type(e).__name__}: {e}",
        )


@router.get("/health")
def internal_health() -> dict:
    return {"status": "ok", "scope": "internal"}
