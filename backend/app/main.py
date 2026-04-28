"""FastAPI app factory + lifespan + CORS + slowapi.

Admin router 는 frontend stream 이 backend/app/routers/admin.py 를 추가하면
자동 마운트 (best-effort import).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .deps import limiter
from .routers import internal_router, public_router
from .settings import get_settings

logger = logging.getLogger("backend")


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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
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
