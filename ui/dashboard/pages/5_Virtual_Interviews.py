"""Page 5 — Virtual interviews (persona cards: vote, reason, key_factors)."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_DASH_ROOT = _HERE.parent.parent
if str(_DASH_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASH_ROOT))

import streamlit as st  # noqa: E402

from components.data_loader import (  # noqa: E402
    get_region_label,
    load_all_results,
    render_placeholder_banner,
    render_sidebar,
    selected_regions,
)

st.set_page_config(page_title="PolitiKAST · Interviews", page_icon="🗣️", layout="wide")
ctx = render_sidebar("Virtual Interviews")

st.title("🗣️ Virtual Interviews")
st.caption("페르소나 → vote · reason · key_factors")

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

# Aggregate interviews across selected regions
all_interviews: list[tuple[str, dict]] = []
for rid in regions:
    for iv in results[rid].get("virtual_interviews", []):
        all_interviews.append((rid, iv))

if not all_interviews:
    st.warning("virtual_interviews가 비어있습니다.")
    st.stop()

# Filters
f1, f2, f3 = st.columns([1.2, 1, 1])

candidate_options = sorted(
    {iv.get("vote") or "기권" for _, iv in all_interviews},
    key=lambda x: x or "",
)
vote_filter = f1.multiselect(
    "투표 후보 (또는 기권)",
    options=candidate_options,
    default=candidate_options,
)

max_n = len(all_interviews)
how_many = f2.slider("표시 개수", min_value=1, max_value=max(max_n, 1), value=min(20, max_n))

key_factor_universe = sorted(
    {kf for _, iv in all_interviews for kf in (iv.get("key_factors") or [])}
)
factor_filter = f3.multiselect(
    "Key factor 필터",
    options=key_factor_universe,
    default=[],
    help="선택한 factor 중 하나라도 포함하는 인터뷰만 표시. 비어있으면 전체.",
)


def _matches(iv: dict) -> bool:
    vote_label = iv.get("vote") or "기권"
    if vote_label not in vote_filter:
        return False
    if factor_filter:
        kfs = set(iv.get("key_factors") or [])
        if not (kfs & set(factor_filter)):
            return False
    return True


filtered = [(rid, iv) for rid, iv in all_interviews if _matches(iv)][:how_many]
st.caption(f"{len(filtered)} / {len(all_interviews)} 인터뷰 표시")

# Build candidate id → display lookup per region
def _candidate_display(rid: str, cid: str | None) -> str:
    if cid is None:
        return "기권"
    for c in results[rid].get("candidates", []):
        if c["id"] == cid:
            party = c.get("party", "-")
            return f"{c.get('name', cid)} ({party})"
    return cid


# Card grid (3 cols)
for i in range(0, len(filtered), 3):
    cols = st.columns(3)
    for col, (rid, iv) in zip(cols, filtered[i : i + 3]):
        with col:
            with st.container(border=True):
                pid = iv.get("persona_id", "-")
                # Truncate long uuids
                pid_short = pid if len(pid) <= 12 else pid[:8] + "…"
                st.markdown(f"**{get_region_label(rid)}** · `{pid_short}`")
                summary = (iv.get("persona_summary") or "").strip()
                if summary:
                    st.caption(summary)
                else:
                    st.caption("페르소나 요약 미제공")
                vote_disp = _candidate_display(rid, iv.get("vote"))
                if iv.get("vote") is None:
                    st.markdown(f"🤐 **{vote_disp}**")
                else:
                    st.markdown(f"🗳️ **{vote_disp}**")
                reason = iv.get("reason", "")
                if reason:
                    st.markdown(f"> {reason}")
                kfs = iv.get("key_factors") or []
                if kfs:
                    st.markdown(" ".join(f"`{kf}`" for kf in kfs))
                t = iv.get("timestep")
                if t is not None:
                    st.caption(f"timestep {t}")
