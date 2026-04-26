#!/usr/bin/env python3
"""Generate submission-grade PolitiKAST paper figures.

The output is intentionally deterministic and vector-first. This is safer than
bitmap image generation for a paper diagram because labels, counts, and paths
must remain exact. Numeric panels read only local artifacts; schematic panels
are explicitly architectural diagrams.
"""

from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = ROOT / "paper" / "assets"
ASSET_DIR.mkdir(parents=True, exist_ok=True)

COLORS = {
    "ink": "#111827",
    "text": "#374151",
    "muted": "#6B7280",
    "line": "#D1D5DB",
    "grid": "#E5E7EB",
    "panel": "#F9FAFB",
    "blue": "#2563EB",
    "blue_light": "#DBEAFE",
    "green": "#059669",
    "green_light": "#D1FAE5",
    "red": "#DC2626",
    "red_light": "#FEE2E2",
    "amber": "#D97706",
    "amber_light": "#FEF3C7",
}


EXTERNAL_SOURCES = {
    "nemotron": {
        "title": "NVIDIA/Hugging Face Nemotron-Personas-Korea",
        "url": "https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea",
        "notes": "Dataset identity, license, record count, field framing, and source citation.",
    },
    "camel": {
        "title": "CAMEL: Communicative Agents for Mind Exploration of Large Language Model Society",
        "url": "https://arxiv.org/abs/2303.17760",
        "notes": "Multi-agent framework context.",
    },
    "electionsim": {
        "title": "ElectionSim: Massive Population Election Simulation Powered by Large Language Model Driven Agents",
        "url": "https://arxiv.org/abs/2410.20746",
        "notes": "Related-work positioning only; no PolitiKAST values copied.",
    },
}


@dataclass
class AssetRecord:
    name: str
    files: list[str]
    caption: str
    evidence: list[str]
    usage: str
    caution: str


records: list[AssetRecord] = []


def load_json(rel: str) -> Any:
    with (ROOT / rel).open(encoding="utf-8") as f:
        return json.load(f)


def wrap(text: str, width: int = 24) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False))


def style_axes(ax) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLORS["line"])
    ax.spines["bottom"].set_color(COLORS["line"])
    ax.tick_params(colors=COLORS["text"], labelsize=8)
    ax.grid(color=COLORS["grid"], linewidth=0.6)


def add_title(fig, title: str, subtitle: str | None = None) -> None:
    fig.text(0.055, 0.945, title, fontsize=13.5, fontweight="bold", color=COLORS["ink"])
    if subtitle:
        fig.text(0.055, 0.905, subtitle, fontsize=8.5, color=COLORS["muted"])


def box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    body: str = "",
    *,
    fc: str = "white",
    ec: str = COLORS["line"],
    title_color: str = COLORS["ink"],
    lw: float = 0.9,
) -> None:
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.012",
        linewidth=lw,
        facecolor=fc,
        edgecolor=ec,
    )
    ax.add_patch(patch)
    ax.text(x + 0.018, y + h - 0.035, title, ha="left", va="top", fontsize=9, fontweight="bold", color=title_color)
    if body:
        ax.text(x + 0.018, y + h - 0.078, body, ha="left", va="top", fontsize=7.5, color=COLORS["text"], linespacing=1.25)


def arrow(ax, start, end, *, color: str = COLORS["muted"], lw: float = 1.0, rad: float = 0.0) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=lw,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
            shrinkA=4,
            shrinkB=4,
        )
    )


def save_asset(fig, name: str, *, caption: str, evidence: list[str], usage: str, caution: str) -> None:
    files = []
    for ext in ("pdf", "svg", "png"):
        path = ASSET_DIR / f"{name}.{ext}"
        fig.savefig(path, bbox_inches="tight", facecolor="white", dpi=260)
        files.append(str(path.relative_to(ROOT)))
    plt.close(fig)
    records.append(AssetRecord(name, files, caption, evidence, usage, caution))


