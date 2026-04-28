"""Calendar lookup adapter for the KG layer.

Phase 2 (#26): KG must not embed any absolute date literal. All defaults
flow through ``ElectionCalendar`` (eval-extender's #21 — Pydantic model +
``_workspace/data/registries/election_calendar.json`` registry).

While #21 is in flight, this adapter:

1. Tries to import the real ``src.schemas.calendar.ElectionCalendar``.
2. Falls back to a built-in resolver that reads the same registry JSON
   directly, and as a last resort scans ``_workspace/data/scenarios/*.json``
   for an ``election_date`` / ``simulation.t_end`` field.

The KG modules import ONLY this adapter — swapping to the real Pydantic
model later is a one-line import change.

Public API
----------

* :func:`get_election_window(region_id)` → ``ElectionWindow`` (dataclass with
  ``election_date`` / ``t_start`` / ``t_end``).
* :func:`get_default_election_date()` → ``datetime``: registry-wide default
  used when no region context is available.
* :func:`get_default_t_start()` → ``datetime``: default simulation start
  (election_date - 40d unless overridden in the registry).
* :func:`get_default_cutoff()` → ``datetime``: ``election_date - 1 day`` —
  the conservative ts the Perplexity ingest uses to drop future leaks.

All accessors are pure functions over an LRU-cached registry; tests can
override behaviour by setting ``POLITIKAST_ELECTION_CALENDAR_PATH`` to a
JSON path, or by monkey-patching the cache via :func:`reset_cache`.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_REGISTRY_PATH = (
    _REPO_ROOT / "_workspace" / "data" / "registries" / "election_calendar.json"
)
_DEFAULT_SCENARIO_DIR = _REPO_ROOT / "_workspace" / "data" / "scenarios"

# Last-resort defaults — used only if the registry is missing AND no scenario
# JSON in the workspace carries an election_date. Kept here (single file) so
# the rest of the KG module set is literal-date-free per #28's grep gate.
_FALLBACK_ELECTION_DATE: datetime = datetime(2026, 6, 3)
_FALLBACK_PRE_ELECTION_DAYS: int = 40


@dataclass(frozen=True)
class ElectionWindow:
    """Per-region election window. Mirrors what eval-extender's
    ``src.schemas.calendar.ElectionWindow`` is expected to expose."""

    region_id: str
    election_date: datetime
    t_start: datetime
    t_end: datetime

    @property
    def cutoff(self) -> datetime:
        """Conservative firewall cutoff — election_date - 1 day."""
        return self.election_date - timedelta(days=1)


def _registry_path() -> Path:
    override = os.environ.get("POLITIKAST_ELECTION_CALENDAR_PATH")
    return Path(override) if override else _DEFAULT_REGISTRY_PATH


@lru_cache(maxsize=1)
def _load_registry() -> dict[str, Any]:
    """Load registry JSON if present. Returns ``{"regions": {}}`` on miss."""
    # 1) Real Pydantic ElectionCalendar (eval-extender #21). The shipping
    #    module exposes ``load_election_calendar()`` (lru-cached factory) plus
    #    ``ElectionCalendar.get(region_id)`` / ``election_date_for`` /
    #    ``cutoff_for``. We probe both the loader function and any classmethod
    #    fallback to stay tolerant of future renames.
    cal: Any = None
    try:
        from src.schemas import calendar as _cal_mod  # type: ignore
        loader = getattr(_cal_mod, "load_election_calendar", None)
        if callable(loader):
            override = os.environ.get("POLITIKAST_ELECTION_CALENDAR_PATH")
            cal = loader(override) if override else loader()
        else:
            ElectionCalendar = getattr(_cal_mod, "ElectionCalendar", None)
            if ElectionCalendar is not None:
                for attr in ("load_default", "load"):
                    fn = getattr(ElectionCalendar, attr, None)
                    if callable(fn):
                        cal = fn()
                        break
    except Exception as exc:  # noqa: BLE001
        log.warning("[kg/calendar] ElectionCalendar load failed: %s", exc)

    if cal is not None:
        return {"_pydantic": cal}

    # 2) Raw registry JSON.
    path = _registry_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            log.warning("[kg/calendar] registry %s parse failed: %s", path, exc)

    # 3) Scenario-derived best effort.
    return _scan_scenarios()


def _scan_scenarios() -> dict[str, Any]:
    """Build a minimal registry from scenario JSONs (election_date /
    simulation.t_start / simulation.t_end). Last-resort fallback so KG keeps
    working without #21's registry on disk."""
    out: dict[str, Any] = {"regions": {}, "default": {}}
    if not _DEFAULT_SCENARIO_DIR.exists():
        return out
    election_dates: list[datetime] = []
    for path in sorted(_DEFAULT_SCENARIO_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, list):
            items = data
        else:
            items = [data]
        for s in items:
            region_id = s.get("region_id")
            if not region_id:
                continue
            ed_raw = (
                s.get("election_date")
                or (s.get("election") or {}).get("date")
                or (s.get("simulation") or {}).get("t_end")
            )
            ts_raw = (s.get("simulation") or {}).get("t_start")
            te_raw = (s.get("simulation") or {}).get("t_end") or ed_raw
            ed = _safe_parse(ed_raw)
            if ed is None:
                continue
            election_dates.append(ed)
            ts = _safe_parse(ts_raw) or (ed - timedelta(days=_FALLBACK_PRE_ELECTION_DAYS))
            te = _safe_parse(te_raw) or ed
            out["regions"][region_id] = {
                "election_date": ed.isoformat(),
                "t_start": ts.isoformat(),
                "t_end": te.isoformat(),
            }
    if election_dates:
        out["default"] = {"election_date": max(election_dates).isoformat()}
    return out


