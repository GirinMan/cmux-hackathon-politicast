"""PolitiKAST 평가 지표 단일 진실의 소스 (SoT).

시뮬 vs 공식 여론조사 비교 4종 지표(MAE / RMSE / margin_error / leader_match)
+ Phase 6 calibration 4종 (Brier / ECE / JS divergence / collapse_flag) 를
한 곳에서 계산한다.

호출 지점:
- src/sim/election_env.ElectionEnv._inject_validation_metrics
- src/eval/validation_harness.run_validation
- src/train/calibrate.score_metrics
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
