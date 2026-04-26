"""Page 4 — Demographics breakdown (age, education, district)."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_DASH_ROOT = _HERE.parent.parent
if str(_DASH_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASH_ROOT))

import streamlit as st  # noqa: E402

from components.charts import demographics_stacked_bar  # noqa: E402
from components.data_loader import (  # noqa: E402
    get_region_label,
    load_all_results,
    render_placeholder_banner,
    render_sidebar,
    selected_regions,
)

st.set_page_config(page_title="PolitiKAST · Demographics", page_icon="👥", layout="wide")
ctx = render_sidebar("Demographics")

st.title("👥 Demographics Breakdown")
st.caption("연령 · 학력 · 지역구별 후보 지지 분포")

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

# Tabs control which segmentation we're looking at.
tab_age, tab_edu, tab_dist, tab_compare = st.tabs(
    ["연령", "학력", "지역구", "광주 vs 대구 (이념 효과)"]
)


def _segment_chart(rid: str, segment_key: str) -> None:
    r = results[rid]
    breakdown = r.get("demographics_breakdown", {}).get(segment_key, {})
    if not breakdown:
        st.caption(f"{rid} · {segment_key} 데이터가 없습니다.")
        return
    st.plotly_chart(
        demographics_stacked_bar(
            breakdown, r.get("candidates", []), title=get_region_label(rid)
        ),
        use_container_width=True,
    )


for tab, key in [
    (tab_age, "by_age_group"),
    (tab_edu, "by_education"),
    (tab_dist, "by_district"),
]:
    with tab:
        if ctx["scope"] == "all":
            rows = [regions[i : i + 2] for i in range(0, len(regions), 2)]
            for row in rows:
                cols = st.columns(len(row))
                for col, rid in zip(cols, row):
                    with col:
                        with st.container(border=True):
                            _segment_chart(rid, key)
        else:
            _segment_chart(regions[0], key)


with tab_compare:
    st.markdown(
        "광주(진보 우세) vs 대구(보수 우세) — **연령대 효과가 이념 prior 위에 어떻게 얹히는지** 비교."
    )
    if "gwangju_mayor" in results and "daegu_mayor" in results:
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown("#### 광주 — 연령대별")
                _segment_chart("gwangju_mayor", "by_age_group")
        with c2:
            with st.container(border=True):
                st.markdown("#### 대구 — 연령대별")
                _segment_chart("daegu_mayor", "by_age_group")

        c3, c4 = st.columns(2)
        with c3:
            with st.container(border=True):
                st.markdown("#### 광주 — 학력별")
                _segment_chart("gwangju_mayor", "by_education")
        with c4:
            with st.container(border=True):
                st.markdown("#### 대구 — 학력별")
                _segment_chart("daegu_mayor", "by_education")
    else:
        st.info("광주/대구 결과가 모두 박제되어야 비교 뷰가 활성화됩니다.")
