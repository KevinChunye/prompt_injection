"""Appendix figure: objective drift (merges v3 Figures 5, 6 and 7).

(a) per-step drift for GPT-4o-mini on memory_poison: the values of Table 4,
    read from main.tex (tab:drift_steps).
(b) gradient-boosted-tree feature importances: the values printed on the v3
    figure (scripts/generate_figures.py, fig8b_feature_importance).
(c) drift distributions: the per-run drift values are not in the released
    logs, so the violins are taken from the v3 raster
    (data/v3_fig8_drift_distributions.png).  Only the plot area is reused; ticks,
    labels and legend are redrawn as vector text.  The v3 legend called the
    grey violins "Clean (no injection)", but the script that drew them
    (scripts/generate_figures.py, fig8a_drift_distributions) splits attacked
    runs by harmful action: grey = attacked runs without the harmful action,
    coloured = attacked runs with it.  The legend here says so.

Drawn at \\textwidth (7.0in); no text below 7.5pt.
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.legend_handler import HandlerTuple
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as pdt
from data_figs import FS, MONO, OUT, TEXTW, save

RASTER = pdt.DATA / "v3_fig8_drift_distributions.png"

FEATURES = [("drift_mean_after_exposure", 0.323), ("drift_max", 0.119), ("tool_repeat_rate", 0.082),
            ("tool_entropy", 0.074), ("tool_switch_rate", 0.054), ("memory_access_rate", 0.042),
            ("subtask_order_deviation", 0.038), ("first_memory_read_fraction", 0.031),
            ("tool_call_count", 0.029), ("memory_dependency_ratio", 0.025),
            ("ew30_memory_access_rate", 0.022), ("ew30_canary_exposed", 0.021),
            ("unique_tool_count", 0.018), ("ew30_tool_entropy", 0.016)]


def drift_steps():
    rows = pdt.table_rows("tab:drift_steps")
    out = []
    for r in rows:
        step, tool = int(r[0]), r[1]
        clean = None if set(r[2].strip()) <= set("-\u2014") else float(r[2])
        out.append((step, tool, clean, float(r[3])))
    return out


def top_row():
    fig, (a, b) = plt.subplots(1, 2, figsize=(TEXTW, 2.6), layout="constrained",
                               gridspec_kw={"width_ratios": [1, 1.25]})
    st = drift_steps()
    xs = [s[0] for s in st]
    a.plot([s[0] for s in st if s[2] is not None], [s[2] for s in st if s[2] is not None],
           "-o", color="#1565C0", lw=1.6, ms=5, label="Clean run")
    a.plot(xs, [s[3] for s in st], "-s", color="#C62828", lw=1.6, ms=5, label="Attacked run")
    a.axvspan(2.6, 3.4, color="#FFCDD2", alpha=0.5, lw=0)
    a.set_xticks(xs)
    a.set_xticklabels([f"step {s[0]}\n" + s[1].replace(" (", "\n(") for s in st], fontsize=FS)
    a.set_xlim(0.6, 3.4)
    a.set_ylim(0.5, 0.92)
    a.tick_params(labelsize=FS)
    a.set_ylabel("Drift (TF-IDF cosine distance\nfrom the task description)", fontsize=8)
    a.legend(fontsize=FS, frameon=False, loc="upper left")
    a.grid(alpha=0.25, lw=0.5)
    a.set_title("(a) Per-step drift, GPT-4o-mini, memory_poison", fontsize=8, loc="left", fontweight="bold")

    names = [f[0] for f in FEATURES][::-1]
    vals = [f[1] for f in FEATURES][::-1]
    colors = ["#e05252" if i < 2 else "#4a90d9" if i < 5 else "#aaaaaa" for i in range(len(FEATURES))][::-1]
    yy = np.arange(len(names))
    b.barh(yy, vals, color=colors, height=0.7, edgecolor="white")
    for y, v in zip(yy, vals):
        b.text(v + 0.004, y, f"{v:.3f}", va="center", fontsize=FS, color="#333")
    b.set_yticks(yy)
    b.set_yticklabels(names, fontsize=FS, **MONO)
    b.set_xlim(0, 0.38)
    b.tick_params(labelsize=FS, axis="x")
    b.tick_params(axis="y", length=0)
    b.set_xlabel("Importance (gradient-boosted trees, 5-fold CV)", fontsize=8)
    b.set_title("(b) Feature importance (GBT classifier)", fontsize=8, loc="left",
                fontweight="bold")
    save(fig, "figA_drift_top")


def violins():
    im = np.array(Image.open(RASTER).convert("RGB"))
    # Axes calibration of the v3 raster (tick marks found at these pixel edges):
    # y = (821 - row) / 620, x = (col - 335) / 385.5.  Crop to y in [0.40, 0.92]
    # (no violin extends outside it) and inside the spines.
    r0, r1, c0, c1 = 250, 573, 142, 1956
    crop = im[r0:r1, c0:c1].copy()
    # blank the v3 annotation "Decision threshold (0.75)" (redundant with the legend)
    crop[326 - r0:346 - r0, 1840 - c0:] = 255
    ext = [(c0 - 335) / 385.5, (c1 - 335) / 385.5, (821 - r1) / 620, (821 - r0) / 620]
    fig, ax = plt.subplots(figsize=(TEXTW, 2.3), layout="constrained")
    ax.imshow(crop, extent=ext, aspect="auto", interpolation="none")
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3])
    ax.set_xticks(range(5)); ax.set_xticklabels([pdt.LABEL[m] for m in pdt.MODELS], fontsize=8)
    ax.set_yticks([0.4, 0.5, 0.6, 0.7, 0.8, 0.9]); ax.tick_params(labelsize=FS)
    ax.set_ylabel("Mean drift after\nexposure", fontsize=8)
    ax.set_title("(c) Drift distributions over attacked runs, by outcome", fontsize=8, loc="left",
                 fontweight="bold")
    harm = tuple(Patch(facecolor=c, edgecolor="none") for c in ("#e67878", "#e6985d", "#72a8e1"))
    handles = [Patch(facecolor="#d7d7d7", edgecolor="none"), harm,
               Line2D([0], [0], color="black", ls="--", lw=0.8, alpha=0.5)]
    labels = ["No harmful action", "Harmful action (colour = model)", "Threshold 0.75"]
    fig.legend(handles, labels, handler_map={tuple: HandlerTuple(ndivide=None, pad=0)}, fontsize=FS,
               frameon=False, loc="outside lower center", ncol=3, handlelength=2.4, columnspacing=2.0)
    save(fig, "figA_drift_violins")


if __name__ == "__main__":
    top_row()
    violins()
    print("ok")
