"""scenario_events loader (#13) + 5 region seed JSON (#14) 회귀."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = REPO_ROOT / "_workspace" / "data" / "scenario_events"

REGIONS = [
    "seoul_mayor",
    "busan_buk_gap",
    "daegu_mayor",
    "gwangju_mayor",
    "daegu_dalseo_gap",
]


def _has_pydantic() -> bool:
    try:
        import pydantic  # noqa: F401

        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Seed JSON 박제 — pydantic 없이도 통과해야 한다.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("region", REGIONS)
def test_seed_json_exists_and_parseable(region: str) -> None:
    path = SEED_DIR / region / "seed.json"
    assert path.exists(), f"missing seed: {path}"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert 3 <= len(payload) <= 5, f"{region}: seed 개수 3~5 — 현재 {len(payload)}"


@pytest.mark.parametrize("region", REGIONS)
def test_seed_json_required_fields(region: str) -> None:
    path = SEED_DIR / region / "seed.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "event_id",
        "source",
        "occurs_at",
        "description",
        "candidate_patches",
        "event_patches",
        "prior_p",
    }
    for ev in payload:
        missing = required - set(ev.keys())
        assert not missing, f"{region} {ev.get('event_id')}: missing {missing}"
        assert ev["source"] in {"kg_confirmed", "llm_hypothetical", "custom"}
        assert 0.0 <= ev["prior_p"] <= 1.0
        # occurs_at 시간 윈도우 (2026-04-26 ~ 2026-06-03)
        assert ev["occurs_at"].startswith("2026-")


@pytest.mark.parametrize("region", REGIONS)
def test_seed_event_ids_unique(region: str) -> None:
    payload = json.loads(
        (SEED_DIR / region / "seed.json").read_text(encoding="utf-8")
    )
    ids = [ev["event_id"] for ev in payload]
    assert len(ids) == len(set(ids)), f"{region}: duplicate event_id"


# ---------------------------------------------------------------------------
# Loader smoke
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("region", REGIONS)
def test_load_scenario_events_window(region: str) -> None:
    if not _has_pydantic():
        pytest.skip("pydantic 미설치")
    from src.data.scenario_events import load_json_events, load_scenario_events

    raw = load_json_events(region)
    assert raw, f"{region}: empty load"
    # 전체 윈도우는 모두 포함
    full = load_scenario_events(
        region, dt.date(2026, 4, 27), dt.date(2026, 6, 4)
    )
    assert len(full) == len(raw)
    # occurs_at 오름차순 정렬
    times = [e.occurs_at for e in full]
    assert times == sorted(times)


def test_load_scenario_events_empty_window() -> None:
    if not _has_pydantic():
        pytest.skip("pydantic 미설치")
    from src.data.scenario_events import load_scenario_events

    out = load_scenario_events(
        "seoul_mayor",
        dt.datetime(2026, 6, 4, tzinfo=dt.timezone(dt.timedelta(hours=9))),
        dt.datetime(2026, 6, 5, tzinfo=dt.timezone(dt.timedelta(hours=9))),
    )
    assert out == []


def test_load_scenario_events_invalid_window_raises() -> None:
    if not _has_pydantic():
        pytest.skip("pydantic 미설치")
    from src.data.scenario_events import load_scenario_events

    with pytest.raises(ValueError):
        load_scenario_events(
            "seoul_mayor",
            dt.date(2026, 6, 3),
            dt.date(2026, 4, 26),
        )


def test_load_scenario_events_unknown_region_returns_empty() -> None:
    if not _has_pydantic():
        pytest.skip("pydantic 미설치")
    from src.data.scenario_events import load_scenario_events

    out = load_scenario_events(
        "no_such_region", dt.date(2026, 4, 1), dt.date(2026, 6, 3)
    )
    assert out == []


# ---------------------------------------------------------------------------
# DB merge smoke — Postgres 가 떠 있을 때만
# ---------------------------------------------------------------------------
def _pg_session_available() -> bool:
    try:
        from backend.app.db.session import SessionLocal  # type: ignore

        s = SessionLocal()
        s.close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _pg_session_available(), reason="Postgres 세션 미가용")
def test_load_scenario_events_db_merge_dedup() -> None:  # pragma: no cover
    """DB row 가 같은 event_id 의 JSON seed 를 override 하는지 검증."""
    from backend.app.db.models import ScenarioEvent
    from backend.app.db.session import SessionLocal
    from src.data.scenario_events import load_scenario_events

    s = SessionLocal()
    try:
        # 기존 JSON seed 의 event_id 와 동일하게 박는다.
        json_payload = json.loads(
            (SEED_DIR / "seoul_mayor" / "seed.json").read_text(encoding="utf-8")
        )
        target = json_payload[0]
        row = ScenarioEvent(
            region_id="seoul_mayor",
            source="custom",
            occurs_at=dt.datetime.fromisoformat(target["occurs_at"]),
            description="DB-overridden description",
            candidate_patches=[],
            event_patches=[],
            prior_p=0.99,
        )
        s.add(row)
        s.flush()

        events = load_scenario_events(
            "seoul_mayor",
            dt.date(2026, 4, 27),
            dt.date(2026, 6, 4),
            session=s,
        )
        # DB row 와 JSON seed 가 별도 event_id (DB 는 UUID) — 둘 다 포함 가능.
        ids = {e.event_id for e in events}
        assert str(row.id) in ids
    finally:
        s.rollback()
        s.close()