def figure_pipeline() -> None:
    fig, ax = plt.subplots(figsize=(7.2, 3.2), facecolor="white")
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    add_title(fig, "PolitiKAST pipeline", "Data, retrieval, and simulation stages used by the current harness.")

    xs = [0.06, 0.27, 0.48, 0.69]
    labels = [
        ("Persona substrate", "Nemotron-Korea\nParquet -> DuckDB"),
        ("Political context", "contests, polls,\nKG events"),
        ("Time-bounded agent", "firewall + LLMPool\nJSON decisions"),
        ("Artifacts", "results index\npaper/dashboard"),
    ]
    for i, (x, (title, body)) in enumerate(zip(xs, labels)):
        box(ax, x, 0.47, 0.16, 0.25, title, body, fc=COLORS["panel"], ec=COLORS["line"])
        if i:
            arrow(ax, (xs[i - 1] + 0.16, 0.595), (x, 0.595))

    box(ax, 0.31, 0.17, 0.18, 0.14, "Temporal firewall", "retrieve only\nD <= t", fc=COLORS["blue_light"], ec=COLORS["blue"])
    box(ax, 0.58, 0.17, 0.18, 0.14, "Capacity policy", "keys, RPM,\ndownscale flags", fc=COLORS["amber_light"], ec=COLORS["amber"])
    arrow(ax, (0.40, 0.31), (0.56, 0.47), color=COLORS["blue"], rad=-0.12)
    arrow(ax, (0.67, 0.31), (0.77, 0.47), color=COLORS["amber"], rad=0.10)
    fig.text(0.055, 0.045, "Schematic only. Evidence: _workspace/contracts, src/kg, src/sim, results_index.json.", fontsize=7.2, color=COLORS["muted"])
    save_asset(
        fig,
        "fig_pipeline_architecture",
        caption="PolitiKAST pipeline from persona data and political context to time-bounded voter-agent artifacts.",
        evidence=["_workspace/contracts/*.json", "src/kg/*.py", "src/sim/*.py", "_workspace/snapshots/results_index.json"],
        usage="Methods overview figure and presentation architecture slide.",
        caution="Architecture schematic only; it does not encode empirical performance.",
    )


def figure_persona_card() -> None:
    fig, ax = plt.subplots(figsize=(6.6, 3.4), facecolor="white")
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    add_title(fig, "Synthetic electorate substrate", "Dataset-card facts used by the simulator design.")

    metrics = [
        ("1,004,752", "records"),
        ("~7M", "persona descriptions"),
        ("26", "fields"),
        ("17", "provinces"),
        ("252", "districts"),
    ]
    for i, (value, label) in enumerate(metrics):
        x = 0.06 + i * 0.18
        ax.add_patch(Rectangle((x, 0.58), 0.145, 0.16, facecolor="white", edgecolor=COLORS["line"], linewidth=0.9))
        ax.text(x + 0.0725, 0.675, value, ha="center", va="center", fontsize=12, fontweight="bold", color=COLORS["blue"])
        ax.text(x + 0.0725, 0.615, label, ha="center", va="center", fontsize=7.4, color=COLORS["text"])

    box(ax, 0.08, 0.22, 0.35, 0.21, "Narrative fields", "core, professional, family,\ntravel, culinary, arts, sports", fc=COLORS["panel"])
    box(ax, 0.56, 0.22, 0.35, 0.21, "Tabular fields", "region, age, sex, education,\nhousehold and occupation fields", fc=COLORS["panel"])
    arrow(ax, (0.43, 0.325), (0.56, 0.325), color=COLORS["blue"])
    fig.text(0.055, 0.05, "External evidence: Hugging Face dataset page. Local coverage: data_paths.json.", fontsize=7.2, color=COLORS["muted"])
    save_asset(
        fig,
        "fig_persona_data_card",
        caption="Dataset-card summary for Nemotron-Personas-Korea as used by the persona layer.",
        evidence=["https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea", "_workspace/contracts/data_paths.json"],
        usage="Data subsection and setup slide.",
        caution="Dataset-level facts are cited externally; this is not an official electorate-size chart.",
    )


