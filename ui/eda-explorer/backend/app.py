"""FastAPI app — Nemotron-Personas-Korea EDA + PolitiKAST 5-region API."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import db
from routers import demographics, health, ontology, personas, regions, results


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Startup 에 connection 초기화 (첫 요청 latency 절감)."""
    try:
        db.get_connection()
    except Exception:
        # 실패해도 /api/health 가 degraded 로 응답하므로 startup 차단하지 않음
        pass
    yield


app = FastAPI(
    title="EDA Explorer API",
    version="0.1.0",
    description=(
        "Nemotron-Personas-Korea (1M personas, CC BY 4.0) 인터랙티브 EDA 백엔드. "
        "PolitiKAST contract regions + ontology graph frontend BFF."
    ),
    lifespan=lifespan,
)

# CORS — frontend dev (8234) 만 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8234", "http://127.0.0.1:8234"],
    allow_methods=["GET"],
    allow_headers=["*"],
    allow_credentials=False,
)


# 라우터 등록
app.include_router(health.router)
app.include_router(demographics.router)
app.include_router(regions.router)
app.include_router(personas.router)
app.include_router(ontology.router)
app.include_router(results.router)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "name": "eda-explorer-api",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health",
    }
