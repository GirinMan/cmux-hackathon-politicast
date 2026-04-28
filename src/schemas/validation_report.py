"""ValidationReport — Phase 6 hidden-label hold-out 산출물.

`src/eval/validation_harness.py` 가 region/train_window/test_window/sim_params
조합 1건을 ElectionEnv 에서 실행한 뒤 evaluate_scenario_result() 로 얻은
ValidationMetrics 를 박제한다. MLflow log_metric / log_artifact 양쪽 모두
이 스키마를 진실의 원천으로 본다.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.result import ValidationMetrics


class TimeWindow(BaseModel):
    """검증/학습 윈도우 (start ≤ end, 둘 다 포함)."""

    model_config = ConfigDict(extra="forbid")

    name: str  # train_2022 | train_rolling_2026 | validation_holdout | test_2026
    start: dt.date
    end: dt.date

    def contains(self, d: dt.date) -> bool:
        return self.start <= d <= self.end


class ValidationReport(BaseModel):
    """Phase 6 validation harness 의 1회 실행 결과.

    metrics 는 evaluate_scenario_result() 가 반환하는 8 종 지표를 그대로
    재사용한다 (mae/rmse/margin/leader/brier/ece/js/collapse).
    """

    model_config = ConfigDict(extra="forbid")

    region_id: str
    contest_id: str
    train_window: TimeWindow
    test_window: TimeWindow
    sim_params: dict[str, Any] = Field(default_factory=dict)
    metrics: ValidationMetrics = Field(default_factory=ValidationMetrics)
    n_personas: Optional[int] = None
    n_timesteps: Optional[int] = None
    sim_result_ref: Optional[str] = None  # _workspace/snapshots/results/{...}.json
    mlflow_run_id: Optional[str] = None
    firewall_passed: bool = True
    notes: str = ""
    created_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))


__all__ = ["TimeWindow", "ValidationReport"]
