"""Hidden-label hold-out validation harness — Phase 6.

`run_validation(region_id, train_window, test_window, sim_params)` 의 절차:

1. `make_split(region_id)` 로 윈도우 일관성 검증
2. `firewall.assert_no_future_leakage(retriever, persona, ts, region_id)` 강제
   (KG retriever / persona 가 주어진 경우에만)
3. `ElectionEnv` 실행 → `ScenarioResult`
4. `evaluate_scenario_result()` 호출 → 8 metrics
5. `ValidationReport` 직렬화 + (옵션) MLflow log_metric

ElectionEnv 는 시그니처 변경 없이 그대로 재사용한다. 호출자가 미리
voters / scenario_meta / candidates 를 주입하거나, `runner` 콜백을 전달해
실행 자체를 위임할 수 있다 (tests 에서 stub 용).
"""
from __future__ import annotations

import asyncio
import datetime as dt
import logging
from typing import Any, Awaitable, Callable, Mapping, Optional

from src.data.temporal_split import make_split
from src.eval.evaluate import evaluate_scenario_result
from src.schemas.calendar import load_election_calendar
from src.schemas.result import ScenarioResult
from src.schemas.temporal_split import TemporalSplit
from src.schemas.validation_report import TimeWindow, ValidationReport

log = logging.getLogger(__name__)

# Runner: train_window / test_window / sim_params → ScenarioResult.
# 호출자가 ElectionEnv 직접 실행하거나, run_region()을 wrapping 한다.
ScenarioRunner = Callable[
    [str, TimeWindow, TimeWindow, Mapping[str, Any]],
    Awaitable[ScenarioResult],
]


class FirewallEnforcer:
    """test_window.start 시점 기준 KG retriever 미래 누수 검사 어댑터.

    persona 가 None 이면 검사 skip (KG retriever 가 None 인 환경에서 회귀
    테스트만 돌릴 때).
    """

    def __init__(
        self,
        retriever: Any | None,
        personas: list[dict[str, Any]] | None = None,
        k: int = 5,
    ) -> None:
        self.retriever = retriever
        self.personas = personas or []
        self.k = k

    def enforce(
        self, region_id: str, cutoff_ts: dt.datetime, t_index: int = 0
    ) -> bool:
        """모든 등록 persona 에 대해 cutoff 이후 누수 검사. True == clean."""
        if self.retriever is None or not self.personas:
            return True
        # local import 로 순환 의존 회피
        from src.kg.firewall import assert_no_future_leakage

        for persona in self.personas:
            assert_no_future_leakage(
                self.retriever, persona, t=t_index, region_id=region_id, k=self.k
            )
        return True


def _to_official_dict(result: ScenarioResult) -> dict[str, float]:
    """meta.official_poll_validation.by_candidate 에서 hidden-label 추출."""
    opv = result.meta.official_poll_validation if result.meta else None
    if not opv or not opv.by_candidate:
        return {}
    return {
        cid: float(row.official_consensus or 0.0)
        for cid, row in opv.by_candidate.items()
        if row.official_consensus is not None
    }


