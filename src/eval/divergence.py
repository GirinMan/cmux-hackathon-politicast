"""KL / JS divergence + distribution-collapse 탐지.

Daegu 같은 100% 단일후보 붕괴 케이스를 진단하기 위한 단순 헬퍼 모음.
zero-prob 처리는 epsilon smoothing 으로 일관 처리한다.
"""
from __future__ import annotations

import math
from typing import Iterable, Mapping, Sequence

EPSILON = 1e-9


def _normalize(probs: Sequence[float]) -> list[float]:
    total = sum(probs)
    if total <= 0:
        # uniform fallback
        n = max(len(probs), 1)
        return [1.0 / n] * n
    return [v / total for v in probs]


def _coerce_pair(
    p: Iterable[float] | Mapping[str, float],
    q: Iterable[float] | Mapping[str, float],
) -> tuple[list[float], list[float]]:
    if isinstance(p, Mapping) and isinstance(q, Mapping):
        keys = sorted(set(p) | set(q))
        if not keys:
            raise ValueError("divergence: 빈 입력")
        pl = [float(p.get(k, 0.0) or 0.0) for k in keys]
        ql = [float(q.get(k, 0.0) or 0.0) for k in keys]
    else:
        pl = [float(v) for v in p]
        ql = [float(v) for v in q]
    if len(pl) != len(ql):
        raise ValueError(f"divergence: 길이 불일치 {len(pl)} vs {len(ql)}")
    if not pl:
        raise ValueError("divergence: 빈 입력")
    pl = _normalize(pl)
    ql = _normalize(ql)
    # epsilon smoothing + renormalize
    pl = [v + EPSILON for v in pl]
    ql = [v + EPSILON for v in ql]
    sp, sq = sum(pl), sum(ql)
    pl = [v / sp for v in pl]
    ql = [v / sq for v in ql]
    return pl, ql


def kl_divergence(
    p: Iterable[float] | Mapping[str, float],
    q: Iterable[float] | Mapping[str, float],
) -> float:
    """KL(p || q) = Σ p · log(p / q). natural log (nats)."""
    pl, ql = _coerce_pair(p, q)
    return sum(pi * math.log(pi / qi) for pi, qi in zip(pl, ql))


def js_divergence(
    p: Iterable[float] | Mapping[str, float],
    q: Iterable[float] | Mapping[str, float],
) -> float:
    """JS = 0.5 · KL(p || m) + 0.5 · KL(q || m), m = (p + q) / 2.

    symmetric, bounded in [0, log 2]. 본 구현은 nats 단위.
    """
    pl, ql = _coerce_pair(p, q)
    ml = [(pi + qi) / 2.0 for pi, qi in zip(pl, ql)]
    kl_pm = sum(pi * math.log(pi / mi) for pi, mi in zip(pl, ml))
    kl_qm = sum(qi * math.log(qi / mi) for qi, mi in zip(ql, ml))
    return 0.5 * kl_pm + 0.5 * kl_qm


def detect_distribution_collapse(
    shares: Iterable[float] | Mapping[str, float],
    threshold: float = 0.99,
) -> bool:
    """단일 후보가 threshold 이상 점유하면 collapse 로 판정."""
    if isinstance(shares, Mapping):
        vals = [float(v) for v in shares.values()]
    else:
        vals = [float(v) for v in shares]
    if not vals:
        return False
    total = sum(vals)
    if total <= 0:
        return False
    return (max(vals) / total) >= threshold


__all__ = ["kl_divergence", "js_divergence", "detect_distribution_collapse", "EPSILON"]
