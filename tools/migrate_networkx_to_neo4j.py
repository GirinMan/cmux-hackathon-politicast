"""Mirror the in-process networkx KG into Neo4j (Phase 4 #80).

Usage:
    PYTHONPATH=. NEO4J_URI=bolt://localhost:7687 \\
        .venv/bin/python -m tools.migrate_networkx_to_neo4j

    # With staging triples grafted:
    POLITIKAST_KG_USE_STAGING=1 NEO4J_URI=... \\
        .venv/bin/python -m tools.migrate_networkx_to_neo4j

The script:
    1. Builds the full KG (``build_kg_from_scenarios`` or
       ``build_with_staging`` when ``POLITIKAST_KG_USE_STAGING=1``).
    2. Opens an async Neo4j session via :mod:`backend.app.db.neo4j_session`.
    3. Applies :func:`src.kg.cypher.schema_ddl` (idempotent).
    4. Mirrors every node + edge with UNWIND batches.
    5. Runs the firewall Cypher audit per region — exits non-zero on leak.

Exit codes:
    0  — success
    1  — driver unavailable / NEO4J_URI not set
    2  — firewall violation (future-dated event mirrored)
    3  — runtime error during MERGE
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("tools.migrate_kg")


def _build_graph():
    if os.environ.get("POLITIKAST_KG_USE_STAGING", "0").lower() in ("1", "true", "yes"):
        from src.kg.builder import build_with_staging
        return build_with_staging()
    from src.kg.builder import build_kg_from_scenarios
    return build_kg_from_scenarios()


def _import_neo4j_session_module():
    """Load ``backend.app.db.neo4j_session`` even when the package init fails
    (e.g. db-postgres SQLAlchemy not yet installed in this checkout)."""
    try:
        from backend.app.db import neo4j_session as mod  # type: ignore
        return mod
    except Exception:
        import importlib.util
        repo_root = Path(__file__).resolve().parent.parent
        path = repo_root / "backend" / "app" / "db" / "neo4j_session.py"
        spec = importlib.util.spec_from_file_location(
            "_kg_neo4j_session_migrator", path,
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        sys.modules["backend.app.db.neo4j_session"] = mod
        spec.loader.exec_module(mod)
        return mod


async def _audit_region(session, region_id: str, cutoff: datetime) -> list[dict]:
    neo4j_mod = _import_neo4j_session_module()
    from src.kg.firewall import assert_no_future_leakage_cypher

    query, params = assert_no_future_leakage_cypher(region_id, cutoff)
    return await neo4j_mod.run_read(session, query, params)


async def _run(uri: Optional[str], dry_run: bool) -> int:
    from src.kg.builder import apply_graph_to_neo4j
    from src.kg._calendar_adapter import get_default_cutoff, get_election_window

    G, index = _build_graph()
    logger.info(
        "[migrate] graph: nodes=%d edges=%d regions=%s",
        G.number_of_nodes(), G.number_of_edges(), sorted(index.by_region),
    )
    if dry_run:
        logger.info("[migrate] dry-run — exiting before MERGE")
        return 0

    neo4j_mod = _import_neo4j_session_module()
    driver_available = neo4j_mod.driver_available
    get_driver = neo4j_mod.get_driver
    session_ctx = neo4j_mod.session_ctx
    if not driver_available():
        logger.error("[migrate] neo4j-python driver not installed — pip install neo4j")
        return 1
    if uri:
        os.environ["NEO4J_URI"] = uri
    drv = await get_driver()
    if drv is None:
        logger.error("[migrate] NEO4J_URI not set / driver unreachable")
        return 1

    try:
        async with session_ctx() as session:
            counters = await apply_graph_to_neo4j(G, session)
            logger.info("[migrate] mirror counters: %s", counters)

            # Per-region firewall audit.
            failures: dict[str, list[dict]] = {}
            for region_id, meta in index.by_region.items():
                win = get_election_window(region_id)
                cutoff = win.cutoff if win else get_default_cutoff()
                leaks = await _audit_region(session, region_id, cutoff)
                if leaks:
                    failures[region_id] = leaks
            if failures:
                logger.error("[migrate] firewall LEAKS: %s",
                             json.dumps(failures, default=str, ensure_ascii=False))
                return 2
            print(json.dumps({"status": "ok", **counters}, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        logger.exception("[migrate] runtime failure: %s", exc)
        return 3
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--uri", help="NEO4J_URI override")
    p.add_argument("--dry-run", action="store_true", help="build only, no MERGE")
    args = p.parse_args(argv)
    return asyncio.run(_run(args.uri, args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