def figure_target_regions() -> None:
    d = load_json("_workspace/contracts/data_paths.json")
    regions = d["regions"]
    pop = d["region_population"]
    avg_age = d["region_avg_age"]
    rows = [(r["label"], r["id"], int(pop[r["id"]]), float(avg_age[r["id"]])) for r in regions]
    rows = sorted(rows, key=lambda x: x[2])
    labels = [wrap(f"{label}\n{id_}", 18) for label, id_, _, _ in rows]
    counts = np.array([c for _, _, c, _ in rows])
    ages = [a for _, _, _, a in rows]
    y = np.arange(len(rows))

    fig, ax = plt.subplots(figsize=(6.8, 3.6), facecolor="white")
    ax.set_xscale("log")
    ax.hlines(y, counts.min() * 0.75, counts, color=COLORS["line"], linewidth=1.1)
    ax.scatter(counts, y, s=46, color=COLORS["blue"], zorder=3)
    ax.set_yticks(y, labels, fontsize=7.2)
    ax.set_xlabel("adult persona records available for sampling (log scale)", fontsize=8)
    style_axes(ax)
    ax.grid(axis="y", visible=False)
    for yi, c, age in zip(y, counts, ages):
        ax.text(c * 1.07, yi, f"{c:,} / age {age:.1f}", va="center", fontsize=7.2, color=COLORS["text"])
    add_title(fig, "Target-region persona coverage", "Local synthetic-persona coverage by current harness region.")
    fig.text(0.055, 0.025, "Source: _workspace/contracts/data_paths.json. Counts are sampling substrate, not population totals.", fontsize=7.2, color=COLORS["muted"])
    fig.subplots_adjust(left=0.30, right=0.88, top=0.80, bottom=0.20)
    save_asset(
        fig,
        "fig_target_region_coverage",
        caption="Synthetic adult-persona coverage for the five target contests in the current harness.",
        evidence=["_workspace/contracts/data_paths.json"],
        usage="Data/methods figure and target-contest selection slide.",
        caution="Local synthetic-persona coverage only; not official electorate size or forecast output.",
    )


def _candidate_labels(result: dict[str, Any]) -> dict[str, str]:
    out = {}
    for candidate in result.get("candidates", []):
        party = candidate.get("party", "")
        label = candidate.get("name", candidate["id"])
        out[candidate["id"]] = f"{label} ({party})" if party else label
    return out


def figure_result_summary() -> None:
    idx_path = ROOT / "_workspace/snapshots/results_index.json"
    if not idx_path.exists():
        return
    idx = load_json("_workspace/snapshots/results_index.json")
    rows = []
    skipped = 0
    for row in idx:
        path = ROOT / row.get("path", "")
        if not path.exists():
            continue
        result = json.loads(path.read_text(encoding="utf-8"))
        outcome = result.get("final_outcome", {})
        shares = outcome.get("vote_share_by_candidate", {}) or {}
        n_responses = int(outcome.get("n_responses", result.get("persona_n", 0)) or 0)
        positive = {k: float(v) for k, v in shares.items() if float(v or 0) > 0}
        if not positive or n_responses == 0:
            skipped += 1
            continue
        winner = outcome.get("winner") or max(positive, key=positive.get)
        rows.append(
            {
                "region": result.get("region_id", row.get("region_id", "?")),
                "n": int(result.get("persona_n", row.get("persona_n", 0)) or 0),
                "turnout": float(outcome.get("turnout", 0.0) or 0.0),
                "winner_share": float(shares.get(winner, 0.0) or 0.0),
                "winner": _candidate_labels(result).get(winner, winner),
            }
        )
    if not rows:
        return

    rows = sorted(rows, key=lambda r: r["region"])
    x = np.arange(len(rows))
    width = 0.34
    fig, ax = plt.subplots(figsize=(6.8, 3.6), facecolor="white")
    ax.bar(x - width / 2, [r["winner_share"] for r in rows], width, color=COLORS["blue"], label="winner share")
    ax.bar(x + width / 2, [r["turnout"] for r in rows], width, color="white", edgecolor=COLORS["blue"], hatch="//", label="turnout")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("share", fontsize=8)
    ax.set_xticks(x, [wrap(f"{r['region']}\nn={r['n']}", 14) for r in rows], rotation=0, fontsize=7.0)
    style_axes(ax)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left", frameon=False, fontsize=7.5)
    add_title(fig, "Indexed local result artifacts", "Diagnostic bars copied from local JSON fields; not calibrated forecasts.")
    if skipped:
        fig.text(0.055, 0.025, f"Source: results_index.json and result JSON files. Skipped {skipped} empty/zero-response artifact(s).", fontsize=7.2, color=COLORS["muted"])
    else:
        fig.text(0.055, 0.025, "Source: results_index.json and result JSON files.", fontsize=7.2, color=COLORS["muted"])
    fig.subplots_adjust(left=0.10, right=0.98, top=0.80, bottom=0.22)
    save_asset(
        fig,
        "fig_local_result_artifacts",
        caption="Winner vote share and turnout for currently available non-empty local result artifacts.",
        evidence=["_workspace/snapshots/results_index.json", "_workspace/snapshots/results/*.json"],
        usage="Results/status figure with explicit smoke-run caveat.",
        caution="Not calibrated forecast evidence. Do not present as real election prediction performance.",
    )


