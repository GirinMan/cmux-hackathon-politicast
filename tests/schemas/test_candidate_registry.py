"""CandidateRegistry — alias resolve + 5 region 시드 회귀."""
from __future__ import annotations

from src.schemas.candidate_registry import (
    CandidateRegistry,
    load_candidate_registry,
)


def test_loads_5_regions() -> None:
    reg = load_candidate_registry()
    assert set(reg.regions.keys()) == {
        "seoul_mayor", "gwangju_mayor", "daegu_mayor",
        "busan_buk_gap", "daegu_dalseo_gap",
    }


def test_minimum_candidate_count_per_region() -> None:
    reg = load_candidate_registry()
    for region_id, entries in reg.regions.items():
        assert len(entries) >= 3, f"{region_id}: only {len(entries)} candidates"


def test_find_by_id() -> None:
    reg = load_candidate_registry()
    e = reg.find_by_id("c_seoul_ppp")
    assert e is not None
    assert e.name == "오세훈"


def test_resolve_korean_text() -> None:
    reg = load_candidate_registry()
    e = reg.resolve("오늘 오세훈 시장이 발표를", region_id="seoul_mayor")
    assert e is not None and e.id == "c_seoul_ppp"


def test_resolve_alias_hanja() -> None:
    reg = load_candidate_registry()
    e = reg.resolve("吳世勳 후보", region_id="seoul_mayor")
    assert e is not None and e.id == "c_seoul_ppp"


def test_resolve_alias_english_lowercase() -> None:
    reg = load_candidate_registry()
    e = reg.resolve("...by HAN DONG-HOON ...", region_id="busan_buk_gap")
    assert e is not None and e.id == "c_busan_indep_han"


def test_resolve_no_match_returns_none() -> None:
    reg = load_candidate_registry()
    assert reg.resolve("이름 없는 사람", region_id="seoul_mayor") is None


def test_resolve_cross_region_when_unspecified() -> None:
    reg = load_candidate_registry()
    e = reg.resolve("강기정")
    assert e is not None and e.id == "c_gwangju_dpk"
