"""ValidationReport / TemporalSplit Pydantic 회귀 테스트."""
from __future__ import annotations

import datetime as dt

import pytest
from pydantic import ValidationError

from src.schemas.result import ValidationMetrics
from src.schemas.temporal_split import TemporalSplit
from src.schemas.validation_report import TimeWindow, ValidationReport


def _tw(name: str, s: str, e: str) -> TimeWindow:
    return TimeWindow(name=name, start=dt.date.fromisoformat(s), end=dt.date.fromisoformat(e))


def test_validation_report_minimal_roundtrip() -> None:
    train = _tw("train_rolling_2026", "2026-04-01", "2026-05-26")
    test = _tw("validation_holdout", "2026-05-20", "2026-05-26")
    rep = ValidationReport(
        region_id="seoul_mayor",
        contest_id="seoul_mayor_2026",
        train_window=train,
        test_window=test,
        sim_params={"bandwagon_weight": 0.1, "second_order_weight": 0.05},
        metrics=ValidationMetrics(mae=0.12, leader_match=True),
        n_personas=200,
    )
    data = rep.model_dump(mode="json")
    reloaded = ValidationReport.model_validate(data)
    assert reloaded.region_id == "seoul_mayor"
    assert reloaded.metrics.mae == pytest.approx(0.12)
    assert reloaded.firewall_passed is True


def test_validation_report_extra_forbid() -> None:
    train = _tw("t", "2026-04-01", "2026-04-30")
    with pytest.raises(ValidationError):
        ValidationReport(
            region_id="seoul_mayor",
            contest_id="x",
            train_window=train,
            test_window=train,
            unexpected_field="boom",  # type: ignore[call-arg]
        )


def test_temporal_split_holdout_within_rolling() -> None:
    split = TemporalSplit(
        region_id="seoul_mayor",
        election_date=dt.date(2026, 6, 3),
        train_rolling_2026=_tw("train_rolling_2026", "2026-04-01", "2026-05-27"),
        validation_holdout=_tw("validation_holdout", "2026-05-21", "2026-05-27"),
        test_2026=_tw("test_2026", "2026-06-03", "2026-06-03"),
    )
    assert split.region_id == "seoul_mayor"


def test_temporal_split_rejects_holdout_outside_rolling() -> None:
    with pytest.raises(ValidationError):
        TemporalSplit(
            region_id="seoul_mayor",
            election_date=dt.date(2026, 6, 3),
            train_rolling_2026=_tw("train_rolling_2026", "2026-04-01", "2026-05-27"),
            validation_holdout=_tw("validation_holdout", "2026-05-28", "2026-06-02"),
            test_2026=_tw("test_2026", "2026-06-03", "2026-06-03"),
        )


def test_temporal_split_rejects_test_missing_election_date() -> None:
    with pytest.raises(ValidationError):
        TemporalSplit(
            region_id="seoul_mayor",
            election_date=dt.date(2026, 6, 3),
            train_rolling_2026=_tw("train_rolling_2026", "2026-04-01", "2026-05-27"),
            validation_holdout=_tw("validation_holdout", "2026-05-21", "2026-05-27"),
            test_2026=_tw("test_2026", "2026-06-04", "2026-06-04"),
        )


def test_temporal_split_rejects_train_2022_outside_year() -> None:
    with pytest.raises(ValidationError):
        TemporalSplit(
            region_id="seoul_mayor",
            election_date=dt.date(2026, 6, 3),
            train_2022=_tw("train_2022", "2021-12-31", "2022-05-31"),
            train_rolling_2026=_tw("train_rolling_2026", "2026-04-01", "2026-05-27"),
            validation_holdout=_tw("validation_holdout", "2026-05-21", "2026-05-27"),
            test_2026=_tw("test_2026", "2026-06-03", "2026-06-03"),
        )


def test_export_jsonschema_includes_phase6_models() -> None:
    from scripts.export_jsonschema import EXPORTS

    assert EXPORTS["validation_report.schema.json"] is ValidationReport
    assert EXPORTS["temporal_split.schema.json"] is TemporalSplit
    # smoke: model_json_schema 가 깨지지 않는다
    ValidationReport.model_json_schema()
    TemporalSplit.model_json_schema()
