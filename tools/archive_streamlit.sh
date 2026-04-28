#!/usr/bin/env bash
# Archive the legacy Streamlit dashboard + companion scripts.
#
# `ui/dashboard/`            → `_archive/streamlit-2026-04-26/dashboard/`
# `scripts/v8*_post_finalize.py` → `_archive/streamlit-2026-04-26/scripts/`
#
# Uses `git mv` when the file is git-tracked so history is preserved; otherwise
# falls back to `mv -v`. Idempotent — safe to run twice.
#
# Usage:
#   tools/archive_streamlit.sh                # interactive preview + apply
#   tools/archive_streamlit.sh --dry-run      # preview only
#   tools/archive_streamlit.sh --yes          # non-interactive apply
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

ARCHIVE_DATE="${ARCHIVE_DATE:-2026-04-26}"
DEST="_archive/streamlit-${ARCHIVE_DATE}"
DRY_RUN=0
ASSUME_YES=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --yes|-y)  ASSUME_YES=1 ;;
    -h|--help)
      sed -n '2,16p' "$0"
      exit 0
      ;;
    *) echo "unknown arg: $arg"; exit 2 ;;
  esac
done

mkdir -p "$DEST/scripts"

# Decide mover (git mv if path is tracked, else plain mv).
move() {
  local src="$1" dst="$2"
  if [ ! -e "$src" ]; then
    echo "  · skip (missing): $src"
    return 0
  fi
  if git ls-files --error-unmatch "$src" >/dev/null 2>&1; then
    if [ "$DRY_RUN" -eq 1 ]; then
      echo "  · git mv $src → $dst"
    else
      mkdir -p "$(dirname "$dst")"
      git mv "$src" "$dst"
    fi
  else
    if [ "$DRY_RUN" -eq 1 ]; then
      echo "  · mv $src → $dst"
    else
      mkdir -p "$(dirname "$dst")"
      mv -v "$src" "$dst"
    fi
  fi
}

echo "Archive plan (target=$DEST, dry-run=$DRY_RUN):"
echo "  ui/dashboard/                  → $DEST/dashboard/"
for s in scripts/v8_post_finalize.py scripts/v8b_post_finalize.py scripts/v8t_post_finalize.py; do
  echo "  $s → $DEST/scripts/$(basename "$s")"
done

if [ "$ASSUME_YES" -ne 1 ] && [ "$DRY_RUN" -ne 1 ]; then
  read -r -p "Proceed? [y/N] " ans
  case "$ans" in y|Y|yes|YES) ;; *) echo "aborted"; exit 1 ;; esac
fi

# Move dashboard if it exists.
if [ -d "ui/dashboard" ]; then
  move "ui/dashboard" "$DEST/dashboard"
fi

# Move v8* finalize scripts (Streamlit 의존).
for s in scripts/v8_post_finalize.py scripts/v8b_post_finalize.py scripts/v8t_post_finalize.py; do
  if [ -e "$s" ]; then
    move "$s" "$DEST/scripts/$(basename "$s")"
  fi
done

cat > "$DEST/README.md" <<EOF
# Streamlit dashboard archive — ${ARCHIVE_DATE}

Frozen Streamlit + post-finalize scripts from the 12-hour hackathon snapshot.
Replaced by the Vite + React SPA under \`frontend/\` (Phase 4 cutover).

Why kept:
- Reproducibility for the paper figures generated from \`scripts/v8*_post_finalize.py\`.
- Reference for KG / Validation Gate page layouts that the new SPA mirrors.

Restoring (development only):
\`\`\`
pip install streamlit altair
streamlit run _archive/streamlit-${ARCHIVE_DATE}/dashboard/app.py
\`\`\`
EOF

echo "done. New SPA → frontend/  (npm run dev)"
