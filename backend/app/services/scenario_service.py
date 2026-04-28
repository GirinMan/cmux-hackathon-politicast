"""Scenario service — 시드 JSON + snapshot outcome merge."""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from src.schemas.result import ScenarioResult

from ..schemas.public_dto import (
    CandidateDTO,
    ScenarioDTO,
    ScenarioOutcomeDTO,
)
from ..settings import REPO_ROOT
from . import _snapshots

logger = logging.getLogger("backend.scenario")

SCENARIOS_DIR = REPO_ROOT / "_workspace" / "data" / "scenarios"


@lru_cache(maxsize=32)
def _load_scenario_seed(scenario_id: str) -> Optional[dict]:
    if not SCENARIOS_DIR.exists():
        return None
    for p in SCENARIOS_DIR.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("scenario_id") == scenario_id or data.get("region_id") == scenario_id:
            return data
    return None


def _scenario_to_dto(seed: dict, snapshot: Optional[ScenarioResult]) -> ScenarioDTO:
    cands_raw = seed.get("candidates") or (snapshot.candidates if snapshot else [])
    cands: list[CandidateDTO] = []
    for c in cands_raw:
        if hasattr(c, "model_dump"):
            c = c.model_dump()
        cands.append(
            CandidateDTO(
                cand_id=str(c.get("id") or c.get("cand_id") or ""),
                name=str(c.get("name") or ""),
                party_id=c.get("party_id") or c.get("party"),
            )
        )
    return ScenarioDTO(
        scenario_id=str(seed.get("scenario_id") or seed.get("region_id")),
        region_id=str(seed.get("region_id")),
        contest_id=str(
            seed.get("contest_id")
            or (seed.get("contest") or {}).get("id")
            or seed.get("scenario_id")
        ),
        election_date=str(
            seed.get("election_date")
            or (seed.get("election") or {}).get("date")
            or ""
        )
        or None,
        candidates=cands,
        timesteps=int((seed.get("simulation") or {}).get("timesteps") or
                      (snapshot.timestep_count if snapshot else 0) or 0),
        persona_n=int(snapshot.persona_n if snapshot else 0),
    )


class ScenarioService:
    def list_scenarios(self) -> list[ScenarioDTO]:
        if not SCENARIOS_DIR.exists():
            return []
        out: list[ScenarioDTO] = []
        for p in sorted(SCENARIOS_DIR.glob("*.json")):
            try:
                seed = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not seed.get("scenario_id"):
                continue
            snap = self._latest_snapshot(seed["region_id"], seed["scenario_id"])
            out.append(_scenario_to_dto(seed, snap))
        return out

    def get_scenario(self, scenario_id: str) -> ScenarioDTO:
        seed = _load_scenario_seed(scenario_id)
        if not seed:
            raise KeyError(scenario_id)
        snap = self._latest_snapshot(seed["region_id"], seed["scenario_id"])
        return _scenario_to_dto(seed, snap)

    def get_outcome(self, scenario_id: str) -> ScenarioOutcomeDTO:
        seed = _load_scenario_seed(scenario_id)
        if not seed:
            raise KeyError(scenario_id)
        snap = self._latest_snapshot(seed["region_id"], seed["scenario_id"])
        if snap is None:
            return ScenarioOutcomeDTO(scenario_id=scenario_id, region_id=seed["region_id"])
        opv = snap.meta.official_poll_validation if snap.meta else None
        m = opv.metrics.model_dump() if opv else {}
        fo = snap.final_outcome
        return ScenarioOutcomeDTO(
            scenario_id=scenario_id,
            region_id=seed["region_id"],
            target_series=getattr(opv, "target_series", None) if opv else None,
            final_vote_share=dict(fo.vote_share_by_candidate) if fo else {},
            winner=getattr(fo, "winner", None) if fo else None,
            turnout=getattr(fo, "turnout", None) if fo else None,
            metrics={k: v for k, v in m.items() if isinstance(v, (int, float, type(None)))},
        )

    # ---- internal ----
    def _latest_snapshot(self, region_id: str, scenario_id: str) -> Optional[ScenarioResult]:
        path = _snapshots.find_latest_snapshot(region_id, scenario_id)
        if path is None:
            return None
        try:
            return _snapshots.load_snapshot(path)
        except Exception as e:
            logger.warning("failed to load snapshot %s: %s", path, e)
            return None


scenario_service = ScenarioService()

__all__ = ["scenario_service", "ScenarioService"]
