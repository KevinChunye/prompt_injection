"""
analyze_replication_v1.py
Generates summary stats and plots for the two replication experiments:
  - perm_esc_replication_v1  (gpt-4o-mini + deepseek-chat, permission_esc, n=24 each)
  - deepseek_mempoison_v1    (deepseek-chat, memory_poison, n=24)

Saves plots into:
  runs/perm_esc_replication_v1/plots/
  runs/deepseek_mempoison_v1/plots/
"""
import json
import os
import sys
from pathlib import Path
from collections import defaultdict

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

MODEL_SHORT = {
    "gpt-4o-mini":     "GPT-4o-mini",
    "gpt-5-mini":      "GPT-5-mini",
    "claude-haiku-4-5":"Claude Haiku",
    "claude-sonnet-4-5":"Claude Sonnet",
    "deepseek-chat":   "DeepSeek Chat",
}
PALETTE = {
    "GPT-4o-mini":   "#4C72B0",
    "DeepSeek Chat": "#DD8452",
    "Claude Haiku":  "#55A868",
    "Claude Sonnet": "#C44E52",
    "GPT-5-mini":    "#8172B2",
}


def load(path: str) -> pd.DataFrame:
    rows = [json.loads(l) for l in open(path)]
    df = pd.DataFrame(rows)
    df["model_short"] = df["model_a"].map(lambda m: MODEL_SHORT.get(m, m))
    return df


def print_summary(df: pd.DataFrame, label: str):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Total runs: {len(df)}")
    for m, grp in df.groupby("model_a"):
        atk = grp[grp["is_attacked"] == True]
        cln = grp[grp["is_attacked"] == False]
        ur  = cln["utility_success"].mean() * 100 if len(cln) else float("nan")
        asr = atk["harmful_action"].mean()  * 100 if len(atk) else float("nan")
        exp = atk["is_compromised"].mean()  * 100 if len(atk) else float("nan")
        ms  = MODEL_SHORT.get(m, m)
        print(f"  {ms:22}  UR={ur:5.1f}%  ASR={asr:5.1f}%  "
              f"Exposed={exp:5.1f}%  n_atk={len(atk)}")


def plot_asr_utility(df: pd.DataFrame, out_dir: Path, label: str):
    models = df["model_short"].unique()
    asr_vals, ur_vals, colors = [], [], []
    for ms in models:
        grp = df[df["model_short"] == ms]
        atk = grp[grp["is_attacked"] == True]
        cln = grp[grp["is_attacked"] == False]
        asr_vals.append(atk["harmful_action"].mean() * 100 if len(atk) else 0)
        ur_vals.append(cln["utility_success"].mean() * 100 if len(cln) else 0)
        colors.append(PALETTE.get(ms, "#999"))

    x = range(len(models))
    fig, ax = plt.subplots(figsize=(7, 4))
    w = 0.35
    ax.bar([i - w/2 for i in x], ur_vals,  width=w, label="Utility (clean)", alpha=0.8,
           color=[c for c in colors])
    ax.bar([i + w/2 for i in x], asr_vals, width=w, label="ASR (attacked)", alpha=0.8,
           color=[c for c in colors], hatch="//")
    ax.set_xticks(list(x))
    ax.set_xticklabels(models, rotation=15, ha="right")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_ylim(0, 115)
    ax.set_ylabel("Rate (%)")
    ax.set_title(f"ASR and Utility — {label}")
    ax.legend()
    ax.axhline(100, ls="--", lw=0.8, color="#ccc")
    fig.tight_layout()
    p = out_dir / "01_asr_utility.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    print(f"  [saved] {p.name}")


def plot_label_decomp(df: pd.DataFrame, out_dir: Path, label: str):
    attacked = df[df["is_attacked"] == True].copy()
    if len(attacked) == 0:
        return
    models = attacked["model_short"].unique()
    comp_rates, harm_rates = [], []
    for ms in models:
        grp = attacked[attacked["model_short"] == ms]
        comp_rates.append(grp["is_compromised"].mean() * 100)
        harm_rates.append(grp["harmful_action"].mean()  * 100)

    x = range(len(models))
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(x, comp_rates, label="Exposed (canary in context)",
           color="#9FC5E8", alpha=0.9)
    ax.bar(x, harm_rates, label="Executed (harmful action)",
           color="#E06666", alpha=0.9)
    ax.set_xticks(list(x))
    ax.set_xticklabels(models, rotation=15, ha="right")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_ylim(0, 115)
    ax.set_ylabel("Fraction of attacked runs (%)")
    ax.set_title(f"Kill-Chain: Exposure vs. Execution — {label}")
    ax.legend()
    fig.tight_layout()
    p = out_dir / "02_label_decomp.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    print(f"  [saved] {p.name}")


def plot_tool_calls(df: pd.DataFrame, out_dir: Path, label: str):
    if "n_tool_calls_a" not in df.columns:
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    for ms, grp in df.groupby("model_short"):
        clean   = grp[grp["is_attacked"] == False]["n_tool_calls_a"].values
        attacked= grp[grp["is_attacked"] == True ]["n_tool_calls_a"].values
        color = PALETTE.get(ms, "#999")
        ax.scatter([ms]*len(clean),    clean,    marker="o", alpha=0.5, color=color, label=f"{ms} clean")
        ax.scatter([ms]*len(attacked), attacked, marker="x", alpha=0.8, color=color, s=80)
    ax.set_ylabel("Tool calls (agent A)")
    ax.set_title(f"Tool Call Count — {label}\n(o=clean, x=attacked)")
    ax.tick_params(axis="x", rotation=15)
    fig.tight_layout()
    p = out_dir / "03_tool_calls.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    print(f"  [saved] {p.name}")


def run_experiment(results_path: str, label: str):
    df = load(results_path)
    out_dir = Path(results_path).parent / "plots"
    out_dir.mkdir(exist_ok=True)

    print_summary(df, label)
    print(f"\n  Generating plots → {out_dir}/")
    plot_asr_utility(df, out_dir, label)
    plot_label_decomp(df, out_dir, label)
    plot_tool_calls(df, out_dir, label)
    print(f"  Done. 3 plots saved.\n")


if __name__ == "__main__":
    run_experiment(
        "runs/perm_esc_replication_v1/results.jsonl",
        "perm_esc_replication_v1 (n=48)"
    )
    run_experiment(
        "runs/deepseek_mempoison_v1/results.jsonl",
        "deepseek_mempoison_v1 (n=24)"
    )
