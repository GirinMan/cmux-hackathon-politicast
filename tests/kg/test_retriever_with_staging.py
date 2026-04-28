"""Phase 3 (#59) — ``make_retriever`` honours ``POLITIKAST_KG_USE_STAGING``."""
from __future__ import annotations

import pytest

from src.kg.retriever import KGRetriever, make_retriever


def test_default_off_uses_scenario_only(monkeypatch):
    monkeypatch.delenv("POLITIKAST_KG_USE_STAGING", raising=False)
    r = make_retriever()
    assert isinstance(r, KGRetriever)
    # All 5 scenarios must still be registered.
    assert {"seoul_mayor", "busan_buk_gap", "daegu_mayor",
            "gwangju_mayor", "daegu_dalseo_gap"} <= set(r.index.by_region)


def test_opt_in_routes_through_build_with_staging(monkeypatch):
    """With env var on, make_retriever must call build_with_staging. We
    assert via a side-effect: the docstring of build_with_staging mentions
    'staging'. Simpler proof: monkey-patch the import target and ensure the
    call happens."""
    monkeypatch.setenv("POLITIKAST_KG_USE_STAGING", "1")
    called = {"n": 0}

    import src.kg.builder as builder_mod
    original = builder_mod.build_with_staging

    def spy(*args, **kwargs):
        called["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(builder_mod, "build_with_staging", spy)
    r = make_retriever()
    assert called["n"] == 1
    assert isinstance(r, KGRetriever)


def test_opt_in_remains_no_op_without_db(monkeypatch, tmp_path):
    """Even with the flag on, an absent DB path should not blow up — staging
    layer is graceful per Phase 3 contract."""
    monkeypatch.setenv("POLITIKAST_KG_USE_STAGING", "1")
    r = make_retriever(db_path=tmp_path / "absent.duckdb")
    assert isinstance(r, KGRetriever)
