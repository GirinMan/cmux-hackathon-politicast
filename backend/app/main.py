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

# Mutating verbs that require origin/referer verification beyond CORS.
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

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
        """CSRF defense for cookie-authenticated mutating endpoints.

        SameSite=Lax cookie 가 cross-site auto-send 를 막지만, same-site
        frame attack / 구형 브라우저 / non-browser client 가 cookie 갈취 후
        write 호출하는 경우를 추가로 차단한다. CORS allow_origins 와 동일
        화이트리스트에 Origin 또는 Referer 가 속해야 통과.

        Skip: GET/OPTIONS/HEAD, /internal/* (service token), /admin/* (JWT),
        그리고 health/docs.
        """
        if request.method not in _MUTATING_METHODS:
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
