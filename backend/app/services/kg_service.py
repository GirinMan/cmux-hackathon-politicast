"""KG subgraph service — Neo4j-first with networkx fallback.

Phase 4 (#80): when ``Settings.enable_neo4j`` is true and the driver +
``NEO4J_URI`` are reachable, this service issues Cypher reads against Neo4j.
Otherwise it falls back to the in-process networkx KG built by
:mod:`src.kg.builder` so the rest of the FastAPI surface keeps working
during dev / CI without a Neo4j container.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import logging
from typing import Optional

from ..schemas.public_dto import KGEdgeDTO, KGNodeDTO, KGSubgraphDTO

logger = logging.getLogger("backend.kg")


class KGService:
    def get_subgraph(
        self,
        region_id: str,
        cutoff: Optional[str] = None,
        k: int = 25,
    ) -> KGSubgraphDTO:
        nodes, edges = self._fetch_graph(region_id, cutoff)
        # 단순 cap — frontend rendering 보호
        nodes = nodes[:k]
        node_ids = {n.id for n in nodes}
        edges = [e for e in edges if e.src in node_ids and e.dst in node_ids][:k * 4]
        return KGSubgraphDTO(
            region_id=region_id, cutoff=cutoff, nodes=nodes, edges=edges
        )

    # ------------------------------------------------------------------
    def _fetch_graph(
        self, region_id: str, cutoff: Optional[str]
    ) -> tuple[list[KGNodeDTO], list[KGEdgeDTO]]:
        cutoff_dt = self._resolve_cutoff(region_id, cutoff)

        if self._neo4j_enabled():
            try:
                return self._fetch_via_neo4j(region_id, cutoff_dt)
            except Exception as exc:  # noqa: BLE001
                logger.info("[kg/service] neo4j read failed (%s) — fallback", exc)

        return self._fetch_via_networkx(region_id, cutoff_dt)

    # ------------------------------------------------------------------
    @staticmethod
    def _neo4j_enabled() -> bool:
        try:
            from ..settings import get_settings
            from ..db.neo4j_session import driver_available
        except Exception:
            return False
        try:
            return bool(get_settings().enable_neo4j and driver_available())
        except Exception:
            return False

    def _fetch_via_neo4j(
        self, region_id: str, cutoff_dt: Optional[dt.datetime],
    ) -> tuple[list[KGNodeDTO], list[KGEdgeDTO]]:
        from ..db.neo4j_session import get_driver, run_read
        from src.kg.cypher import visible_events_query

        async def _read():
            drv = await get_driver()
            if drv is None:
                raise RuntimeError("driver unavailable")
            session = drv.session()
            try:
                cutoff_param = cutoff_dt.isoformat() if cutoff_dt else None
                event_rows = await run_read(
                    session,
                    visible_events_query(),
                    {"region_id": region_id, "cutoff": cutoff_param},
                )
                edge_rows = await run_read(
                    session,
                    "MATCH (s)-[r]->(d) "
                    "WHERE s.region_id = $region_id OR d.region_id = $region_id "
                    "RETURN s.node_id AS src, d.node_id AS dst, "
                    "       type(r) AS pred, r.confidence AS confidence",
                    {"region_id": region_id},
                )
                return event_rows, edge_rows
            finally:
                await session.close()

        event_rows, edge_rows = asyncio.run(_read())
        nodes = [
            KGNodeDTO(
                id=str(r.get("node_id")),
                kind=str(r.get("type") or "") or None,
                label=str(r.get("title") or "") or None,
                ts=self._iso(r.get("ts")),
            )
            for r in event_rows
        ]
        edges = [
            KGEdgeDTO(
                src=str(r.get("src")),
                dst=str(r.get("dst")),
                pred=str(r.get("pred") or ""),
                ts=None,
                confidence=r.get("confidence"),
            )
            for r in edge_rows
        ]
        return nodes, edges

    def _fetch_via_networkx(
        self, region_id: str, cutoff_dt: Optional[dt.datetime],
    ) -> tuple[list[KGNodeDTO], list[KGEdgeDTO]]:
        try:
            from src.kg.builder import build_for_region
        except Exception as e:
            logger.info("kg service degraded — builder import failed: %s", e)
            return [], []
        try:
            G = build_for_region(region_id=region_id, cutoff=cutoff_dt)
        except Exception as e:
            logger.info("kg service degraded — build_for_region failed: %s", e)
            return [], []

        nodes: list[KGNodeDTO] = []
        for nid, attrs in (G.nodes(data=True) if G is not None else []):
            nodes.append(
                KGNodeDTO(
                    id=str(nid),
                    kind=str(attrs.get("kind") or attrs.get("type") or "") or None,
                    label=str(attrs.get("label") or attrs.get("name") or "") or None,
                    ts=self._iso(attrs.get("ts")),
                )
            )
        edges: list[KGEdgeDTO] = []
        if G is not None and G.is_multigraph():
            for u, v, key, attrs in G.edges(keys=True, data=True):
                edges.append(
                    KGEdgeDTO(
                        src=str(u),
                        dst=str(v),
                        pred=str(key or attrs.get("pred") or ""),
                        ts=self._iso(attrs.get("ts")),
                        confidence=attrs.get("confidence"),
                    )
                )
        return nodes, edges

    # ------------------------------------------------------------------
    @staticmethod
    def _iso(v) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, (dt.date, dt.datetime)):
            return v.isoformat()
        return str(v)

    @staticmethod
    def _resolve_cutoff(region_id: str, cutoff: Optional[str]):
        if cutoff:
            try:
                return dt.datetime.fromisoformat(cutoff)
            except Exception:
                pass
        try:
            from src.schemas.calendar import load_election_calendar
            cal = load_election_calendar()
            d = cal.cutoff_for(region_id)
            return dt.datetime.combine(d, dt.time(0, 0))
        except Exception:
            return None


kg_service = KGService()

__all__ = ["kg_service", "KGService"]
