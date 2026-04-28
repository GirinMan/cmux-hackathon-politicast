"""DataSource registry + IngestRun 모델 검증."""
from __future__ import annotations

import pytest

from src.schemas.data_source import (
    DEFAULT_REGISTRY_PATH,
    DataSource,
    DataSourceRegistry,
    IngestRun,
    load_data_source_registry,
)

EXPECTED_SOURCES = ("nesdc_poll", "nec_candidate", "news_article", "perplexity")


def test_default_registry_loads_4_sources() -> None:
    reg = load_data_source_registry()
    assert isinstance(reg, DataSourceRegistry)
    for sid in EXPECTED_SOURCES:
        assert sid in reg.sources, sid
        ds = reg.get(sid)
        assert ds.fetcher_module.startswith("src.ingest.adapters.")


def test_kind_split_structured_vs_llm() -> None:
    reg = load_data_source_registry()
    assert reg.get("nesdc_poll").kind == "structured"
    assert reg.get("news_article").kind == "llm"
    assert reg.get("perplexity").target_kind == "kg_triple"


def test_unknown_source_raises_keyerror() -> None:
    reg = load_data_source_registry()
    with pytest.raises(KeyError):
        reg.get("does_not_exist")


def test_extra_fields_forbidden_on_data_source() -> None:
    with pytest.raises(Exception):
        DataSource(
            id="x", kind="structured", target_kind="raw_poll",
            fetcher_module="x", unknown=1,  # type: ignore[call-arg]
        )


def test_extra_fields_forbidden_on_ingest_run() -> None:
    with pytest.raises(Exception):
        IngestRun(
            run_id="r", source_id="s", started_at="2026-04-26T00:00:00+09:00",
            unknown=1,  # type: ignore[call-arg]
        )


def test_ingest_run_default_status_pending() -> None:
    run = IngestRun(run_id="r", source_id="s", started_at="2026-04-26T00:00:00+09:00")
    assert run.status == "pending"
    assert run.dry_run is False
    assert run.n_fetched == 0


def test_default_registry_path_exists() -> None:
    assert DEFAULT_REGISTRY_PATH.exists(), DEFAULT_REGISTRY_PATH


def test_enabled_ids_filters_disabled() -> None:
    reg = DataSourceRegistry(
        sources={
            "a": DataSource(id="a", kind="structured", target_kind="raw_poll",
                            fetcher_module="x", enabled=True),
            "b": DataSource(id="b", kind="llm", target_kind="kg_triple",
                            fetcher_module="y", enabled=False),
        }
    )
    assert reg.enabled_ids() == ["a"]
