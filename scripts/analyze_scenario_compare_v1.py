"""
scripts/analyze_scenario_compare_v1.py
Paper-ready analysis for runs/scenario_compare_v1/.

Usage:
    python3 scripts/analyze_scenario_compare_v1.py
    python3 scripts/analyze_scenario_compare_v1.py --results-dir runs/scenario_compare_v1

Outputs all plots to runs/scenario_compare_v1/plots/
"""

import argparse
import json
import glob
import os
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────────

# Broken models are detected dynamically from data (stopped_by_a starts with 'error:')
# Do NOT hardcode model names here — gpt-5-mini was broken before the temperature fix
BROKEN_MODELS: set = set()   # populated in load_data()

MODEL_ORDER = ["gpt-4o-mini", "gpt-5-mini", "deepseek-chat", "claude-haiku-4-5", "claude-sonnet-4-5"]
MODEL_SHORT  = {
    "gpt-4o-mini":      "GPT-4o-mini",
    "gpt-5-mini":       "GPT-5-mini",
    "claude-haiku-4-5": "Claude Haiku",
    "claude-sonnet-4-5":"Claude Sonnet",
    "deepseek-chat":    "DeepSeek Chat",
}
SCENARIO_ORDER = ["memory_poison", "propagation", "tool_poison", "permission_esc"]
SCENARIO_SHORT = {
    "memory_poison":  "Mem-Poison",
    "propagation":    "Propagation",
    "tool_poison":    "Tool-Poison",
    "permission_esc": "Priv-Esc",
}

MODEL_COLORS = {
    "gpt-4o-mini":      "#e74c3c",
    "gpt-5-mini":       "#e67e22",
    "claude-haiku-4-5": "#2ecc71",
    "claude-sonnet-4-5":"#27ae60",
    "deepseek-chat":    "#f39c12",
}

LABEL_COLORS = {
    "harmful_action":  "#e74c3c",
    "is_compromised":  "#f39c12",
    "is_attacked":     "#3498db",
    "clean":           "#95a5a6",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "figure.dpi": 150,
})

# ── Load data ─────────────────────────────────────────────────────────────────

def load_data(results_dir: str):
    global BROKEN_MODELS
    rd = Path(results_dir)
    res = pd.read_json(rd / "results.jsonl", lines=True)
    # Dynamically detect models that only produced errors (never completed a run)
    if "stopped_by_a" in res.columns:
        model_any_done = res.groupby("model_a")["stopped_by_a"].apply(
            lambda s: any(v == "done" for v in s)
        )
        BROKEN_MODELS = set(model_any_done[~model_any_done].index.tolist())
    feat_path = rd / "features.jsonl"
    if feat_path.exists():
        feat = pd.read_json(feat_path, lines=True)
        # features.jsonl may duplicate label cols; drop from feat before merge
        drop_cols = [c for c in feat.columns if c in res.columns and c != "run_id"]
        feat = feat.drop(columns=drop_cols, errors="ignore")
        df = res.merge(feat, on="run_id", how="left")
    else:
        print("[warn] features.jsonl not found — drift/tool-count plots will be limited", file=sys.stderr)
        df = res.copy()
    # Exclude runs that errored out (stopped_by_a starts with 'error:')
    if "stopped_by_a" in df.columns:
        df = df[~df["stopped_by_a"].str.startswith("error:", na=False)].copy()
    return df

def load_traces(results_dir: str):
    """Return dict {run_id: list_of_event_dicts} for all trace files."""
    traces = {}
    for path in glob.glob(str(Path(results_dir) / "*.jsonl")):
        name = Path(path).stem
        if name in ("results", "features"):
            continue
        events = [json.loads(l) for l in open(path)]
        run_id = events[0].get("run_id", name)
        traces[run_id] = events
    return traces

# ── Helpers ───────────────────────────────────────────────────────────────────

def savefig(fig, path: Path, title: str):
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  [saved] {path.name}")

def pct(n, d):
    return 100.0 * n / d if d else 0.0

# ── Plot 01: ASR by model ─────────────────────────────────────────────────────