def _safe_parse(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo is not None else value
    # ElectionCalendar (eval-extender #21) stores ``election_date`` as
    # ``datetime.date``. Promote to midnight datetime for consistency with
    # the rest of the KG stack which uses naive ``datetime``.
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    if isinstance(value, str):
        s = value.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            try:
                dt = datetime.fromisoformat(s.split("T", 1)[0])
            except ValueError:
                return None
        return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt
    return None


def reset_cache() -> None:
    """Drop the LRU cache. Tests use this when they monkey-patch the env
    variable or write a new registry file mid-run."""
    _load_registry.cache_clear()


# ---------------------------------------------------------------------------
# Public accessors
# ---------------------------------------------------------------------------
def get_election_window(region_id: str) -> Optional[ElectionWindow]:
    reg = _load_registry()

    pyd = reg.get("_pydantic")
    if pyd is not None:
        # Try ``cal.get(region_id)`` (eval-extender's API) then a generic
        # ``cal.lookup(region_id)`` for forward-compat.
        win_obj: Any = None
        for attr in ("get", "lookup"):
            fn = getattr(pyd, attr, None)
            if callable(fn):
                try:
                    win_obj = fn(region_id)
                    break
                except Exception:
                    win_obj = None
        if win_obj is not None:
            ed = _safe_parse(getattr(win_obj, "election_date", None))
            ts = _safe_parse(
                getattr(win_obj, "t_start", None)
                or getattr(win_obj, "fieldwork_start", None)
            )
            te = _safe_parse(
                getattr(win_obj, "t_end", None)
                or getattr(win_obj, "election_date", None)
            )
            if ed is not None:
                return ElectionWindow(
                    region_id=region_id,
                    election_date=ed,
                    t_start=ts or (ed - timedelta(days=_FALLBACK_PRE_ELECTION_DAYS)),
                    t_end=te or ed,
                )

    info = (reg.get("regions") or {}).get(region_id) or {}
    ed = _safe_parse(info.get("election_date"))
    if ed is None:
        return None
    ts = _safe_parse(info.get("t_start")) or (
        ed - timedelta(days=_FALLBACK_PRE_ELECTION_DAYS)
    )
    te = _safe_parse(info.get("t_end")) or ed
    return ElectionWindow(
        region_id=region_id, election_date=ed, t_start=ts, t_end=te,
    )


def get_default_election_date() -> datetime:
    reg = _load_registry()

    pyd = reg.get("_pydantic")
    if pyd is not None:
        # Probe explicit defaults first, then fall back to the max
        # election_date across registered windows.
        for attr in ("default_election_date", "default_date"):
            fn = getattr(pyd, attr, None)
            if callable(fn):
                try:
                    val = _safe_parse(fn())
                    if val is not None:
                        return val
                except Exception:
                    pass
        windows = getattr(pyd, "windows", None) or {}
        ds: list[datetime] = []
        for win in windows.values():
            d = _safe_parse(getattr(win, "election_date", None))
            if d is not None:
                ds.append(d)
        if ds:
            return max(ds)

    default_block = reg.get("default") or {}
    ed = _safe_parse(default_block.get("election_date"))
    if ed is not None:
        return ed
    # Fallback: max election_date across all regions in the registry.
    ds: list[datetime] = []
    for info in (reg.get("regions") or {}).values():
        d = _safe_parse((info or {}).get("election_date"))
        if d is not None:
            ds.append(d)
    if ds:
        return max(ds)
    return _FALLBACK_ELECTION_DATE


def get_default_t_start() -> datetime:
    return get_default_election_date() - timedelta(days=_FALLBACK_PRE_ELECTION_DAYS)


def get_default_cutoff() -> datetime:
    """Conservative ingest cutoff — election_date - 1 day, end-of-day."""
    ed = get_default_election_date()
    cutoff = ed - timedelta(days=1)
    return cutoff.replace(hour=23, minute=59, second=59, microsecond=0)
