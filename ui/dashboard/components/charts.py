"""Plotly chart factories shared across dashboard pages."""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Color palette — keep candidate colors stable across pages.
# ---------------------------------------------------------------------------
PARTY_COLORS = {
    # Korean canonical names
    "더불어민주당": "#004EA2",
    "국민의힘": "#E61E2B",
    "정의당": "#FFCC00",
    "진보당": "#D6001C",
    "개혁신당": "#FF7A00",
    "조국혁신당": "#5A2D82",
    "기본소득당": "#00B760",
    "녹색정의당": "#62C036",
    "무소속": "#888888",
    # Sim-engineer slug encodings
    "p_dem": "#004EA2",
    "p_ppp": "#E61E2B",
    "p_jpp": "#FFCC00",
    "p_rebuild": "#FF7A00",
    "p_jhk": "#5A2D82",   # 조국혁신당
    "p_progressive": "#D6001C",
    "p_basic": "#00B760",
    "p_indep": "#888888",
    "p_none": "#AAAAAA",
}

ABSTAIN_COLOR = "#BBBBBB"


def _candidate_color(candidate: dict[str, Any]) -> str:
    party = candidate.get("party")
    return PARTY_COLORS.get(party, "#3D8BFD")


def candidate_color_map(candidates: list[dict[str, Any]]) -> dict[str, str]:
    return {c["id"]: _candidate_color(c) for c in candidates}


def candidate_label(candidate: dict[str, Any]) -> str:
    name = candidate.get("name", candidate["id"])
    party = candidate.get("party")
    return f"{name} ({party})" if party else name


# ---------------------------------------------------------------------------
# Poll trajectory
# ---------------------------------------------------------------------------
def poll_trajectory_chart(result: dict[str, Any], title: str | None = None) -> go.Figure:
    candidates = result.get("candidates", [])
    cmap = candidate_color_map(candidates)
    cnames = {c["id"]: candidate_label(c) for c in candidates}
    traj = result.get("poll_trajectory", [])

    fig = go.Figure()
    if not traj:
        fig.add_annotation(text="poll_trajectory 비어있음", showarrow=False)
        return fig

    xs = [p.get("date") or p.get("timestep") for p in traj]

    for c in candidates:
        cid = c["id"]
        ys = [p.get("support_by_candidate", {}).get(cid, 0) for p in traj]
        # consensus interval
        var = [p.get("consensus_var", 0) for p in traj]
        upper = [y + (v ** 0.5) for y, v in zip(ys, var)]
        lower = [max(0, y - (v ** 0.5)) for y, v in zip(ys, var)]
        color = cmap.get(cid, "#3D8BFD")

        fig.add_trace(
            go.Scatter(
                x=xs + xs[::-1],
                y=upper + lower[::-1],
                fill="toself",
                fillcolor=_rgba(color, 0.12),
                line=dict(color="rgba(0,0,0,0)"),
                hoverinfo="skip",
                showlegend=False,
                name=f"{cnames[cid]} CI",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines+markers",
                line=dict(color=color, width=2.5),
                name=cnames[cid],
                hovertemplate="%{x}<br>%{y:.1%}<extra>" + cnames[cid] + "</extra>",
            )
        )

    fig.update_layout(
        title=title,
        yaxis=dict(tickformat=".0%", range=[0, 1]),
        xaxis_title="시점",
        yaxis_title="지지율",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=40, b=20),
        height=380,
        legend=dict(orientation="h", y=-0.2),
    )
    return fig