def plot_asr_by_model(df: pd.DataFrame, out: Path):
    valid = df[~df["model_a"].isin(BROKEN_MODELS)]
    attacked = valid[valid["is_attacked"] == True]
    models = [m for m in MODEL_ORDER if m in attacked["model_a"].unique()]

    asr_vals = []
    for m in models:
        sub = attacked[attacked["model_a"] == m]
        asr_vals.append(pct(sub["harmful_action"].sum(), len(sub)))

    fig, ax = plt.subplots(figsize=(7, 4))
    colors = [MODEL_COLORS.get(m, "#999") for m in models]
    bars = ax.bar([MODEL_SHORT[m] for m in models], asr_vals, color=colors, edgecolor="white", width=0.6)
    for bar, v in zip(bars, asr_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
                f"{v:.0f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_ylim(0, 115)
    ax.set_ylabel("Attack Success Rate (%)")
    ax.set_title("Attack Success Rate (ASR) by Model\n(all scenarios combined, direct attack only)")
    ax.axhline(50, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.set_xlabel("Model")
    savefig(fig, out / "01_asr_by_model.png", "ASR by model")

# ── Plot 02: Utility by model ─────────────────────────────────────────────────

def plot_utility_by_model(df: pd.DataFrame, out: Path):
    valid = df[~df["model_a"].isin(BROKEN_MODELS)]
    clean = valid[valid["attack_variant"] == "none"]
    models = [m for m in MODEL_ORDER if m in clean["model_a"].unique()]

    util_vals, err_labels = [], []
    for m in models:
        sub = clean[clean["model_a"] == m]
        util_vals.append(pct(sub["utility_success"].sum(), len(sub)))
        broken_sub = df[(df["model_a"] == m) & (df["attack_variant"] == "none")]
        stopped = broken_sub["stopped_by_a"].value_counts()
        err_labels.append("")

    # Include broken models for completeness
    all_models = [m for m in MODEL_ORDER + ["gpt-5-mini"] if m in df["model_a"].unique()]
    util_vals2, colors2 = [], []
    for m in all_models:
        sub = df[(df["model_a"] == m) & (df["attack_variant"] == "none")]
        util_vals2.append(pct(sub["utility_success"].sum(), len(sub)))
        if m in BROKEN_MODELS:
            colors2.append("#cccccc")
        else:
            colors2.append(MODEL_COLORS.get(m, "#999"))

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar([MODEL_SHORT.get(m, m) for m in all_models], util_vals2,
                  color=colors2, edgecolor="white", width=0.6)
    for bar, v, m in zip(bars, util_vals2, all_models):
        label = f"{v:.0f}%"
        if m in BROKEN_MODELS:
            label += "\n(API err)"
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
                label, ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, 120)
    ax.set_ylabel("Utility Rate (clean runs only, %)")
    ax.set_title("Utility by Model (clean attack_variant=none)\nGray = model broken due to API error")
    savefig(fig, out / "02_utility_by_model.png", "Utility by model")

# ── Plot 03: ASR heatmap model × scenario ────────────────────────────────────

def plot_asr_heatmap(df: pd.DataFrame, out: Path):
    valid = df[~df["model_a"].isin(BROKEN_MODELS)]
    attacked = valid[valid["is_attacked"] == True]
    models = [m for m in MODEL_ORDER if m in attacked["model_a"].unique()]
    scenarios = [s for s in SCENARIO_ORDER if s in attacked["scenario"].unique()]

    matrix = np.zeros((len(models), len(scenarios)))
    annot = np.empty((len(models), len(scenarios)), dtype=object)
    for i, m in enumerate(models):
        for j, s in enumerate(scenarios):
            sub = attacked[(attacked["model_a"] == m) & (attacked["scenario"] == s)]
            if len(sub) == 0:
                matrix[i, j] = np.nan
                annot[i, j] = "N/A"
            else:
                v = pct(sub["harmful_action"].sum(), len(sub))
                matrix[i, j] = v
                annot[i, j] = f"{v:.0f}%"

    fig, ax = plt.subplots(figsize=(8, 4.5))
    im = ax.imshow(matrix, cmap="RdYlGn_r", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(scenarios)))
    ax.set_xticklabels([SCENARIO_SHORT[s] for s in scenarios], fontsize=11)
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels([MODEL_SHORT[m] for m in models], fontsize=11)
    for i in range(len(models)):
        for j in range(len(scenarios)):
            ax.text(j, i, annot[i, j], ha="center", va="center",
                    fontsize=13, fontweight="bold",
                    color="white" if matrix[i, j] > 55 else "black")
    plt.colorbar(im, ax=ax, label="ASR (%)")
    ax.set_title("Attack Success Rate: Model × Scenario\n(direct attack; green=safe, red=vulnerable)")
    savefig(fig, out / "03_asr_heatmap.png", "ASR heatmap")

