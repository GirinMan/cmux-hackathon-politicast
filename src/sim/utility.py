"""Utility decomposition: U = U^base + ΔU^media + ΔU^poll + ΔU^gov + ε.

These functions are *prior-side* nudges that we render into the prompt context
(text bullets) so the LLM voter can incorporate them into its decision. We do
NOT shape logits directly — the ε term lives implicitly inside the LLM
sampling. The numerical helpers here are also used to compute calibration
metrics (predicted vs latest poll consensus) for paper-writer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Baseline utility — party affinity from persona
# ---------------------------------------------------------------------------
# Conservative / progressive priors are *very* coarse. Real model would learn
# from KOSIS / Gallup cross-tabs. For the hackathon we use a stylized prior so
# bandwagon/underdog effects are visible against a non-zero baseline.
_PARTY_AXIS: dict[str, float] = {
    # +1.0 = strongly progressive, -1.0 = strongly conservative
    "더불어민주당": 1.0,
    "민주당": 1.0,
    "조국혁신당": 0.8,
    "정의당": 0.7,
    "녹색정의당": 0.7,
    "진보당": 0.6,
    "국민의힘": -1.0,
    "개혁신당": -0.5,
    "무소속": 0.0,
    "기타": 0.0,
}


def party_axis(party: str) -> float:
    return _PARTY_AXIS.get(party, 0.0)


def baseline_utility(persona: dict[str, Any], candidate: dict[str, Any]) -> float:
    """U^base — coarse persona × candidate affinity in [-1, 1]."""
    axis_c = party_axis(candidate.get("party", ""))
    # Persona axis from age + education (very rough; replace with KOSIS prior).
    age = float(persona.get("age", 45) or 45)
    age_term = -0.4 * ((age - 50.0) / 30.0)  # older → more conservative
    edu = (persona.get("education_level") or "").lower()
    edu_term = 0.1 if any(k in edu for k in ("graduate", "master", "ph", "bachelor")) else 0.0
    persona_axis = max(-1.0, min(1.0, age_term + edu_term))
    return persona_axis * axis_c


# ---------------------------------------------------------------------------
# Media shock — events affecting candidate at time t
# ---------------------------------------------------------------------------
@dataclass
class MediaShock:
    candidate_id: str
    delta: float
    summary: str  # human-readable, goes into prompt


def media_shock(events: list[dict[str, Any]], candidate_id: str, t: int) -> MediaShock:
    """ΔU^media — sum signed sentiment of events targeting `candidate_id` at time ≤ t."""
    deltas: list[float] = []
    bullets: list[str] = []
    for ev in events:
        if ev.get("target") != candidate_id:
            continue
        if int(ev.get("timestep", 0)) > t:
            continue
        sign = float(ev.get("polarity", 0.0))
        deltas.append(sign)
        bullets.append(f"- t={ev.get('timestep')} [{ev.get('type', 'event')}] {ev.get('summary', '')}")
    return MediaShock(
        candidate_id=candidate_id,
        delta=sum(deltas),
        summary="\n".join(bullets),
    )


# ---------------------------------------------------------------------------
# Second-order effects — central gov approval punishes/rewards aligned party
# ---------------------------------------------------------------------------
def second_order(
    gov_approval: float,
    candidate_party: str,
    position_type: str,
    *,
    ruling_party: str = "국민의힘",
) -> float:
    """ΔU^gov — central gov approval ricochet onto local candidates.

    Rule of thumb: low gov approval punishes ruling-party local candidates and
    boosts the largest opposition.
    """
    # Approval centered around 0.4 (Korean baseline)
    deviation = gov_approval - 0.4
    if candidate_party == ruling_party:
        return 0.5 * deviation
    if party_axis(candidate_party) * party_axis(ruling_party) < 0:
        # opposition aligned: gets the inverse of ruling-party penalty
        return -0.3 * deviation
    return 0.0
