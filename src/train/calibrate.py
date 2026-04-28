"""Phase 6 calibration — Stage 1 (Optuna TPE) + Stage 2 (prompt variants).

Stage 1 — hyperparameter grid:
    n_trials=30 trials. Param space loaded from
    `_workspace/contracts/calibration_space.json`. 각 trial 은
    `validation_harness.run_validation` 을 호출해 ValidationReport 를 받고
    `scoring.score_metrics` 로 점수 산출. MLflow log_param/log_metric.

Stage 2 — prompt template variants:
    Stage 1 best params 고정. 3..5 wording variant 를 LLM-judge pairwise 로
    비교 → Bradley-Terry 선호도 점수 → 최고 wording. 본 모듈은 entrypoint 만
    제공하고 핵심 로직은 `src.train.llm_judge` 에 위임한다.

CLI:
    python -m src.train.calibrate --stage 1 --regions seoul_mayor --n-trials 30
    python -m src.train.calibrate --stage 2 --regions seoul_mayor --variants v1 v2 v3
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Mapping

from src.data.temporal_split import make_split
from src.eval.validation_harness import (
    FirewallEnforcer,
    ScenarioRunner,
    run_validation,
)
from src.schemas.validation_report import ValidationReport
from src.train.scoring import (
    DEFAULT_SPACE_PATH,
    load_calibration_space,
    score_metrics,
)

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
CALIBRATION_OUT_DIR = REPO_ROOT / "_workspace" / "contracts" / "calibration"


@dataclass
class TrialResult:
    trial_id: int
    params: dict[str, Any]
    score: float
    report: ValidationReport


def _suggest_random(space: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    """Optuna 미설치 시 fallback random search sampler."""
    out: dict[str, Any] = {}
    for name, spec in space["params"].items():
        if spec["type"] == "float":
            out[name] = rng.uniform(spec["low"], spec["high"])
        elif spec["type"] == "int":
            out[name] = rng.randint(spec["low"], spec["high"])
        else:
            raise ValueError(f"unsupported param type: {spec['type']!r} ({name})")
    return out


def _maybe_mlflow_log(
    region_id: str, trial: TrialResult, *, run_name: str | None = None
) -> str | None:
    try:
        import mlflow  # type: ignore[import-not-found]
    except Exception:  # pragma: no cover
        return None
    try:
        with mlflow.start_run(run_name=run_name or f"{region_id}_stage1_t{trial.trial_id}") as active:
            mlflow.log_param("region_id", region_id)
            for k, v in trial.params.items():
                mlflow.log_param(f"sim.{k}", v)
            mlflow.log_metric("score", trial.score)
            m = trial.report.metrics
            for fname in ("mae", "rmse", "brier", "ece", "js_divergence"):
                v = getattr(m, fname, None)
                if v is not None:
                    mlflow.log_metric(fname, float(v))
            if m.leader_match is not None:
                mlflow.log_metric("leader_match", float(bool(m.leader_match)))
            return active.info.run_id
    except Exception as exc:  # pragma: no cover
        log.warning("MLflow log skipped: %s", exc)
        return None


async def run_stage1(
    region_id: str,
    *,
    runner: ScenarioRunner,
    n_trials: int = 30,
    space: dict[str, Any] | None = None,
    firewall: FirewallEnforcer | None = None,
    seed: int = 0,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """Stage 1 calibration — n_trials TPE search → best params artifact."""
    space = space or load_calibration_space()
    out_dir = out_dir or CALIBRATION_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    split = make_split(region_id)

    try:
        import optuna  # type: ignore[import-not-found]

        sampler = optuna.samplers.TPESampler(seed=seed)
        study = optuna.create_study(direction="maximize", sampler=sampler)
        trials: list[TrialResult] = []

        async def _eval_params(trial_id: int, params: dict[str, Any]) -> TrialResult:
            report = await run_validation(
                region_id,
                split.train_rolling_2026,
                split.validation_holdout,
                params,
                runner=runner,
                firewall=firewall,
            )
            score = score_metrics(report.metrics, weights=space["scoring"]["weights"])
            tr = TrialResult(trial_id=trial_id, params=params, score=score, report=report)
            _maybe_mlflow_log(region_id, tr)
            return tr

        # Optuna 는 동기 인터페이스이므로 trial 별 asyncio.run 으로 bridge.
        def _objective(trial: "optuna.Trial") -> float:  # type: ignore[name-defined]
            params: dict[str, Any] = {}
            for name, spec in space["params"].items():
                if spec["type"] == "float":
                    params[name] = trial.suggest_float(name, spec["low"], spec["high"])
                elif spec["type"] == "int":
                    params[name] = trial.suggest_int(name, spec["low"], spec["high"])
                else:
                    raise ValueError(f"unsupported param type: {spec['type']!r}")
            tr = asyncio.get_event_loop().run_until_complete(  # pragma: no cover
                _eval_params(trial.number, params)
            )
            trials.append(tr)
            return tr.score

        # nested-loop 회피: Optuna 호출 자체를 thread 로 격리해 새 event loop 생성
        import functools

        await asyncio.to_thread(
            functools.partial(study.optimize, _objective, n_trials=n_trials)
        )
        best = max(trials, key=lambda t: t.score)
        sampler_name = "TPE"
    except ImportError:
        # Fallback: random search (해커톤 환경에서 optuna 미설치 시 회귀 대비)
        rng = random.Random(seed)
        trials = []
        for i in range(n_trials):
            params = _suggest_random(space, rng)
            report = await run_validation(
                region_id,
                split.train_rolling_2026,
                split.validation_holdout,
                params,
                runner=runner,
                firewall=firewall,
            )
            score = score_metrics(report.metrics, weights=space["scoring"]["weights"])
            tr = TrialResult(trial_id=i, params=params, score=score, report=report)
            _maybe_mlflow_log(region_id, tr)
            trials.append(tr)
        best = max(trials, key=lambda t: t.score)
        sampler_name = "random_fallback"

    artifact = {
        "schema_version": "v1",
        "region_id": region_id,
        "sampler": sampler_name,
        "n_trials": len(trials),
        "best_params": best.params,
        "best_score": best.score,
        "best_trial_id": best.trial_id,
        "best_metrics": best.report.metrics.model_dump(),
        "scoring_weights": space["scoring"]["weights"],
    }
    out_path = out_dir / f"{region_id}_stage1_best.json"
    out_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2))
    log.info("[%s] stage1 best score=%.4f params=%s -> %s",
             region_id, best.score, best.params, out_path)
    return artifact


async def run_stage2(
    region_id: str,
    *,
    runner: ScenarioRunner,
    variants: list[str] | None = None,
    out_dir: Path | None = None,
    judge: Callable[[str, str, str], Awaitable[float]] | None = None,
) -> dict[str, Any]:
    """Stage 2 — prompt template variant comparison via LLM-judge.

    judge(variant_a, variant_b, region_id) -> float in [0, 1] (P(a beats b)).
    None 이면 src.train.llm_judge.default_judge 를 사용한다.
    """
    from src.train import llm_judge

    out_dir = out_dir or CALIBRATION_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    variants = variants or list(llm_judge.DEFAULT_VARIANTS.keys())
    if not variants:
        raise ValueError("variants must be non-empty")

    judge_fn = judge or llm_judge.default_judge
    bt_scores = await llm_judge.bradley_terry_pairwise(variants, judge_fn, region_id=region_id)
    best = max(bt_scores.items(), key=lambda kv: kv[1])
    best_variant = best[0]

    artifact_path = out_dir / f"{region_id}_stage2_template.txt"
    artifact_path.write_text(
        llm_judge.DEFAULT_VARIANTS.get(best_variant, best_variant), encoding="utf-8"
    )
    summary = {
        "region_id": region_id,
        "variants": variants,
        "bt_scores": bt_scores,
        "best_variant": best_variant,
        "template_path": (
            str(artifact_path.relative_to(REPO_ROOT))
            if REPO_ROOT in artifact_path.parents else str(artifact_path)
        ),
    }
    summary_path = out_dir / f"{region_id}_stage2_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    log.info("[%s] stage2 best=%s -> %s", region_id, best_variant, artifact_path)
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_real_runner() -> ScenarioRunner:
    """CLI default runner — src.sim.run_scenario.run_region 위임 (heavy).

    해커톤 freeze 단계에서는 actual run 을 doing 하기 어려우므로, 본 함수는
    호출 시점에 lazy-import 한다. 실제 runner 는 cutoff 적용까지는 미구현 —
    Phase 6 후속 작업으로 남겨둔다 (TODO: cutoff override hook).
    """
    raise NotImplementedError(
        "calibrate CLI default runner 는 별도 통합이 필요. "
        "프로그래밍 인터페이스 (run_stage1 의 runner=) 로 사용하라."
    )


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=int, choices=[1, 2], required=True)
    parser.add_argument("--regions", nargs="+", required=True)
    parser.add_argument("--n-trials", type=int, default=30)
    parser.add_argument("--variants", nargs="*", default=None)
    parser.add_argument("--space", type=Path, default=DEFAULT_SPACE_PATH)
    args = parser.parse_args(argv)

    runner = _build_real_runner()  # raises — CLI 사용 시 hook 필요
    space = load_calibration_space(args.space)
    for rid in args.regions:
        if args.stage == 1:
            asyncio.run(run_stage1(rid, runner=runner, n_trials=args.n_trials, space=space))
        else:
            asyncio.run(run_stage2(rid, runner=runner, variants=args.variants))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())


__all__ = ["run_stage1", "run_stage2", "TrialResult", "CALIBRATION_OUT_DIR"]
