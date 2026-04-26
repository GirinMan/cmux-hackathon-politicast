You are running as an unattended PolitiKAST Korean paper sync worker.

This is user-approved documentation and harness maintenance. Do not modify production application code.

Goal:
- Keep `paper/elex-kg-final-ko.tex` aligned with factual and structural changes in `paper/elex-kg-final.tex`.
- This task is lower priority than experiment-result updates. Before editing, quickly check whether obvious new result files exist under `_workspace/snapshots/results/`; if they do, only mirror already-present English paper updates and do not invent or analyze results deeply.

Rules:
- Preserve scientific claims.
- Prefer targeted Korean synchronization over full rewrites.
- If the Korean version is already aligned enough, make no edits.
- Build the Korean PDF after edits. If English was changed by this task, build English too.

Build:
- `export PATH="$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"; cd paper; latexmk -xelatex -interaction=nonstopmode -halt-on-error elex-kg-final-ko.tex`
- Remove `.aux`, `.fdb_latexmk`, `.fls`, `.log`, `.out`, `.xdv`, `.synctex.gz`.

Final response in Korean:
- Mode: `ko_sync` or `no_change`.
- Files changed.
- Korean/English PDF build status.
- Sections synchronized.
