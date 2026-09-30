#!/usr/bin/env bash
# Build dist/arxiv_submission.zip and check it the way arXiv does.
#
# arXiv scans the source for the files it uses *without expanding macros*, and
# files the scan does not find referenced are left out of the compile.  So:
#   1. every \includegraphics / \input / \include argument must be a literal
#      path (no backslash macros), and each must be in the zip;
#   2. every file in the zip must be referenced (or be main.tex, the .sty or
#      00README.json);
#   3. the unpacked zip must compile on its own with pdflatex, with no
#      warnings and no overfull boxes.
# Usage (from paper/):  bash tools/make_arxiv_zip.sh
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=dist/arxiv_submission.zip
STAGE=$(mktemp -d)
TEST=$(mktemp -d)
trap 'rm -rf "$STAGE" "$TEST"' EXIT

python3 - "$STAGE" <<'PY'
import re, shutil, sys
from pathlib import Path
stage = Path(sys.argv[1])
tex = Path("main.tex").read_text()
body = re.sub(r"(?<!\\)%.*", "", tex)                       # ignore comments
refs = re.findall(r"\\(?:includegraphics|input|include)\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}", body)
bad = [r for r in refs if "\\" in r or "#" in r]
if bad:
    sys.exit(f"non-literal file paths (arXiv's scan cannot resolve these): {bad}")
files = ["main.tex", "icml2025.sty", "00README.json"] + sorted(set(refs))
for f in files:
    src = Path(f)
    if not src.exists() and src.suffix == "" and Path(f + ".tex").exists():
        src = Path(f + ".tex")
    if not src.exists():
        sys.exit(f"referenced file not found: {f}")
    dst = stage / src
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
print("scan: %d literal file references, all present" % len(set(refs)))
PY

mkdir -p dist
rm -f "$OUT"
(cd "$STAGE" && zip -q -X -D -r "$OLDPWD/$OUT" .)

# arXiv-style scan of the zip itself: referenced <-> present, nothing unused
unzip -q "$OUT" -d "$TEST"
python3 - "$TEST" <<'PY'
import re, sys
from pathlib import Path
root = Path(sys.argv[1])
body = re.sub(r"(?<!\\)%.*", "", (root / "main.tex").read_text())
refs = set(re.findall(r"\\(?:includegraphics|input|include)\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}", body))
present = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
missing = sorted(r for r in refs if r not in present)
unused = sorted(present - refs - {"main.tex", "icml2025.sty", "00README.json"})
print(f"zip scan: {len(present)} files; missing {missing or 'none'}; unreferenced {unused or 'none'}")
sys.exit(1 if missing or unused else 0)
PY

(cd "$TEST" && for i in 1 2 3; do pdflatex -interaction=nonstopmode -halt-on-error main.tex > /dev/null; done)
warn=$(grep -c "Warning" "$TEST/main.log" || true)
over=$(grep -c "Overfull" "$TEST/main.log" || true)
pages=$(pdfinfo "$TEST/main.pdf" | awk '/^Pages/ {print $2}')
echo "== $OUT"
unzip -l "$OUT"
echo "== clean-room compile: $pages pages, $warn warnings, $over overfull boxes"
test "$warn" = 0 && test "$over" = 0
