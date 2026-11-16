#!/usr/bin/env bash
# Build main.pdf (AAAI-27 LAUT workshop submission). Usage: bash build.sh
set -euo pipefail
cd "$(dirname "$0")"
pdflatex -interaction=nonstopmode main >/dev/null
bibtex main >/dev/null
pdflatex -interaction=nonstopmode main >/dev/null
pdflatex -interaction=nonstopmode main | grep -E "^!|Warning|Overfull|Output written" || true
