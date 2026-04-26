You are running as an unattended PolitiKAST paper quality-maintenance worker.

This is user-approved documentation and harness maintenance. Do not modify production application code.

Priority:
1. First check for new experiment result files under `_workspace/snapshots/results/` and `_workspace/snapshots/results_index.json`.
2. If new results appear to need paper integration, do not do polish; leave the result work to the results updater and report `blocked_by_results`.
3. If there are no result updates or factual contradictions, perform a small claim-preserving quality pass on `paper/elex-kg-final.tex`: refactoring, humanization, deduplication, clearer transitions, terminology consistency, and removal of repeated claims.
4. Apply Korean-version maintenance only when the corresponding edit is straightforward and low risk.

Rules:
- Do not change scientific claims, metrics, or implementation status.
- Keep edits small and reviewable.
- Prefer one or two coherent sections rather than many scattered rewrites.
- Build PDFs after edits.

Build:
- `export PATH="$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"; cd paper; latexmk -pdf -interaction=nonstopmode -halt-on-error elex-kg-final.tex`
- If Korean source changed, build it with `latexmk -xelatex -interaction=nonstopmode -halt-on-error elex-kg-final-ko.tex`.
- Remove `.aux`, `.fdb_latexmk`, `.fls`, `.log`, `.out`, `.xdv`, `.synctex.gz`.

Final response in Korean:
- Mode: `quality_maintenance`, `blocked_by_results`, or `no_change`.
- Files changed.
- English/Korean PDF build status.
- Short description of claim-preserving edits.
