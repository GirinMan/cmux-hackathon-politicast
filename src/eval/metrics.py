"""Validation metrics — 시뮬 vote share vs 공식 여론조사 consensus 비교.

`_workspace/validation/official_poll_validation_targets.md` 가 정한 4종 지표:
  - MAE          : Σ|sim - off| / N    (per candidate, then averaged)
  - RMSE         : sqrt(Σ(sim - off)^2 / N)
  - margin_error : |(sim_top - sim_2nd) - (off_top - off_2nd)|
  - leader_match : argmax(sim) == argmax(off)

핵심 정책:
  - sim 과 official 양쪽이 모두 가지고 있는 후보(`union_keys = sim ∩ official`)
    로 한정해서 각 측을 다시 정규화 (renormalize) 한 뒤 비교한다. 이는 sim 이
    placeholder 후보를 가지고 있고 공식 폴은 없거나 그 반대인 경우의 잘못된
    페널티를 막기 위한 디자인 결정 (election_env.py:849 주석 참조).
  - overlap 이 비면 None 4종 + reason 을 돌려준다 — 호출자가
    `target_series="missing_candidate_overlap"` 으로 처리.
"""
from __future__ import annotations

import math
from typing import Iterable

from src.schemas.result import ValidationByCandidate, ValidationMetrics


def renormalize_to_overlap(
    a: dict[str, float], b: dict[str, float]
) -> tuple[list[str], dict[str, float], dict[str, float]]:
    """양쪽 dict 의 공통 키만 남겨 각 측을 share=1.0 으로 재정규화."""
    keys = sorted(set(a) & set(b))

    def _renorm(d: dict[str, float]) -> dict[str, float]:
        sub = {k: float(d.get(k, 0.0) or 0.0) for k in keys}
        total = sum(sub.values())
        if total <= 0:
            return {k: 0.0 for k in keys}
        return {k: v / total for k, v in sub.items()}

    return keys, _renorm(a), _renorm(b)


def _round(x: float | None, n: int = 4) -> float | None:
    return None if x is None else round(x, n)


def compute_validation_metrics(
    simulated: dict[str, float],
    official: dict[str, float],
    *,
    keys: Iterable[str] | None = None,
) -> ValidationMetrics:
    """sim 과 official 모두 (후보_id → share) dict.

    `keys` 가 주어지면 해당 키만, 아니면 양쪽의 교집합으로 평가한다.
    overlap 이 없을 땐 모든 metric 이 None.
    """
    if keys is None:
        union_keys, sim_n, off_n = renormalize_to_overlap(simulated, official)
    else:
        union_keys = list(keys)
        # 외부에서 정한 키가 한쪽에 없는 경우 0.0 으로 채워서 정규화
        sub_a = {k: float(simulated.get(k, 0.0) or 0.0) for k in union_keys}
        sub_b = {k: float(official.get(k, 0.0) or 0.0) for k in union_keys}
        ta, tb = sum(sub_a.values()), sum(sub_b.values())
        sim_n = {k: (v / ta) if ta > 0 else 0.0 for k, v in sub_a.items()}
        off_n = {k: (v / tb) if tb > 0 else 0.0 for k, v in sub_b.items()}

    if not union_keys:
        return ValidationMetrics()

    errors = [sim_n[k] - off_n[k] for k in union_keys]
    abs_errors = [abs(e) for e in errors]
    sq_errors = [e * e for e in errors]
    mae = sum(abs_errors) / len(abs_errors)
    rmse = math.sqrt(sum(sq_errors) / len(sq_errors))

    sim_leader = max(sim_n.items(), key=lambda kv: kv[1])[0]
    off_leader = max(off_n.items(), key=lambda kv: kv[1])[0]

    sim_sorted = sorted(sim_n.values(), reverse=True)
    off_sorted = sorted(off_n.values(), reverse=True)
    sim_margin = sim_sorted[0] - (sim_sorted[1] if len(sim_sorted) > 1 else 0.0)
    off_margin = off_sorted[0] - (off_sorted[1] if len(off_sorted) > 1 else 0.0)
    margin_error = abs(sim_margin - off_margin)

    return ValidationMetrics(
        mae=_round(mae),
        rmse=_round(rmse),
        margin_error=_round(margin_error),
        leader_match=bool(sim_leader == off_leader),
    )


def summarize_by_candidate(
    simulated: dict[str, float],
    official: dict[str, float],
    *,
    keys: Iterable[str] | None = None,
) -> dict[str, ValidationByCandidate]:
    """후보별 (simulated_share, official_consensus, error) — JSON 직렬화용."""
    if keys is None:
        union_keys, sim_n, off_n = renormalize_to_overlap(simulated, official)
    else:
        union_keys = list(keys)
        sub_a = {k: float(simulated.get(k, 0.0) or 0.0) for k in union_keys}
        sub_b = {k: float(official.get(k, 0.0) or 0.0) for k in union_keys}
        ta, tb = sum(sub_a.values()), sum(sub_b.values())
        sim_n = {k: (v / ta) if ta > 0 else 0.0 for k, v in sub_a.items()}
        off_n = {k: (v / tb) if tb > 0 else 0.0 for k, v in sub_b.items()}

    return {
        cid: ValidationByCandidate(
            simulated_share=_round(sim_n[cid]),
            official_consensus=_round(off_n[cid]),
            error=_round(sim_n[cid] - off_n[cid]),
        )
        for cid in union_keys
    }
