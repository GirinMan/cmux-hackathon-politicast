"""Synthetic 5-event / 4-timestep scenario for firewall round-trip tests.

Lifted from the previously-inlined ``src/kg/firewall.py::_make_synthetic_scenario``
(Phase 2, task #27). All timestamps are computed as offsets from a base
``datetime`` returned by the calendar adapter — no absolute date literal.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from src.kg._calendar_adapter import get_default_t_start

SYNTHETIC_REGION_ID = "seoul_mayor"
SYNTHETIC_TIMESTEPS = 4


def _base_date() -> datetime:
    """Anchor for all synthetic timestamps — derived from the active election
    calendar so the fixture moves whenever ``ElectionCalendar`` does."""
    return get_default_t_start()


def make_synthetic_scenario() -> dict[str, Any]:
    """Return a dict in builder's normalized scenario shape.

    Layout:
      base + 1d  → ev_01 (MediaEvent, debate)
      base + 15d → ev_02 (ScandalEvent, education)
      base + 30d → ev_03 (PressConference, housing)
      base + 45d → ev_04 (Verdict, acquittal)
      base + 60d → ev_05 (MediaEvent, D-3 wrap-up)
      base + 20d / 50d → polls

    The 4 timesteps span ``[base, base + 63d]`` so the firewall sees a
    progressive disclosure curve.
    """
    base = _base_date()
    return {
        "scenario_id": "test_seoul_mayor",
        "region_id": SYNTHETIC_REGION_ID,
        "election": {
            "election_id": "ROK_local_test",
            "name": "제9회 전국동시지방선거",
            "date": (base + timedelta(days=63)).isoformat(),
            "type": "local",
        },
        "contest": {
            "contest_id": "seoul_mayor_test",
            "position_type": "metropolitan_mayor",
        },
        "district": {"province": "서울특별시", "district": None, "population": 9700000},
        "parties": [
            {"party_id": "p_dem", "name": "더불어민주당", "ideology": -0.4},
            {"party_id": "p_ppp", "name": "국민의힘", "ideology": 0.5},
        ],
        "candidates": [
            {"candidate_id": "c_kim", "name": "김민주", "party": "p_dem"},
            {"candidate_id": "c_lee", "name": "이보수", "party": "p_ppp"},
        ],
        "issues": [
            {"issue_id": "i_housing", "name": "부동산", "type": "부동산"},
            {"issue_id": "i_edu", "name": "입시정책", "type": "교육"},
        ],
        "frames": [
            {"frame_id": "f_judgement", "label": "정권심판"},
            {"frame_id": "f_stability", "label": "안정호소"},
        ],
        "events": [
            {
                "event_id": "ev_01",
                "type": "MediaEvent",
                "ts": (base + timedelta(days=1)).isoformat(),
                "source": "조선일보",
                "title": "서울시장 후보 1차 토론회 개최",
                "sentiment": 0.0,
                "about": ["c_kim", "c_lee"],
                "mentions": ["i_housing"],
                "frame_id": "f_stability",
            },
            {
                "event_id": "ev_02",
                "type": "ScandalEvent",
                "ts": (base + timedelta(days=15)).isoformat(),
                "source": "한겨레",
                "title": "이보수 후보 자녀 입시 의혹 제기",
                "sentiment": -0.5,
                "severity": 0.7,
                "credibility": 0.5,
                "target_candidate_id": "c_lee",
                "about": ["c_lee"],
                "mentions": ["i_edu"],
                "frame_id": "f_judgement",
            },
            {
                "event_id": "ev_03",
                "type": "PressConference",
                "ts": (base + timedelta(days=30)).isoformat(),
                "source": "민주당",
                "title": "김민주 부동산 공약 발표",
                "sentiment": 0.3,
                "about": ["c_kim"],
                "mentions": ["i_housing"],
                "frame_id": "f_judgement",
                "speaker": "김민주",
                "party_id": "p_dem",
            },
            {
                "event_id": "ev_04",
                "type": "Verdict",
                "ts": (base + timedelta(days=45)).isoformat(),
                "source": "서울중앙지법",
                "title": "이보수 후보 자녀 입시 의혹 1심 무죄",
                "sentiment": 0.2,
                "outcome": "acquittal",
                "target_candidate_id": "c_lee",
                "about": ["c_lee"],
            },
            {
                "event_id": "ev_05",
                "type": "MediaEvent",
                "ts": (base + timedelta(days=60)).isoformat(),
                "source": "JTBC",
                "title": "선거 D-3 종합 분석",
                "sentiment": 0.0,
                "about": ["c_kim", "c_lee"],
            },
        ],
        "polls": [
            {
                "poll_id": 1,
                "ts": (base + timedelta(days=20)).isoformat(),
                "sample_size": 1000,
                "leader_candidate": "c_kim",
                "leader_share": 0.42,
            },
            {
                "poll_id": 2,
                "ts": (base + timedelta(days=50)).isoformat(),
                "sample_size": 1200,
                "leader_candidate": "c_kim",
                "leader_share": 0.46,
            },
        ],
        "simulation": {
            "t_start": base.isoformat(),
            "t_end": (base + timedelta(days=63)).isoformat(),
            "timesteps": SYNTHETIC_TIMESTEPS,
        },
    }
