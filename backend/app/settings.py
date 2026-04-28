"""Runtime settings — env 기반 + 합리적 기본값.

POLITIKAST_API_* 접두사 env 변수로 override 가능.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="POLITIKAST_API_",
        env_file=str(REPO_ROOT / ".env"),
        extra="ignore",
        case_sensitive=False,
    )

    env: str = "dev"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    rate_limit_default: str = "60/minute"

    snapshots_dir: Path = REPO_ROOT / "_workspace" / "snapshots" / "results"
    duckdb_path: Path = REPO_ROOT / "_workspace" / "db" / "politikast.duckdb"

    internal_service_token: str = Field(default="dev-internal-token-change-me")
    admin_jwt_secret: str = Field(default="dev-admin-jwt-secret-change-me")
    admin_jwt_alg: str = "HS256"

    enable_neo4j: bool = False
    neo4j_uri: Optional[str] = None
    neo4j_user: Optional[str] = None
    neo4j_password: Optional[str] = None

    enable_postgres: bool = False
    postgres_dsn: Optional[str] = None

    # Phase 6 — MLflow tracking server (docker-compose service `mlflow`)
    mlflow_tracking_uri: Optional[str] = "http://localhost:5000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [s.strip() for s in self.cors_origins.split(",") if s.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


__all__ = ["Settings", "get_settings", "REPO_ROOT"]
