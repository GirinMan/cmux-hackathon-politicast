"""PolitiKAST 단일 진실의 소스 (SoT) — Pydantic v2 스키마.

각 도메인 모델은 자체 모듈에서 정의하고 여기서 re-export 한다.
- persona:       Nemotron-Personas-Korea 페르소나 + 사용 컬럼 freeze
- scenario:      시나리오 시드 JSON (5 region)
- poll:          raw_poll, poll_consensus_daily, NESDC 등록 여론조사 메타
- result:        ScenarioResult — 시뮬레이션 출력 (snapshots/results/*.json)
- ground_truth:  공식 여론조사 + 선거 결과 (DuckDB official_poll, election_result)
- kg:            지식그래프 노드/엣지 (src/kg/ontology.py 의 dataclass 미러)

`SCHEMA_VERSION` 은 모든 최상위 산출물에 박제되며, migration script 는
부재 시 v0 로 간주하고 기본값을 채워 v1 로 변환한다.
"""
from __future__ import annotations

SCHEMA_VERSION = "v1"

from .persona import (  # noqa: E402
    PERSONA_CORE_COLUMNS,
    PERSONA_PROVINCE_CANDIDATES,
    PERSONA_DISTRICT_CANDIDATES,
    PERSONA_TEXT_SUFFIX,
    PersonaCore,
    PersonaText,
)
from .scenario import (  # noqa: E402
    Candidate,
    Contest,
    District,
    Election,
    Issue,
    NarrativeFrame,
    Party,
    Scenario,
    SeedEvent,
    SimulationWindow,
)
from .poll import (  # noqa: E402
    PollConsensusDaily,
    RawPoll,
)
from .result import (  # noqa: E402
    DemographicsBreakdown,
    FinalOutcome,
    Meta,
    OfficialPollValidation,
    PollTrajectoryPoint,
    ScenarioResult,
    ValidationByCandidate,
    ValidationMetrics,
    VirtualInterview,
    KgEventUsed,
    CandidateRef,
)
from .ground_truth import (  # noqa: E402
    ElectionResult,
    OfficialPollSnapshot,
)
from .llm_strategy import (  # noqa: E402
    LLMFallbackEntry,
    LLMPrimaryPath,
    LLMProvider,
    LLMStrategy,
    load_llm_strategy,
    provider_key_env_map,
)
from .calendar import (  # noqa: E402
    ElectionCalendar,
    ElectionWindow,
    load_election_calendar,
)
from .sim_constants import (  # noqa: E402
    BandwagonParams,
    ConsensusParams,
    EnvDefaults,
    SimConstants,
    load_sim_constants,
)
from .pollster import (  # noqa: E402
    HOUSE_EFFECT_BOUND,
    MODE_EFFECT_BOUND,
    HouseEffect,
    ModeEffect,
    PollsterRegistry,
    load_pollster_registry,
)
from .party import (  # noqa: E402
    PartyEntry,
    PartyRegistry,
    load_party_registry,
)
from .cohort import (  # noqa: E402
    AgeBucket,
    AgeBuckets,
    DEFAULT_AGE_BUCKETS,
    load_age_buckets,
)
from .typology import (  # noqa: E402
    ELECTION_TYPE_LABELS,
    ElectionType,
    POSITION_TYPE_LABELS,
    PositionType,
    TypologyEntry,
    election_type_values,
    is_valid_election_type,
    is_valid_position_type,
    position_type_values,
)
from .persona_axis import (  # noqa: E402
    NumericBucket,
    PersonaAxis,
    PersonaAxisRegistry,
    load_persona_axes,
)
from .data_source import (  # noqa: E402
    DataSource,
    DataSourceRegistry,
    IngestRun,
    load_data_source_registry,
)
from .candidate_registry import (  # noqa: E402
    CandidateEntry,
    CandidateRegistry,
    load_candidate_registry,
)
from .issue_registry import (  # noqa: E402
    IssueEntry,
    IssueRegistry,
    load_issue_registry,
)
from .person_registry import (  # noqa: E402
    PersonEntry,
    PersonRegistry,
    load_person_registry,
)

__all__ = [
    "SCHEMA_VERSION",
    # data source / ingest
    "DataSource",
    "DataSourceRegistry",
    "IngestRun",
    "load_data_source_registry",
    # calendar
    "ElectionCalendar",
    "ElectionWindow",
    "load_election_calendar",
    # sim constants
    "BandwagonParams",
    "ConsensusParams",
    "EnvDefaults",
    "SimConstants",
    "load_sim_constants",
    # persona
    "PERSONA_CORE_COLUMNS",
    "PERSONA_PROVINCE_CANDIDATES",
    "PERSONA_DISTRICT_CANDIDATES",
    "PERSONA_TEXT_SUFFIX",
    "PersonaCore",
    "PersonaText",
    # scenario
    "Candidate",
    "Contest",
    "District",
    "Election",
    "Issue",
    "NarrativeFrame",
    "Party",
    "Scenario",
    "SeedEvent",
    "SimulationWindow",
    # poll
    "PollConsensusDaily",
    "RawPoll",
    # result
    "CandidateRef",
    "DemographicsBreakdown",
    "FinalOutcome",
    "KgEventUsed",
    "Meta",
    "OfficialPollValidation",
    "PollTrajectoryPoint",
    "ScenarioResult",
    "ValidationByCandidate",
    "ValidationMetrics",
    "VirtualInterview",
    # ground truth
    "ElectionResult",
    "OfficialPollSnapshot",
    # llm strategy
    "LLMFallbackEntry",
    "LLMPrimaryPath",
    "LLMProvider",
    "LLMStrategy",
    "load_llm_strategy",
    "provider_key_env_map",
    # pollster
    "HOUSE_EFFECT_BOUND",
    "MODE_EFFECT_BOUND",
    "HouseEffect",
    "ModeEffect",
    "PollsterRegistry",
    "load_pollster_registry",
    # party
    "PartyEntry",
    "PartyRegistry",
    "load_party_registry",
    # cohort (age buckets)
    "AgeBucket",
    "AgeBuckets",
    "DEFAULT_AGE_BUCKETS",
    "load_age_buckets",
    # typology
    "ELECTION_TYPE_LABELS",
    "ElectionType",
    "POSITION_TYPE_LABELS",
    "PositionType",
    "TypologyEntry",
    "election_type_values",
    "is_valid_election_type",
    "is_valid_position_type",
    "position_type_values",
    # persona axis
    "NumericBucket",
    "PersonaAxis",
    "PersonaAxisRegistry",
    "load_persona_axes",
    # candidate registry
    "CandidateEntry",
    "CandidateRegistry",
    "load_candidate_registry",
    # issue registry
    "IssueEntry",
    "IssueRegistry",
    "load_issue_registry",
    # person registry
    "PersonEntry",
    "PersonRegistry",
    "load_person_registry",
]
