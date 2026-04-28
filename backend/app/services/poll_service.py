"""Poll trajectory service — snapshot.poll_trajectory wrap."""
from __future__ import annotations

from typing import Optional

from src.schemas.result import ScenarioResult

from ..schemas.public_dto import PollPointDTO
from . import _snapshots


class PollService:
    def get_trajectory(
        self, region_id: str, scenario_id: Optional[str] = None
    ) -> list[PollPointDTO]:
        path = _snapshots.find_latest_snapshot(region_id, scenario_id)
        if path is None:
            return []
        snap: ScenarioResult = _snapshots.load_snapshot(path)
        return [
            PollPointDTO(
                timestep=p.timestep,
                date=p.date,
                support_by_candidate=dict(p.support_by_candidate or {}),
                turnout_intent=p.turnout_intent,
                consensus_var=p.consensus_var,
            )
            for p in (snap.poll_trajectory or [])
        ]


poll_service = PollService()

__all__ = ["poll_service", "PollService"]
