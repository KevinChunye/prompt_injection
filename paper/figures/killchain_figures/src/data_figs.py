"""K3, K4, K5: the data figures.  Every plotted count comes from paper_data,
which reads data/runs.csv and data/pdf_relay_cells.csv and checks each cell
against Tables 2, 3, 5 and 6 of main.tex.

Figures are drawn at their final printed width (7.0in = \\textwidth for K3/K4,
3.375in = \\columnwidth for K5) and saved without cropping, so 1pt in the
figure is 1pt on paper.  No text is smaller than 7.5pt.
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_data as pdt

OUT = Path(__file__).resolve().parent.parent / "output"
OUT.mkdir(exist_ok=True)
TEXTW, COLW = 7.0, 3.375
FS = 7.5          # smallest font used anywhere

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.spines.top": False,
                     "axes.spines.right": False, "pdf.fonttype": 42, "svg.fonttype": "none",
                     "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6})
GREEN, AMBER, RED = "#43A047", "#FFB300", "#E53935"
MONO = {"family": "DejaVu Sans Mono"}
CMAP = plt.get_cmap("Reds")


def save(fig, name):
    for ext, kw in (("pdf", {}), ("svg", {}), ("png", {"dpi": 300})):
        fig.savefig(OUT / f"{name}.{ext}", **kw)
    plt.close(fig)


# ---------------------------------------------------------------- K3: last stage reached
def fig_k3():
    rs = pdt.relay_stages()
    pc = pdt.pdf_cells()
    same = pc[pc.pairing == "same_model"].set_index(["writer", "variant"])
    panels = [("Text relay", "propagation", None), ("PDF relay, visible text", "pdf_append", "pdf_append"),
              ("PDF relay, white text", "pdf_whitefont", "pdf_whitefont")]
    fig, axes = plt.subplots(1, 3, figsize=(TEXTW, 2.3), sharey=True, layout="constrained")
    fig.get_layout_engine().set(w_pad=0.02, wspace=0.06)
    y = np.arange(len(pdt.MODELS))[::-1]
    for ax, (title, code, variant) in zip(axes, panels):
        for yi, m in zip(y, pdt.MODELS):
            if variant is None:
                r = rs[m]
                segs, n = (r["last_absent"], r["last_relayed"], r["last_executed"]), r["n"]
                exposed = r["exposed"]
            else:
                d = same.loc[(m, variant)]
                n, exposed = int(d["n"]), int(d["exposed"])
                assert d["persisted"] == d["relayed"], "persisted-but-not-relayed needs its own category"
                segs = (int(d["exposed"] - d["relayed"]), int(d["relayed"] - d["executed"]), int(d["executed"]))
            if exposed == 0:
                ax.barh(yi, 1, color="#F2F2F2", edgecolor="#AAAAAA", hatch="////", height=0.66, lw=0.5)
                ax.text(0.5, yi, "no parse_pdf call", ha="center", va="center", fontsize=FS, color="#444")
                ax.text(1.03, yi, f"n={n}", va="center", fontsize=FS, color="#444")
                continue
            assert sum(segs) == n, (m, code, segs, n)
            left = 0.0
            for k, color in zip(segs, (GREEN, AMBER, RED)):
                ax.barh(yi, k / n, left=left, color=color, edgecolor="white", height=0.66, lw=0.6)
                left += k / n
            ax.text(1.03, yi, f"n={n}", va="center", fontsize=FS, color="#444")
        ax.set_xlim(0, 1)
        ax.set_xticks([0, 0.5, 1]); ax.set_xticklabels(["0%", "50%", "100%"], fontsize=FS)
        ax.set_title(title, fontsize=8.5, fontweight="bold", loc="left", pad=11)
        ax.text(0, 1.015, code, transform=ax.transAxes, fontsize=FS, color="#444", va="bottom", **MONO)
        ax.tick_params(axis="y", length=0)
    axes[0].set_yticks(y); axes[0].set_yticklabels([pdt.LABEL[m] for m in pdt.MODELS], fontsize=8)
    axes[1].set_xlabel("Share of attacked runs, by the last stage the canary token reached", fontsize=8)
    handles = [Patch(color=GREEN, label="Exposed only (no token in the memory write)"),
               Patch(color=AMBER, label="Relayed, not Executed"),
               Patch(color=RED, label="Executed")]
    fig.legend(handles=handles, loc="outside lower center", ncol=3, frameon=False, fontsize=8,
               handlelength=1.4, columnspacing=1.6)
    save(fig, "figK3_where_it_stopped")


# ---------------------------------------------------------------- K4: model x channel ASR
def fig_k4():
    tc = pdt.text_cells()
    pc = pdt.pdf_cells()
    same = pc[pc.pairing == "same_model"].set_index(["writer", "variant"])
    cols = pdt.TEXT_SCENARIOS + ["pdf_append", "pdf_whitefont"]
    fig, ax = plt.subplots(figsize=(TEXTW, 2.75), layout="constrained")
    nm = len(pdt.MODELS)
    for i, m in enumerate(pdt.MODELS):
        for j, c in enumerate(cols):
            x, yv = j, nm - 1 - i
            if c in pdt.TEXT_SCENARIOS:
                k, n = tc[(c, m)]
                exposed = True
            else:
                d = same.loc[(m, c)]
                k, n, exposed = int(d["executed"]), int(d["n"]), int(d["exposed"]) > 0
            if not exposed:
                ax.add_patch(Rectangle((x, yv), 1, 1, facecolor="#EEEEEE", edgecolor="white", lw=2, hatch="////"))
                ax.text(x + 0.5, yv + 0.5, f"no parse_pdf\ncall (n={n})", ha="center", va="center",
                        fontsize=FS, color="#444", linespacing=1.3)
                continue
            p = k / n
            lo, hi = pdt.wilson(k, n)
            ax.add_patch(Rectangle((x, yv), 1, 1, facecolor=CMAP(0.03 + 0.85 * p), edgecolor="white", lw=2))
            tc_ = "white" if p > 0.55 else "#222"
            ax.text(x + 0.5, yv + 0.63, f"{k}/{n}", ha="center", va="center", fontsize=9, fontweight="bold", color=tc_)
            ax.text(x + 0.5, yv + 0.28, f"[{pdt.pct(lo)}–{pdt.pct(hi)}%]", ha="center", va="center",
                    fontsize=FS, color=tc_)
    ax.axvline(4, color="#333", lw=1.0, ls=(0, (4, 3)))
    ds = nm - 1 - pdt.MODELS.index("deepseek-chat")
    ax.add_patch(Rectangle((0.04, ds + 0.04), 1.92, 0.92, fill=False, edgecolor="#1E88E5", lw=1.8))
    ax.set_xlim(0, len(cols)); ax.set_ylim(0, nm + 0.42)
    ax.set_xticks(np.arange(len(cols)) + 0.5)
    ax.set_xticklabels(cols, fontsize=FS, **MONO)
    ax.set_yticks(np.arange(nm) + 0.5); ax.set_yticklabels([pdt.LABEL[m] for m in pdt.MODELS][::-1], fontsize=8)
    ax.tick_params(length=0)
    for s in ["left", "bottom"]:
        ax.spines[s].set_visible(False)
    ax.text(2, nm + 0.2, "Text surfaces (n = 8–36 per cell)", ha="center", va="center",
            fontsize=8, color="#333", fontweight="bold")
    ax.text(5, nm + 0.2, "PDF relay (n = 3 per cell)", ha="center", va="center",
            fontsize=8, color="#333", fontweight="bold")
    save(fig, "figK4_surface_heatmap")


# ---------------------------------------------------------------- K5: writer x reader
def fig_k5():
    pc = pdt.pdf_cells()
    pa = pc[pc.variant == "pdf_append"].set_index(["writer", "reader"])
    wr = ["gpt-4o-mini", "deepseek-chat", "claude-haiku-4-5"]
    short = {"gpt-4o-mini": "GPT-4o-mini", "deepseek-chat": "DeepSeek\nChat", "claude-haiku-4-5": "Claude\nHaiku 4.5"}
    fig, ax = plt.subplots(figsize=(COLW, 2.55), layout="constrained")
    for i, w in enumerate(wr):
        for j, r in enumerate(wr):
            x, yv = j, len(wr) - 1 - i
            if (w, r) not in pa.index:
                ax.add_patch(Rectangle((x, yv), 1, 1, facecolor="#F3F3F3", edgecolor="white", lw=2, hatch="////"))
                ax.text(x + 0.5, yv + 0.5, "not tested", ha="center", va="center", fontsize=FS, color="#555")
                continue
            d = pa.loc[(w, r)]
            k, n, pk = int(d["executed"]), int(d["n"]), int(d["persisted"])
            p = k / n
            ax.add_patch(Rectangle((x, yv), 1, 1, facecolor=CMAP(0.08 + 0.8 * p), edgecolor="white", lw=2))
            tc_ = "white" if p > 0.55 else "#222"
            ax.text(x + 0.5, yv + 0.64, f"Executed {k}/{n}", ha="center", va="center", fontsize=FS,
                    fontweight="bold", color=tc_)
            ax.text(x + 0.5, yv + 0.32, f"Persisted {pk}/{n}", ha="center", va="center", fontsize=FS, color=tc_)
    ax.set_xlim(0, 3); ax.set_ylim(0, 3)
    ax.set_xticks(np.arange(3) + 0.5); ax.set_xticklabels([short[m] for m in wr], fontsize=FS)
    ax.set_yticks(np.arange(3) + 0.5); ax.set_yticklabels([short[m] for m in wr][::-1], fontsize=FS)
    ax.set_xlabel("Agent B (reads memory, acts)", fontsize=8)
    ax.set_ylabel("Agent A (reads PDF, writes memory)", fontsize=8)
    ax.tick_params(length=0)
    for s in ["left", "bottom"]:
        ax.spines[s].set_visible(False)
    save(fig, "figK5_relay_matrix")


if __name__ == "__main__":
    report, bad = pdt.verify()
    (OUT / "verification.txt").write_text(report + "\n")
    print(report.splitlines()[-1], "(full report: output/verification.txt)")
    fig_k3()
    fig_k4()
    fig_k5()
    print("ok")
