#!/usr/bin/env python
"""Pydantic 모델 → JSON Schema export.

논문 부록·외부 도구·LLM tool-use 등에서 정식 스키마가 필요할 때 사용한다.
출력 디렉토리: _workspace/contracts/jsonschema/
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.schemas import (
    AgeBuckets,
    CandidateRegistry,
    DataSourceRegistry,
    ElectionResult,
    IngestRun,
    IssueRegistry,
    LLMStrategy,
    OfficialPollSnapshot,
    PartyRegistry,
    PersonRegistry,
    PersonaAxisRegistry,
    PollConsensusDaily,
    PollsterRegistry,
    RawPoll,
    Scenario,
    ScenarioResult,
    SimConstants,
)
from src.schemas.calendar import ElectionCalendar
from src.schemas.beam_event import BeamEvent
from src.schemas.scenario_tree import BeamConfig, BeamNode, ScenarioTree
from src.schemas.temporal_split import TemporalSplit
from src.schemas.validation_report import ValidationReport

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = REPO_ROOT / "_workspace" / "contracts" / "jsonschema"

EXPORTS = {
    "scenario.schema.json": Scenario,
    "scenario_result.schema.json": ScenarioResult,
    "raw_poll.schema.json": RawPoll,
    "poll_consensus_daily.schema.json": PollConsensusDaily,
    "official_poll.schema.json": OfficialPollSnapshot,
    "election_result.schema.json": ElectionResult,
    "llm_strategy.schema.json": LLMStrategy,
    "pollster_registry.schema.json": PollsterRegistry,
    "election_calendar.schema.json": ElectionCalendar,
    "party_registry.schema.json": PartyRegistry,
    "age_buckets.schema.json": AgeBuckets,
    "persona_axes.schema.json": PersonaAxisRegistry,
    "sim_constants.schema.json": SimConstants,
    "data_sources.schema.json": DataSourceRegistry,
    "ingest_run.schema.json": IngestRun,
    "candidate_registry.schema.json": CandidateRegistry,
    "issue_registry.schema.json": IssueRegistry,
    "person_registry.schema.json": PersonRegistry,
    "validation_report.schema.json": ValidationReport,
    "temporal_split.schema.json": TemporalSplit,
    "beam_event.schema.json": BeamEvent,
    "beam_config.schema.json": BeamConfig,
    "beam_node.schema.json": BeamNode,
    "scenario_tree.schema.json": ScenarioTree,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    for fname, model in EXPORTS.items():
        path = args.out / fname
        schema = model.model_json_schema()
        path.write_text(json.dumps(schema, ensure_ascii=False, indent=2))
        print(f"  wrote {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
