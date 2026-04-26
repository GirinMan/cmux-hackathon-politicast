"""Page 1 — Scenario Designer.

Lets the user pick a region, view candidates, tweak parameters, and trigger
a sim run. The actual run is fire-and-forget (subprocess.Popen) so the dashboard
doesn't block.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_DASH_ROOT = _HERE.parent.parent
if str(_DASH_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASH_ROOT))

import streamlit as st  # noqa: E402

from components.data_loader import (  # noqa: E402
    REGION_ORDER,
    REPO_ROOT,
    get_region_label,
    load_all_results,
    load_contracts,
    load_policy,
    render_placeholder_banner,
    render_sidebar,
)

st.set_page_config(page_title="PolitiKAST · Scenario", page_icon="🎬", layout="wide")
ctx = render_sidebar("Scenario")

st.title("🎬 Scenario Designer")
st.caption("region · timesteps · feature flags 지정 → 시뮬레이션 트리거")

results, is_placeholder = load_all_results()
contracts = load_contracts()
policy = load_policy() or {}

if is_placeholder:
    render_placeholder_banner()

# ---------------------------------------------------------------------------
# Form
# ---------------------------------------------------------------------------
with st.container(border=True):
    c1, c2, c3 = st.columns([1.2, 1, 1])

    with c1:
        region_id = st.selectbox(
            "Region",
            options=REGION_ORDER,
            format_func=get_region_label,
        )
    with c2:
        timesteps = st.slider("Timesteps", min_value=1, max_value=8, value=4)
    with c3:
        persona_n = st.number_input(
            "Persona n",
            min_value=10,
            max_value=2000,
            value=int(policy.get("persona_per_region", 100)) if isinstance(policy.get("persona_per_region"), (int, float)) else 100,
            step=10,
        )

    f1, f2, f3, f4 = st.columns(4)
    bandwagon = f1.checkbox("Bandwagon 효과", value=True)
    underdog = f2.checkbox("Underdog 효과", value=True)
    second_order = f3.checkbox("Second-order belief", value=False)
    kg_context = f4.checkbox("KG context 주입", value=True)

    instruction_mode = st.radio(
        "Instruction mode",
        options=["secret_ballot", "poll_response", "virtual_interview"],
        horizontal=True,
        index=0,
    )

    run_col, dry_col, _ = st.columns([1, 1, 3])
    run_clicked = run_col.button("▶️ Run scenario", type="primary", use_container_width=True)
    dry_clicked = dry_col.button("Dry-run (config 출력)", use_container_width=True)

config = {
    "region_id": region_id,
    "timesteps": timesteps,
    "persona_n": persona_n,
    "bandwagon": bandwagon,
    "underdog": underdog,
    "second_order": second_order,
    "kg_context": kg_context,
    "instruction_mode": instruction_mode,
}

if dry_clicked:
    st.json(config)

if run_clicked:
    cmd = [
        sys.executable,
        "-m",
        "src.sim.run_scenario",
        "--region",
        region_id,
        "--timesteps",
        str(timesteps),
        "--persona-n",
        str(persona_n),
        "--instruction-mode",
        instruction_mode,
    ]
    if not bandwagon:
        cmd.append("--no-bandwagon")
    if not underdog:
        cmd.append("--no-underdog")
    if second_order:
        cmd.append("--second-order")
    if not kg_context:
        cmd.append("--no-kg-context")

    log_dir = REPO_ROOT / "_workspace" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"sim_{region_id}.log"

    try:
        with log_path.open("a", encoding="utf-8") as logf:
            subprocess.Popen(
                cmd,
                cwd=str(REPO_ROOT),
                stdout=logf,
                stderr=subprocess.STDOUT,
                env=os.environ.copy(),
            )
        st.success(
            f"실행 시작 — 로그: `{log_path.relative_to(REPO_ROOT)}`. "
            "결과가 박제되면 다른 페이지에서 자동 표시됩니다.",
            icon="🚀",
        )
        st.code(" ".join(cmd))
    except FileNotFoundError:
        st.warning(
            "`src.sim.run_scenario` 모듈이 아직 없거나 import 경로가 다릅니다. "
            "sim-engineer가 빌드 중입니다.",
            icon="⏳",
        )
        st.code(" ".join(cmd))

st.divider()

# ---------------------------------------------------------------------------
# Snapshot of selected region
# ---------------------------------------------------------------------------
st.subheader(f"Region snapshot · {get_region_label(region_id)}")

if region_id in results:
    r = results[region_id]
    st.caption(
        ("🛰️ placeholder" if r.get("_placeholder") else "✅ live")
        + f" · scenario_id: `{r.get('scenario_id', '-')}`"
        + f" · contest_id: `{r.get('contest_id', '-')}`"
    )

    cands = r.get("candidates", [])
    if cands:
        st.markdown("**후보 목록**")
        st.dataframe(
            [
                {
                    "id": c["id"],
                    "이름": c.get("name", "-"),
                    "정당": c.get("party", "-"),
                }
                for c in cands
            ],
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info(f"`{region_id}` 결과가 아직 박제되지 않았습니다.", icon="⏳")

st.divider()

# ---------------------------------------------------------------------------
# Policy & log tail
# ---------------------------------------------------------------------------
with st.expander("📜 Policy & 빌드 로그", expanded=False):
    st.markdown("**Active policy**")
    if policy:
        st.json(policy)
    else:
        st.caption("policy.json 미존재")

    log_md = REPO_ROOT / "_workspace" / "checkpoints" / "policy_log.md"
    st.markdown("**policy_log.md (마지막 50줄)**")
    if log_md.exists():
        text = log_md.read_text(encoding="utf-8", errors="replace").splitlines()
        st.code("\n".join(text[-50:]) or "(empty)")
    else:
        st.caption("policy_log.md 미존재")