# ---------------------------------------------------------------------------
# Final outcome
# ---------------------------------------------------------------------------
def final_outcome_bar(result: dict[str, Any], title: str | None = None) -> go.Figure:
    candidates = result.get("candidates", [])
    cmap = candidate_color_map(candidates)
    cnames = {c["id"]: candidate_label(c) for c in candidates}
    cnames["abstain"] = "기권"
    cmap["abstain"] = ABSTAIN_COLOR

    shares = result.get("final_outcome", {}).get("vote_share_by_candidate", {})
    if not shares:
        fig = go.Figure()
        fig.add_annotation(text="final_outcome 비어있음", showarrow=False)
        return fig

    items = sorted(shares.items(), key=lambda kv: -kv[1])
    fig = go.Figure(
        data=go.Bar(
            x=[cnames.get(k, k) for k, _ in items],
            y=[v for _, v in items],
            marker_color=[cmap.get(k, "#3D8BFD") for k, _ in items],
            text=[f"{v:.1%}" for _, v in items],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=title,
        yaxis=dict(tickformat=".0%", range=[0, max(items[0][1] + 0.1, 0.5)]),
        margin=dict(l=20, r=20, t=40, b=20),
        height=320,
    )
    return fig


def turnout_gauge(turnout: float, title: str = "투표율") -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=turnout * 100,
            number={"suffix": "%"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#3D8BFD"},
                "steps": [
                    {"range": [0, 40], "color": "#fee"},
                    {"range": [40, 60], "color": "#fed"},
                    {"range": [60, 100], "color": "#dfd"},
                ],
            },
            title={"text": title},
        )
    )
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=240)
    return fig


# ---------------------------------------------------------------------------
# Demographics (stacked bar)
# ---------------------------------------------------------------------------
def demographics_stacked_bar(
    breakdown: dict[str, dict[str, float]],
    candidates: list[dict[str, Any]],
    title: str = "",
) -> go.Figure:
    cmap = candidate_color_map(candidates)
    cmap["abstain"] = ABSTAIN_COLOR
    cnames = {c["id"]: candidate_label(c) for c in candidates}
    cnames["abstain"] = "기권"

    if not breakdown:
        fig = go.Figure()
        fig.add_annotation(text="breakdown 비어있음", showarrow=False)
        return fig

    segments = list(breakdown.keys())
    # Collect candidate ids across segments
    cids: list[str] = []
    for seg, dist in breakdown.items():
        for cid in dist:
            if cid not in cids:
                cids.append(cid)

    fig = go.Figure()
    for cid in cids:
        ys = [breakdown[seg].get(cid, 0) for seg in segments]
        fig.add_trace(
            go.Bar(
                name=cnames.get(cid, cid),
                x=segments,
                y=ys,
                marker_color=cmap.get(cid, "#3D8BFD"),
                hovertemplate="%{x}<br>%{y:.1%}<extra>" + cnames.get(cid, cid) + "</extra>",
            )
        )
    fig.update_layout(
        barmode="stack",
        title=title,
        yaxis=dict(tickformat=".0%", range=[0, 1]),
        margin=dict(l=20, r=20, t=40, b=20),
        height=340,
        legend=dict(orientation="h", y=-0.25),
    )
    return fig


# ---------------------------------------------------------------------------
# KG node-link (plotly fallback; no pyvis dependency required)
# ---------------------------------------------------------------------------
def _edge_endpoints(e: dict[str, Any]) -> tuple[str | None, str | None, str]:
    """Tolerate both `src`/`dst` and `source`/`target` edge schemas."""
    src = e.get("src") or e.get("source")
    dst = e.get("dst") or e.get("target")
    rel = e.get("rel") or e.get("type") or ""
    return src, dst, rel


