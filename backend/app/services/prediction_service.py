"""Prediction service — counterfactual / prediction_only branch trajectory.

snapshot.poll_trajectory 와 동일 구조지만, target_series=='prediction_only' /
'counterfactual_prediction' 인 snapshot 만 사용. 명시적 분리 라우터로 노출하여
시청자/연구자가 'held-out label 비교' 와 'pure inference' 를 구분 가능.
"""
from __future__ import annotations

from typing import Optional

from src.schemas.result import ScenarioResult

from ..schemas.public_dto import PredictionPointDTO
from . import _snapshots


_PREDICTION_SERIES = {"prediction_only", "counterfactual_prediction"}


class PredictionService:
    def get_trajectory(
        self, region_id: str, scenario_id: Optional[str] = None
    ) -> list[PredictionPointDTO]:
        # prediction-flavored snapshot 우선 탐색
        for path in _snapshots.find_all_for_region(region_id):
            try:
                snap: ScenarioResult = _snapshots.load_snapshot(path)
            except Exception:
                continue
            opv = snap.meta.official_poll_validation if snap.meta else None
            ts = getattr(opv, "target_series", None) if opv else None
            if ts in _PREDICTION_SERIES and (
                scenario_id is None or snap.scenario_id == scenario_id
            ):
                return self._to_points(snap)
        # 없으면 latest 의 trajectory 를 prediction 으로 노출 (degraded)
        path = _snapshots.find_latest_snapshot(region_id, scenario_id)
        if path is None:
            return []
        return self._to_points(_snapshots.load_snapshot(path))

    @staticmethod
    def _to_points(snap: ScenarioResult) -> list[PredictionPointDTO]:
        out: list[PredictionPointDTO] = []
        for p in snap.poll_trajectory or []:
            shares = dict(p.support_by_candidate or {})
            top2 = sorted(shares.values(), reverse=True)[:2]
            margin = (top2[0] - top2[1]) if len(top2) == 2 else None
            leader = max(shares.items(), key=lambda kv: kv[1])[0] if shares else None
            out.append(
                PredictionPointDTO(
                    timestep=p.timestep,
                    date=p.date,
                    predicted_share=shares,
                    margin_top2=margin,
                    leader=leader,
                )
            )
        return out


prediction_service = PredictionService()

__all__ = ["prediction_service", "PredictionService"]
