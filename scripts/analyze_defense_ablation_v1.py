"""
scripts/analyze_defense_ablation_v1.py
Paper-ready analysis for runs/defense_ablation_v1/.

Shows how each defense mechanism affects ASR and utility for vulnerable models.

Usage:
    python3 scripts/analyze_defense_ablation_v1.py
    python3 scripts/analyze_defense_ablation_v1.py --results-dir runs/defense_ablation_v1
"""

import argparse
import json
import glob
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────────

MODEL_ORDER    = ["gpt-4o-mini", "deepseek-chat"]
MODEL_SHORT    = {"gpt-4o-mini": "GPT-4o-mini", "deepseek-chat": "DeepSeek Chat"}
MODEL_COLORS   = {"gpt-4o-mini": "#e74c3c", "deepseek-chat": "#f39c12"}

DEFENSE_ORDER  = ["none", "write_filter", "pi_detector", "spotlighting", "all"]
DEFENSE_LABELS = {
    "none":         "No Defense",
    "write_filter": "Write Filter",
    "pi_detector":  "PI Detector",
    "spotlighting": "Spotlighting",
    "all":          "All Combined",
}
DEFENSE_COLORS = {
    "none":         "#e74c3c",
    "write_filter": "#e67e22",
    "pi_detector":  "#3498db",
    "spotlighting": "#9b59b6",
    "all":          "#27ae60",
}

SCENARIO_ORDER = ["propagation", "tool_poison"]
SCENARIO_SHORT = {"propagation": "Propagation", "tool_poison": "Tool-Poison"}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "figure.dpi": 150,
})

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_data(results_dir: str) -> pd.DataFrame:
    rd = Path(results_dir)
    res = pd.read_json(rd / "results.jsonl", lines=True)
    feat_path = rd / "features.jsonl"
    if feat_path.exists():
        feat = pd.read_json(feat_path, lines=True)
        drop = [c for c in feat.columns if c in res.columns and c != "run_id"]
        feat = feat.drop(columns=drop, errors="ignore")
        return res.merge(feat, on="run_id", how="left")
    return res

def pct(n, d): return 100.0 * n / d if d else 0.0

def savefig(fig, path: Path, label: str):
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  [saved] {path.name}")

# ── Plot 01: ASR reduction by defense (main result) ──────────────────────────

def plot_asr_reduction(df: pd.DataFrame, out: Path):
    """
    For each model: grouped bars showing ASR under each defense condition.
    The key figure: does any defense bring ASR to 0 without hurting utility?
    """
    attacked = df[df["is_attacked"] == True]
    defenses = [d for d in DEFENSE_ORDER if d in attacked["defense"].unique()]
    models   = [m for m in MODEL_ORDER if m in attacked["model_a"].unique()]

    fig, axes = plt.subplots(1, len(models), figsize=(7*len(models), 5), sharey=True)
    if len(models) == 1:
        axes = [axes]

    for ax, m in zip(axes, models):
        sub = attacked[attacked["model_a"] == m]
        x   = np.arange(len(defenses))
        asrs = [pct(sub[sub["defense"]==d]["harmful_action"].sum(),
                    len(sub[sub["defense"]==d])) for d in defenses]
        colors = [DEFENSE_COLORS.get(d, "#999") for d in defenses]
        bars = ax.bar(x, asrs, color=colors, edgecolor="white", width=0.6)

        for bar, v in zip(bars, asrs):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1.5,
                    f"{v:.0f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels([DEFENSE_LABELS.get(d,d) for d in defenses],
                           rotation=20, ha="right", fontsize=10)
        ax.set_ylim(0, 115)
        ax.set_ylabel("ASR (%)" if ax is axes[0] else "")
        ax.set_title(f"{MODEL_SHORT.get(m,m)}")
        ax.axhline(0, color="gray", linewidth=0.5)

    fig.suptitle("Attack Success Rate by Defense Condition\n"
                 "(direct attack only; lower = better defense)", fontsize=13)
    savefig(fig, out / "01_asr_by_defense.png", "ASR by defense")

# ── Plot 02: Utility preservation ────────────────────────────────────────────

