"""Page 3 — Final outcome bars + turnout gauge + district breakdown."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_DASH_ROOT = _HERE.parent.parent
if str(_DASH_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASH_ROOT))

import streamlit as st  # noqa: E402

from components.charts import (  # noqa: E402
    demographics_stacked_bar,
    final_outcome_bar,
    turnout_gauge,
)
from components.data_loader import (  # noqa: E402
    get_region_label,
    load_all_results,
    render_placeholder_banner,
    render_sidebar,
    result_status_badge,
    selected_regions,
)

st.set_page_config(page_title="PolitiKAST · Outcome", page_icon="🏆", layout="wide")
ctx = render_sidebar("Final Outcome")

st.title("🏆 Final Outcome")
st.caption("후보별 최종 득표율 · 투표율 · 시·구 단위 분포")

results, is_placeholder = load_all_results()
if is_placeholder:
    render_placeholder_banner()

if not results:
    st.warning("결과가 없습니다.", icon="⚠️")
    st.stop()

regions = selected_regions(ctx["scope"], list(results.keys()))
if not regions:
    st.info("선택된 region이 없습니다.")
    st.stop()


def _render_region(rid: str) -> None:
    r = results[rid]
    st.markdown(f"### {get_region_label(rid)}  ·  {result_status_badge(r)}")

    bar_col, gauge_col = st.columns([2, 1])
    with bar_col:
        st.plotly_chart(final_outcome_bar(r, title="최종 득표율"), use_container_width=True)
    with gauge_col:
        turnout = r.get("final_outcome", {}).get("turnout", 0)
        st.plotly_chart(turnout_gauge(turnout), use_container_width=True)

    breakdown = r.get("demographics_breakdown", {}).get("by_district", {})
    if breakdown:
        st.markdown("**시·구 단위 분포**")
        st.plotly_chart(
            demographics_stacked_bar(breakdown, r.get("candidates", [])),
            use_container_width=True,
        )
    else:
        st.caption("by_district 데이터가 없습니다.")


if ctx["scope"] == "all":
    for rid in regions:
        with st.container(border=True):
            _render_region(rid)
else:
    _render_region(regions[0])