def _maybe_log_mlflow(
    report: ValidationReport, *, mlflow_run_id: Optional[str]
) -> Optional[str]:
    """MLflow log_metric. Module 미설치/서버 미연결이면 silent skip."""
    try:
        import mlflow  # type: ignore[import-not-found]
    except Exception:  # pragma: no cover — env에 mlflow가 없으면 skip
        return None
    try:
        if mlflow_run_id:
            ctx = mlflow.start_run(run_id=mlflow_run_id, nested=True)
        else:
            ctx = mlflow.start_run(nested=False)
        with ctx as active:
            m = report.metrics
            if m.mae is not None:
                mlflow.log_metric("mae", float(m.mae))
            if m.rmse is not None:
                mlflow.log_metric("rmse", float(m.rmse))
            if m.brier is not None:
                mlflow.log_metric("brier", float(m.brier))
            if m.ece is not None:
                mlflow.log_metric("ece", float(m.ece))
            if m.js_divergence is not None:
                mlflow.log_metric("js_divergence", float(m.js_divergence))
            if m.leader_match is not None:
                mlflow.log_metric("leader_match", float(bool(m.leader_match)))
            if m.collapse_flag is not None:
                mlflow.log_metric("collapse_flag", float(bool(m.collapse_flag)))
            mlflow.log_param("region_id", report.region_id)
            mlflow.log_param("contest_id", report.contest_id)
            for k, v in (report.sim_params or {}).items():
                try:
                    mlflow.log_param(f"sim.{k}", v)
                except Exception:
                    pass
            return active.info.run_id
    except Exception as exc:  # pragma: no cover — tracking server 불가 시
        log.warning("MLflow log skipped: %s", exc)
        return None


async def run_validation(
    region_id: str,
    train_window: TimeWindow,
    test_window: TimeWindow,
    sim_params: Mapping[str, Any],
    *,
    runner: ScenarioRunner,
    firewall: FirewallEnforcer | None = None,
    contest_id: Optional[str] = None,
    mlflow_run_id: Optional[str] = None,
    notes: str = "",
) -> ValidationReport:
    """Hidden-label hold-out 검증 1회.

    runner 는 caller 가 ElectionEnv.run() 을 wrapping 한 코루틴. test 환경에서는
    stub 로 ScenarioResult 만 만들어 넘긴다.
    """
    # 1) split 일관성 — make_split 결과와 비교 (윈도우가 calendar 와 충돌하면 raise)
    split = make_split(region_id)
    if train_window.end > split.election_date:
        raise ValueError(
            f"train_window.end {train_window.end} > election_date {split.election_date}"
        )

    # 2) firewall — test_window.start 를 cutoff 로 사용
    cutoff_ts = dt.datetime.combine(test_window.start, dt.time.min, tzinfo=dt.timezone.utc)
    firewall_passed = True
    if firewall is not None:
        try:
            firewall.enforce(region_id, cutoff_ts)
        except Exception:
            # FirewallViolation 은 호출자에게 전파 (catch 하지 않음)
            raise

    # 3) ElectionEnv 실행 (runner 위임)
    result = await runner(region_id, train_window, test_window, dict(sim_params))

    # 4) hidden-label 추출 후 evaluate
    official = _to_official_dict(result)
    metrics = evaluate_scenario_result(result, official=official or None)

    # 5) ValidationReport
    cal = load_election_calendar()
    win = cal.get(region_id)
    contest = contest_id or win.election_id
    n_personas = None
    n_timesteps = None
    if result.meta:
        meta_d = result.meta.model_dump() if hasattr(result.meta, "model_dump") else {}
        n_personas = meta_d.get("n_personas") or meta_d.get("persona_n")
        n_timesteps = meta_d.get("timesteps") or meta_d.get("n_timesteps")

    report = ValidationReport(
        region_id=region_id,
        contest_id=contest,
        train_window=train_window,
        test_window=test_window,
        sim_params=dict(sim_params),
        metrics=metrics,
        n_personas=n_personas if isinstance(n_personas, int) else None,
        n_timesteps=n_timesteps if isinstance(n_timesteps, int) else None,
        firewall_passed=firewall_passed,
        notes=notes,
    )

    mlf_id = _maybe_log_mlflow(report, mlflow_run_id=mlflow_run_id)
    if mlf_id:
        report = report.model_copy(update={"mlflow_run_id": mlf_id})
    return report


def run_validation_sync(*args: Any, **kwargs: Any) -> ValidationReport:
    """Sync wrapper — pytest / CLI 호출용."""
    return asyncio.run(run_validation(*args, **kwargs))


__all__ = [
    "FirewallEnforcer",
    "ScenarioRunner",
    "run_validation",
    "run_validation_sync",
]
