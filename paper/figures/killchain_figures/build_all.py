"""Rebuild every Kill-Chain Canaries figure into output/ (PDF, PNG, SVG), then
copy the PDFs that ../../main.tex includes into ../ (paper/figures/).

main.tex includes figures by literal path (figures/<name>.pdf, no macros), so
that arXiv's file scan, which does not expand macros, finds every figure.

data_figs.py first writes output/verification.txt: every plotted cell checked
against the tables and captions of ../../main.tex.
"""
import re
import runpy
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
PAPER = HERE.parent.parent
for script in ["figK1.py", "figK2.py", "data_figs.py", "fig_drift.py"]:
    print(f"building {script} ...")
    runpy.run_path(str(SRC / script), run_name="__main__")

used = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{figures/([^}/]+\.pdf)\}", (PAPER / "main.tex").read_text())
for name in sorted(set(used)):
    shutil.copy2(HERE / "output" / name, PAPER / "figures" / name)
    print(f"exported figures/{name}")
print("done: see output/ and ../")
