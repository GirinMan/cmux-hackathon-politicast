"""KL/JS + collapse 탐지 단위 테스트."""
from __future__ import annotations

import math

import pytest

from src.eval.divergence import (
    detect_distribution_collapse,
    js_divergence,
    kl_divergence,
)


def test_kl_zero_for_identical() -> None:
    assert kl_divergence([0.5, 0.5], [0.5, 0.5]) == pytest.approx(0.0, abs=1e-6)


def test_kl_positive_when_different() -> None:
    assert kl_divergence([0.9, 0.1], [0.1, 0.9]) > 0.5


def test_js_symmetric() -> None:
    p = [0.7, 0.3]
    q = [0.4, 0.6]
    assert js_divergence(p, q) == pytest.approx(js_divergence(q, p), abs=1e-9)


def test_js_bounded_by_log2() -> None:
    # 완전 disjoint (epsilon smoothing 후) — JS ≤ log 2 + small slack
    js = js_divergence([1.0, 0.0], [0.0, 1.0])
    assert 0.0 <= js <= math.log(2) + 1e-3


def test_js_zero_for_identical() -> None:
    assert js_divergence([0.6, 0.4], [0.6, 0.4]) == pytest.approx(0.0, abs=1e-6)


def test_dict_input_union_keys() -> None:
    # sim 에 c 추가, off 에 없음 — union 으로 평가
    p = {"a": 0.5, "b": 0.4, "c": 0.1}
    q = {"a": 0.6, "b": 0.4}
    out = js_divergence(p, q)
    assert out >= 0.0


def test_collapse_detected_at_threshold() -> None:
    assert detect_distribution_collapse([1.0, 0.0, 0.0]) is True
    assert detect_distribution_collapse({"a": 0.99, "b": 0.01}, threshold=0.99) is True


def test_collapse_not_detected_when_distributed() -> None:
    assert detect_distribution_collapse([0.5, 0.3, 0.2]) is False


def test_collapse_handles_empty() -> None:
    assert detect_distribution_collapse([]) is False
    assert detect_distribution_collapse([0.0, 0.0]) is False
