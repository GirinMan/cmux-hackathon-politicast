"""PollsterRegistry — 한국 여론조사 기관/모드별 house · mode effect prior 의 SoT.

Phase 1 #17 에서 시드된 `_workspace/data/poll_priors.json` 를 Phase 2 #38 에서
`_workspace/data/registries/pollsters.json` 로 이동하면서 Pydantic 으로 래핑.

`src/sim/poll_consensus.py` 의 `default_house_effect()` / `default_mode_effect()`
가 본 모듈의 dict view (`as_house_effect_dict` / `as_mode_effect_dict`) 를 사용한다.

Sanity: |effect| ≤ 0.05 (시드 정책: 보수적 ±0.02, 여유 50%).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = (
    REPO_ROOT / "_workspace" / "data" / "registries" / "pollsters.json"
)
LEGACY_REGISTRY_PATH = REPO_ROOT / "_workspace" / "data" / "poll_priors.json"

# 절대값 클램프 — 시드된 prior 가 ±0.02 이내이지만, fitted estimate 도입 시
# 약간의 여유(50%)를 둔다. 이를 초과하면 ValidationError.
HOUSE_EFFECT_BOUND = 0.05
MODE_EFFECT_BOUND = 0.05


class HouseEffect(BaseModel):
    """단일 여론조사 기관의 subtractive bias prior."""

    model_config = ConfigDict(extra="forbid")

    pollster: str
    effect: float = Field(..., description="p_tilde = y - effect (subtractive)")
    aliases: list[str] = Field(default_factory=list)
    note: Optional[str] = None

    @field_validator("effect")
    @classmethod
    def _clamp(cls, v: float) -> float:
        if abs(v) > HOUSE_EFFECT_BOUND + 1e-12:
            raise ValueError(
                f"|house_effect|={abs(v):.4f} exceeds bound {HOUSE_EFFECT_BOUND}"
            )
        return float(v)


class ModeEffect(BaseModel):
    """단일 조사 모드(phone/online/ARS/...)의 subtractive bias prior."""

    model_config = ConfigDict(extra="forbid")

    mode: str
    effect: float = Field(..., description="p_tilde = y - effect (subtractive)")
    aliases: list[str] = Field(default_factory=list)
    note: Optional[str] = None

    @field_validator("effect")
    @classmethod
    def _clamp(cls, v: float) -> float:
        if abs(v) > MODE_EFFECT_BOUND + 1e-12:
            raise ValueError(
                f"|mode_effect|={abs(v):.4f} exceeds bound {MODE_EFFECT_BOUND}"
            )
        return float(v)


class PollsterRegistry(BaseModel):
    """house/mode effect 의 SoT registry."""

    model_config = ConfigDict(extra="forbid")

    version: str = "v1"
    description: str = ""
    sources: list[str] = Field(default_factory=list)
    houses: list[HouseEffect] = Field(default_factory=list)
    modes: list[ModeEffect] = Field(default_factory=list)

    def as_house_effect_dict(self) -> dict[str, float]:
        """Flatten houses + aliases → {label: effect} for poll_consensus()."""
        out: dict[str, float] = {}
        for h in self.houses:
            out[h.pollster] = h.effect
            for a in h.aliases:
                out[a] = h.effect
        return out

    def as_mode_effect_dict(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for m in self.modes:
            out[m.mode] = m.effect
            for a in m.aliases:
                out[a] = m.effect
        return out


# ---------------------------------------------------------------------------
# Loader — supports both new (registry/PollsterRegistry shape) and legacy
# (flat house_effect/mode_effect dicts) formats.
# ---------------------------------------------------------------------------
def _coerce_legacy(raw: dict) -> dict:
    """Convert legacy poll_priors.json (flat dicts) to PollsterRegistry shape."""
    if "houses" in raw or "modes" in raw:
        return raw  # already new format
    meta = raw.get("_meta", {}) or {}
    houses = [
        {"pollster": k, "effect": float(v)}
        for k, v in (raw.get("house_effect") or {}).items()
    ]
    modes = [
        {"mode": k, "effect": float(v)}
        for k, v in (raw.get("mode_effect") or {}).items()
    ]
    return {
        "version": "v1",
        "description": meta.get("purpose", ""),
        "sources": meta.get("sources", []) or [],
        "houses": houses,
        "modes": modes,
    }


@lru_cache(maxsize=4)
def load_pollster_registry(path: str | None = None) -> PollsterRegistry:
    """Load PollsterRegistry from disk (cached).

    Resolution order when `path` is None:
      1. POLITIKAST_REGISTRY_DIR/pollsters.json (env override)
      2. _workspace/data/registries/pollsters.json (canonical)
      3. _workspace/data/poll_priors.json (legacy, deprecated)
    """
    import os

    if path:
        p = Path(path)
    else:
        env_dir = os.environ.get("POLITIKAST_REGISTRY_DIR")
        if env_dir:
            p = Path(env_dir) / "pollsters.json"
        else:
            p = DEFAULT_REGISTRY_PATH
        if not p.exists() and LEGACY_REGISTRY_PATH.exists():
            p = LEGACY_REGISTRY_PATH

    if not p.exists():
        # Soft-fail: empty registry (poll_consensus tolerates missing keys).
        return PollsterRegistry()

    raw = json.loads(p.read_text(encoding="utf-8"))
    return PollsterRegistry.model_validate(_coerce_legacy(raw))


__all__ = [
    "HouseEffect",
    "ModeEffect",
    "PollsterRegistry",
    "HOUSE_EFFECT_BOUND",
    "MODE_EFFECT_BOUND",
    "DEFAULT_REGISTRY_PATH",
    "LEGACY_REGISTRY_PATH",
    "load_pollster_registry",
]
