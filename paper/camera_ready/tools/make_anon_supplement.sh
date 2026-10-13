#!/usr/bin/env bash
# Build the anonymized code + run-log supplement for double-blind review (TMLR).
# Copies the benchmark code, analysis scripts and released run logs, strips
# every author-identifying string, and fails if any survives.
# Usage (from paper/camera_ready/):  bash tools/make_anon_supplement.sh <out.zip>
set -euo pipefail
cd "$(dirname "$0")/../../.."          # repo root
OUT=$(realpath -m "${1:-paper/camera_ready/tmlr/tmlr_supplementary_anonymized.zip}")
STAGE=$(mktemp -d); trap 'rm -rf "$STAGE"' EXIT
S="$STAGE/supplementary"; mkdir -p "$S"

cp -r agent_bench scripts tests "$S"/
mkdir -p "$S/datasets" && cp datasets/*.py "$S/datasets/"
cp run_phase3.py run_phase3_focused.py requirements.txt "$S"/
# Figure code + per-run logs, laid out as in the repo so that the verifier
# (src/paper_data.py) checks every number against the anonymized paper source.
F="$S/paper/figures/killchain_figures"; mkdir -p "$F"
cp -r paper/figures/killchain_figures/{build_all.py,requirements.txt,src,data,fonts} "$F/"
python3 - paper/camera_ready/tmlr/main.tex "$S/paper/main.tex" <<'PY2'
import re, sys
from pathlib import Path
t = Path(sys.argv[1]).read_text()
# author block and camera-ready links are hidden in the PDF but present in the source
t, n = re.subn(r"\\author\{.*?University of Chicago\}", r"\\author{Anonymous authors}", t, flags=re.S)
assert n == 1, "author block not found"
t = t.replace("https://github.com/KevinChunye/prompt_injection", "https://github.com/ANONYMIZED")
Path(sys.argv[2]).write_text(t)
PY2
find "$S" -name '__pycache__' -prune -exec rm -rf {} + ; find "$S" -name '*.pyc' -delete

# README without the arXiv / Hugging Face links (they name the authors)
sed -e '/arxiv\.org\|huggingface\.co/d' README.md > "$S/README.md"
cat >> "$S/README.md" <<'TXT'

## Supplementary material for anonymous review

- `agent_bench/`, `scripts/`, `datasets/`, `run_phase3*.py`: the benchmark harness and
  analysis code used for every run in the paper.
- `paper/main.tex`: the LaTeX source of the submitted (anonymized) paper.
- `paper/figures/killchain_figures/`: code that draws every figure and recomputes every
  count quoted in the paper from the per-run log. `data/runs.csv` is the per-run log of
  the text-surface runs (rows with `in_paper == True` are the runs in the paper);
  `data/pdf_relay_cells.csv` holds the per-cell PDF relay counts.
- `cd paper/figures/killchain_figures && pip install -r requirements.txt && python src/paper_data.py`
  checks every table cell and quoted count against `paper/main.tex`;
  `python build_all.py` also redraws the figures (needs Cairo for `cairosvg`).

Links to the public repository and dataset were removed for double-blind review; they
will be restored in the camera-ready version.
TXT

# Scrub identifying strings in the copied figure code
for f in "$F/src/paper_data.py"; do
  sed -i -e 's#Hugging Face dataset kevinwhc/kill-chain-canaries#the released per-run dataset (link withheld for review)#' \
         -e 's#kevinwhc/kill-chain-canaries#[anonymized dataset]#g' \
         -e 's#arXiv 2603\.28013v3#the preprint version of this paper#g' "$f"
done

# Fail if anything identifying survives
if grep -rniE "kevin|haochuan|zechen|wang ?h|mit\.edu|uchicago|kevinwhc|KevinChunye|2603\.28013|wanghaochuan" "$S"; then
  echo "identifying strings remain" >&2; exit 1
fi

rm -f "$OUT"; mkdir -p "$(dirname "$OUT")"
(cd "$STAGE" && zip -q -X -r "$OUT" supplementary)
echo "== $OUT: $(unzip -l "$OUT" | tail -1 | awk '{print $2}') files, $(du -h "$OUT" | cut -f1)"
