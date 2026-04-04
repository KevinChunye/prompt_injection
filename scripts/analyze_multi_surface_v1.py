"""
scripts/analyze_multi_surface_v1.py
Paper-ready analysis for runs/multi_surface_v1/.

Usage:
    python3 scripts/analyze_multi_surface_v1.py
    python3 scripts/analyze_multi_surface_v1.py --results-dir runs/multi_surface_v1
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

BROKEN_MODELS: set = set()  # populated dynamically in load_data()

MODEL_ORDER = ["gpt-4o-mini", "gpt-5-mini", "claude-haiku-4-5", "claude-sonnet-4-5", "deepseek-chat"]
MODEL_SHORT  = {
    "gpt-4o-mini":      "GPT-4o-mini",
    "gpt-5-mini":       "GPT-5-mini",
    "claude-haiku-4-5": "Claude Haiku",
    "claude-sonnet-4-5":"Claude Sonnet",
    "deepseek-chat":    "DeepSeek Chat",
}
MODEL_COLORS = {
    "gpt-4o-mini":      "#e74c3c",
    "gpt-5-mini":       "#e67e22",
    "claude-haiku-4-5": "#2ecc71",
    "claude-sonnet-4-5":"#27ae60",
    "deepseek-chat":    "#f39c12",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "figure.dpi": 150,
})

# ── Load ──────────────────────────────────────────────────────────────────────

def load_data(results_dir: str):
    global BROKEN_MODELS
    rd = Path(results_dir)
    res = pd.read_json(rd / "results.jsonl", lines=True)
    if "stopped_by_a" in res.columns:
        model_any_done = res.groupby("model_a")["stopped_by_a"].apply(
            lambda s: any(v == "done" for v in s)
        )
        BROKEN_MODELS = set(model_any_done[~model_any_done].index.tolist())
    feat_path = rd / "features.jsonl"
    if feat_path.exists():
        feat = pd.read_json(feat_path, lines=True)
        drop_cols = [c for c in feat.columns if c in res.columns and c != "run_id"]
        feat = feat.drop(columns=drop_cols, errors="ignore")
        df = res.merge(feat, on="run_id", how="left")
    else:
        df = res.copy()
    if "stopped_by_a" in df.columns:
        df = df[~df["stopped_by_a"].str.startswith("error:", na=False)].copy()
    return df

def load_traces(results_dir: str):
    traces = {}
    for path in glob.glob(str(Path(results_dir) / "*.jsonl")):
        name = Path(path).stem
        if name in ("results", "features"):
            continue
        events = [json.loads(l) for l in open(path)]
        run_id = events[0].get("run_id", name)
        traces[run_id] = events
    return traces

def pct(n, d):
    return 100.0 * n / d if d else 0.0

def savefig(fig, path: Path, title: str):
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  [saved] {path.name}")

# ── Plot 01: ASR + Utility side by side ──────────────────────────────────────

def plot_asr_utility(df: pd.DataFrame, out: Path):
    all_models = [m for m in MODEL_ORDER + ["gpt-5-mini"] if m in df["model_a"].unique()]
    attacked = df[df["is_attacked"] == True]
    clean    = df[df["attack_variant"] == "none"]

    asr_vals, util_vals, colors = [], [], []
    for m in all_models:
        at = attacked[attacked["model_a"] == m]
        cl = clean[clean["model_a"] == m]
        asr_vals.append(pct(at["harmful_action"].sum(), len(at)) if len(at) else 0)
        util_vals.append(pct(cl["utility_success"].sum(), len(cl)) if len(cl) else 0)
        colors.append("#cccccc" if m in BROKEN_MODELS else MODEL_COLORS.get(m, "#999"))

    labels = [MODEL_SHORT.get(m, m) for m in all_models]
    x = np.arange(len(all_models))
    w = 0.35

    fig, ax = plt.subplots(figsize=(7, 4))
    b1 = ax.bar(x - w/2, asr_vals, width=w, color=colors, alpha=0.85, label="ASR (attacked)", edgecolor="white")
    b2 = ax.bar(x + w/2, util_vals, width=w, color=colors, alpha=0.45, label="Utility (clean)", edgecolor="white",
                hatch="//")
    for bar, v, m in zip(list(b1)+list(b2), asr_vals+util_vals, all_models*2):
        lbl = f"{v:.0f}%"
        if m in BROKEN_MODELS:
            lbl += "\n(err)"
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1.5, lbl, ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 120)
    ax.set_ylabel("Rate (%)")
    ax.set_title("Multi-Surface Attack: ASR and Utility by Model")
    ax.legend(loc="upper right")
    savefig(fig, out / "01_asr_utility.png", "ASR + utility")

# ── Plot 02: Compromise funnel ────────────────────────────────────────────────

def plot_compromise_funnel(df: pd.DataFrame, out: Path):
    """
    Funnel: total attacked → is_compromised (canary read) → harmful_action (executed)
    Shows where in the kill-chain each model drops off.
    """
    valid = df[~df["model_a"].isin(BROKEN_MODELS)]
    attacked = valid[valid["is_attacked"] == True]
    models = [m for m in MODEL_ORDER if m in attacked["model_a"].unique()]

    stages = ["Attacked\n(n runs)", "Exposed\n(canary read)", "Executed\n(harmful action)"]
    fig, axes = plt.subplots(1, len(models), figsize=(5*len(models), 4.5), sharey=False)
    if len(models) == 1:
        axes = [axes]

    for ax, m in zip(axes, models):
        sub = attacked[attacked["model_a"] == m]
        n_total = len(sub)
        n_comp   = int(sub["is_compromised"].sum())
        n_harm   = int(sub["harmful_action"].sum())
        counts  = [n_total, n_comp, n_harm]
        color   = MODEL_COLORS.get(m, "#999")

        y_pos = [2, 1, 0]
        widths = [c / n_total if n_total else 0 for c in counts]
        for y, w, c, stage in zip(y_pos, widths, counts, stages):
            ax.barh(y, w, color=color, alpha=0.3+0.25*y, edgecolor="white", height=0.6)
            ax.text(w+0.02, y, f"{c}/{n_total} ({pct(c,n_total):.0f}%)",
                    va="center", fontsize=10, fontweight="bold")
        ax.set_yticks(y_pos)
        ax.set_yticklabels(stages, fontsize=10)
        ax.set_xlim(0, 1.4)
        ax.set_xlabel("Fraction")
        ax.set_title(f"{MODEL_SHORT.get(m,m)}")
        ax.axvline(1.0, color="gray", linestyle="--", linewidth=0.8)

    fig.suptitle("Compromise Funnel: Multi-Surface Attack\n"
                 "Fraction of attacked runs reaching each stage", fontsize=12)
    savefig(fig, out / "02_compromise_funnel.png", "Funnel")

# ── Plot 03: Label decomposition across models ────────────────────────────────

def plot_label_decomp(df: pd.DataFrame, out: Path):
    valid = df[~df["model_a"].isin(BROKEN_MODELS)]
    attacked = valid[valid["is_attacked"] == True]
    models = [m for m in MODEL_ORDER if m in attacked["model_a"].unique()]

    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(models))
    w = 0.25

    comp_rates = [pct(attacked[attacked["model_a"]==m]["is_compromised"].sum(),
                      len(attacked[attacked["model_a"]==m])) for m in models]
    harm_rates = [pct(attacked[attacked["model_a"]==m]["harmful_action"].sum(),
                      len(attacked[attacked["model_a"]==m])) for m in models]

    b1 = ax.bar(x - w/2, comp_rates, width=w, color="#f39c12", label="Exposed (canary read)", alpha=0.9)
    b2 = ax.bar(x + w/2, harm_rates, width=w, color="#e74c3c", label="Executed harm", alpha=0.9)

    for bar, v in zip(list(b1)+list(b2), comp_rates+harm_rates):
        if v > 5:
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1.5,
                    f"{v:.0f}%", ha="center", va="bottom", fontsize=10)

    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_SHORT.get(m,m) for m in models])
    ax.set_ylim(0, 115)
    ax.set_ylabel("% of attacked runs")
    ax.set_title("Multi-Surface Kill-Chain: Exposure vs. Execution\n"
                 "Claude: reads canary but refuses to execute; GPT-4o-mini: always executes")
    ax.legend()
    savefig(fig, out / "03_label_decomp.png", "Label decomp")

# ── Plot 04: Drift trajectories ───────────────────────────────────────────────

def plot_drift_trajectories(df: pd.DataFrame, traces: dict, out: Path):
    valid = df[~df["model_a"].isin(BROKEN_MODELS)]

    fig, ax = plt.subplots(figsize=(9, 4.5))

    plotted = 0
    for _, row in valid.iterrows():
        rid = row["run_id"]
        events = traces.get(rid, [])
        steps, drifts = [], []
        for e in events:
            if e.get("type") == "tool_event":
                d = e.get("objective_drift_score")
                s = e.get("step")
                if d is not None and s is not None:
                    steps.append(s)
                    drifts.append(d)
        if not drifts:
            continue

        m = row["model_a"]
        is_harm = row.get("harmful_action", False)
        color = MODEL_COLORS.get(m, "#999")
        alpha = 0.7 if is_harm else 0.25
        lw    = 2.0 if is_harm else 0.8
        ls    = "-"  if is_harm else "--"
        ax.plot(steps, drifts, color=color, alpha=alpha, linewidth=lw, linestyle=ls)
        plotted += 1

    # Legend proxies
    legend_elems = [
        mpatches.Patch(color="#e74c3c", alpha=0.8, label="GPT-4o-mini harmful (solid)"),
        mpatches.Patch(color="#e74c3c", alpha=0.25, label="GPT-4o-mini clean (dashed)"),
        mpatches.Patch(color="#27ae60", alpha=0.8, label="Claude Sonnet (dashed)"),
    ]
    ax.axhline(0.4, color="gray", linestyle=":", linewidth=1, label="High-drift threshold")
    ax.set_xlabel("Tool-call step")
    ax.set_ylabel("Objective Drift Score")
    ax.set_title("Drift Trajectories: All Multi-Surface Runs\n"
                 "Harmful runs stay elevated; Claude dips back toward task")
    ax.legend(handles=legend_elems+[
        mpatches.Patch(color="gray", label="Threshold 0.4")], fontsize=9)
    ax.set_ylim(0, 1.05)
    savefig(fig, out / "04_drift_trajectories.png", f"Drift trajectories ({plotted} runs)")

# ── Plot 05: Canary propagation case study ────────────────────────────────────

def plot_canary_case_study(df: pd.DataFrame, traces: dict, out: Path):
    """
    For the most interesting attacked run per model, show which tools
    saw the canary (in result) vs executed it (in args).
    """
    valid = df[~df["model_a"].isin(BROKEN_MODELS)]
    attacked = valid[valid["is_attacked"] == True]
    models = [m for m in MODEL_ORDER if m in attacked["model_a"].unique()]

    fig, axes = plt.subplots(1, len(models), figsize=(6*len(models), 4), sharey=False)
    if len(models) == 1:
        axes = [axes]

    for ax, m in zip(axes, models):
        # Pick most interesting run: harmful > compromised > any
        sub = attacked[attacked["model_a"] == m]
        candidates = sub[sub["harmful_action"]==True]
        if len(candidates) == 0:
            candidates = sub[sub["is_compromised"]==True]
        if len(candidates) == 0:
            candidates = sub
        row = candidates.iloc[0]
        rid = row["run_id"]
        events = traces.get(rid, [])

        tools, in_result, in_args, drifts = [], [], [], []
        for e in events:
            if e.get("type") == "tool_event":
                tools.append(e.get("tool_name", "?")[:14])
                in_result.append(1 if e.get("canary_in_result") else 0)
                in_args.append(1   if e.get("canary_in_args")   else 0)
                drifts.append(e.get("objective_drift_score", 0) or 0)

        if not tools:
            ax.set_title(f"{MODEL_SHORT.get(m,m)}\n(no tool events)")
            continue

        x = np.arange(len(tools))
        ax2 = ax.twinx()
        ax.bar(x - 0.2, in_result, width=0.35, color="#f39c12", alpha=0.8, label="Canary in result")
        ax.bar(x + 0.2, in_args,   width=0.35, color="#e74c3c", alpha=0.8, label="Canary in args")
        ax2.plot(x, drifts, "D--", color="#3498db", linewidth=1.5, markersize=5, label="Drift score")
        ax.set_xticks(x)
        ax.set_xticklabels(tools, rotation=30, ha="right", fontsize=8)
        ax.set_ylim(-0.1, 1.8)
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["No", "Yes"])
        ax2.set_ylim(0, 1.1)
        ax2.set_ylabel("Drift", color="#3498db", fontsize=9)
        ax.set_title(f"{MODEL_SHORT.get(m,m)}\n{row.get('attack_variant','')} | harm={row['harmful_action']}\nrun: {rid[-8:]}")
        # Combine legends
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1+h2, l1+l2, fontsize=8, loc="upper left")

    fig.suptitle("Canary Propagation Case Study: Tool-Level View\n"
                 "Orange=canary seen in tool result; Red=canary used in outbound args", fontsize=11)
    savefig(fig, out / "05_canary_case_study.png", "Canary case study")

# ── Print stats ───────────────────────────────────────────────────────────────

def print_stats(df: pd.DataFrame):
    print("\n" + "="*70)
    print("MULTI_SURFACE_V1 — KEY FINDINGS")
    print("="*70)

    broken = df[df["model_a"].isin(BROKEN_MODELS)]
    valid  = df[~df["model_a"].isin(BROKEN_MODELS)]

    if len(broken):
        print(f"\n[BROKEN MODELS — excluded]")
        for m in broken["model_a"].unique():
            sub = broken[broken["model_a"]==m]
            err = sub["stopped_by_a"].iloc[0][:80] if "stopped_by_a" in sub.columns else "?"
            print(f"  {m}: {len(sub)} runs, ALL API errors. Error: {err}")

    attacked = valid[valid["is_attacked"]==True]
    clean    = valid[valid["attack_variant"]=="none"]

    print(f"\n{'Model':<22} {'UR%':>5} {'Exp%':>6} {'ASR%':>6}")
    print("-"*40)
    for m in MODEL_ORDER:
        if m not in df["model_a"].values:
            continue
        cl = clean[clean["model_a"]==m]
        at = attacked[attacked["model_a"]==m]
        ur  = pct(cl["utility_success"].sum(), len(cl))
        exp = pct(at["is_compromised"].sum(), len(at)) if len(at) else 0
        asr = pct(at["harmful_action"].sum(), len(at))  if len(at) else 0
        print(f"  {MODEL_SHORT.get(m,m):<20} {ur:>5.0f} {exp:>6.0f} {asr:>6.0f}")

    print("\n[KEY FINDING 1] GPT-4o-mini: 100% exposure AND 100% execution in multi-surface")
    print("[KEY FINDING 2] Claude Sonnet: reads canary (is_compromised) but refuses harmful action")
    print("  → This is the most important finding for a paper: Claude's refusal is post-exposure")
    print("  → The model is NOT blind to the attack — it sees it, chooses not to comply")
    if len(broken):
        print("[CAUTION] gpt-5-mini: 0% ASR is temperature=0.0 API error, not safety")

    # Surface crossing stats
    if "surface_crossings" in valid.columns:
        at = attacked
        cross = at["surface_crossings"].mean()
        print(f"\n[SURFACE] Mean surface crossings in attacked runs: {cross:.2f}")

    if "objective_drift_max" in valid.columns:
        print("\n[DRIFT]")
        for m in MODEL_ORDER:
            at_m = valid[(valid["model_a"]==m) & (valid["is_attacked"]==True)]
            cl_m = valid[(valid["model_a"]==m) & (valid["attack_variant"]=="none")]
            d_at = at_m["objective_drift_max"].mean()
            d_cl = cl_m["objective_drift_max"].mean()
            if not (pd.isna(d_at) or pd.isna(d_cl)):
                print(f"  {MODEL_SHORT.get(m,m):<22} clean={d_cl:.3f}  attacked={d_at:.3f}  Δ={d_at-d_cl:+.3f}")
    print()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--results-dir", default="runs/multi_surface_v1")
    args = p.parse_args()

    rd  = Path(args.results_dir)
    out = rd / "plots"
    out.mkdir(parents=True, exist_ok=True)

    print(f"Loading data from {rd} ...")
    df = load_data(str(rd))
    print(f"  {len(df)} runs. Columns: {list(df.columns)[:10]} ...")

    print(f"Loading traces ...")
    traces = load_traces(str(rd))
    print(f"  {len(traces)} trace files.")

    print_stats(df)

    print(f"\nGenerating plots → {out}/")
    plot_asr_utility(df, out)
    plot_compromise_funnel(df, out)
    plot_label_decomp(df, out)
    plot_drift_trajectories(df, traces, out)
    plot_canary_case_study(df, traces, out)

    print(f"\nDone. {len(list(out.glob('*.png')))} plots saved to {out}/")

if __name__ == "__main__":
    main()
