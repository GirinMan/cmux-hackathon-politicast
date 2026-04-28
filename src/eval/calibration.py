"""Calibration metrics — Brier score + Expected Calibration Error (ECE).

PolitiKAST 시뮬레이터는 voter 별 logits 를 노출하지 않는다. 따라서 calibration
입력은 후보별 (predicted_share, observed_share) 쌍으로 단순화한다:
  - predicted = simulated vote share (renormalized to overlap)
  - observed  = official poll consensus share (renormalized to overlap)

이는 후보별 "확률분포" 가 official_consensus 라는 ground truth 를 얼마나 잘
재현하는가에 대한 calibration view 다 (proper scoring). 1-hot label 이 아니라
soft target 인 점에 유의: Brier 는 일반화된 quadratic score (MSE on probs),
ECE 는 confidence(=predicted_share) 와 accuracy(=observed_share) 의 bin-wise
가중평균 절대 차이.

Synthetic 사용을 위해 1-hot 입력(True/False outcome) 도 받는다.
"""
from __future__ import annotations

from typing import Iterable, Mapping, Sequence


def _coerce(probs: Iterable[float] | Mapping[str, float]) -> list[float]:
    if isinstance(probs, Mapping):
        return [float(v) for v in probs.values()]
    return [float(v) for v in probs]


def brier_score(
    predicted_probs: Iterable[float] | Mapping[str, float],
    observed_outcomes: Iterable[float] | Mapping[str, float],
) -> float:
    """Generalized Brier score = mean( (p_i - o_i)^2 ) over candidates.

    표준 Brier 는 1-hot outcome 을 가정하지만, 여기서는 soft target
    (official share) 도 허용한다. 입력이 dict 면 (양쪽이 dict 인 경우)
    공통 키만 사용한다 — 호출자가 미리 정렬을 끝낸 가정.
    """
    if isinstance(predicted_probs, Mapping) and isinstance(observed_outcomes, Mapping):
        keys = sorted(set(predicted_probs) & set(observed_outcomes))
        if not keys:
            raise ValueError("brier_score: predicted/observed dict 의 공통 키가 없음")
        p = [float(predicted_probs[k]) for k in keys]
        o = [float(observed_outcomes[k]) for k in keys]
    else:
        p = _coerce(predicted_probs)
        o = _coerce(observed_outcomes)
    if len(p) != len(o):
        raise ValueError(f"brier_score: 길이 불일치 {len(p)} vs {len(o)}")
    if not p:
        raise ValueError("brier_score: 빈 입력")
    return sum((pi - oi) ** 2 for pi, oi in zip(p, o)) / len(p)


def expected_calibration_error(
    predicted_probs: Iterable[float] | Mapping[str, float],
    observed_outcomes: Iterable[float] | Mapping[str, float],
    n_bins: int = 10,
) -> float:
    """ECE = Σ_b (|B_b| / N) · |conf(B_b) - acc(B_b)|.

    각 후보를 하나의 'sample' 로 보고, predicted_share 를 confidence,
    observed_share 를 accuracy proxy 로 사용한다 (soft).
    n_bins 는 [0,1] 을 균등 분할.
    """
    if n_bins < 1:
        raise ValueError("expected_calibration_error: n_bins ≥ 1")
    if isinstance(predicted_probs, Mapping) and isinstance(observed_outcomes, Mapping):
        keys = sorted(set(predicted_probs) & set(observed_outcomes))
        p = [float(predicted_probs[k]) for k in keys]
        o = [float(observed_outcomes[k]) for k in keys]
    else:
        p = _coerce(predicted_probs)
        o = _coerce(observed_outcomes)
    if len(p) != len(o):
        raise ValueError(f"ECE: 길이 불일치 {len(p)} vs {len(o)}")
    n = len(p)
    if n == 0:
        raise ValueError("ECE: 빈 입력")

    # bin 경계 [0, 1/n_bins, ..., 1]. 첫 bin 은 [0, 1/n_bins], 이후 (a, b]
    bin_indices: list[list[int]] = [[] for _ in range(n_bins)]
    for i, pi in enumerate(p):
        # clamp
        pc = max(0.0, min(1.0, pi))
        idx = min(int(pc * n_bins), n_bins - 1)
        bin_indices[idx].append(i)

    ece = 0.0
    for bucket in bin_indices:
        if not bucket:
            continue
        conf = sum(p[i] for i in bucket) / len(bucket)
        acc = sum(o[i] for i in bucket) / len(bucket)
        ece += (len(bucket) / n) * abs(conf - acc)
    return ece


__all__ = ["brier_score", "expected_calibration_error"]
