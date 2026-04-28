"""ConsensusParams + BandwagonParams + EnvDefaults — 시뮬 매직 상수의 SoT.

`src/sim/poll_consensus.consensus(...)` / `bandwagon_underdog(...)` /
`election_env.ElectionEnv` 가 인자 없이 호출되면 `_workspace/contracts/
sim_constants.json` 에서 본 모델을 로드한다. 기본값은 현재 매직 값 그대로
시드 — 회귀 13/13 이 깨지면 안 된다.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT_PATH = REPO_ROOT / "_workspace" / "contracts" / "sim_constants.json"


class ConsensusParams(BaseModel):
    """poll_consensus.consensus() 의 가중치/감쇠 파라미터."""

    model_config = ConfigDict(extra="forbid")

    alpha: float = 0.5
    """sample-size weighting exponent (n^alpha)."""

    lam: float = 0.05
    """time-decay rate per day (exp(-lam · Δt))."""

    ref_day: int = 0
    """reference day used for Δt computation in consensus()."""

    smoothing: float = 0.0
    """optional Laplace-style smoothing (currently unused — placeholder)."""

    fieldwork_window_days: int = 30
    """election_env scenario_fallback: poll.day=N → date = e_date - 30d + N."""


class BandwagonParams(BaseModel):
    """bandwagon_underdog() utilities."""

    model_config = ConfigDict(extra="forbid")

    bandwagon_w: float = 0.3
    underdog_w: float = 0.1
    trigger_threshold: float = 0.1  # |margin| > threshold → underdog kicks in
    enable_bandwagon: bool = True
    enable_underdog: bool = True


class EnvDefaults(BaseModel):
    """ElectionEnv 기본 런타임 값."""

    model_config = ConfigDict(extra="forbid")

    timesteps: int = 4
    n_interviews: int = 30
    concurrency: int = 8
    base_date_strategy: str = "scenario_t_start"  # | "election_date_minus_T" | "today"


class SimConstants(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = "v1"
    consensus: ConsensusParams = Field(default_factory=ConsensusParams)
    bandwagon: BandwagonParams = Field(default_factory=BandwagonParams)
    env: EnvDefaults = Field(default_factory=EnvDefaults)


@lru_cache(maxsize=4)
def load_sim_constants(path: Optional[str] = None) -> SimConstants:
    """Cached loader. 파일 부재 시 모델 기본값을 사용 (현재 매직 값과 일치)."""
    p = Path(path) if path else DEFAULT_CONTRACT_PATH
    if not p.exists():
        return SimConstants()
    raw = json.loads(p.read_text(encoding="utf-8"))
    return SimConstants.model_validate(raw)


__all__ = [
    "ConsensusParams",
    "BandwagonParams",
    "EnvDefaults",
    "SimConstants",
    "load_sim_constants",
    "DEFAULT_CONTRACT_PATH",
]
