"""Dashboard용 KG export (P1).

``_workspace/snapshots/kg_{region_id}_t{t}.json`` 형식 — d3-friendly.
dashboard-engineer가 KG Viewer 페이지에서 폴링.

시점 t 의 firewall 을 적용한 서브그래프만 dump (미래 이벤트 표시 X).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import networkx as nx

from src.kg.builder import ScenarioIndex, ScenarioMeta
from src.kg.ontology import EVENT_NODE_TYPES

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SNAPSHOT_DIR = REPO_ROOT / "_workspace" / "snapshots"


def _safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _node_to_d3(node_id: str, attrs: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": attrs.get("type", "?"),
        "label": attrs.get("label", node_id),
        "ts": _safe(attrs.get("ts")),
        "sentiment": attrs.get("sentiment"),
        "frame_id": attrs.get("frame_id"),
        "region_id": attrs.get("region_id"),
        # subset of additional attrs for tooltip
        "attrs": {
            k: _safe(v)
            for k, v in attrs.items()
            if k not in {"type", "label", "ts", "sentiment", "frame_id", "region_id"}
        },
    }


def _edge_to_d3(u: str, v: str, key: str, attrs: dict[str, Any]) -> dict[str, Any]:
    return {
        "src": u,
        "dst": v,
        "rel": key,
        "attrs": {k: _safe(val) for k, val in attrs.items() if k != "rel"},
    }


def _filter_by_cutoff(
    G: nx.MultiDiGraph, cutoff: datetime | None
) -> tuple[set[str], list[tuple[str, str, str, dict[str, Any]]]]:
    """firewall 적용 — cutoff 이후 event 노드 및 그 incident edges 제외."""
    keep_nodes: set[str] = set()
    for n, attrs in G.nodes(data=True):
        if attrs.get("type") in EVENT_NODE_TYPES:
            ts = attrs.get("ts")
            if cutoff is not None and isinstance(ts, datetime) and ts > cutoff:
                continue
        keep_nodes.add(n)
    edges: list[tuple[str, str, str, dict[str, Any]]] = []
    for u, v, k, attrs in G.edges(keys=True, data=True):
        if u in keep_nodes and v in keep_nodes:
            edges.append((u, v, k, attrs))
    return keep_nodes, edges


def _is_region_local(
    G: nx.MultiDiGraph, node: str, region_id: str, contest_id: str | None
) -> bool:
    """노드가 region_id 에 '귀속' 되는지 best-effort 판정."""
    attrs = G.nodes[node]
    if attrs.get("region_id") == region_id:
        return True
    if contest_id and attrs.get("contest_id") == contest_id:
        return True
    # Election/District/Contest 노드는 외부 region 일 수도 있어 명시 매칭만 통과.
    # Candidate / Party / PolicyIssue / NarrativeFrame 등 — region 어트리뷰트
    # 없으면 region 경계 밖으로 간주.
    return False


def export_kg_for_dashboard(
    G: nx.MultiDiGraph,
    index: ScenarioIndex,
    region_id: str,
    t: int,
    *,
    snapshot_dir: Path | str = DEFAULT_SNAPSHOT_DIR,
    region_only: bool = True,
) -> Path:
    """region_id 의 timestep t 시점 KG 서브그래프를 JSON 으로 dump.

    Args:
        region_only: True 면 해당 region 에 귀속된 노드 + 1-hop 이웃만 포함.
    """
    meta: ScenarioMeta | None = index.by_region.get(region_id)
    cutoff = meta.t_to_realtime(t) if meta else None
    contest_id = index.contest_for_region.get(region_id)

    keep, edges = _filter_by_cutoff(G, cutoff)

    if region_only:
        # 1) seed: region-local nodes
        seed: set[str] = {n for n in keep if _is_region_local(G, n, region_id, contest_id)}
        # 2) expand 1-hop: edge 가 seed 에 닿는 모든 노드 추가
        expanded: set[str] = set(seed)
        for u, v, _k, _attrs in edges:
            if u in seed:
                expanded.add(v)
            if v in seed:
                expanded.add(u)
        keep = expanded
        edges = [(u, v, k, a) for (u, v, k, a) in edges if u in keep and v in keep]

    nodes_payload = [_node_to_d3(n, G.nodes[n]) for n in sorted(keep)]
    edges_payload = [_edge_to_d3(u, v, k, attrs) for (u, v, k, attrs) in edges]

    out_dir = Path(snapshot_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"kg_{region_id}_t{t}.json"

    payload = {
        "region_id": region_id,
        "timestep": t,
        "cutoff_ts": _safe(cutoff),
        "scenario_id": meta.scenario_id if meta else None,
        "nodes": nodes_payload,
        "edges": edges_payload,
        "stats": {
            "node_count": len(nodes_payload),
            "edge_count": len(edges_payload),
        },
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("[kg-export] %s nodes=%d edges=%d → %s",
             region_id, len(nodes_payload), len(edges_payload), out_path)
    return out_path


def export_all(
    G: nx.MultiDiGraph,
    index: ScenarioIndex,
    *,
    timesteps: Iterable[int] | None = None,
    snapshot_dir: Path | str = DEFAULT_SNAPSHOT_DIR,
) -> list[Path]:
    """모든 region × timestep 조합 export."""
    paths: list[Path] = []
    for region_id, meta in index.by_region.items():
        ts_range = list(timesteps) if timesteps is not None else list(range(meta.timesteps))
        for t in ts_range:
            paths.append(export_kg_for_dashboard(G, index, region_id, t, snapshot_dir=snapshot_dir))
    return paths


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    from src.kg.builder import build_kg_from_scenarios
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    G, index = build_kg_from_scenarios()
    if not index.by_region:
        log.warning("[kg-export] no scenarios — nothing to export")
        return 0
    out = export_all(G, index)
    print(f"[kg-export] wrote {len(out)} snapshot files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
