"""Page 6 — Knowledge Graph viewer (region + timestep aware)."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_DASH_ROOT = _HERE.parent.parent
if str(_DASH_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASH_ROOT))

import streamlit as st  # noqa: E402

from components.charts import _edge_endpoints, kg_nodelink  # noqa: E402
from components.data_loader import (  # noqa: E402
    REGION_ORDER,
    get_region_label,
    list_kg_snapshots,
    load_kg,
    render_placeholder_banner,
    render_sidebar,
)

st.set_page_config(page_title="PolitiKAST · KG", page_icon="🕸️", layout="wide")
ctx = render_sidebar("KG Viewer")

st.title("🕸️ Knowledge Graph Viewer")
st.caption("Election + Event/Discourse 온톨로지 — 시점별 KG 변화")

snapshots = list_kg_snapshots()

# What regions/timesteps does the sim have on disk?
real_snaps = [s for s in snapshots if not s["is_placeholder"] and s["region_id"]]
regions_available = sorted({s["region_id"] for s in real_snaps if s["region_id"] in REGION_ORDER})
if not regions_available:
    regions_available = [r for r in REGION_ORDER]  # placeholder fallback

c1, c2 = st.columns([1, 1])
with c1:
    region_id = st.selectbox(
        "Region",
        options=regions_available,
        format_func=get_region_label,
        index=0,
    )
with c2:
    region_snaps = [s for s in real_snaps if s["region_id"] == region_id]
    timesteps_available = sorted({s["timestep"] for s in region_snaps if s["timestep"] is not None})
    if timesteps_available:
        timestep = st.select_slider(
            "Timestep",
            options=timesteps_available,
            value=timesteps_available[-1],
        )
    else:
        timestep = None
        st.caption("실 KG 스냅샷 없음 — placeholder 표시")

kg, is_placeholder = load_kg(region_id=region_id, timestep=timestep)

if is_placeholder:
    render_placeholder_banner()

cutoff = kg.get("cutoff_ts")
if cutoff:
    st.caption(f"📅 cutoff: `{cutoff}` · scenario_id: `{kg.get('scenario_id', '-')}`")

nodes = kg.get("nodes", [])
edges = kg.get("edges", [])

if not nodes:
    st.warning(
        "KG 데이터가 비어있습니다. kg-engineer가 `_workspace/snapshots/kg_<region>_t<N>.json`을 박제하면 활성화됩니다.",
        icon="⚠️",
    )
    st.stop()

types = sorted({n.get("type", "Other") for n in nodes})
visible_types = st.multiselect("표시 노드 타입", options=types, default=types)
filtered_kg = {
    "nodes": [n for n in nodes if n.get("type", "Other") in visible_types],
    "edges": edges,
}

st.plotly_chart(kg_nodelink(filtered_kg), use_container_width=True)

# Stats
c1, c2, c3, c4 = st.columns(4)
visible_ids = {n["id"] for n in filtered_kg["nodes"]}
visible_edges = [
    e for e in edges
    if (_edge_endpoints(e)[0] in visible_ids and _edge_endpoints(e)[1] in visible_ids)
]
c1.metric("Visible nodes", len(filtered_kg["nodes"]))
c2.metric("Visible edges", len(visible_edges))
c3.metric("Total nodes", len(nodes))
c4.metric("Available timesteps", len(timesteps_available) if timesteps_available else 0)

# Snapshot catalog
with st.expander("🗂️ KG 스냅샷 카탈로그", expanded=False):
    if real_snaps:
        st.dataframe(
            [
                {
                    "region": s["region_id"],
                    "timestep": s["timestep"],
                    "scenario": s["scenario_id"],
                    "path": Path(s["path"]).name,
                }
                for s in real_snaps
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("아직 실 KG 스냅샷이 없습니다.")

with st.expander("📋 raw KG payload (head)", expanded=False):
    st.json({"nodes": filtered_kg["nodes"][:20], "edges": visible_edges[:40]})
    if len(nodes) > 20 or len(visible_edges) > 40:
        st.caption("(상위 20 노드 / 40 엣지만 표시)")
