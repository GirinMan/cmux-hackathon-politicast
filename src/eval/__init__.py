"""PolitiKAST 평가 지표 단일 진실의 소스 (SoT).

기존 src/sim/election_env.py:840-915 와 dashboard 레이어에 분산되어 있던
시뮬 vs 공식 여론조사 비교 4종 지표(MAE / RMSE / margin_error / leader_match)
를 한 곳에서 계산한다.

호출 지점:
- src/sim/election_env.ElectionEnv._inject_validation_metrics
- ui/dashboard/components/data_loader.evaluate_validation_metrics (임계값 평가;
  값은 본 모듈이 사전 산출한 결과를 읽기만 함)
"""
from __future__ import annotations

from .calibration import brier_score, expected_calibration_error
from .divergence import detect_distribution_collapse, js_divergence, kl_divergence
from .evaluate import evaluate_scenario_result
from .metrics import (
    compute_validation_metrics,
    renormalize_to_overlap,
    summarize_by_candidate,
)

__all__ = [
    "compute_validation_metrics",
    "renormalize_to_overlap",
    "summarize_by_candidate",
    "brier_score",
    "expected_calibration_error",
    "kl_divergence",
    "js_divergence",
    "detect_distribution_collapse",
    "evaluate_scenario_result",
]
