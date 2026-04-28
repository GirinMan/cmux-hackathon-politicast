"""Task #9 — ``KGRetriever.cutoff_for(region, t)`` invariants.

For every (region, t) combination across the 5 real scenarios:

  * ``cutoff_for(region, 0) == meta.t_start``
  * ``cutoff_for(region, T-1) == meta.t_end``
  * sequence ``[cutoff_for(region, t) for t in 0..T-1]`` is monotone
    non-decreasing.
  * out-of-range ``t`` is clamped (not raised).

Skips when the scenario dir is missing.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from src.kg.builder import DEFAULT_SCENARIO_DIR, build_kg_from_scenarios
from src.kg.retriever import KGRetriever


@pytest.fixture(scope="module")
def real_kg():
    if not Path(DEFAULT_SCENARIO_DIR).exists():
        pytest.skip("scenario dir missing")
    G, index = build_kg_from_scenarios()
    if not G.number_of_nodes():
        pytest.skip("KG empty")
    return KGRetriever(G, index), index


def test_cutoff_for_unknown_region_is_none(real_kg):
    retriever, _index = real_kg
    assert retriever.cutoff_for("region_does_not_exist", 0) is None


def test_cutoff_for_endpoints_match_meta(real_kg):
    retriever, index = real_kg
    for region_id, meta in index.by_region.items():
        assert retriever.cutoff_for(region_id, 0) == meta.t_start, (
            f"{region_id}: cutoff_for(t=0) != t_start"
        )
        assert retriever.cutoff_for(region_id, meta.timesteps - 1) == meta.t_end, (
            f"{region_id}: cutoff_for(t=T-1) != t_end"
        )


def test_cutoff_for_monotone_non_decreasing(real_kg):
    retriever, index = real_kg
    for region_id, meta in index.by_region.items():
        cutoffs = [retriever.cutoff_for(region_id, t) for t in range(meta.timesteps)]
        assert all(isinstance(c, datetime) for c in cutoffs), region_id
        for a, b in zip(cutoffs, cutoffs[1:]):
            assert a <= b, f"{region_id}: cutoff sequence not monotone: {cutoffs}"


def test_cutoff_for_out_of_range_clamped(real_kg):
    retriever, index = real_kg
    for region_id, meta in index.by_region.items():
        below = retriever.cutoff_for(region_id, -10)
        above = retriever.cutoff_for(region_id, meta.timesteps + 5)
        assert below == meta.t_start, f"{region_id}: t<0 not clamped to t_start"
        assert above == meta.t_end, f"{region_id}: t>T-1 not clamped to t_end"
