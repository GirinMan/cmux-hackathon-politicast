"""election_env.py 의 시간 도메인 정리(#24) 회귀 가드.

- '2026-06-03' 인라인 fallback 제거
- base_date 가 today() 가 아니라 scenario.simulation.t_start / ElectionCalendar 에서 옴
- ConsensusParams.fieldwork_window_days 가 적용됨
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = REPO_ROOT / "src" / "sim" / "election_env.py"


def test_election_env_no_hardcoded_2026_06_03() -> None:
    src = ENV_PATH.read_text(encoding="utf-8")
    # '2026-06-03' 리터럴이 election_env.py 에 더 이상 존재하면 안 됨.
    assert "2026-06-03" not in src, "election_env.py: '2026-06-03' 하드코딩 잔존"
    # date.today() 도 base_date 시드로 더 이상 사용되지 않아야 함.
    assert "dt.date.today()" not in src or "_resolve_base_date" in src


def test_election_env_imports_calendar_helpers() -> None:
    src = ENV_PATH.read_text(encoding="utf-8")
    assert "load_sim_constants" in src
    assert "now_kst" in src or "from src.utils.tz" in src


def test_resolve_base_date_uses_scenario_t_start() -> None:
    """ElectionEnv._resolve_base_date 가 scenario.simulation.t_start 를 우선."""
    from src.sim.election_env import ElectionEnv

    env = ElectionEnv.__new__(ElectionEnv)
    env.region_id = "seoul_mayor"
    env.scenario_meta = {"simulation": {"t_start": "2026-04-19T00:00:00+09:00"}}
    assert env._resolve_base_date() == dt.date(2026, 4, 19)


def test_resolve_base_date_falls_back_to_calendar() -> None:
    from src.sim.election_env import ElectionEnv

    env = ElectionEnv.__new__(ElectionEnv)
    env.region_id = "seoul_mayor"
    env.scenario_meta = {}
    # ElectionCalendar.cutoff_for(seoul_mayor) = 2026-06-02
    assert env._resolve_base_date() == dt.date(2026, 6, 2)


def test_consensus_from_scenario_uses_fieldwork_window() -> None:
    """day=0 짜리 poll → poll_date == e_date - fieldwork_window_days."""
    from src.sim.election_env import ElectionEnv
    from src.schemas.sim_constants import load_sim_constants

    fw = load_sim_constants().consensus.fieldwork_window_days
    e_date = dt.date(2026, 6, 3)
    expected = (e_date - dt.timedelta(days=fw)).isoformat()

    env = ElectionEnv.__new__(ElectionEnv)
    env.region_id = "seoul_mayor"
    env.scenario_meta = {
        "election_date": "2026-06-03",
        "raw_polls": [
            {"poll_id": "p1", "shares": {"a": 0.6, "b": 0.4},
             "n": 1000, "quality": 1.0, "day": 0},
        ],
    }
    out = env._consensus_from_scenario(dt.date(2026, 6, 3))
    assert out is not None
    shares, ids, latest = out
    assert latest is not None
    assert latest.isoformat() == expected
