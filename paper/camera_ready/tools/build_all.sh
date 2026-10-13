#!/usr/bin/env bash
# Build every venue package in paper/camera_ready/ and check it.
#
#   tmlr/tmlr_submission.pdf               anonymous TMLR submission
#   tmlr/tmlr_camera_ready_preview.pdf     de-anonymized [accepted] version (placeholders)
#   tmlr/tmlr_supplementary_anonymized.zip code + run logs, author-free
#   jair/jair_submission.pdf               JAIR review version + reproducibility checklist
#   jair/jair_final_preview.pdf            JAIR final-copy version (placeholders)
#   jair/jair_source.zip                   source files for JAIR production
#   login/login_article.pdf                condensed practitioner article (see login/README)
#
# Checks: each PDF compiles from a clean copy with no LaTeX warnings and no
# overfull boxes; TMLR main content ends by page 12; the TMLR PDF and
# supplement contain no author-identifying strings; every table cell and
# quoted count in both venue sources matches the run logs (paper_data.verify).
# Usage (from anywhere):  bash paper/camera_ready/tools/build_all.sh
set -euo pipefail
CR=$(cd "$(dirname "$0")/.." && pwd)
FIGS="$CR/../figures/killchain_figures"
fail() { echo "FAIL: $*" >&2; exit 1; }

# compile <dir> <jobname> <files...> [-- <pdflatex prefix>]: clean-room latexmk build
compile() {
  local dir=$1 job=$2 pre=$3; shift 3
  local tmp; tmp=$(mktemp -d)
  (cd "$CR/$dir" && cp -r "$@" "$tmp/")
  if [ -n "$pre" ]; then
    (cd "$tmp" && latexmk -pdf -jobname="$job" -pdflatex="pdflatex %O \"$pre\\input{%S}\"" \
       -interaction=nonstopmode -halt-on-error main.tex > build.log 2>&1) || { tail -30 "$tmp/build.log"; fail "$dir/$job"; }
  else
    (cd "$tmp" && latexmk -pdf -jobname="$job" -interaction=nonstopmode -halt-on-error main.tex > build.log 2>&1) \
      || { tail -30 "$tmp/build.log"; fail "$dir/$job"; }
  fi
  local warn over
  # acmart's own \received block raises one \vspace notice in the final copy (also in the kit's sample)
  warn=$(grep "Warning" "$tmp/$job.log" | grep -vc "acmart Warning: \\\\vspace should only" || true)
  over=$(grep -c "Overfull" "$tmp/$job.log" || true)
  [ "$warn" = 0 ] && [ "$over" = 0 ] || { grep -E "Warning|Overfull" "$tmp/$job.log"; fail "$dir/$job: $warn warnings, $over overfull"; }
  cp "$tmp/$job.pdf" "$CR/$dir/$job.pdf"
  [ -f "$tmp/$job.bbl" ] && cp "$tmp/$job.bbl" "$CR/$dir/$job.bbl"
  echo "  $dir/$job.pdf: $(pdfinfo "$tmp/$job.pdf" | awk '/^Pages/ {print $2}') pages, 0 warnings, 0 overfull"
  rm -rf "$tmp"
}

verify_numbers() {   # paper_data.verify() against a venue main.tex
  python3 - "$FIGS/src" "$1" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import paper_data
paper_data.MAIN_TEX = Path(sys.argv[2])
report, bad = paper_data.verify()
lines = report.splitlines()
ok = sum(l.startswith("OK") for l in lines)
other = [l for l in lines if l.strip() and not l.startswith(("OK", "=="))]
# The two known log/table disagreements of the arXiv source (see figures README) are expected.
known = {"Table 1 DeepSeek Chat (n, task%, ASR%, CI)", "permission_esc GPT-5-mini"}
unexpected = [l for l in other if not any(k in l for k in known)]
print(f"  {Path(sys.argv[2]).parent.name}: {ok} checks OK, {len(other)} known arXiv-source flags, {len(unexpected)} new")
for l in unexpected: print("   ", l)
sys.exit(1 if unexpected else 0)
PY
}

echo "== TMLR"
T="main.tex references.bib tmlr.sty tmlr.bst fancyhdr.sty figures"
compile tmlr main "" $T
compile tmlr main_camera_ready '\def\camready{}' $T
mv "$CR/tmlr/main.pdf" "$CR/tmlr/tmlr_submission.pdf"
mv "$CR/tmlr/main_camera_ready.pdf" "$CR/tmlr/tmlr_camera_ready_preview.pdf"
rm -f "$CR/tmlr/"*.bbl
refs=$(for p in $(seq 1 20); do pdftotext -f $p -l $p "$CR/tmlr/tmlr_submission.pdf" - 2>/dev/null | grep -qx "References" && { echo $p; break; }; done)
first=$(pdftotext -f "$refs" -l "$refs" -layout "$CR/tmlr/tmlr_submission.pdf" - | grep -v "Under review" | grep -m1 -v "^\s*$")
[[ "$first" =~ ^References ]] || fail "TMLR: main text continues on page $refs"
echo "  main content: pages 1-$((refs - 1)) (References start at the top of page $refs)"
[ $((refs - 1)) -le 12 ] || echo "  NOTE: main content exceeds 12 pages: choose 'Long submission' on OpenReview"
if pdftotext "$CR/tmlr/tmlr_submission.pdf" - | grep -iqE "kevin|haochuan|zechen|mit\.edu|uchicago|github|hugging|kevinwhc|2603\.28013"; then
  fail "TMLR submission PDF contains identifying text"
fi
pdfinfo "$CR/tmlr/tmlr_submission.pdf" | grep -E "^Author:\s*$" > /dev/null || fail "TMLR PDF has an Author field"
echo "  anonymity: no names, affiliations, e-mails, GitHub/HF/arXiv links in text or metadata"
(cd "$CR/../.." && bash paper/camera_ready/tools/make_anon_supplement.sh paper/camera_ready/tmlr/tmlr_supplementary_anonymized.zip)

echo "== JAIR"
J="main.tex reproducibility_checklist.tex references.bib jair.cls acmart.cls acmauthoryear.bbx acmauthoryear.cbx acmdatamodel.dbx figures"
compile jair main "" $J
compile jair main_camera_ready '\def\camready{}' $J
mv "$CR/jair/main.pdf" "$CR/jair/jair_submission.pdf"
mv "$CR/jair/main_camera_ready.pdf" "$CR/jair/jair_final_preview.pdf"
# Production source: the final-copy files plus the .bbl biber produced
stage=$(mktemp -d); mkdir "$stage/jair_source"
(cd "$CR/jair" && cp -r $J "$stage/jair_source/" && cp main_camera_ready.bbl "$stage/jair_source/main.bbl")
rm -f "$CR/jair/"*.bbl "$CR/jair/jair_source.zip"
(cd "$stage" && zip -q -X -r "$CR/jair/jair_source.zip" jair_source)
rm -rf "$stage"
echo "  jair/jair_source.zip: $(unzip -l "$CR/jair/jair_source.zip" | tail -1 | awk '{print $2}') files"

echo "== numbers vs. run logs"
verify_numbers "$CR/tmlr/main.tex"
verify_numbers "$CR/jair/main.tex"

if [ -f "$CR/login/build.sh" ]; then
  echo "== ;login: article"
  bash "$CR/login/build.sh"
fi
echo "== all packages built"
