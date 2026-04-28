"""scenario_events loader — _workspace/data/scenario_events/{region}/*.json
+ DB ``scenario_event`` 테이블 머지.

Phase 6 (pipeline-counterfactual). EventProposer 의 ``CustomJSONProposer`` /
``KGConfirmedProposer`` (DB-side) 가 공통적으로 호출하는 backbone. event_id
기준 dedup (DB row 가 우선 — admin 이 등록한 최신 메타가 정답), 그리고
시간 firewall: ``current_t < occurs_at <= as_of`` 에 해당하는 이벤트만 반환.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path
from typing import Any, Iterable, Optional

from src.schemas.beam_event import BeamEvent

logger = logging.getLogger(__name__)


REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_EVENTS_DIR = REPO_ROOT / "_workspace" / "data" / "scenario_events"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ensure_aware(value: dt.datetime) -> dt.datetime:
    """Naive datetime → assume KST (+09:00) → aware datetime."""
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone(dt.timedelta(hours=9)))
    return value


def _to_datetime(value: Any) -> dt.datetime:
    """Accept datetime / date / ISO 8601 string."""
    if isinstance(value, dt.datetime):
        return _ensure_aware(value)
    if isinstance(value, dt.date):
        return _ensure_aware(dt.datetime.combine(value, dt.time(0, 0)))
    if isinstance(value, str):
        # fromisoformat 은 'Z' 를 직접 처리 못 함 (3.10 이하). 안전하게 변환.
        return _ensure_aware(
            dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        )
    raise TypeError(f"Unsupported datetime value: {value!r}")


def _payload_to_beam_event(payload: dict[str, Any]) -> BeamEvent:
    """Pydantic-validated BeamEvent from a JSON / DB payload."""
    return BeamEvent.model_validate(payload)


# ---------------------------------------------------------------------------
# JSON loader
# ---------------------------------------------------------------------------
def load_json_events(region_id: str) -> list[BeamEvent]:
    """Read every ``*.json`` under ``_workspace/data/scenario_events/{region}``.

    Each file may contain a list of BeamEvent payloads or a single payload.
    Pydantic ``extra="forbid"`` 가 잘못된 키를 잡아낸다.
    """
    region_dir = SCENARIO_EVENTS_DIR / region_id
    if not region_dir.exists():
        logger.debug("scenario_events dir missing: %s", region_dir)
        return []

    events: list[BeamEvent] = []
    for path in sorted(region_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.warning("scenario_events JSON parse failed (%s): %s", path, exc)
            continue
        rows = payload if isinstance(payload, list) else [payload]
        for row in rows:
            try:
                events.append(_payload_to_beam_event(row))
            except Exception as exc:  # pragma: no cover — pydantic ValidationError 등
                logger.warning(
                    "scenario_events row failed validation in %s: %s", path, exc
                )
    return events


# ---------------------------------------------------------------------------
# DB loader
# ---------------------------------------------------------------------------
def load_db_events(
    region_id: str,
    *,
    session: Optional[Any] = None,
) -> list[BeamEvent]:
    """Fetch active ``scenario_event`` rows for ``region_id`` from Postgres.

    PG/SQLAlchemy 가 없는 테스트 환경(또는 session=None) 에서는 빈 리스트
    반환 — JSON-only 모드. session 이 주어지면 ORM ``ScenarioEvent`` 를
    조회한다.
    """
    if session is None:
        return []

    try:
        from backend.app.db.models import ScenarioEvent  # local import — soft dep
    except Exception as exc:  # pragma: no cover
        logger.debug("ScenarioEvent ORM unavailable: %s", exc)
        return []

    try:
        rows = (
            session.query(ScenarioEvent)
            .filter(
                ScenarioEvent.region_id == region_id,
                ScenarioEvent.is_active.is_(True),
            )
            .all()
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("scenario_event DB query failed: %s", exc)
        return []

    out: list[BeamEvent] = []
    for r in rows:
        payload = {
            "event_id": str(r.id),
            "source": r.source,
            "occurs_at": r.occurs_at,
            "description": r.description,
            "candidate_patches": list(r.candidate_patches or []),
            "event_patches": list(r.event_patches or []),
            "prior_p": float(r.prior_p),
            "metadata": dict(r.event_metadata or {}),
        }
        try:
            out.append(_payload_to_beam_event(payload))
        except Exception as exc:  # pragma: no cover
            logger.warning("scenario_event row %s failed validation: %s", r.id, exc)
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def _dedup_by_event_id(
    primary: Iterable[BeamEvent],
    secondary: Iterable[BeamEvent],
) -> list[BeamEvent]:
    """``primary`` 가 우선 — 같은 ``event_id`` 가 secondary 에 있으면 무시."""
    seen: dict[str, BeamEvent] = {}
    for ev in primary:
        seen[ev.event_id] = ev
    for ev in secondary:
        seen.setdefault(ev.event_id, ev)
    # 정렬: occurs_at 오름차순 — Sankey 위→아래 시간 정렬과 일치.
    return sorted(seen.values(), key=lambda e: e.occurs_at)


def load_scenario_events(
    region_id: str,
    current_t: dt.datetime | dt.date,
    as_of: dt.datetime | dt.date,
    *,
    session: Optional[Any] = None,
) -> list[BeamEvent]:
    """Load scenario events for a region, time-filtered to (current_t, as_of].

    Args:
        region_id: e.g. ``"seoul_mayor"``.
        current_t: lower bound (exclusive) — beam search 의 현재 leaf 시각.
        as_of: upper bound (inclusive) — election cutoff 또는 트리 빌드 시각.
        session: optional SQLAlchemy session — DB-registered events 머지에 사용.

    Returns:
        Time-filtered, dedup'd, sorted ``list[BeamEvent]``.
    """
    lo = _to_datetime(current_t)
    hi = _to_datetime(as_of)
    if lo > hi:
        raise ValueError(
            f"current_t ({lo.isoformat()}) > as_of ({hi.isoformat()}) — invalid window"
        )

    db_events = load_db_events(region_id, session=session)
    json_events = load_json_events(region_id)

    # DB event_id 기준 우선 (admin override). JSON seed 가 동일 event_id 면
    # DB 가 이긴다 — 운영 중 admin 이 메타 갱신했을 가능성 보호.
    merged = _dedup_by_event_id(db_events, json_events)

    return [
        ev
        for ev in merged
        if lo < _ensure_aware(ev.occurs_at) <= hi
    ]


__all__ = [
    "SCENARIO_EVENTS_DIR",
    "load_db_events",
    "load_json_events",
    "load_scenario_events",
]
