"""Rebuild every Kill-Chain Canaries figure into output/ (PDF, PNG, SVG).

data_figs.py first writes output/verification.txt: every plotted cell checked
against the tables and captions of ../../main.tex.
"""
import runpy
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
for script in ["figK1.py", "figK2.py", "data_figs.py", "fig_drift.py"]:
    print(f"building {script} ...")
    runpy.run_path(str(SRC / script), run_name="__main__")
print("done: see output/")
