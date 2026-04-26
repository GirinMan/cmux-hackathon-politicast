#!/usr/bin/env bash
set -u

ROOT="/Users/girinman/repos/cmux-hackathon-politicast"
PAPER_DIR="$ROOT/paper"
export PATH="$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"

cd "$PAPER_DIR" || exit 1

build_one() {
  tex="$1"
  [ -f "$tex" ] || return 0
  latexmk -pdf -interaction=nonstopmode -halt-on-error "$tex"
}

build_one_xelatex() {
  tex="$1"
  [ -f "$tex" ] || return 0
  latexmk -xelatex -interaction=nonstopmode -halt-on-error "$tex"
}

status=0
build_one "elex-kg-final.tex" || status=$?
if [ "$status" -eq 0 ]; then
  build_one_xelatex "elex-kg-final-ko.tex" || status=$?
fi

find "$PAPER_DIR" -maxdepth 1 \( \
  -name '*.aux' -o \
  -name '*.fdb_latexmk' -o \
  -name '*.fls' -o \
  -name '*.log' -o \
  -name '*.out' -o \
  -name '*.xdv' -o \
  -name '*.synctex.gz' \
\) -delete

exit "$status"