def figure_capacity_status() -> None:
    c = load_json("_workspace/checkpoints/capacity_probe.json")
    configured = int(c.get("n_configured_keys", c.get("n_keys", 0)) or 0)
    active = int(c.get("n_active_keys", c.get("n_keys", configured)) or 0)
    rpm = float(c.get("measured_total_rpm", c.get("total_rpm", 0.0)) or 0.0)

    fig, ax = plt.subplots(figsize=(6.8, 3.1), facecolor="white")
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    add_title(fig, "LLM capacity gate", "Operational probe artifact used to set sampling budgets.")
    metrics = [("configured keys", configured), ("active keys", active), ("measured RPM", rpm)]
    for i, (label, value) in enumerate(metrics):
        x = 0.08 + i * 0.30
        ax.add_patch(Rectangle((x, 0.48), 0.22, 0.20, facecolor="white", edgecolor=COLORS["line"], linewidth=0.9))
        shown = f"{value:.1f}" if isinstance(value, float) and value % 1 else f"{int(value)}"
        ax.text(x + 0.11, 0.60, shown, ha="center", va="center", fontsize=13, fontweight="bold", color=COLORS["blue"])
        ax.text(x + 0.11, 0.52, label, ha="center", va="center", fontsize=7.2, color=COLORS["text"])
    status = str(c.get("_status", c.get("status", "recorded")))
    box(ax, 0.16, 0.20, 0.68, 0.13, "Policy interpretation", f"status={status}; sample sizes remain policy-controlled", fc=COLORS["panel"])
    fig.text(0.055, 0.045, "Source: _workspace/checkpoints/capacity_probe.json and policy.json. No secrets displayed.", fontsize=7.2, color=COLORS["muted"])
    save_asset(
        fig,
        "fig_capacity_gate",
        caption="Current capacity-gating summary from the local capacity-probe artifact.",
        evidence=["_workspace/checkpoints/capacity_probe.json", "_workspace/checkpoints/policy.json"],
        usage="Reproducibility/limitations figure.",
        caution="Operational status figure, not experimental performance.",
    )


def figure_kg_ontology() -> None:
    fig, ax = plt.subplots(figsize=(7.1, 3.7), facecolor="white")
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    add_title(fig, "Political KG ontology", "Election backbone plus time-stamped discourse layer.")

    left = ["Election", "Contest", "District", "Party", "Candidate"]
    right = ["PolicyIssue", "NarrativeFrame", "MediaEvent", "ScandalEvent", "Investigation", "Verdict", "PressConference", "PollPublication"]
    for i, name in enumerate(left):
        box(ax, 0.07, 0.66 - i * 0.105, 0.20, 0.065, name, fc="white", ec=COLORS["line"])
    for i, name in enumerate(right):
        x = 0.62 if i < 4 else 0.79
        y = 0.66 - (i % 4) * 0.105
        box(ax, x, y, 0.145, 0.065, name, fc=COLORS["panel"], ec=COLORS["line"])
    bridge = [
        ("candidateIn", (0.27, 0.34), (0.62, 0.53)),
        ("belongsTo", (0.27, 0.235), (0.62, 0.235)),
        ("about", (0.62, 0.64), (0.27, 0.55)),
        ("framedBy", (0.70, 0.61), (0.79, 0.61)),
        ("publishesPoll", (0.79, 0.35), (0.27, 0.45)),
    ]
    for label, s, e in bridge:
        arrow(ax, s, e, color=COLORS["blue"], lw=0.8, rad=0.05)
        ax.text((s[0] + e[0]) / 2, (s[1] + e[1]) / 2 + 0.025, label, fontsize=6.8, color=COLORS["muted"], ha="center")
    box(ax, 0.36, 0.11, 0.27, 0.10, "Firewall", "filters event nodes by ts <= cutoff(t)", fc=COLORS["blue_light"], ec=COLORS["blue"])
    fig.text(0.055, 0.035, "Source: src/kg/ontology.py and src/kg/export_d3.py.", fontsize=7.2, color=COLORS["muted"])
    save_asset(
        fig,
        "fig_kg_ontology_schematic",
        caption="Schematic of PolitiKAST's election and discourse KG ontology.",
        evidence=["src/kg/ontology.py", "src/kg/export_d3.py"],
        usage="KG methods figure and GraphRAG presentation slide.",
        caution="Schematic structure only; it does not imply a specific graph instance.",
    )