def kg_nodelink(kg: dict[str, Any], timestep_max: int | None = None) -> go.Figure:
    nodes = list(kg.get("nodes", []))
    edges = list(kg.get("edges", []))
    if timestep_max is not None:
        # Only filter if nodes/edges actually have timestep keys (legacy schema).
        if any(n.get("timestep") is not None for n in nodes):
            nodes = [n for n in nodes if n.get("timestep") is None or n.get("timestep") <= timestep_max]
            node_ids = {n["id"] for n in nodes}
            edges = [
                e for e in edges
                if (e.get("timestep") is None or e.get("timestep") <= timestep_max)
                and (_edge_endpoints(e)[0] in node_ids)
                and (_edge_endpoints(e)[1] in node_ids)
            ]

    if not nodes:
        fig = go.Figure()
        fig.add_annotation(text="KG 비어있음", showarrow=False)
        return fig

    # Layout by type ring. Inner rings = "core" entities, outer = events/discourse.
    type_radius = {
        "Election": 0.0,
        "Contest": 0.8,
        "Candidate": 1.6,
        "Party": 2.4,
        "District": 2.4,
        "PolicyIssue": 3.2,
        "NarrativeFrame": 3.2,
        # Events & discourse on outer ring
        "MediaEvent": 4.4,
        "ScandalEvent": 4.4,
        "PressConference": 4.4,
        "PollPublication": 4.4,
        "Event": 4.4,
        "Issue": 3.2,  # legacy
        "Frame": 3.2,  # legacy
    }
    type_color = {
        "Election": "#264653",
        "Contest": "#1D3557",
        "Candidate": "#E63946",
        "Party": "#A8DADC",
        "District": "#F1FAEE",
        "PolicyIssue": "#457B9D",
        "NarrativeFrame": "#8338EC",
        "MediaEvent": "#2A9D8F",
        "ScandalEvent": "#E76F51",
        "PressConference": "#F4A261",
        "PollPublication": "#06A77D",
        "Event": "#2A9D8F",
        "Issue": "#1D3557",
        "Frame": "#457B9D",
    }

    by_type: dict[str, list[dict]] = {}
    for n in nodes:
        by_type.setdefault(n.get("type", "Other"), []).append(n)

    import math

    pos: dict[str, tuple[float, float]] = {}
    for t, bucket in by_type.items():
        r = type_radius.get(t, 5.2)
        # Phase offset per type to avoid stacking on same axis.
        phase = (hash(t) % 360) / 360.0 * 2 * math.pi
        for i, n in enumerate(bucket):
            if r == 0.0:
                pos[n["id"]] = (0.0, 0.0)
                continue
            theta = phase + 2 * math.pi * i / max(len(bucket), 1)
            pos[n["id"]] = (r * math.cos(theta), r * math.sin(theta))

    edge_x: list[float] = []
    edge_y: list[float] = []
    edge_hover: list[str] = []
    for e in edges:
        src, dst, rel = _edge_endpoints(e)
        if src in pos and dst in pos:
            x0, y0 = pos[src]
            x1, y1 = pos[dst]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            edge_hover.append(rel)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=edge_x, y=edge_y, mode="lines",
            line=dict(color="#bbb", width=1),
            hoverinfo="none", showlegend=False,
        )
    )
    for t, bucket in by_type.items():
        xs = [pos[n["id"]][0] for n in bucket]
        ys = [pos[n["id"]][1] for n in bucket]
        labels = [n.get("label") or n["id"] for n in bucket]
        fig.add_trace(
            go.Scatter(
                x=xs, y=ys, mode="markers+text",
                marker=dict(size=20, color=type_color.get(t, "#888"), line=dict(color="#fff", width=1)),
                text=labels, textposition="bottom center",
                hovertemplate="%{text}<extra>" + t + "</extra>",
                name=t,
            )
        )
    fig.update_layout(
        showlegend=True,
        height=600,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
        legend=dict(itemsizing="constant"),
    )
    return fig


# ---------------------------------------------------------------------------
# Tiny helpers
# ---------------------------------------------------------------------------
def _rgba(hex_color: str, alpha: float) -> str:
    """Convert #rrggbb → rgba string."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return f"rgba(60,139,253,{alpha})"
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def candidates_legend_df(candidates: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"후보": c.get("name", c["id"]), "정당": c.get("party", "-"), "id": c["id"]}
            for c in candidates
        ]
    )
