# PolitiKAST Paper Asset Manifest

Generated assets live in `paper/assets/` and are designed for both LaTeX insertion and presentation reuse.
Numeric figures use only local JSON artifacts. Schematic figures are explicitly marked as schematics.

## External Sources Checked

- **NVIDIA/Hugging Face Nemotron-Personas-Korea**: https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea
  Evidence use: Used for dataset identity, license, persona-field framing, and source citation.
- **NVIDIA Nemotron datasets overview**: https://developer.nvidia.com/nemotron
  Evidence use: Used for high-level description of Nemotron persona datasets as synthetic, privacy-safe, demographically grounded personas.
- **CAMEL: Communicative Agents for 'Mind' Exploration of Large Language Model Society**: https://arxiv.org/abs/2303.17760
  Evidence use: Used for CAMEL multi-agent framework context.
- **ElectionSim: Massive Population Election Simulation Powered by Large Language Model Driven Agents**: https://arxiv.org/abs/2410.20746
  Evidence use: Used for related-work positioning only, not for PolitiKAST empirical values.

## Assets

### `fig_pipeline_architecture`

- Files: `paper/assets/fig_pipeline_architecture_ai.png` (current paper figure), plus deterministic backups `paper/assets/fig_pipeline_architecture.svg`, `paper/assets/fig_pipeline_architecture.pdf`, `paper/assets/fig_pipeline_architecture.png`
- Caption: PolitiKAST end-to-end pipeline: persona substrate, election/poll records, political KG, LLM voter agents, and output artifacts.
- Usage: Main paper methods overview or presentation architecture slide.
- Caution: AI-generated text-free schematic; not an empirical result figure. All exact labels and factual claims are carried by the LaTeX caption/body, not by in-image text.
- Evidence:
  - `_workspace/contracts/data_paths.json`
  - `_workspace/contracts/api_contract.json`
  - `_workspace/contracts/result_schema.json`
  - `src/kg/ontology.py`
  - `src/sim/election_env.py`

### `fig_persona_data_card`

- Files: `paper/assets/fig_persona_data_card_ai.png` (current paper figure, image-generated bitmap without in-image source/footer), plus deterministic backups `paper/assets/fig_persona_data_card.svg`, `paper/assets/fig_persona_data_card.pdf`, `paper/assets/fig_persona_data_card.png`
- Caption: Data card for the synthetic Korean electorate used by PolitiKAST.
- Usage: Intro/methods figure and presentation setup slide.
- Caution: AI-generated labeled bitmap. Dataset-level facts are cited externally; target-contest names are local harness contract values, not national voter counts.
- Evidence:
  - https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea
  - `_workspace/contracts/data_paths.json`
  - `paper/elex-kg-final.tex`

### `fig_target_region_coverage`

- Files: `paper/assets/fig_target_region_coverage_ai.png` (current paper figure, image-generated bitmap without in-image source/footer), plus deterministic backups `paper/assets/fig_target_region_coverage.svg`, `paper/assets/fig_target_region_coverage.pdf`, `paper/assets/fig_target_region_coverage.png`
- Caption: Synthetic adult-persona coverage for the five target contests in the current harness.
- Usage: Methods/data section; presentation slide explaining target-contest selection.
- Caution: AI-generated labeled bitmap checked against local values. Uses local synthetic-persona coverage only; not official electorate size or forecast output.
- Evidence:
  - `_workspace/contracts/data_paths.json`

### `fig_local_result_artifacts`

- Files: `paper/assets/fig_local_result_artifacts_ai.png` (retired from the submission paper), plus deterministic backups `paper/assets/fig_local_result_artifacts.svg`, `paper/assets/fig_local_result_artifacts.pdf`, `paper/assets/fig_local_result_artifacts.png`
- Caption: Retired vote-share diagnostic for currently available non-empty local result artifacts.
- Usage: Do not insert in the submission paper. Keep only as an archived engineering diagnostic unless superseded by a validation-run figure with recorded cache state, key rotation, and official-poll labels.
- Caution: v1.4 cache/key-rotation review invalidated the current vote-share fields for substantive interpretation. Do not present this asset as forecast evidence, validation evidence, or headline result evidence.
- Evidence:
  - `_workspace/snapshots/results_index.json`
  - `_workspace/snapshots/results/*.json`

### `fig_capacity_gate`

- Status: Excluded from submission-facing paper assets. Retained in place only for compatibility with older paper variants and local history; do not add this figure back to the submission paper.
- Files: `paper/assets/fig_capacity_gate_ai.png`, plus deterministic backups `paper/assets/fig_capacity_gate.svg`, `paper/assets/fig_capacity_gate.pdf`, `paper/assets/fig_capacity_gate.png`
- Caption: Current Gemini capacity gate from the local capacity-probe artifact.
- Usage: Optional presentation-only context if a deck needs to explain operational downscaling. Prefer regenerating from the latest policy/capacity artifacts before external use.
- Caution: AI-generated labeled bitmap checked against local capacity artifact. Operational status figure, not an experimental performance result.
- Handling recommendation: Do not delete or move during the paper freeze while non-submission TeX/snippet consumers may still reference `fig_capacity_gate.pdf`. Once those references are retired, move the full `fig_capacity_gate_*` family to a presentation/archive-only location or remove it from `paper/assets/`.
- Evidence:
  - `_workspace/checkpoints/capacity_probe.json`
  - `_workspace/checkpoints/policy.json`

### `fig_kg_ontology_schematic`

- Files: `paper/assets/fig_kg_ontology_schematic_ai.png` (current paper figure), plus deterministic backups `paper/assets/fig_kg_ontology_schematic.svg`, `paper/assets/fig_kg_ontology_schematic.pdf`, `paper/assets/fig_kg_ontology_schematic.png`
- Caption: Schematic of PolitiKAST's election and discourse KG ontology.
- Usage: Methods KG subsection; presentation slide for GraphRAG design.
- Caution: AI-generated text-free schematic; does not imply a particular graph instance or node count. Exact ontology classes remain in Table 1 and the caption/body text.
- Evidence:
  - `src/kg/ontology.py`
  - `src/kg/export_d3.py`

### `fig_temporal_firewall`

- Files: `paper/assets/fig_temporal_firewall_ai.png` (current paper figure), plus deterministic backups `paper/assets/fig_temporal_firewall.svg`, `paper/assets/fig_temporal_firewall.pdf`, `paper/assets/fig_temporal_firewall.png`
- Caption: Temporal information firewall used to prevent future information from entering voter-agent prompts.
- Usage: Methods or limitations figure; useful in presentations for leakage mitigation.
- Caution: AI-generated text-free conceptual diagram; no empirical quantities are encoded. The formal cutoff definition remains in the LaTeX equations.
- Evidence:
  - `paper/elex-kg-final.tex`
  - `src/kg/firewall.py`
  - `src/kg/export_d3.py`
