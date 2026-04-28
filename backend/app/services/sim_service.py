"""Simulation result upload service — internal API 의 백엔드.

외부 시뮬레이터가 ScenarioResult JSON 을 보내면 `_workspace/snapshots/results/`
에 박제한다. 같은 (region_id, scenario_id) 는 timestamp 접미사로 누적.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
from pathlib import Path
from typing import Any

from src.schemas.result import ScenarioResult
from src.utils.tz import now_kst

from ..schemas.admin_dto import SimResultUploadDTO, SimResultUploadResponseDTO
from ..settings import get_settings

logger = logging.getLogger("backend.sim")

_SAFE_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def _sanitize(name: str) -> str:
    return _SAFE_RE.sub("_", name).strip("_") or "x"


class SimService:
    def store_upload(self, payload: SimResultUploadDTO) -> SimResultUploadResponseDTO:
        # src 도메인 검증 — extra='allow' 라 raw dict 를 그대로 넘겨도 통과
        data: dict[str, Any] = payload.model_dump()
        result = ScenarioResult.model_validate(data)

        out_dir = get_settings().snapshots_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = now_kst().strftime("%Y%m%dT%H%M%SZ")
        fname = f"{_sanitize(result.region_id)}__{_sanitize(result.scenario_id)}__upload_{ts}.json"
        path = out_dir / fname
        body = json.dumps(result.model_dump(), ensure_ascii=False, indent=2)
        path.write_text(body, encoding="utf-8")
        logger.info("sim upload stored: %s (%d bytes)", path, len(body))

        return SimResultUploadResponseDTO(
            snapshot_path=str(path.relative_to(get_settings().snapshots_dir.parent.parent.parent)
                              if path.is_relative_to(get_settings().snapshots_dir.parent.parent.parent)
                              else path),
            scenario_id=result.scenario_id,
            region_id=result.region_id,
            bytes_written=len(body),
        )


sim_service = SimService()

__all__ = ["sim_service", "SimService"]
