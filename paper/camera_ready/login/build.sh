#!/usr/bin/env bash
# Build the condensed practitioner article (Markdown -> PDF and DOCX) with pandoc.
# Figures are the paper's PNG renders (all >= 1400 px wide, as ;login: asked).
set -euo pipefail
cd "$(dirname "$0")"
SRC=../../figures/killchain_figures/output
mkdir -p figures
cp "$SRC/figK1_same_score_different_story.png" figures/fig1_same_score_different_story.png
cp "$SRC/figK2_setup_channels_defenses.png"    figures/fig2_setup_channels_defenses.png
cp "$SRC/figK3_where_it_stopped.png"           figures/fig3_where_it_stopped.png
cp "$SRC/figK4_surface_heatmap.png"            figures/fig4_surface_heatmap.png
python3 - <<'PY'
from PIL import Image; import glob
for f in sorted(glob.glob("figures/*.png")):
    w, h = Image.open(f).size
    assert w >= 1400, f"{f} is {w}px wide (< 1400)"
PY
pandoc article.md -o login_article.pdf --pdf-engine=pdflatex \
  -V geometry:margin=1in -V fontsize=11pt -V colorlinks=true -V linkcolor=blue -V urlcolor=blue \
  -V papersize=letter --highlight-style=tango \
  -V 'header-includes=\usepackage{float}\floatplacement{figure}{H}' 2> pandoc.log || { cat pandoc.log; exit 1; }
pandoc article.md -o login_article.docx
rm -f pandoc.log
words=$(python3 - <<'PY'
import re
t = open("article.md").read().split("---", 2)[2].split("## References")[0]
print(len(re.sub(r"```.*?```|!\[.*?\]\(.*?\)", "", t, flags=re.S).split()))
PY
)
echo "  login/login_article.pdf: $(pdfinfo login_article.pdf | awk '/^Pages/ {print $2}') pages; login_article.docx; ${words} words of body text"
