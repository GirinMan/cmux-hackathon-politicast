"""Page 2 — Poll trajectory across timesteps."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_DASH_ROOT = _HERE.parent.parent
if str(_DASH_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASH_ROOT))

import streamlit as st  # noqa: E402

from components.charts import poll_trajectory_chart  # noqa: E402
from components.data_loader import (  # noqa: E402
    get_region_label,
    load_all_results,
    render_placeholder_banner,
    render_sidebar,
    selected_regions,
)

st.set_page_config(page_title="PolitiKAST · Poll", page_icon="📈", layout="wide")
ctx = render_sidebar("Poll Trajectory")

st.title("📈 Poll Trajectory")
st.caption("timestep × 후보 지지율 추이 — consensus 신뢰구간 음영")

results, is_placeholder = load_all_results()
if is_placeholder:
    render_placeholder_banner()

if not results:
    st.warning("결과가 없습니다.", icon="⚠️")
    st.stop()

regions = selected_regions(ctx["scope"], list(results.keys()))
if not regions:
    st.info("선택된 region이 없습니다. 사이드바에서 region을 선택하세요.")
    st.stop()

if ctx["scope"] == "all":
    # 5-region grid: 2 columns × ceil(N/2) rows
    rows = [regions[i : i + 2] for i in range(0, len(regions), 2)]
    for row in rows:
        cols = st.columns(len(row))
        for col, rid in zip(cols, row):
            with col:
                with st.container(border=True):
                    st.markdown(f"#### {get_region_label(rid)}")
                    fig = poll_trajectory_chart(results[rid])
                    st.plotly_chart(fig, use_container_width=True)
else:
    rid = regions[0]
    r = results[rid]
    st.subheader(get_region_label(rid))
    fig = poll_trajectory_chart(r)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 raw poll_trajectory", expanded=False):
        st.dataframe(r.get("poll_trajectory", []), use_container_width=True)
