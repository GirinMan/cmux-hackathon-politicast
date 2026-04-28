"""FastAPI app factory + lifespan + CORS + origin guard + slowapi.

Admin router 는 frontend stream 이 backend/app/routers/admin.py 를 추가하면
자동 마운트 (best-effort import).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .deps import limiter
from .routers import internal_router, public_router
from .settings import get_settings

logger = logging.getLogger("backend")

# Paths that authenticate via mechanisms other than the anonymous cookie and
# therefore should not be subjected to the origin guard.
_ORIGIN_GUARD_SKIP_PREFIXES = (
    "/internal/",   # service-token authenticated server-to-server
    "/admin/",      # JWT bearer authenticated, no cookie ambient auth
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("PolitiKAST backend starting (env=%s)", settings.env)
    # Admin bootstrap (env ADMIN_BOOTSTRAP_PASSWORD).
    try:
        from .services.auth_service import bootstrap_admin_user
        bootstrap_admin_user(settings)
    except Exception:
        logger.exception("admin bootstrap failed (continuing without admin user)")
    # 향후 여기서 SQLAlchemy engine.dispose() / Neo4j driver.close() 등을 hook.
    try:
        yield
    finally:
        logger.info("PolitiKAST backend shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="PolitiKAST API",
        version="1.0.0",
        description="Korean local-election agent-based simulation backend.",
        lifespan=lifespan,
    )

    # ---- middleware ----
    allowed_origins = set(settings.cors_origin_list)

    @app.middleware("http")
    async def origin_guard(request: Request, call_next):
        """CSRF + cookie-auth data-exfil defense.

        Anonymous ``politikast_uid`` 쿠키 인증은 GET 응답에도 PII (사용자
        프로필 / 작성 글 등) 를 담는다. 쿠키 누설 + non-browser client 가
        조용히 read-out 하는 시나리오를 막기 위해 mutating verbs 뿐 아니라
        모든 method 에 동일한 Origin/Referer 화이트리스트 검사를 적용한다.

        통과 조건 (둘 중 하나만 만족):
        - ``Origin`` 헤더 ∈ ``cors_origin_list``
        - ``Referer`` 헤더의 origin ∈ ``cors_origin_list``

        Skip:
        - ``OPTIONS`` (CORS preflight 는 CORSMiddleware 가 처리)
        - ``/internal/*``  (service token 인증, ambient cookie 사용 안 함)
        - ``/admin/*``     (JWT bearer 인증, ambient cookie 사용 안 함)
        - ``/health``, ``/docs``, ``/redoc``, ``/openapi.json``
          (정적/공개 — 인증 cookie 와 무관)
        """
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        if any(path.startswith(p) for p in _ORIGIN_GUARD_SKIP_PREFIXES):
            return await call_next(request)

        origin = request.headers.get("origin")
        if origin and origin in allowed_origins:
            return await call_next(request)
        referer = request.headers.get("referer")
        if referer:
            parsed = urlparse(referer)
            if parsed.scheme and parsed.netloc:
                ref_origin = f"{parsed.scheme}://{parsed.netloc}"
                if ref_origin in allowed_origins:
                    return await call_next(request)
        return JSONResponse(
            status_code=403,
            content={"detail": "Origin/Referer not allowed (CSRF guard)"},
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # ---- routers ----
    app.include_router(public_router)
    app.include_router(internal_router)
    # admin (optional, frontend stream 이 정의)
    try:
        from .routers.admin import router as admin_router  # type: ignore
        app.include_router(admin_router)
    except Exception:
        logger.debug("admin router not available — frontend stream will add it")

    @app.get("/health", tags=["public"])
    def health() -> dict:
        return {"status": "ok", "service": "politikast-backend", "env": settings.env}

    return app


app = create_app()


__all__ = ["app", "create_app", "lifespan"]