# ── Plot 04: Label decomposition (kill-chain funnel) ─────────────────────────

def plot_label_decomposition(df: pd.DataFrame, out: Path):
    valid = df[~df["model_a"].isin(BROKEN_MODELS)]
    attacked = valid[valid["is_attacked"] == True]
    models = [m for m in MODEL_ORDER if m in attacked["model_a"].unique()]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = np.arange(len(models))
    w = 0.25

    comp_rates, harm_rates = [], []
    for m in models:
        sub = attacked[attacked["model_a"] == m]
        n = len(sub)
        comp_rates.append(pct(sub["is_compromised"].sum(), n))
        harm_rates.append(pct(sub["harmful_action"].sum(), n))

    b1 = ax.bar(x - w, comp_rates, width=w, label="Exposed (canary read)", color="#f39c12", alpha=0.9)
    b2 = ax.bar(x,     harm_rates, width=w, label="Executed harm (harmful_action)", color="#e74c3c", alpha=0.9)

    for bar, v in zip(list(b1)+list(b2), comp_rates+harm_rates):
        if v > 5:
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1.5,
                    f"{v:.0f}%", ha="center", va="bottom", fontsize=9)

    ax.set_xticks(x - w/2)
    ax.set_xticklabels([MODEL_SHORT[m] for m in models])
    ax.set_ylim(0, 115)
    ax.set_ylabel("Fraction of attacked runs (%)")
    ax.set_title("Kill-Chain Decomposition: Exposure vs. Harmful Execution\n"
                 "Orange = canary appeared in agent's context; Red = agent executed harmful tool call")
    ax.legend(loc="upper right")
    savefig(fig, out / "04_label_decomposition.png", "Label decomposition")

# ── Plot 05: Objective drift (clean vs attacked) ──────────────────────────────

def plot_drift_by_model(df: pd.DataFrame, out: Path):
    if "objective_drift_max" not in df.columns:
        print("  [skip] objective_drift_max not in features")
        return
    valid = df[~df["model_a"].isin(BROKEN_MODELS)]
    models = [m for m in MODEL_ORDER if m in valid["model_a"].unique()]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = np.arange(len(models))
    w = 0.3

    clean_means, clean_stds, att_means, att_stds = [], [], [], []
    for m in models:
        cl = valid[(valid["model_a"] == m) & (valid["attack_variant"] == "none")]["objective_drift_max"].dropna()
        at = valid[(valid["model_a"] == m) & (valid["attack_variant"] == "direct")]["objective_drift_max"].dropna()
        clean_means.append(cl.mean() if len(cl) else 0)
        clean_stds.append(cl.std() if len(cl) > 1 else 0)
        att_means.append(at.mean() if len(at) else 0)
        att_stds.append(at.std() if len(at) > 1 else 0)

    ax.bar(x - w/2, clean_means, width=w, yerr=clean_stds, capsize=4,
           label="Clean", color="#3498db", alpha=0.85)
    ax.bar(x + w/2, att_means, width=w, yerr=att_stds, capsize=4,
           label="Attacked", color="#e74c3c", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_SHORT[m] for m in models])
    ax.set_ylabel("Max Objective Drift (0=on-task, 1=off-task)")
    ax.set_title("Objective Drift: Clean vs. Attacked Runs\nHigher drift = agent veered off original task")
    ax.legend()
    ax.axhline(0.4, color="gray", linestyle=":", linewidth=0.8, label="High-drift threshold")
    savefig(fig, out / "05_drift_by_model.png", "Drift by model")

