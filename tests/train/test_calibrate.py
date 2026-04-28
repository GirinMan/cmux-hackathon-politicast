"""calibrate Stage 1 / Stage 2 — Phase 6 회귀 테스트.

Optuna / MLflow 가 환경에 없어도 본 회귀는 통과해야 한다 (random fallback +
silent skip).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.eval.validation_harness import FirewallEnforcer  # noqa: F401
from src.schemas.result import (
    FinalOutcome,
    Meta,
    OfficialPollValidation,
    ScenarioResult,
    ValidationByCandidate,
)
from src.train import llm_judge
from src.train.calibrate import run_stage1, run_stage2
from src.train.scoring import load_calibration_space, score_metrics
from src.schemas.result import ValidationMetrics


def _toy_runner_factory():
    """params 가 정답 (0.1, 0.05) 에 가까울수록 좋은 점수를 주는 toy."""
    target = {"bandwagon_weight": 0.1, "second_order_weight": 0.05,
              "influence_decay": 0.9, "persona_diversity_temp": 1.0}

    async def runner(region_id, train_w, test_w, sim_params):
        # 후보 a 가 진짜 winner. params 가 target 에서 멀수록 a 의 share 가 0.5 로 회귀.
        dist = sum((sim_params.get(k, 0) - v) ** 2 for k, v in target.items()) ** 0.5
        a_share = max(0.05, 0.7 - 0.4 * dist)
        b_share = 1.0 - a_share
        return ScenarioResult(
            scenario_id="toy",
            region_id=region_id,
            contest_id=f"{region_id}_2026",
            timesteps=4,
            final_outcome=FinalOutcome(
                vote_share_by_candidate={"a": a_share, "b": b_share},
                winner="a",
            ),
            poll_trajectory=[],
            meta=Meta(
                official_poll_validation=OfficialPollValidation(
                    target_series="poll_consensus_daily",
                    cutoff_ts="2026-05-27T00:00:00+00:00",
                    by_candidate={
                        "a": ValidationByCandidate(simulated_share=a_share, official_consensus=0.55),
                        "b": ValidationByCandidate(simulated_share=b_share, official_consensus=0.45),
                    },
                )
            ),
        )

    return runner


def test_score_metrics_monotone() -> None:
    good = ValidationMetrics(mae=0.02, leader_match=True, js_divergence=0.01)
    bad = ValidationMetrics(mae=0.4, leader_match=False, js_divergence=0.5)
    s_good = score_metrics(good)
    s_bad = score_metrics(bad)
    assert 0.9 < s_good <= 1.0
    assert 0.0 <= s_bad < 0.4
    assert s_good > s_bad


def test_score_metrics_handles_missing() -> None:
    empty = ValidationMetrics()
    s = score_metrics(empty)
    # leader_match=None → 0, mae=None → worst (1.0), js=None → worst (1.0). score=0.
    assert s == pytest.approx(0.0, abs=1e-6)


def test_load_calibration_space_present() -> None:
    space = load_calibration_space()
    assert "params" in space and set(space["params"].keys()) >= {
        "bandwagon_weight", "second_order_weight", "influence_decay", "persona_diversity_temp"
    }
    assert space["scoring"]["higher_is_better"] is True


def test_run_stage1_writes_artifact(tmp_path: Path) -> None:
    runner = _toy_runner_factory()
    import asyncio

    artifact = asyncio.run(
        run_stage1(
            "seoul_mayor",
            runner=runner,
            n_trials=8,
            firewall=None,
            seed=42,
            out_dir=tmp_path,
        )
    )
    assert artifact["region_id"] == "seoul_mayor"
    assert artifact["n_trials"] == 8
    assert 0.0 <= artifact["best_score"] <= 1.0
    out_file = tmp_path / "seoul_mayor_stage1_best.json"
    assert out_file.exists()
    payload = json.loads(out_file.read_text())
    assert set(payload["best_params"].keys()) >= {"bandwagon_weight", "influence_decay"}


def test_run_stage1_search_finds_better_than_worst(tmp_path: Path) -> None:
    """8 trial 만으로도 random worst 보다는 나아야 한다."""
    import asyncio

    runner = _toy_runner_factory()
    artifact = asyncio.run(
        run_stage1(
            "seoul_mayor",
            runner=runner,
            n_trials=8,
            firewall=None,
            seed=0,
            out_dir=tmp_path,
        )
    )
    # toy runner 의 best 영역에서는 leader_match=True, mae<0.05 가능 → score ≥ 0.6
    assert artifact["best_score"] >= 0.4


def test_bradley_terry_simple_three_way() -> None:
    import asyncio

    async def constant_judge(a, b, region_id):
        # v3 가 항상 70% 로 v1, v2 를 이긴다고 가정
        if "v3" in (DEFAULT_LABEL_MAP.get(a, "")):
            return 0.7
        if "v3" in (DEFAULT_LABEL_MAP.get(b, "")):
            return 0.3
        return 0.5

    DEFAULT_LABEL_MAP = {v: k for k, v in llm_judge.DEFAULT_VARIANTS.items()}
    scores = asyncio.run(
        llm_judge.bradley_terry_pairwise(
            ["v1_baseline", "v2_neutral_framing", "v3_issue_first"],
            constant_judge,
            region_id="seoul_mayor",
        )
    )
    assert scores["v3_issue_first"] > scores["v1_baseline"]
    assert scores["v3_issue_first"] > scores["v2_neutral_framing"]
    assert abs(sum(scores.values()) - 1.0) < 1e-6


def test_run_stage2_writes_template(tmp_path: Path) -> None:
    import asyncio

    artifact = asyncio.run(
        run_stage2(
            "seoul_mayor",
            runner=lambda *a, **kw: None,  # not used
            variants=["v1_baseline", "v2_neutral_framing", "v3_issue_first"],
            out_dir=tmp_path,
        )
    )
    template_path = tmp_path / "seoul_mayor_stage2_template.txt"
    assert template_path.exists()
    summary_path = tmp_path / "seoul_mayor_stage2_summary.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text())
    assert summary["best_variant"] in summary["variants"]
    assert abs(sum(summary["bt_scores"].values()) - 1.0) < 1e-6
