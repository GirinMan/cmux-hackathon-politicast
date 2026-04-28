"""AgeBuckets — election_env._age_group 외화 회귀 테스트."""
from __future__ import annotations

import pytest

from src.schemas.cohort import DEFAULT_AGE_BUCKETS, AgeBuckets, load_age_buckets


@pytest.fixture(scope="module")
def buckets() -> AgeBuckets:
    return load_age_buckets()


# election_env._age_group 의 원래 동작:
#   <30 -> 20s, <40 -> 30s, <50 -> 40s, <60 -> 50s, else 60s+, non-int -> unknown
@pytest.mark.parametrize(
    "age,expected",
    [
        (0, "20s"),
        (19, "20s"),
        (29, "20s"),
        (30, "30s"),
        (39, "30s"),
        (40, "40s"),
        (49, "40s"),
        (50, "50s"),
        (59, "50s"),
        (60, "60s+"),
        (75, "60s+"),
        (200, "60s+"),
        ("45", "40s"),  # str-coercion
        (None, "unknown"),
        ("abc", "unknown"),
        ([], "unknown"),
    ],
)
def test_bucket_for_matches_legacy(buckets: AgeBuckets, age, expected: str) -> None:
    assert buckets.bucket_for(age) == expected


def test_default_singleton_matches_loaded(buckets: AgeBuckets) -> None:
    assert DEFAULT_AGE_BUCKETS.labels() == buckets.labels()


def test_election_env_uses_buckets_singleton() -> None:
    """`ElectionEnv._demographics_breakdown` 의 grouper 가 DEFAULT 와 일치."""
    from src.schemas.cohort import DEFAULT_AGE_BUCKETS as DAB

    # 동작 핀 — 75세는 60s+, 35세는 30s.
    assert DAB.bucket_for(75) == "60s+"
    assert DAB.bucket_for(35) == "30s"
