"""Precomputed snapshot loader — `_workspace/snapshots/results/*.json`.

snapshot 파일명 규약: `{region_id}__{scenario_id}[__suffix].json`. region_id 는
ElectionCalendar 에 등록된 5종 중 하나, scenario_id 는 시나리오 시드의 id.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from src.schemas.result import ScenarioResult

from ..settings import get_settings

logger = logging.getLogger("backend.snapshots")


def list_snapshot_paths(snapshots_dir: Optional[Path] = None) -> list[Path]:
    d = snapshots_dir or get_settings().snapshots_dir
    if not d.exists():
        return []
    return sorted(d.glob("*.json"))


def load_snapshot(path: Path) -> ScenarioResult:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ScenarioResult.model_validate(raw)


def find_latest_snapshot(
    region_id: str,
    scenario_id: Optional[str] = None,
    snapshots_dir: Optional[Path] = None,
) -> Optional[Path]:
    """region_id (+ optional scenario_id) 일치하는 가장 최근 mtime snapshot.

    suffix 가 `__mock` 인 파일은 후순위로 둠 (실 결과 우선).
    """
    candidates: list[Path] = []
    for p in list_snapshot_paths(snapshots_dir):
        name = p.stem
        if not name.startswith(f"{region_id}__"):
            continue
        if scenario_id and not (
            name == f"{region_id}__{scenario_id}"
            or name.startswith(f"{region_id}__{scenario_id}__")
        ):
            continue
        candidates.append(p)
    if not candidates:
        return None

    def _key(p: Path) -> tuple[int, float]:
        is_mock = "__mock" in p.stem
        return (1 if is_mock else 0, -p.stat().st_mtime)

    candidates.sort(key=_key)
    return candidates[0]


def find_all_for_region(
    region_id: str, snapshots_dir: Optional[Path] = None
) -> list[Path]:
    return [
        p for p in list_snapshot_paths(snapshots_dir) if p.stem.startswith(f"{region_id}__")
    ]


__all__ = [
    "list_snapshot_paths",
    "load_snapshot",
    "find_latest_snapshot",
    "find_all_for_region",
]