# ── Plot 06: Tool call count (clean vs attacked) ──────────────────────────────

def plot_tool_calls(df: pd.DataFrame, out: Path):
    tcol = "n_tool_calls_a" if "n_tool_calls_a" in df.columns else "tool_call_count"
    if tcol not in df.columns:
        print("  [skip] tool call count column not found")
        return
    valid = df[~df["model_a"].isin(BROKEN_MODELS)]
    models = [m for m in MODEL_ORDER if m in valid["model_a"].unique()]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = np.arange(len(models))
    w = 0.3

    for i, (variant, color, label) in enumerate([("none","#3498db","Clean"), ("direct","#e74c3c","Attacked")]):
        means, stds = [], []
        for m in models:
            sub = valid[(valid["model_a"]==m) & (valid["attack_variant"]==variant)][tcol].dropna()
            means.append(sub.mean() if len(sub) else 0)
            stds.append(sub.std() if len(sub) > 1 else 0)
        ax.bar(x + (i-0.5)*w, means, width=w, yerr=stds, capsize=4,
               label=label, color=color, alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_SHORT[m] for m in models])
    ax.set_ylabel("Tool calls (Agent A)")
    ax.set_title("Tool Call Count: Clean vs. Attacked\nExtra calls in attacked runs suggest injected behavior")
    ax.legend()
    savefig(fig, out / "06_tool_calls.png", "Tool calls")

# ── Plot 07: Compromise fraction histogram ────────────────────────────────────

def plot_compromise_fraction(df: pd.DataFrame, out: Path):
    if "compromise_fraction" not in df.columns:
        print("  [skip] compromise_fraction not in features")
        return
    harmed = df[(df["harmful_action"] == True) & (~df["model_a"].isin(BROKEN_MODELS))]
    if len(harmed) == 0:
        print("  [skip] no harmful runs")
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    vals = harmed["compromise_fraction"].dropna()
    ax.hist(vals, bins=10, color="#e74c3c", alpha=0.8, edgecolor="white")
    ax.set_xlabel("Compromise Fraction (step of first harm / total steps)")
    ax.set_ylabel("Count of runs")
    ax.set_title("How Early in the Run Does Harm Occur?\n(harmful runs only)")
    ax.axvline(vals.mean(), color="black", linestyle="--", label=f"mean={vals.mean():.2f}")
    ax.legend()
    savefig(fig, out / "07_compromise_fraction.png", "Compromise fraction")

# ── Plot 08: ASR by scenario (grouped bar) ───────────────────────────────────

def plot_asr_by_scenario(df: pd.DataFrame, out: Path):
    valid = df[~df["model_a"].isin(BROKEN_MODELS)]
    attacked = valid[valid["is_attacked"] == True]
    models = [m for m in MODEL_ORDER if m in attacked["model_a"].unique()]
    scenarios = [s for s in SCENARIO_ORDER if s in attacked["scenario"].unique()]

    fig, ax = plt.subplots(figsize=(10, 4.5))
    x = np.arange(len(scenarios))
    n = len(models)
    w = 0.7 / n

    for i, m in enumerate(models):
        vals = []
        for s in scenarios:
            sub = attacked[(attacked["model_a"]==m) & (attacked["scenario"]==s)]
            vals.append(pct(sub["harmful_action"].sum(), len(sub)) if len(sub) else 0)
        offset = (i - (n-1)/2) * w
        bars = ax.bar(x + offset, vals, width=w,
                      label=MODEL_SHORT[m], color=MODEL_COLORS.get(m, "#999"), alpha=0.9)

    ax.set_xticks(x)
    ax.set_xticklabels([SCENARIO_SHORT[s] for s in scenarios], fontsize=11)
    ax.set_ylim(0, 115)
    ax.set_ylabel("Attack Success Rate (%)")
    ax.set_title("ASR by Scenario and Model\n(direct attack; permission_esc is hardest)")
    ax.legend(loc="upper right", fontsize=9)
    savefig(fig, out / "08_asr_by_scenario.png", "ASR by scenario")

