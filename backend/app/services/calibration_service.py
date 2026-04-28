"""Phase 6 — Calibration service (MLflow proxy + spawn).

Reads MLflow run metadata via the official `mlflow` python client when it's
installed and the tracking server (`docker compose up -d mlflow`) is up.
Falls back to a degraded `available=False` response so the admin UI keeps
working in dev when MLflow isn't running.

Stage 1 / 2 calibration jobs are kicked off as fire-and-forget subprocesses
(`python -m src.train.calibrate --stage N --regions REGION`); pipeline-train
team owns the actual implementation.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import Any, Optional

from ..schemas.admin_dto import (
    CalibrationStartRequestDTO,
    CalibrationStartResponseDTO,
    MLflowRunListResponseDTO,
    MLflowRunSummaryDTO,
)
from ..settings import REPO_ROOT, get_settings

logger = logging.getLogger("backend.calibration")

VALID_STAGES = {1, 2}


def _client():  # pragma: no cover - import-side
    try:
        from mlflow.tracking import MlflowClient  # type: ignore

        s = get_settings()
        uri = s.mlflow_tracking_uri
        if not uri:
            return None, None
        return MlflowClient(tracking_uri=uri), uri
    except Exception as exc:
        logger.info("mlflow client unavailable: %s", exc)
        return None, None


def _run_to_dto(run: Any, *, experiment_lookup: dict[str, str]) -> MLflowRunSummaryDTO:
    info = run.info
    data = run.data
    tags = data.tags or {}
    metrics = {k: float(v) for k, v in (data.metrics or {}).items()}
    params = {k: str(v) for k, v in (data.params or {}).items()}
    return MLflowRunSummaryDTO(
        run_id=info.run_id,
        experiment_id=info.experiment_id,
        experiment_name=experiment_lookup.get(info.experiment_id),
        run_name=tags.get("mlflow.runName"),
        status=info.status,
        start_time=(
            None
            if info.start_time is None
            else __import__("datetime").datetime.utcfromtimestamp(
                info.start_time / 1000.0
            ).isoformat()
            + "Z"
        ),
        end_time=(
            None
            if info.end_time is None
            else __import__("datetime").datetime.utcfromtimestamp(
                info.end_time / 1000.0
            ).isoformat()
            + "Z"
        ),
        region_id=tags.get("region_id") or params.get("region_id"),
        stage=tags.get("stage") or params.get("stage"),
        metrics=metrics,
        params=params,
        artifact_uri=info.artifact_uri,
    )


def list_runs(
    *,
    region_id: Optional[str] = None,
    stage: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> MLflowRunListResponseDTO:
    page = max(1, page)
    page_size = max(1, min(200, page_size))
    client, uri = _client()
    if client is None:
        return MLflowRunListResponseDTO(
            data=[],
            page=page,
            page_size=page_size,
            total=0,
            tracking_uri=uri,
            available=False,
            error="mlflow client not installed or tracking server unreachable",
        )
    try:
        experiments = client.search_experiments()
        exp_lookup = {e.experiment_id: e.name for e in experiments}
        filter_parts: list[str] = []
        if region_id:
            filter_parts.append(f"tags.region_id = '{region_id}'")
        if stage:
            filter_parts.append(f"tags.stage = '{stage}'")
        filter_string = " and ".join(filter_parts) if filter_parts else ""
        all_runs = client.search_runs(
            experiment_ids=list(exp_lookup.keys()),
            filter_string=filter_string,
            order_by=["attribute.start_time DESC"],
            max_results=min(page * page_size, 1000),
        )
        total = len(all_runs)
        slice_ = all_runs[(page - 1) * page_size : page * page_size]
        return MLflowRunListResponseDTO(
            data=[_run_to_dto(r, experiment_lookup=exp_lookup) for r in slice_],
            page=page,
            page_size=page_size,
            total=total,
            tracking_uri=uri,
            available=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("mlflow search_runs failed: %s", exc)
        return MLflowRunListResponseDTO(
            data=[],
            page=page,
            page_size=page_size,
            total=0,
            tracking_uri=uri,
            available=False,
            error=str(exc),
        )


def start_calibration(
    payload: CalibrationStartRequestDTO,
) -> CalibrationStartResponseDTO:
    if payload.stage not in VALID_STAGES:
        return CalibrationStartResponseDTO(
            region_id=payload.region_id,
            stage=payload.stage,
            status="failed",
            detail=f"invalid stage: {payload.stage}",
        )
    cmd = [
        sys.executable,
        "-m",
        "src.train.calibrate",
        "--stage", str(payload.stage),
        "--regions", payload.region_id,
    ]
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(REPO_ROOT))
    s = get_settings()
    if s.mlflow_tracking_uri:
        env.setdefault("MLFLOW_TRACKING_URI", s.mlflow_tracking_uri)
    try:
        subprocess.Popen(  # noqa: S603 — controlled args
            cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            close_fds=True,
        )
    except FileNotFoundError as exc:
        return CalibrationStartResponseDTO(
            region_id=payload.region_id,
            stage=payload.stage,
            status="failed",
            detail=f"interpreter not found: {exc}",
        )
    return CalibrationStartResponseDTO(
        region_id=payload.region_id,
        stage=payload.stage,
        status="started",
        detail=f"spawned: {' '.join(cmd)}",
    )


__all__ = ["list_runs", "start_calibration"]
