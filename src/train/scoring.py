"""Scoring — Stage 1 calibration objective.

Score = leader_match × 0.5 + (1 − normalized_MAE) × 0.3 + (1 − JS_divergence) × 0.2

normalized_MAE 는 ValidationMetrics.mae 를 0..1 로 클립한 값이다.
JS divergence 는 본질적으로 0..ln(2) 범위지만, evaluate.py 의 js_divergence
는 base-2 로 0..1 범위로 정규화되어 있으므로 그대로 사용한다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.schemas.result import ValidationMetrics

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPACE_PATH = REPO_ROOT / "_workspace" / "contracts" / "calibration_space.json"


def load_calibration_space(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else DEFAULT_SPACE_PATH
    if not p.exists():
        raise FileNotFoundError(f"calibration_space registry missing: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _clip01(x: float | None, default: float = 1.0) -> float:
    """Missing → default (worst case 1.0). Else clip to [0, 1]."""
    if x is None:
        return default
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def score_metrics(
    metrics: ValidationMetrics,
    *,
    weights: dict[str, float] | None = None,
) -> float:
    """Stage 1 score — higher is better, in [0, 1]."""
    w = weights or {"leader_match": 0.5, "normalized_mae": 0.3, "js_divergence": 0.2}
    leader = 1.0 if metrics.leader_match else 0.0
    norm_mae = _clip01(metrics.mae, default=1.0)
    js = _clip01(metrics.js_divergence, default=1.0)
    return (
        w["leader_match"] * leader
        + w["normalized_mae"] * (1.0 - norm_mae)
        + w["js_divergence"] * (1.0 - js)
    )


__all__ = ["score_metrics", "load_calibration_space", "DEFAULT_SPACE_PATH"]
