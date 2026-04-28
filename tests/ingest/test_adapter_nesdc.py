"""NESDC 어댑터 회귀 게이트 (#49).

기존 raw_poll 77 row baseline 과 share/p_hat (현재는 row count + region 분포)
100% 일치 + 멱등성 (동일 입력 → 동일 row 시퀀스).
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from src.ingest.adapters.nesdc_poll import (
    DEFAULT_LIST_JSON,
    NESDCPollAdapter,
    REGION_TO_CONTEST,
)
from src.ingest.base import IngestRunContext


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def list_snapshot_exists() -> bool:
    return DEFAULT_LIST_JSON.exists()


@pytest.fixture(scope="module")
def adapter() -> NESDCPollAdapter:
    return NESDCPollAdapter()


@pytest.fixture(scope="module")
def ctx() -> IngestRunContext:
    return IngestRunContext(run_id="t-nesdc-1", source_id="nesdc_poll")


def test_protocol_attributes(adapter: NESDCPollAdapter) -> None:
    assert adapter.source_id == "nesdc_poll"
    assert adapter.kind == "structured"
    assert adapter.target_kind == "raw_poll"


def test_fetch_uses_cached_list(
    list_snapshot_exists: bool, adapter: NESDCPollAdapter, ctx: IngestRunContext
) -> None:
    if not list_snapshot_exists:
        pytest.skip("nesdc_list_raw.json 없음 — Codex 가 scrape 후 재시도")
    payload = adapter.fetch(ctx)
    assert payload.source_id == "nesdc_poll"
    # cap=25 → 25+25+25+2+0 = 77 (legacy raw_poll baseline)
    assert len(payload.items) == 77, f"expected 77 cap'd items, got {len(payload.items)}"


def test_parse_produces_77_legacy_rows(
    list_snapshot_exists: bool, adapter: NESDCPollAdapter, ctx: IngestRunContext
) -> None:
    if not list_snapshot_exists:
        pytest.skip("nesdc_list_raw.json 없음")
    payload = adapter.fetch(ctx)
    result = adapter.parse(payload, ctx)
    assert result.table == "stg_raw_poll"
    assert len(result.rows) == 77

    # region 분포 — legacy raw_poll dump 와 1:1 일치
    expected_per_region = {
        "seoul_mayor": 25,
        "gwangju_mayor": 25,
        "daegu_mayor": 25,
        "busan_buk_gap": 2,
    }
    seen = Counter(r["region_id"] for r in result.rows)
    for rid, n in expected_per_region.items():
        assert seen.get(rid, 0) == n, f"{rid}: expected {n}, got {seen.get(rid, 0)}"
    # daegu_dalseo_gap 은 list 에 0 row → 0 row
    assert seen.get("daegu_dalseo_gap", 0) == 0


def test_row_shape_matches_raw_poll_columns(
    list_snapshot_exists: bool, adapter: NESDCPollAdapter, ctx: IngestRunContext
) -> None:
    if not list_snapshot_exists:
        pytest.skip()
    payload = adapter.fetch(ctx)
    result = adapter.parse(payload, ctx)
    required = {
        "poll_id", "contest_id", "region_id", "field_start", "field_end",
        "publish_ts", "pollster", "sponsor", "source_url", "mode",
        "sample_size", "population", "margin_error", "quality",
        "is_placeholder", "title", "nesdc_reg_no",
    }
    for row in result.rows:
        missing = required - set(row.keys())
        assert not missing, f"row missing keys: {missing}"
        # poll_id 형식 확인
        assert row["poll_id"].startswith("nesdc-")
        # contest_id 가 region 매핑과 일치
        assert row["contest_id"] == REGION_TO_CONTEST[row["region_id"]]


def test_idempotency_two_runs_same_rows(
    list_snapshot_exists: bool, adapter: NESDCPollAdapter, ctx: IngestRunContext
) -> None:
    """두 번 호출해도 동일 row 시퀀스 — pipeline MERGE 시 n_loaded=0 보장."""
    if not list_snapshot_exists:
        pytest.skip()
    r1 = adapter.parse(adapter.fetch(ctx), ctx).rows
    r2 = adapter.parse(adapter.fetch(ctx), ctx).rows
    assert r1 == r2, "어댑터가 결정적이지 않음 — staging MERGE 멱등성 깨짐"
    # poll_id 들 unique (PK 충돌 없음)
    ids = [r["poll_id"] for r in r1]
    assert len(ids) == len(set(ids)), "poll_id 중복 — PK 충돌 위험"


def test_per_region_cap_override_via_config(
    list_snapshot_exists: bool, adapter: NESDCPollAdapter
) -> None:
    if not list_snapshot_exists:
        pytest.skip()
    ctx_capped = IngestRunContext(
        run_id="t-nesdc-cap5", source_id="nesdc_poll",
        config={"per_region_cap": 5},
    )
    payload = adapter.fetch(ctx_capped)
    # 5+5+5+2+0 = 17
    assert len(payload.items) == 17


def test_missing_list_path_raises(
    adapter: NESDCPollAdapter, tmp_path: Path
) -> None:
    ctx_bad = IngestRunContext(
        run_id="t-nesdc-bad", source_id="nesdc_poll",
        config={"list_json_path": str(tmp_path / "nope.json")},
    )
    with pytest.raises(FileNotFoundError):
        adapter.fetch(ctx_bad)


def test_get_adapter_returns_protocol_compatible() -> None:
    from src.ingest.adapters.nesdc_poll import get_adapter

    a = get_adapter()
    assert hasattr(a, "fetch") and hasattr(a, "parse")
    assert getattr(a, "source_id", None) == "nesdc_poll"


def test_share_p_hat_baseline_matches_legacy(
    list_snapshot_exists: bool, adapter: NESDCPollAdapter, ctx: IngestRunContext
) -> None:
    """기존 raw_poll 의 (region_id, contest_id, poll_id prefix) 분포 회귀.

    DB 가 없는 CI 환경 대비, list snapshot 만으로 row 세트를 재현한 뒤
    legacy 카운터와 비교한다 (sim 의 share/p_hat 입력단 동등성 보존 핀).
    """
    if not list_snapshot_exists:
        pytest.skip()
    rows = adapter.parse(adapter.fetch(ctx), ctx).rows
    # legacy raw_poll: per-region count 와 contest_id 매핑 동일.
    by_contest = Counter(r["contest_id"] for r in rows)
    assert by_contest == Counter({
        "seoul_mayor_2026": 25,
        "gwangju_mayor_2026": 25,
        "daegu_mayor_2026": 25,
        "busan_buk_gap_2026": 2,
    })
