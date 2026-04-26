You are running as an unattended periodic consistency checker for the PolitiKAST repository.

This is user-approved documentation and harness maintenance. A Jira ticket is not required unless you modify production application code. Do not modify production application code in this periodic check.

Goal:
- Every run, compare the current paper draft at `paper/elex-kg-final.tex` with the current Claude Code harness under `.claude/`, runtime contracts under `_workspace/contracts/`, research notes under `_workspace/research/`, and any implementation artifacts under `src/`, `ui/`, `docker/`, and `docs/`.
- If the harness or experiment implementation contradicts the paper, update the paper to reflect the current implementation truth.
- If harness metadata points to the old root-level `elex-kg-final.tex`, update that harness metadata to `paper/elex-kg-final.tex`.
- Do not invent empirical results. Only add factual implementation details, placeholders, limitations, or reproducibility notes backed by repo files.
- Do not modify unrelated user files.

Priority order:
1. Experiment-result updates are the highest priority. First inspect `_workspace/snapshots/results/`, `_workspace/snapshots/results_index.json`, `_workspace/checkpoints/`, and relevant result-producing source files. If there are new factual experiment outputs, update the paper's methods/results/limitations/reproducibility sections from those files, then build PDFs.
2. If there are no new results, check for contradictions between the paper and harness/contracts/implementation. Correct only factual mismatches.
3. If there are no clear factual updates and the situation is ambiguous, use the remaining time for low-risk paper quality maintenance: refactoring, humanization, deduplication, clearer transitions, terminology consistency, and removal of repeated claims. Do not change scientific claims during this maintenance pass.
4. If `paper/elex-kg-final-ko.tex` exists, mirror factual updates into the Korean version. For quality-only maintenance, apply Korean-version edits only when they are straightforward and lower risk than leaving it stale.
5. Build PDFs after any paper edit. Prefer building both English and Korean sources when both exist.

Scope control:
- Do not bulk-read entire skill files or long generated logs.
- Prefer `rg`, `find`, `git diff --stat`, and targeted reads of contract JSON files and relevant paper sections.
- If no contradiction or result update is found, quality-only paper refactoring is allowed, but keep it small, reversible, and claim-preserving.
- Keep the run short and finish after one consistency pass.
- Do not spend time on polish if new experiment results are available.

Required checks:
- Paper source path is `paper/elex-kg-final.tex`; root `elex-kg-final.tex` should not be recreated.
- Compile with TinyTeX if available:
  `export PATH="$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"; cd paper; latexmk -pdf -interaction=nonstopmode -halt-on-error elex-kg-final.tex`
- If `paper/elex-kg-final-ko.tex` exists and was changed, also compile it with `latexmk -xelatex -interaction=nonstopmode -halt-on-error elex-kg-final-ko.tex`.
- Remove transient LaTeX files after compile: `.aux`, `.fdb_latexmk`, `.fls`, `.log`, `.out`, `.xdv`, `.synctex.gz`.
- Leave generated PDFs if compilation succeeds.

Expected final response:
- Concise Korean summary.
- State the selected mode: `results_update`, `consistency_fix`, `quality_maintenance`, or `no_change`.
- List any files changed.
- State whether English/Korean PDF compilation passed, skipped, or failed.
- Mention where the raw evidence came from, using local file paths only.
