"""Figure 2: task success on clean runs vs attack success (panel (a) of the
v3 figure; panel (b) is dropped).  Values are the Table 1 columns, computed
from data/runs.csv by paper_data.overall() and checked against Table 1.
Drawn at \\columnwidth (3.375in); no text below 7.5pt."""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as pdt
from data_figs import COLW, FS, OUT, save  # noqa: F401  (shared style)

STYLE = {"gpt-4o-mini": ("X", "#E91E63"), "deepseek-chat": ("D", "#1E88E5"), "gpt-5-mini": ("s", "#FB8C00"),
         "claude-haiku-4-5": ("v", "#43A047"), "claude-sonnet-4-5": ("^", "#00897B")}


def main():
    ov = pdt.overall()
    fig, ax = plt.subplots(figsize=(COLW, 2.25), layout="constrained")
    for m in pdt.MODELS:
        o = ov[m]
        x, y = 100 * o["task"], 100 * o["asr"]
        lo, hi = 100 * o["ci"][0], 100 * o["ci"][1]
        mk, col = STYLE[m]
        ax.errorbar(x, y, yerr=[[y - lo], [hi - y]], fmt="none", ecolor=col, elinewidth=1.0, capsize=2.5, alpha=0.8)
        ax.scatter(x, y, marker=mk, s=46, color=col, edgecolor="black", linewidth=0.6, zorder=3,
                   label=f"{pdt.LABEL[m]} (n={o['n']})")
    ax.set_xlim(86, 101.5)
    ax.set_ylim(-4, 82)
    ax.set_xlabel("Task success on clean runs (%)", fontsize=8)
    ax.set_ylabel("Attack success, no defense (%)", fontsize=8)
    ax.tick_params(labelsize=FS)
    ax.grid(alpha=0.25, lw=0.5)
    ax.legend(fontsize=FS, loc="upper right", frameon=True, framealpha=0.95, edgecolor="#cccccc",
              handletextpad=0.3, borderpad=0.4, labelspacing=0.35, scatterpoints=1)
    save(fig, "figU_utility_vs_asr")


if __name__ == "__main__":
    main()
    print("ok")
