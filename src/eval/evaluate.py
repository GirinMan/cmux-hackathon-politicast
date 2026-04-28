"""상위 evaluator — ScenarioResult + official dict → 통합 metric.

기존 4종 (MAE/RMSE/margin_error/leader_match) + 확장 4종
(Brier/ECE/JS/collapse_flag) 을 한 번에 산출한다.

입력 official dict 는 후보_id → share 매핑. 호출자가 명시적으로 넘기지
못한 경우, ScenarioResult.meta.official_poll_validation.by_candidate
의 official_consensus 를 fallback 으로 사용한다.
"""
from __future__ import annotations

from typing import Mapping, Optional

from src.schemas.result import ScenarioResult, ValidationMetrics

from .calibration import brier_score, expected_calibration_error
from .divergence import detect_distribution_collapse, js_divergence
from .metrics import compute_validation_metrics, renormalize_to_overlap


def _extract_simulated_shares(result: ScenarioResult) -> dict[str, float]:
    """final_outcome.vote_share_by_candidate 우선, 없으면 마지막 trajectory."""
    if result.final_outcome and result.final_outcome.vote_share_by_candidate:
        return {k: float(v) for k, v in result.final_outcome.vote_share_by_candidate.items()}
    if result.poll_trajectory:
        last = result.poll_trajectory[-1]
        return {k: float(v) for k, v in last.support_by_candidate.items()}
    return {}


def _extract_official_from_meta(result: ScenarioResult) -> dict[str, float]:
    opv = result.meta.official_poll_validation if result.meta else None
    if not opv:
        return {}
    return {
        cid: float(row.official_consensus or 0.0)
        for cid, row in (opv.by_candidate or {}).items()
        if row.official_consensus is not None
    }


def evaluate_scenario_result(
    result: ScenarioResult,
    official: Optional[Mapping[str, float]] = None,
    *,
    n_bins: int = 10,
    collapse_threshold: float = 0.99,
) -> ValidationMetrics:
    """ScenarioResult 한 건 + official share dict → ValidationMetrics.

    official 이 None 또는 비어있으면 meta.official_poll_validation 의
    by_candidate 에서 fallback 추출. 그래도 비어있으면 base 4종은 None,
    Brier/ECE/JS 는 None, collapse_flag 만 simulated 기준으로 채움.
    """
    simulated = _extract_simulated_shares(result)
    off_dict: dict[str, float] = dict(official) if official else _extract_official_from_meta(result)

    # collapse 는 official 이 없어도 simulated 만으로 평가 가능.
    collapse = detect_distribution_collapse(simulated, threshold=collapse_threshold) if simulated else None

    if not simulated or not off_dict:
        return ValidationMetrics(collapse_flag=collapse)

    # base 4종 (overlap renormalize 는 metrics 모듈이 책임)
    base = compute_validation_metrics(simulated, off_dict)

    # 확장 4종은 같은 overlap renormalize 결과 위에서 계산.
    keys, sim_n, off_n = renormalize_to_overlap(simulated, off_dict)
    if not keys:
        return ValidationMetrics(
            mae=base.mae,
            rmse=base.rmse,
            margin_error=base.margin_error,
            leader_match=base.leader_match,
            collapse_flag=collapse,
        )

    sim_vec = [sim_n[k] for k in keys]
    off_vec = [off_n[k] for k in keys]
    brier = brier_score(sim_vec, off_vec)
    ece = expected_calibration_error(sim_vec, off_vec, n_bins=n_bins)
    js = js_divergence(sim_vec, off_vec)

    return ValidationMetrics(
        mae=base.mae,
        rmse=base.rmse,
        margin_error=base.margin_error,
        leader_match=base.leader_match,
        brier=round(brier, 6),
        ece=round(ece, 6),
        js_divergence=round(js, 6),
        collapse_flag=collapse,
    )


__all__ = ["evaluate_scenario_result"]
