"""validation_harness — Phase 6 hidden-label hold-out 회귀 테스트."""
from __future__ import annotations

import datetime as dt

import pytest

from src.data.temporal_split import make_split
from src.eval.validation_harness import (
    FirewallEnforcer,
    run_validation_sync,
)
from src.schemas.result import (
    FinalOutcome,
    Meta,
    OfficialPollValidation,
    PollTrajectoryPoint,
    ScenarioResult,
    ValidationByCandidate,
)
from src.schemas.validation_report import TimeWindow, ValidationReport


def _make_stub_result(region_id: str) -> ScenarioResult:
    """후보 a/b가 0.55/0.45, official 0.50/0.50 인 toy result."""
    return ScenarioResult(
        scenario_id=f"{region_id}_2026__test",
        region_id=region_id,
        contest_id=f"{region_id}_2026",
        timesteps=4,
        final_outcome=FinalOutcome(
            vote_share_by_candidate={"a": 0.55, "b": 0.45},
            winner="a",
        ),
        poll_trajectory=[
            PollTrajectoryPoint(timestep=4, support_by_candidate={"a": 0.55, "b": 0.45}),
        ],
        meta=Meta(
            official_poll_validation=OfficialPollValidation(
                target_series="poll_consensus_daily",
                cutoff_ts="2026-05-27T00:00:00+00:00",
                by_candidate={
                    "a": ValidationByCandidate(simulated_share=0.55, official_consensus=0.50),
                    "b": ValidationByCandidate(simulated_share=0.45, official_consensus=0.50),
                },
            )
        ),
    )


@pytest.fixture
def stub_runner():
    captured: dict = {}

    async def runner(region_id, train_w, test_w, sim_params):
        captured["region_id"] = region_id
        captured["train_w"] = train_w
        captured["test_w"] = test_w
        captured["sim_params"] = sim_params
        return _make_stub_result(region_id)

    runner.captured = captured  # type: ignore[attr-defined]
    return runner


def test_run_validation_returns_report_with_metrics(stub_runner) -> None:
    split = make_split("seoul_mayor")
    rep = run_validation_sync(
        "seoul_mayor",
        split.train_rolling_2026,
        split.validation_holdout,
        {"bandwagon_weight": 0.2, "second_order_weight": 0.05},
        runner=stub_runner,
        firewall=None,
    )
    assert isinstance(rep, ValidationReport)
    assert rep.region_id == "seoul_mayor"
    assert rep.contest_id == "seoul_mayor_2026"
    assert rep.metrics.mae == pytest.approx(0.05, abs=1e-6)  # |0.55-0.50| = 0.05
    assert rep.metrics.leader_match in (True, False)  # official tie → leader_match 정의됨
    assert rep.firewall_passed is True
    # sim_params 전달
    assert stub_runner.captured["sim_params"]["bandwagon_weight"] == 0.2


def test_run_validation_rejects_train_after_election(stub_runner) -> None:
    bad_train = TimeWindow(
        name="bad",
        start=dt.date(2026, 6, 1),
        end=dt.date(2026, 6, 10),  # 선거일 이후
    )
    test_w = TimeWindow(name="t", start=dt.date(2026, 5, 27), end=dt.date(2026, 6, 2))
    with pytest.raises(ValueError):
        run_validation_sync(
            "seoul_mayor",
            bad_train,
            test_w,
            {},
            runner=stub_runner,
            firewall=None,
        )


def test_firewall_enforcer_skip_when_no_retriever() -> None:
    fw = FirewallEnforcer(retriever=None, personas=[{"persona_id": "x"}])
    assert fw.enforce("seoul_mayor", dt.datetime(2026, 5, 27, tzinfo=dt.timezone.utc)) is True


def test_firewall_enforcer_skip_when_no_personas() -> None:
    class _StubRetriever:
        pass

    fw = FirewallEnforcer(retriever=_StubRetriever(), personas=[])
    assert fw.enforce("seoul_mayor", dt.datetime(2026, 5, 27, tzinfo=dt.timezone.utc)) is True


def test_run_validation_serializes_to_json(stub_runner) -> None:
    split = make_split("busan_buk_gap")
    rep = run_validation_sync(
        "busan_buk_gap",
        split.train_rolling_2026,
        split.validation_holdout,
        {},
        runner=stub_runner,
        firewall=None,
    )
    payload = rep.model_dump(mode="json")
    # roundtrip
    rep2 = ValidationReport.model_validate(payload)
    assert rep2.region_id == "busan_buk_gap"
