"""Tests for IssueRegistry + PersonRegistry — load + alias resolve."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.schemas.issue_registry import (
    IssueEntry,
    IssueRegistry,
    load_issue_registry,
)
from src.schemas.person_registry import (
    PersonEntry,
    PersonRegistry,
    load_person_registry,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
ISSUES_PATH = REPO_ROOT / "_workspace" / "data" / "registries" / "issues.json"
PERSONS_PATH = REPO_ROOT / "_workspace" / "data" / "registries" / "persons.json"


# ----- Issues -----------------------------------------------------------------
def test_issues_registry_loads() -> None:
    reg = load_issue_registry()
    assert isinstance(reg, IssueRegistry)
    assert len(reg.issues) >= 10


def test_issues_covers_all_scenario_issue_ids() -> None:
    """Every issue_id appearing in scenarios/*.json must be in the registry."""
    scen_dir = REPO_ROOT / "_workspace" / "data" / "scenarios"
    seen: set[str] = set()
    for p in scen_dir.glob("*.json"):
        if p.stem.startswith("hill_climbing_"):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for issue in data.get("issues", []) or []:
            iid = issue.get("issue_id") or issue.get("id")
            if iid:
                seen.add(iid)
    reg = load_issue_registry()
    known = {e.id for e in reg.issues}
    missing = seen - known
    assert not missing, f"Issue IDs in scenarios not in registry: {missing}"


def test_issues_resolve_by_alias() -> None:
    reg = load_issue_registry()
    out = reg.resolve("이재명 정부 중간평가 관련 코멘트")
    assert out is not None
    assert out.id in {"i_judgement", "i_lee_check"}


def test_issues_resolve_returns_none_on_no_match() -> None:
    reg = load_issue_registry()
    assert reg.resolve("완전히 무관한 텍스트 zzz") is None


def test_issue_entry_all_names_includes_id_and_aliases() -> None:
    e = IssueEntry(id="i_x", name="X", aliases=["x_alias"])
    assert "i_x" in e.all_names()
    assert "X" in e.all_names()
    assert "x_alias" in e.all_names()


# ----- Persons ----------------------------------------------------------------
def test_persons_registry_loads() -> None:
    reg = load_person_registry()
    assert isinstance(reg, PersonRegistry)
    assert len(reg.persons) >= 10


def test_persons_required_keys_present() -> None:
    reg = load_person_registry()
    ids = {p.id for p in reg.persons}
    # 시나리오에서 자주 등장하는 비후보 정치인.
    for k in ("p_lee_jaemyung", "p_han_donghoon", "p_kim_boo_kyum"):
        assert k in ids


def test_persons_resolve_by_name() -> None:
    reg = load_person_registry()
    out = reg.resolve("이재명 대통령이 어제 회의를 주재했다")
    assert out is not None
    assert out.id == "p_lee_jaemyung"


def test_persons_resolve_by_hanja_alias() -> None:
    reg = load_person_registry()
    out = reg.resolve("韓東勳 says ...")
    assert out is not None
    assert out.id == "p_han_donghoon"


def test_persons_find_by_id() -> None:
    reg = load_person_registry()
    e = reg.find_by_id("p_lee_jaemyung")
    assert e is not None
    assert e.name == "이재명"


def test_persons_resolve_returns_none_on_empty() -> None:
    reg = load_person_registry()
    assert reg.resolve("") is None


def test_person_entry_party_id_optional() -> None:
    e = PersonEntry(id="p_x", name="X")
    assert e.party_id is None
