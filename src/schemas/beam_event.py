"""BeamEvent — single discrete event proposed for scenario tree expansion.

Phase 6 (pipeline-model) 산출물. Event proposers (KG / LLM / custom) 가
공통적으로 emit 하는 unit. Pydantic v2, `extra="forbid"` — 미정의 필드 박제
방지.

Patch shape contract (decision: 2026-04-28, task #21)
-----------------------------------------------------
``candidate_patches`` 와 ``event_patches`` 는 두 정식 shape 를 모두 허용한다.
`src/sim/scenario_tree.py::_splice_event_into_scenario` 가 dispatch 한다.

* **Declarative** (PRIMARY — pipeline-counterfactual seed JSON, LLM hypotheses,
  custom 시나리오의 기본 표현). 후보 boost / 이슈 salience 같은 free-form
  modifier 를 그대로 voter prompt enrichment 와 KG 레이어로 흘려보낸다::

      candidate_patches=[
          {"candidate_id": "c_seoul_dpk", "boost": 0.06, "reason": "단일화 흡수"},
          {"candidate_id": "c_seoul_rebuild", "drop_out": True},
      ]
      event_patches=[
          {"issue": "야권_단일화", "salience": 0.30},
      ]

* **Imperative / op-shape** (LEGACY — `run_counterfactual.apply_intervention`
  과 동형, 후보 roster 자체를 수정해야 하는 actual-branch 인터벤션에서 사용)::

      candidate_patches=[
          {"op": "set", "candidate_id": "...", "fields": {...}},
          {"op": "upsert", "candidate_id": "...", "candidate": {...}},
          {"op": "withdraw", "candidate_id": "..."},
      ]
      event_patches=[
          {"op": "add", "event": {"event_id": "...", "timestep": 2, ...}},
          {"op": "remove", "event_id": "..."},
      ]

이 두 shape 는 키 패턴(``op`` / ``fields`` / ``candidate`` / ``event`` 존재
여부)으로 자동 분기된다. 두 shape 가 섞인 list 도 정상 동작한다.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

EventSource = Literal["kg_confirmed", "llm_hypothetical", "custom"]


class BeamEvent(BaseModel):
    """Discrete event proposed by an `EventProposer`.

    See module docstring for the official `candidate_patches` / `event_patches`
    shape contract — declarative (primary) and imperative (legacy) are both
    accepted; the splicer routes them appropriately.
    """

    model_config = ConfigDict(extra="forbid")

    event_id: str
    source: EventSource
    occurs_at: dt.datetime
    description: str = Field(..., description="한국어 라벨, Sankey 노드에 표시")
    candidate_patches: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Declarative ({candidate_id, boost|drop_out|reason, …}) is the "
            "primary form. Imperative ({op, candidate_id, fields|candidate}) "
            "is also supported for run_counterfactual interop."
        ),
    )
    event_patches: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Declarative ({issue, salience, …}) is the primary form. "
            "Imperative ({op:'add'|'remove', event:{event_id,…}}) is also "
            "supported for run_counterfactual interop."
        ),
    )
    prior_p: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = ["BeamEvent", "EventSource"]