def plot_utility_preservation(df: pd.DataFrame, out: Path):
    """Shows utility on clean runs doesn't degrade with defenses."""
    clean  = df[df["attack_variant"] == "none"]
    defenses = [d for d in DEFENSE_ORDER if d in clean["defense"].unique()]
    models   = [m for m in MODEL_ORDER if m in clean["model_a"].unique()]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = np.arange(len(defenses))
    n = len(models)
    w = 0.6 / n

    for i, m in enumerate(models):
        utils = [pct(clean[(clean["model_a"]==m) & (clean["defense"]==d)]["utility_success"].sum(),
                     len(clean[(clean["model_a"]==m) & (clean["defense"]==d)])) for d in defenses]
        offset = (i - (n-1)/2) * w
        ax.bar(x + offset, utils, width=w,
               label=MODEL_SHORT.get(m,m),
               color=MODEL_COLORS.get(m,"#999"), alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels([DEFENSE_LABELS.get(d,d) for d in defenses], rotation=20, ha="right")
    ax.set_ylim(0, 115)
    ax.set_ylabel("Utility Rate (%)")
    ax.set_title("Utility Preservation Across Defenses\n(clean runs; should stay near 100%)")
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.legend()
    savefig(fig, out / "02_utility_by_defense.png", "Utility by defense")

# ── Plot 03: Defense × Scenario heatmap ──────────────────────────────────────

def plot_defense_scenario_heatmap(df: pd.DataFrame, out: Path):
    attacked = df[df["is_attacked"] == True]
    defenses  = [d for d in DEFENSE_ORDER if d in attacked["defense"].unique()]
    scenarios = [s for s in SCENARIO_ORDER if s in attacked["scenario"].unique()]
    models    = [m for m in MODEL_ORDER if m in attacked["model_a"].unique()]

    for m in models:
        sub = attacked[attacked["model_a"] == m]
        matrix = np.zeros((len(defenses), len(scenarios)))
        annot  = np.empty((len(defenses), len(scenarios)), dtype=object)
        for i, d in enumerate(defenses):
            for j, s in enumerate(scenarios):
                cell = sub[(sub["defense"]==d) & (sub["scenario"]==s)]
                v = pct(cell["harmful_action"].sum(), len(cell)) if len(cell) else np.nan
                matrix[i, j] = v if not np.isnan(v) else 0
                annot[i, j]  = f"{v:.0f}%" if not np.isnan(v) else "N/A"

        fig, ax = plt.subplots(figsize=(7, 5))
        im = ax.imshow(matrix, cmap="RdYlGn_r", vmin=0, vmax=100, aspect="auto")
        ax.set_xticks(range(len(scenarios)))
        ax.set_xticklabels([SCENARIO_SHORT.get(s,s) for s in scenarios], fontsize=12)
        ax.set_yticks(range(len(defenses)))
        ax.set_yticklabels([DEFENSE_LABELS.get(d,d) for d in defenses], fontsize=11)
        for i in range(len(defenses)):
            for j in range(len(scenarios)):
                ax.text(j, i, annot[i, j], ha="center", va="center",
                        fontsize=14, fontweight="bold",
                        color="white" if matrix[i,j] > 55 else "black")
        plt.colorbar(im, ax=ax, label="ASR (%)")
        slug = MODEL_SHORT.get(m,m).replace(" ","_")
        ax.set_title(f"Defense × Scenario ASR — {MODEL_SHORT.get(m,m)}\n"
                     "(green=defended, red=still vulnerable)")
        savefig(fig, out / f"03_defense_scenario_{slug}.png", f"Defense heatmap {m}")

# ── Plot 04: ASR + Utility trade-off scatter ──────────────────────────────────

def plot_tradeoff_scatter(df: pd.DataFrame, out: Path):
    """Each point = (model, defense). x=utility, y=1-ASR (safety). Want top-right."""
    attacked = df[df["is_attacked"] == True]
    clean    = df[df["attack_variant"] == "none"]
    defenses = [d for d in DEFENSE_ORDER if d in df["defense"].unique()]
    models   = [m for m in MODEL_ORDER if m in df["model_a"].unique()]

    fig, ax = plt.subplots(figsize=(7, 6))
    for m in models:
        xs, ys, labels = [], [], []
        for d in defenses:
            at = attacked[(attacked["model_a"]==m) & (attacked["defense"]==d)]
            cl = clean[(clean["model_a"]==m)   & (clean["defense"]==d)]
            if len(at) == 0 or len(cl) == 0:
                continue
            asr  = pct(at["harmful_action"].sum(), len(at))
            util = pct(cl["utility_success"].sum(), len(cl))
            xs.append(util)
            ys.append(100 - asr)
            labels.append(DEFENSE_LABELS.get(d,d))
        color = MODEL_COLORS.get(m, "#999")
        ax.scatter(xs, ys, c=color, s=120, zorder=3, label=MODEL_SHORT.get(m,m))
        for x, y, lbl in zip(xs, ys, labels):
            ax.annotate(lbl, (x, y), textcoords="offset points",
                        xytext=(5, 4), fontsize=8, color=color)
        if len(xs) > 1:
            ax.plot(xs, ys, "--", color=color, alpha=0.4, linewidth=1)

    ax.axvline(90, color="gray", linestyle=":", alpha=0.5)
    ax.axhline(90, color="gray", linestyle=":", alpha=0.5)
    ax.set_xlabel("Utility Rate (%) →  higher is better")
    ax.set_ylabel("Safety Rate (100% − ASR) →  higher is better")
    ax.set_xlim(0, 110); ax.set_ylim(0, 110)
    ax.set_title("Defense Trade-Off: Utility vs. Safety\n"
                 "Ideal defense = top-right corner (high utility, high safety)")
    ax.legend()
    savefig(fig, out / "04_tradeoff_scatter.png", "Trade-off scatter")

# ── Plot 05: Label decomposition per defense ──────────────────────────────────

def plot_label_by_defense(df: pd.DataFrame, out: Path):
    """For each defense: exposure rate vs execution rate. Shows where defenses block."""
    attacked = df[df["is_attacked"] == True]
    defenses = [d for d in DEFENSE_ORDER if d in attacked["defense"].unique()]
    models   = [m for m in MODEL_ORDER if m in attacked["model_a"].unique()]

    fig, axes = plt.subplots(1, len(models), figsize=(8*len(models), 4.5), sharey=True)
    if len(models) == 1:
        axes = [axes]

    for ax, m in zip(axes, models):
        sub  = attacked[attacked["model_a"] == m]
        x    = np.arange(len(defenses))
        w    = 0.3
        comp = [pct(sub[sub["defense"]==d]["is_compromised"].sum(),
                    len(sub[sub["defense"]==d])) for d in defenses]
        harm = [pct(sub[sub["defense"]==d]["harmful_action"].sum(),
                    len(sub[sub["defense"]==d])) for d in defenses]

        ax.bar(x - w/2, comp, width=w, color="#f39c12", alpha=0.85, label="Exposed")
        ax.bar(x + w/2, harm, width=w, color="#e74c3c", alpha=0.85, label="Executed")
        ax.set_xticks(x)
        ax.set_xticklabels([DEFENSE_LABELS.get(d,d) for d in defenses],
                           rotation=20, ha="right", fontsize=9)
        ax.set_ylim(0, 115)
        ax.set_title(f"{MODEL_SHORT.get(m,m)}")
        if ax is axes[0]:
            ax.set_ylabel("% of attacked runs")
            ax.legend()

    fig.suptitle("Defense Impact on Kill-Chain: Exposure vs. Execution\n"
                 "Write_filter should block exposure; PI detector may only block execution",
                 fontsize=12)
    savefig(fig, out / "05_label_by_defense.png", "Label by defense")

# ── Print stats ───────────────────────────────────────────────────────────────

def print_stats(df: pd.DataFrame):
    print("\n" + "="*70)
    print("DEFENSE_ABLATION_V1 — KEY FINDINGS")
    print("="*70)

    attacked = df[df["is_attacked"] == True]
    clean    = df[df["attack_variant"] == "none"]
    defenses = [d for d in DEFENSE_ORDER if d in df["defense"].unique()]
    models   = [m for m in MODEL_ORDER if m in df["model_a"].unique()]

    print(f"\n{'Model':<18} {'Defense':<16} {'n':>3} {'ASR%':>6} {'Util%':>6} {'Exp%':>6}")
    print("-"*58)
    for m in models:
        for d in defenses:
            at = attacked[(attacked["model_a"]==m) & (attacked["defense"]==d)]
            cl = clean[(clean["model_a"]==m)   & (clean["defense"]==d)]
            if len(at) == 0:
                continue
            asr  = pct(at["harmful_action"].sum(), len(at))
            util = pct(cl["utility_success"].sum(), len(cl)) if len(cl) else 0
            exp  = pct(at["is_compromised"].sum(), len(at))
            marker = " ✓" if asr == 0 and util >= 90 else (" ✗" if asr > 50 else "  ")
            print(f"  {MODEL_SHORT.get(m,m):<16} {DEFENSE_LABELS.get(d,d):<16} "
                  f"{len(at):>3} {asr:>5.0f}% {util:>5.0f}% {exp:>5.0f}%{marker}")
        print()

    # Most effective defense
    print("[RECOMMENDATION] Best defense = lowest ASR with ≥90% utility retained")
    for m in models:
        best = None
        for d in defenses:
            if d == "none":
                continue
            at = attacked[(attacked["model_a"]==m) & (attacked["defense"]==d)]
            cl = clean[(clean["model_a"]==m) & (clean["defense"]==d)]
            if len(at) == 0:
                continue
            asr  = pct(at["harmful_action"].sum(), len(at))
            util = pct(cl["utility_success"].sum(), len(cl)) if len(cl) else 0
            if best is None or asr < best[1]:
                best = (d, asr, util)
        if best:
            print(f"  {MODEL_SHORT.get(m,m)}: {DEFENSE_LABELS.get(best[0],best[0])} "
                  f"→ ASR={best[1]:.0f}%, Util={best[2]:.0f}%")
    print()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--results-dir", default="runs/defense_ablation_v1")
    args = p.parse_args()

    rd  = Path(args.results_dir)
    out = rd / "plots"
    out.mkdir(parents=True, exist_ok=True)

    print(f"Loading data from {rd} ...")
    df = load_data(str(rd))
    print(f"  {len(df)} runs. Scenarios: {sorted(df['scenario'].unique())}")
    print(f"  Defenses: {sorted(df['defense'].unique())}")
    print(f"  Models:   {sorted(df['model_a'].unique())}")

    print_stats(df)

    print(f"\nGenerating plots → {out}/")
    plot_asr_reduction(df, out)
    plot_utility_preservation(df, out)
    plot_defense_scenario_heatmap(df, out)
    plot_tradeoff_scatter(df, out)
    plot_label_by_defense(df, out)

    print(f"\nDone. {len(list(out.glob('*.png')))} plots saved to {out}/")

if __name__ == "__main__":
    main()