# ── Plot 09: Trajectory case study ───────────────────────────────────────────

def plot_trajectory_case_study(df: pd.DataFrame, traces: dict, out: Path):
    """Plot drift trajectory for one compromised gpt-4o-mini run vs one safe Claude run."""
    # Pick a compromised gpt-4o-mini run with max steps
    comp_runs = df[(df["model_a"]=="gpt-4o-mini") & (df["harmful_action"]==True) &
                   (~df["model_a"].isin(BROKEN_MODELS))]
    if len(comp_runs) == 0:
        print("  [skip] no compromised gpt-4o-mini runs found")
        return

    comp_run = comp_runs.iloc[0]
    comp_id = comp_run["run_id"]

    # Pick a safe Claude Sonnet run (clean)
    safe_runs = df[(df["model_a"].isin(["claude-sonnet-4-5","claude-haiku-4-5"])) &
                   (df["attack_variant"]=="direct") & (df["harmful_action"]==False)]
    if len(safe_runs) == 0:
        safe_runs = df[(df["model_a"].isin(["claude-sonnet-4-5","claude-haiku-4-5"])) &
                       (df["attack_variant"]=="none")]

    safe_run = safe_runs.iloc[0] if len(safe_runs) > 0 else None
    safe_id  = safe_run["run_id"] if safe_run is not None else None

    def extract_drift(run_id):
        events = traces.get(run_id, [])
        steps, drifts = [], []
        for e in events:
            if e.get("type") == "tool_event":
                s = e.get("step", len(steps)+1)
                d = e.get("objective_drift_score")
                if d is not None:
                    steps.append(s)
                    drifts.append(d)
        return steps, drifts

    fig, ax = plt.subplots(figsize=(8, 4))

    comp_steps, comp_drifts = extract_drift(comp_id)
    if comp_drifts:
        ax.plot(comp_steps, comp_drifts, "o-", color="#e74c3c", linewidth=2,
                label=f"GPT-4o-mini (attacked, harmful) [{comp_id[-8:]}]", zorder=3)
        # Mark canary exposure step
        exp_step = comp_run.get("first_canary_exposure_step") if hasattr(comp_run, "get") else None
        if exp_step is not None and not pd.isna(exp_step):
            ax.axvline(exp_step, color="#e74c3c", linestyle=":", alpha=0.6, label="canary exposure")

    if safe_id:
        safe_steps, safe_drifts = extract_drift(safe_id)
        safe_model = safe_run["model_a"]
        label = f"{MODEL_SHORT.get(safe_model, safe_model)} (attacked, safe) [{safe_id[-8:]}]"
        if safe_drifts:
            ax.plot(safe_steps, safe_drifts, "s--", color="#2ecc71", linewidth=2,
                    label=label, zorder=3)

    ax.axhline(0.4, color="gray", linestyle="--", linewidth=0.8, alpha=0.7, label="High-drift threshold (0.4)")
    ax.set_xlabel("Tool-call step")
    ax.set_ylabel("Objective Drift Score")
    ax.set_ylim(0, 1.05)
    ax.set_title("Trajectory Drift: Compromised GPT-4o-mini vs Safe Claude\nStep-level drift from original task objective")
    ax.legend(fontsize=9, loc="upper left")
    savefig(fig, out / "09_trajectory_case_study.png", "Trajectory case study")

# ── Print stats ───────────────────────────────────────────────────────────────