def figure_temporal_firewall() -> None:
    fig, ax = plt.subplots(figsize=(6.8, 2.8), facecolor="white")
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    add_title(fig, "Temporal information firewall", "Retrieval is clipped at the simulated wall-clock cutoff.")

    y = 0.47
    ax.plot([0.08, 0.92], [y, y], color=COLORS["ink"], linewidth=1.1)
    ticks = [(0.16, "t-2"), (0.32, "t-1"), (0.50, "t"), (0.68, "t+1"), (0.86, "result")]
    for x, label in ticks:
        ax.plot([x, x], [y - 0.035, y + 0.035], color=COLORS["ink"], linewidth=0.8)
        ax.text(x, y - 0.10, label, ha="center", fontsize=7.5, color=COLORS["text"])
    ax.add_patch(Rectangle((0.08, 0.56), 0.42, 0.15, facecolor=COLORS["green_light"], edgecolor=COLORS["green"], linewidth=0.8))
    ax.add_patch(Rectangle((0.50, 0.56), 0.42, 0.15, facecolor=COLORS["red_light"], edgecolor=COLORS["red"], linewidth=0.8))
    ax.text(0.29, 0.635, "retrievable context\nD <= t", ha="center", va="center", fontsize=8.2, color=COLORS["green"], fontweight="bold")
    ax.text(0.71, 0.635, "blocked future context\nD > t", ha="center", va="center", fontsize=8.2, color=COLORS["red"], fontweight="bold")
    box(ax, 0.26, 0.16, 0.48, 0.13, "Prompt contract", "agent receives only KG/document slices at or before cutoff(t)", fc=COLORS["panel"])
    save_asset(
        fig,
        "fig_temporal_firewall",
        caption="Temporal information firewall used to prevent future information from entering voter-agent prompts.",
        evidence=["paper/elex-kg-final.tex", "src/kg/firewall.py", "src/kg/export_d3.py"],
        usage="Leakage-mitigation figure.",
        caution="Conceptual mechanism diagram; no empirical quantities are encoded.",
    )


def write_manifest() -> None:
    lines = [
        "# PolitiKAST Paper Asset Manifest",
        "",
        "Generated assets live in `paper/assets/` and are designed for LaTeX insertion and presentation reuse.",
        "Numeric figures use only local JSON artifacts. Schematic figures are explicitly marked as schematics.",
        "",
        "## External Sources Checked",
        "",
    ]
    for src in EXTERNAL_SOURCES.values():
        lines.append(f"- **{src['title']}**: {src['url']}")
        lines.append(f"  Evidence use: {src['notes']}")
    lines.extend(["", "## Assets", ""])
    for rec in records:
        lines.extend(
            [
                f"### `{rec.name}`",
                "",
                f"- Files: {', '.join(f'`{f}`' for f in rec.files)}",
                f"- Caption: {rec.caption}",
                f"- Usage: {rec.usage}",
                f"- Caution: {rec.caution}",
                "- Evidence:",
            ]
        )
        for ev in rec.evidence:
            lines.append(f"  - {ev}" if ev.startswith("http") else f"  - `{ev}`")
        lines.append("")
    (ASSET_DIR / "ASSET_MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    font_names = []
    for candidate in ("Helvetica Neue", "Arial", "DejaVu Sans"):
        try:
            font_manager.findfont(candidate, fallback_to_default=False)
            font_names.append(candidate)
        except ValueError:
            continue
    if not font_names:
        font_names = ["DejaVu Sans"]
    plt.rcParams.update(
        {
            "font.family": font_names,
            "font.size": 8,
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )
    figure_pipeline()
    figure_persona_card()
    figure_target_regions()
    figure_result_summary()
    figure_capacity_status()
    figure_kg_ontology()
    figure_temporal_firewall()
    write_manifest()
    print(f"generated {len(records)} assets in {ASSET_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
