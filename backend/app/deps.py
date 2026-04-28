"""FastAPI dependencies — auth, rate limit, db sessions, anon user cookie, blackout."""
from __future__ import annotations

import datetime as dt
import logging
from typing import Optional

from fastapi import Cookie, Depends, Header, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from .settings import Settings, get_settings

logger = logging.getLogger("backend.deps")

# Cookie name for anonymous user id (httponly, secure, samesite=lax).
ANON_COOKIE_NAME = "politikast_uid"


# ---------------------------------------------------------------------------
# Rate limit (slowapi)
# ---------------------------------------------------------------------------
def _key_func(request) -> str:
    return get_remote_address(request)


limiter = Limiter(
    key_func=_key_func,
    default_limits=[get_settings().rate_limit_default],
)


# ---------------------------------------------------------------------------
# Auth — internal service token + admin bearer (verify only; admin issuance은 fe stream)
# ---------------------------------------------------------------------------
def require_internal_token(
    authorization: Optional[str] = Header(default=None),
    x_service_token: Optional[str] = Header(default=None, alias="X-Service-Token"),
    settings: Settings = Depends(get_settings),
) -> str:
    """Internal API용 정적 service token. 외부 시뮬레이터가 결과 업로드 시 사용.

    `Authorization: Bearer <token>` 또는 `X-Service-Token: <token>` 둘 다 허용.
    """
    token = None
    if x_service_token:
        token = x_service_token.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token or token != settings.internal_service_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing internal service token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


# ---------------------------------------------------------------------------
# DB session placeholders — db-postgres / kg-neo4j stream 이 채움
# ---------------------------------------------------------------------------
async def get_pg_session():  # pragma: no cover — db stream 의존
    """SQLAlchemy AsyncSession 의존성 — db-postgres 가 backend/app/db/session.py 에서 구현."""
    try:
        from .db.session import get_session  # type: ignore
    except Exception:
        yield None
        return
    async for s in get_session():  # pragma: no cover
        yield s


async def get_neo4j_session():  # pragma: no cover — kg stream 의존
    try:
        from .db.neo4j_session import get_session  # type: ignore
    except Exception:
        yield None
        return
    async for s in get_session():  # pragma: no cover
        yield s


_AUTH_REQUIRED_DETAIL = "consent required: visit /api/v1/users/anonymous to obtain a cookie"


def get_current_user(
    politikast_uid: Optional[str] = Cookie(default=None, alias=ANON_COOKIE_NAME),
):
    """Optional anon user — cookie 가 있으면 store 에서 조회, 없으면 None.

    GET 전용 라우트에서 사용 (None 허용). write 는 require_consented_user.
    """
    if not politikast_uid:
        return None
    # local import — service 모듈 import 순환 회피
    from .services.anon_user_service import get_user
    return get_user(politikast_uid)


def require_consented_user(
    politikast_uid: Optional[str] = Cookie(default=None, alias=ANON_COOKIE_NAME),
):
    """Cookie 동의된 사용자만 통과. 미동의 → 401 + 'consent required'."""
    if not politikast_uid:
        raise HTTPException(status_code=401, detail=_AUTH_REQUIRED_DETAIL)
    from .services.anon_user_service import get_user
    u = get_user(politikast_uid)
    if u is None:
        raise HTTPException(status_code=401, detail=_AUTH_REQUIRED_DETAIL)
    return u


def require_active_user(user=Depends(require_consented_user)):
    """추가로 banned 사용자 차단. write 모든 라우트 기본."""
    if getattr(user, "banned", False):
        raise HTTPException(status_code=401, detail="user is banned")
    return user


def get_blackout_status(region_id: str):
    from .services.blackout_service import get_status
    return get_status(region_id)


__all__ = [
    "limiter",
    "require_internal_token",
    "get_pg_session",
    "get_neo4j_session",
    "ANON_COOKIE_NAME",
    "get_current_user",
    "require_consented_user",
    "require_active_user",
    "get_blackout_status",
]