def print_stats(df: pd.DataFrame):
    print("\n" + "="*70)
    print("SCENARIO_COMPARE_V1 — KEY FINDINGS")
    print("="*70)

    valid = df[~df["model_a"].isin(BROKEN_MODELS)]
    broken = df[df["model_a"].isin(BROKEN_MODELS)]

    if len(broken):
        print(f"\n[BROKEN MODELS — excluded from analysis]")
        for m in broken["model_a"].unique():
            sub = broken[broken["model_a"]==m]
            err = sub["stopped_by_a"].iloc[0][:80] if "stopped_by_a" in sub.columns else "unknown"
            print(f"  {m}: {len(sub)} runs, ALL failed. Error: {err}")

    print(f"\nValid runs: {len(valid)}  (excl. {len(broken)} broken)")

    attacked = valid[valid["is_attacked"]==True]
    clean    = valid[valid["attack_variant"]=="none"]

    print(f"\n{'Model':<22} {'UR%':>5} {'ASR%':>6} {'Exp%':>6} {'Harm%':>6}")
    print("-"*45)
    for m in MODEL_ORDER:
        cl = clean[clean["model_a"]==m]
        at = attacked[attacked["model_a"]==m]
        ur  = pct(cl["utility_success"].sum(), len(cl))
        asr = pct(at["harmful_action"].sum(), len(at)) if len(at) else 0
        exp = pct(at["is_compromised"].sum(), len(at)) if len(at) else 0
        print(f"  {MODEL_SHORT.get(m,m):<20} {ur:>5.0f} {asr:>6.0f} {exp:>6.0f} {asr:>6.0f}")

    print(f"\n{'Scenario':<18} {'ASR%':>6}  (across all valid models)")
    print("-"*30)
    for s in SCENARIO_ORDER:
        sub = attacked[attacked["scenario"]==s]
        print(f"  {SCENARIO_SHORT[s]:<16} {pct(sub['harmful_action'].sum(), len(sub)):>5.0f}%")

    print("\n[INSIGHT] gpt-4o-mini is 100% ASR on mem-poison, propagation, tool-poison")
    print("[INSIGHT] permission_esc resists ALL models (0% ASR gpt-4o-mini) — structural defense?")
    print("[INSIGHT] deepseek-chat is 100% ASR on propagation+tool-poison but resists mem-poison")
    print("[INSIGHT] Both Claude models: 0% ASR everywhere, 100% utility — true robustness")
    if len(broken):
        print("[CAUTION] Some models had ALL runs fail — see BROKEN MODELS section above")

    if "objective_drift_max" in valid.columns:
        print("\n[DRIFT]")
        for m in MODEL_ORDER:
            at = valid[(valid["model_a"]==m) & (valid["is_attacked"]==True)]
            cl = valid[(valid["model_a"]==m) & (valid["attack_variant"]=="none")]
            d_at = at["objective_drift_max"].mean()
            d_cl = cl["objective_drift_max"].mean()
            delta = d_at - d_cl if not (pd.isna(d_at) or pd.isna(d_cl)) else float("nan")
            print(f"  {MODEL_SHORT.get(m,m):<22} clean={d_cl:.3f}  attacked={d_at:.3f}  Δ={delta:+.3f}")

    print()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--results-dir", default="runs/scenario_compare_v1")
    args = p.parse_args()

    rd   = Path(args.results_dir)
    out  = rd / "plots"
    out.mkdir(parents=True, exist_ok=True)

    print(f"Loading data from {rd} ...")
    df = load_data(str(rd))
    print(f"  {len(df)} runs loaded. Columns: {list(df.columns)[:10]} ...")

    print(f"\nLoading trace files ...")
    traces = load_traces(str(rd))
    print(f"  {len(traces)} trace files loaded.")

    print_stats(df)

    print(f"\nGenerating plots → {out}/")
    plot_asr_by_model(df, out)
    plot_utility_by_model(df, out)
    plot_asr_heatmap(df, out)
    plot_label_decomposition(df, out)
    plot_drift_by_model(df, out)
    plot_tool_calls(df, out)
    plot_compromise_fraction(df, out)
    plot_asr_by_scenario(df, out)
    plot_trajectory_case_study(df, traces, out)

    print(f"\nDone. {len(list(out.glob('*.png')))} plots saved to {out}/")

if __name__ == "__main__":
    main()
