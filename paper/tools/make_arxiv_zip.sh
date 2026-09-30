#!/usr/bin/env bash
# Build dist/arxiv_submission.zip: only the files main.tex needs, then prove it
# compiles on its own by unpacking into an empty directory and running pdflatex.
# Usage (from paper/):  bash tools/make_arxiv_zip.sh
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=dist/arxiv_submission.zip
STAGE=$(mktemp -d)
TEST=$(mktemp -d)
trap 'rm -rf "$STAGE" "$TEST"' EXIT

cp main.tex icml2025.sty 00README.json "$STAGE"/
# every figure main.tex includes through \KF{...}
grep -o '\\KF{[^}]*}' main.tex | sed 's/\\KF{\(.*\)}/\1/' | sort -u | while read -r f; do
  src="figures/killchain_figures/output/$f"
  test -f "$src" || { echo "missing figure: $src" >&2; exit 1; }
  mkdir -p "$STAGE/figures/killchain_figures/output"
  cp "$src" "$STAGE/figures/killchain_figures/output/"
done

mkdir -p dist
rm -f "$OUT"
(cd "$STAGE" && zip -q -X -r "$OLDPWD/$OUT" .)

# clean-room compile
unzip -q "$OUT" -d "$TEST"
(cd "$TEST" && for i in 1 2 3; do pdflatex -interaction=nonstopmode -halt-on-error main.tex > /dev/null; done)
warn=$(grep -c "Warning" "$TEST/main.log" || true)
over=$(grep -c "Overfull" "$TEST/main.log" || true)
pages=$(pdfinfo "$TEST/main.pdf" | awk '/^Pages/ {print $2}')
echo "== $OUT"
unzip -l "$OUT"
echo "== clean-room compile: $pages pages, $warn warnings, $over overfull boxes"
test "$warn" = 0 && test "$over" = 0
