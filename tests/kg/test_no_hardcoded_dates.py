"""Task #28 — regression gate: ``src/kg/`` must contain ZERO YYYY-MM-DD
literals (regex ``\\b20\\d\\d-\\d\\d-\\d\\d\\b``).

Time defaults must flow through ``src.kg._calendar_adapter`` (which itself
delegates to eval-extender's ``ElectionCalendar`` when present, with a
last-resort fallback constant kept in ``datetime(YYYY, M, D)`` form so it
remains regex-blind).

Why a regex gate? It is cheap, explicit, and prevents future authors from
re-inlining absolute dates in comments / fixtures / fallbacks — the most
common Phase-1 regression pattern.

The adapter itself (``_calendar_adapter.py``) is whitelisted because it is
the documented single point of fallback. Anything else under ``src/kg/`` —
modules, comments, docstrings — must stay clean.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


_DATE_RE = re.compile(r"\b20\d\d-\d\d-\d\d\b")
_KG_DIR = Path(__file__).resolve().parents[1].parent / "src" / "kg"
_WHITELIST_FILES: frozenset[str] = frozenset({
    "_calendar_adapter.py",
})


def _kg_python_files() -> list[Path]:
    return sorted(p for p in _KG_DIR.rglob("*.py") if "__pycache__" not in p.parts)


def test_kg_module_has_no_yyyy_mm_dd_literals():
    offenders: list[str] = []
    for path in _kg_python_files():
        if path.name in _WHITELIST_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _DATE_RE.search(line):
                offenders.append(f"{path.relative_to(_KG_DIR.parent.parent)}:{lineno}: {line.strip()}")
    if offenders:
        pytest.fail(
            "src/kg/ contains hardcoded YYYY-MM-DD literals (route through "
            "src.kg._calendar_adapter instead):\n  " + "\n  ".join(offenders)
        )


def test_calendar_adapter_is_only_whitelisted_file():
    """Sanity-check the whitelist hasn't grown silently."""
    assert _WHITELIST_FILES == frozenset({"_calendar_adapter.py"}), (
        "Whitelist should remain a single file. Add an explicit comment "
        "explaining any new entry."
    )
