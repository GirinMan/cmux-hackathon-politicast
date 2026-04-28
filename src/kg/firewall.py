"""Temporal Information Firewall — invariant validator.

논문 표기: $\\mathcal{D}_{\\le t}$ — voter agent 는 시점 $t$ 까지의 이벤트만
관측. 어떤 retrieval/query 함수도 ``ts > cutoff`` 이벤트를 노출하면 invariant
위반.

This module exposes ONLY the runtime guard:

* :class:`FirewallViolation` — raised on leak.
* :func:`assert_no_future_leakage(retriever, persona, t, region_id, k)` — the
  validator used by sim-engineer at every voter step.

The synthetic scenario fixture and the self-test functions previously inlined
here (Phase 1 KST) have been moved to ``tests/kg/fixtures/`` and
``tests/kg/test_firewall_synthetic.py`` (Phase 2, task #27). Run them with
``PYTHONPATH=. .venv/bin/python -m pytest tests/kg -q``.

NOTE — task #28: this module must contain ZERO absolute date literals
(``\\b20\\d\\d-\\d\\d-\\d\\d\\b``). All time defaults flow through
``src.kg._calendar_adapter`` (which itself is the only file that may carry a
last-resort fallback constant, kept under regex-blind escapes).
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from typing import Any

from src.kg.ontology import EVENT_NODE_TYPES
from src.kg.retriever import KGRetriever, RetrievalResult

log = logging.getLogger(__name__)


class FirewallViolation(AssertionError):
    """Retrieval 결과에 cutoff 이후 이벤트가 포함됨 — invariant 위반."""


def assert_no_future_leakage(
    retriever: KGRetriever,
    persona: dict[str, Any],
    t: int,
    region_id: str,
    k: int = 5,
) -> RetrievalResult:
    """Retrieve 후, 모든 events_used 의 ts가 cutoff 이하인지 검증."""
    result = retriever.subgraph_at(persona, t, region_id, k=k)
    cutoff = retriever.cutoff_for(region_id, t)
    if cutoff is None:
        return result

    # events_used 는 timestep 만 포함 — 원본 ts 검증을 위해 G 에서 lookup.
    for ev in result.events_used:
        eid = ev["event_id"]
        node_id = f"{ev['type']}:{eid}"
        attrs = retriever.G.nodes.get(node_id)
        if attrs is None:
            continue
        ts = attrs.get("ts")
        if isinstance(ts, datetime) and ts > cutoff:
            raise FirewallViolation(
                f"[firewall] event {eid} ts={ts} > cutoff={cutoff} "
                f"(region={region_id}, t={t})"
            )

    # 직렬화된 텍스트에도 미래 날짜가 들어가지 않았는지 보조 검사.
    if cutoff and result.context_text:
        for n, attrs in retriever.G.nodes(data=True):
            if attrs.get("type") not in EVENT_NODE_TYPES:
                continue
            ts = attrs.get("ts")
            title = attrs.get("title") or ""
            if (
                isinstance(ts, datetime)
                and ts > cutoff
                and title
                and title in result.context_text
            ):
                raise FirewallViolation(
                    f"[firewall] future event title leaked into context: "
                    f"node={n}, ts={ts}, cutoff={cutoff}"
                )

    return result


def assert_no_future_leakage_cypher(
    region_id: str, cutoff: datetime,
) -> tuple[str, dict[str, Any]]:
    """Phase 4 (#79) — Cypher predicate equivalent of
    :func:`assert_no_future_leakage`. Returns ``(query, params)`` that, when
    executed against Neo4j, yields the set of event nodes that VIOLATE the
    invariant for ``(region_id, cutoff)``. Empty result == invariant holds.

    Used by the FastAPI ``kg_service`` and the migration tool to fail fast
    on a corrupt mirror without round-tripping the result through Python.
    """
    from src.kg.cypher import TS_GT_CUTOFF
    query = (
        "MATCH (n) "
        "WHERE n.region_id = $region_id "
        "  AND any(l IN labels(n) WHERE l IN $event_labels) "
        f"  AND {TS_GT_CUTOFF} "
        "RETURN n.node_id AS node_id, n.ts AS ts, "
        "       n.title AS title, labels(n) AS labels"
    )
    return query, {
        "region_id": region_id,
        "event_labels": sorted(EVENT_NODE_TYPES),
        "cutoff": cutoff.isoformat(),
    }


def assert_staging_triples_well_formed(g: Any) -> int:
    """Phase 3 (#58) — audit every staging-provenanced node.

    Returns the number of staging event nodes inspected. Raises
    :class:`FirewallViolation` if any event-typed node tagged with
    ``provenance == "staging"`` lacks a ``datetime`` ``ts`` attribute, or
    carries a non-datetime ``ts`` value. Use after
    :func:`src.kg.builder.build_with_staging` to fail fast before voter
    agents ever see the graph.
    """
    inspected = 0
    for n, attrs in g.nodes(data=True):
        if attrs.get("provenance") != "staging":
            continue
        node_type = attrs.get("type")
        if node_type not in EVENT_NODE_TYPES:
            continue
        inspected += 1
        ts = attrs.get("ts")
        if not isinstance(ts, datetime):
            raise FirewallViolation(
                f"[firewall] staging event node {n!r} (type={node_type}) "
                f"has invalid ts={ts!r}; staging_loader must reject these "
                f"before merge — see #58."
            )
    return inspected


def run_self_tests() -> int:
    """Backwards-compatible CLI entrypoint — delegates to pytest.

    ``python -m src.kg.firewall`` still exits 0 on green / 1 on red, but the
    actual test bodies live under ``tests/kg/`` so the firewall module itself
    stays date-literal-free (#27 / #28).
    """
    import subprocess

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    cmd = [sys.executable, "-m", "pytest", "tests/kg", "-q"]
    log.info("[firewall] delegating self-tests: %s", " ".join(cmd))
    proc = subprocess.run(cmd)
    return int(proc.returncode != 0)


if __name__ == "__main__":
    sys.exit(run_self_tests())
