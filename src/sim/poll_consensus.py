"""Poll aggregation + bandwagon/underdog signal.

`consensus(raw_polls, ...)` follows the recipe documented in the paper:
    p~_j = y_j - δ_house_j - δ_mode_j
    p_hat = Σ w_j p~_j / Σ w_j
    w_j = n_j^α · exp(-λ Δt_j) · quality_j
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

# ---------------------------------------------------------------------------
# House/mode effect priors — SoT: src/schemas/pollster.PollsterRegistry
# (registry JSON: _workspace/data/registries/pollsters.json; legacy fallback:
# _workspace/data/poll_priors.json)
# ---------------------------------------------------------------------------
from src.schemas.pollster import load_pollster_registry  # noqa: E402


def default_house_effect() -> dict[str, float]:
    """Return seeded Korean-pollster house-effect priors (subtractive)."""
    return load_pollster_registry().as_house_effect_dict()


def default_mode_effect() -> dict[str, float]:
    """Return seeded Korean polling-mode effect priors (subtractive)."""
    return load_pollster_registry().as_mode_effect_dict()


def _safe_get(d: dict[str, Any], key: str, default: float = 0.0) -> float:
    v = d.get(key, default)
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def consensus(
    raw_polls: list[dict[str, Any]],
    *,
    house_effect: dict[str, float] | None = None,
    mode_effect: dict[str, float] | None = None,
    alpha: float = 0.5,
    lam: float = 0.05,
    ref_day: int = 0,
) -> dict[str, dict[str, float]]:
    """Returns {candidate_id: {p_hat, var}} aggregated across polls.

    Each `raw_poll` is a dict:
        {
          "pollster": str,
          "mode": "phone"|"online"|"...",
          "n": int,
          "day": int,                 # days since campaign start
          "shares": {candidate_id: float},
          "quality": float (0..1, optional, default 1.0),
        }
    """
    # Auto-load Korean pollster priors when caller doesn't pass explicit dicts.
    # Pass house_effect={} / mode_effect={} explicitly to disable prior bias correction.
    if house_effect is None:
        house_effect = default_house_effect()
    if mode_effect is None:
        mode_effect = default_mode_effect()

    # Per-candidate weighted accumulator
    num: dict[str, float] = defaultdict(float)
    den: dict[str, float] = defaultdict(float)
    sq: dict[str, float] = defaultdict(float)

    for poll in raw_polls:
        n = max(1.0, _safe_get(poll, "n", 1.0))
        day = int(poll.get("day", 0))
        quality = _safe_get(poll, "quality", 1.0) or 1.0
        delta_t = max(0, ref_day - day)
        w = (n ** alpha) * math.exp(-lam * delta_t) * quality
        if w <= 0:
            continue

        h = house_effect.get(str(poll.get("pollster", "")), 0.0)
        m = mode_effect.get(str(poll.get("mode", "")), 0.0)

        shares = poll.get("shares") or {}
        for cid, y in shares.items():
            try:
                y_f = float(y)
            except (TypeError, ValueError):
                continue
            p_tilde = y_f - h - m
            num[cid] += w * p_tilde
            den[cid] += w
            sq[cid] += w * (p_tilde ** 2)

    out: dict[str, dict[str, float]] = {}
    for cid, w_sum in den.items():
        if w_sum <= 0:
            out[cid] = {"p_hat": 0.0, "var": 0.0}
            continue
        mean = num[cid] / w_sum
        var = max(0.0, sq[cid] / w_sum - mean ** 2)
        out[cid] = {"p_hat": mean, "var": var}
    return out


def bandwagon_underdog(
    p_hat: dict[str, float],
    candidate_id: str,
    *,
    bandwagon_w: float = 0.3,
    underdog_w: float = 0.1,
    enable_bandwagon: bool = True,
    enable_underdog: bool = True,
) -> float:
    """ΔU^poll for a single candidate from current consensus.

    Bandwagon: boost frontrunner. Underdog: small inverse boost for trailing.
    """
    if not p_hat:
        return 0.0
    own = float(p_hat.get(candidate_id, 0.0))
    if not p_hat:
        return 0.0
    leader_share = max(p_hat.values())
    margin = own - leader_share  # 0 for leader, negative otherwise

    delta = 0.0
    if enable_bandwagon:
        delta += bandwagon_w * margin  # leader gets 0; trailers get penalty
    if enable_underdog:
        # underdog bumps the *most* trailing candidate (asymmetric)
        if margin < -0.1:
            delta += underdog_w * abs(margin)
    return delta


def aggregate_poll_response(
    responses: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Tally a wave of poll-mode voter responses → support shares + turnout."""
    counts: dict[str, int] = {c["id"]: 0 for c in candidates}
    counts["__abstain__"] = 0
    turnout_yes = 0
    n_total = 0
    for r in responses:
        n_total += 1
        if r.get("turnout") is True:
            turnout_yes += 1
        v = r.get("vote")
        if v is None or v == "abstain":
            counts["__abstain__"] += 1
            continue
        if v in counts:
            counts[v] += 1
        else:
            counts["__abstain__"] += 1
    decided = max(1, n_total - counts["__abstain__"])
    shares = {cid: counts[cid] / decided for cid in counts if cid != "__abstain__"}
    turnout_intent = turnout_yes / max(1, n_total)
    # consensus_var = variance over candidate shares (broad spread → low certainty)
    if shares:
        mean = sum(shares.values()) / len(shares)
        var = sum((s - mean) ** 2 for s in shares.values()) / len(shares)
    else:
        var = 0.0
    return {
        "support_by_candidate": shares,
        "turnout_intent": turnout_intent,
        "consensus_var": var,
        "n_responses": n_total,
        "n_abstain": counts["__abstain__"],
    }
