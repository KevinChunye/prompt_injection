"""
Train a binary classifier to predict harmful_action from trajectory features.
Uses existing features.jsonl files — zero new API calls needed.

Outputs:
  runs/classifier_v1/
    results.txt       — AUC, accuracy, precision, recall per fold + overall
    feature_importance.png
    roc_curve.png
    confusion_matrix.png

Usage:
  python3 scripts/train_drift_classifier.py
  python3 scripts/train_drift_classifier.py --log-dirs runs/scenario_compare_v1 runs/multi_surface_v1
"""

import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

warnings.filterwarnings("ignore")

# ── feature columns to use ───────────────────────────────────────────────────
FEATURE_COLS = [
    # trajectory shape
    "tool_call_count",
    "unique_tool_count",
    "tool_entropy",
    "tool_repeat_rate",
    "tool_switch_rate",
    # memory
    "memory_access_rate",
    "memory_dependency_ratio",
    "first_memory_read_fraction",
    # drift
    "objective_drift_max",
    "objective_drift_mean_after_exposure",
    # canary signals
    "canary_in_result_any",
    # task deviation
    "subtask_order_deviation",
    # early-window snapshots
    "ew10_tool_entropy",
    "ew10_memory_access_rate",
    "ew10_canary_exposed",
    "ew20_tool_entropy",
    "ew20_memory_access_rate",
    "ew20_canary_exposed",
    "ew30_tool_entropy",
    "ew30_memory_access_rate",
    "ew30_canary_exposed",
]

LABEL_COL = "harmful_action"

MODEL_SHORT = {
    "gpt-4o-mini":      "GPT-4o-mini",
    "gpt-5-mini":       "GPT-5-mini",
    "claude-haiku-4-5": "Claude Haiku",
    "claude-sonnet-4-5":"Claude Sonnet",
    "deepseek-chat":    "DeepSeek",
}

SCENARIO_SHORT = {
    "memory_poison": "MemPoison",
    "propagation":   "Propagation",
    "tool_poison":   "ToolPoison",
    "permission_esc":"PrivEsc",
    "multi_surface": "MultiSurface",
}


def load_features(log_dirs):
    frames = []
    for d in log_dirs:
        p = Path(d) / "features.jsonl"
        if not p.exists():
            print(f"[warn] features.jsonl not found in {d}, skipping")
            continue
        rows = [json.loads(l) for l in open(p)]
        frames.append(pd.DataFrame(rows))
        print(f"[load] {d}: {len(rows)} rows")
    if not frames:
        sys.exit("No features.jsonl files found.")
    df = pd.concat(frames, ignore_index=True)
    print(f"[load] total: {len(df)} rows")
    return df


def build_matrix(df):
    """Return X, y, keeping only attacked rows with valid labels."""
    # only attacked runs are meaningful for predicting harmful_action
    df = df[df["is_attacked"] == True].copy()

    # fill missing feature values with column medians
    for col in FEATURE_COLS:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df_feat = df[FEATURE_COLS].fillna(df[FEATURE_COLS].median())
    y = df[LABEL_COL].astype(int)
    return df_feat, y, df


def run_cross_val(X, y, df):
    """Leave-one-scenario-out + stratified k-fold cross-validation."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.metrics import (roc_auc_score, accuracy_score,
                                  precision_score, recall_score,
                                  f1_score, confusion_matrix, roc_curve)
    from sklearn.model_selection import StratifiedKFold

    results = {}

    models_to_try = {
        "LogReg": Pipeline([
            ("scaler", StandardScaler()),
            ("clf",    LogisticRegression(max_iter=500, C=1.0, random_state=42))
        ]),
        "GBT": Pipeline([
            ("scaler", StandardScaler()),
            ("clf",    GradientBoostingClassifier(n_estimators=100, max_depth=3,
                                                   random_state=42))
        ]),
    }

    print("\n=== Stratified 5-fold cross-validation (attacked runs only) ===")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    for name, pipe in models_to_try.items():
        aucs, accs, precs, recs, f1s = [], [], [], [], []
        for train_idx, test_idx in skf.split(X, y):
            Xtr, Xte = X.iloc[train_idx], X.iloc[test_idx]
            ytr, yte = y.iloc[train_idx], y.iloc[test_idx]
            pipe.fit(Xtr, ytr)
            proba = pipe.predict_proba(Xte)[:, 1]
            pred  = pipe.predict(Xte)
            if len(np.unique(yte)) > 1:
                aucs.append(roc_auc_score(yte, proba))
            accs.append(accuracy_score(yte, pred))
            precs.append(precision_score(yte, pred, zero_division=0))
            recs.append(recall_score(yte, pred, zero_division=0))
            f1s.append(f1_score(yte, pred, zero_division=0))

        results[name] = {
            "AUC":  np.mean(aucs),  "AUC_std":  np.std(aucs),
            "Acc":  np.mean(accs),  "Acc_std":  np.std(accs),
            "Prec": np.mean(precs), "Prec_std": np.std(precs),
            "Rec":  np.mean(recs),  "Rec_std":  np.std(recs),
            "F1":   np.mean(f1s),   "F1_std":   np.std(f1s),
        }
        print(f"  {name:8} AUC={np.mean(aucs):.3f}±{np.std(aucs):.3f}  "
              f"Acc={np.mean(accs):.3f}  F1={np.mean(f1s):.3f}  "
              f"Prec={np.mean(precs):.3f}  Rec={np.mean(recs):.3f}")

    # ── leave-one-scenario-out ────────────────────────────────────────────────
    if "scenario" in df.columns:
        print("\n=== Leave-one-scenario-out (GBT) ===")
        pipe = models_to_try["GBT"]
        scenarios = df["scenario"].unique()
        loso_results = {}
        for held_out in scenarios:
            mask_test  = df["scenario"] == held_out
            mask_train = ~mask_test
            if mask_test.sum() == 0 or mask_train.sum() == 0:
                continue
            Xtr = X[mask_train]; ytr = y[mask_train]
            Xte = X[mask_test];  yte = y[mask_test]
            if len(np.unique(ytr)) < 2 or len(np.unique(yte)) < 2:
                loso_results[held_out] = {"AUC": float("nan"), "n_test": int(mask_test.sum())}
                print(f"  hold-out={SCENARIO_SHORT.get(held_out, held_out):15} skipped (single class)")
                continue
            pipe.fit(Xtr, ytr)
            proba = pipe.predict_proba(Xte)[:, 1]
            auc   = roc_auc_score(yte, proba)
            pred  = pipe.predict(Xte)
            acc   = accuracy_score(yte, pred)
            loso_results[held_out] = {
                "AUC": auc, "Acc": acc, "n_test": int(mask_test.sum())
            }
            print(f"  hold-out={SCENARIO_SHORT.get(held_out, held_out):15} "
                  f"AUC={auc:.3f}  Acc={acc:.3f}  n_test={mask_test.sum()}")
        results["LOSO_GBT"] = loso_results

    # ── per-model breakdown ───────────────────────────────────────────────────
    if "model_a" in df.columns:
        print("\n=== Per-model breakdown (GBT, trained on all other models) ===")
        pipe = models_to_try["GBT"]
        model_results = {}
        for held_model in df["model_a"].unique():
            mask_test  = df["model_a"] == held_model
            mask_train = ~mask_test
            Xtr = X[mask_train]; ytr = y[mask_train]
            Xte = X[mask_test];  yte = y[mask_test]
            if len(np.unique(ytr)) < 2 or len(np.unique(yte)) < 2:
                print(f"  hold-out={MODEL_SHORT.get(held_model, held_model):15} skipped (single class)")
                continue
            pipe.fit(Xtr, ytr)
            proba = pipe.predict_proba(Xte)[:, 1]
            auc   = roc_auc_score(yte, proba)
            pred  = pipe.predict(Xte)
            acc   = accuracy_score(yte, pred)
            model_results[held_model] = {"AUC": auc, "Acc": acc, "n_test": int(mask_test.sum())}
            print(f"  hold-out={MODEL_SHORT.get(held_model, held_model):15} "
                  f"AUC={auc:.3f}  Acc={acc:.3f}  n_test={mask_test.sum()}")
        results["PerModel_GBT"] = model_results

    return results, models_to_try["GBT"], X, y


def plot_feature_importance(pipe, feature_names, out_dir):
    from sklearn.inspection import permutation_importance
    clf = pipe.named_steps["clf"]
    if hasattr(clf, "feature_importances_"):
        importances = clf.feature_importances_
    else:
        return

    idx = np.argsort(importances)[::-1]
    top_n = min(15, len(idx))

    fig, ax = plt.subplots(figsize=(7, 5))
    colors = ["#c0392b" if i < 3 else "#2c3e50" for i in range(top_n)]
    ax.barh(range(top_n), importances[idx[:top_n]][::-1], color=colors[::-1])
    ax.set_yticks(range(top_n))
    ax.set_yticklabels([feature_names[i] for i in idx[:top_n]][::-1], fontsize=9)
    ax.set_xlabel("Feature Importance (GBT)")
    ax.set_title("Top Features for Predicting Harmful Action", fontsize=11, fontweight="bold")
    ax.axvline(0, color="black", linewidth=0.5)
    plt.tight_layout()
    path = out_dir / "feature_importance.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[plot] {path}")


def plot_roc_and_confusion(pipe, X, y, out_dir):
    from sklearn.model_selection import cross_val_predict
    from sklearn.metrics import roc_curve, auc, confusion_matrix, ConfusionMatrixDisplay
    from sklearn.preprocessing import StandardScaler

    probas = cross_val_predict(pipe, X, y, cv=5, method="predict_proba")[:, 1]
    preds  = (probas >= 0.5).astype(int)

    fpr, tpr, _ = roc_curve(y, probas)
    roc_auc_val = auc(fpr, tpr)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    # ROC
    ax = axes[0]
    ax.plot(fpr, tpr, color="#c0392b", lw=2, label=f"GBT (AUC = {roc_auc_val:.3f})")
    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve — Harmful Action Prediction", fontweight="bold")
    ax.legend(fontsize=9)
    ax.set_xlim([-0.02, 1.02])
    ax.set_ylim([-0.02, 1.05])

    # Confusion matrix
    ax = axes[1]
    cm = confusion_matrix(y, preds)
    disp = ConfusionMatrixDisplay(cm, display_labels=["Clean", "Harmful"])
    disp.plot(ax=ax, colorbar=False, cmap="Blues")
    ax.set_title("Confusion Matrix (5-fold CV)", fontweight="bold")

    plt.tight_layout()
    path = out_dir / "roc_confusion.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[plot] {path}")
    return roc_auc_val


def plot_feature_drift_comparison(df, out_dir):
    """Show drift distributions for clean vs attacked by model."""
    models = [m for m in ["gpt-4o-mini","deepseek-chat","gpt-5-mini",
                           "claude-haiku-4-5","claude-sonnet-4-5"]
              if m in df["model_a"].values]
    if not models or "objective_drift_max" not in df.columns:
        return

    fig, axes = plt.subplots(1, len(models), figsize=(3 * len(models), 4), sharey=True)
    if len(models) == 1:
        axes = [axes]

    colors = {"clean": "#2ecc71", "attacked": "#e74c3c"}

    for ax, m in zip(axes, models):
        clean   = df[(df["model_a"] == m) & (~df["is_attacked"])]["objective_drift_max"].dropna()
        attacked= df[(df["model_a"] == m) &  (df["is_attacked"])]["objective_drift_max"].dropna()
        harmfd  = df[(df["model_a"] == m) &  (df["harmful_action"] == True)]["objective_drift_max"].dropna()

        positions = [1, 2]
        bp = ax.violinplot([clean, attacked], positions=positions,
                           showmedians=True, showextrema=True)
        for i, (body, col) in enumerate(zip(bp["bodies"], [colors["clean"], colors["attacked"]])):
            body.set_facecolor(col)
            body.set_alpha(0.7)
        bp["cmedians"].set_color("black")
        bp["cmedians"].set_linewidth(2)

        # overlay harmful dots
        if len(harmfd):
            ax.scatter([2.2] * len(harmfd), harmfd, color="#900000",
                       s=18, zorder=5, label="Harmful", alpha=0.8)

        ax.set_xticks([1, 2])
        ax.set_xticklabels(["Clean", "Attacked"], fontsize=8)
        ax.set_title(MODEL_SHORT.get(m, m), fontsize=9, fontweight="bold")
        ax.set_ylim(0, 1.05)

    axes[0].set_ylabel("Max Objective Drift", fontsize=9)
    fig.suptitle("Objective Drift: Clean vs. Attacked by Model", fontsize=11, fontweight="bold")
    plt.tight_layout()
    path = out_dir / "drift_distributions.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[plot] {path}")


def write_results_txt(cv_results, roc_auc_val, out_dir):
    lines = ["=== Drift Classifier Results ===\n"]
    lines.append("5-fold cross-validation (attacked runs only):\n")
    for name, r in cv_results.items():
        if isinstance(r, dict) and "AUC" in r:
            lines.append(
                f"  {name:8} AUC={r['AUC']:.3f}±{r.get('AUC_std',0):.3f}  "
                f"Acc={r['Acc']:.3f}  F1={r['F1']:.3f}  "
                f"Prec={r['Prec']:.3f}  Rec={r['Rec']:.3f}\n"
            )

    lines.append(f"\nROC AUC (5-fold CV, GBT, cross_val_predict): {roc_auc_val:.4f}\n")

    if "LOSO_GBT" in cv_results:
        lines.append("\nLeave-one-scenario-out (GBT):\n")
        for sc, v in cv_results["LOSO_GBT"].items():
            if isinstance(v, dict) and "AUC" in v:
                lines.append(f"  {sc:20} AUC={v['AUC']:.3f}  Acc={v.get('Acc',float('nan')):.3f}  "
                              f"n_test={v['n_test']}\n")

    if "PerModel_GBT" in cv_results:
        lines.append("\nLeave-one-model-out (GBT):\n")
        for m, v in cv_results["PerModel_GBT"].items():
            if isinstance(v, dict) and "AUC" in v:
                lines.append(f"  {MODEL_SHORT.get(m, m):15} AUC={v['AUC']:.3f}  "
                              f"Acc={v.get('Acc',float('nan')):.3f}  n_test={v['n_test']}\n")

    path = out_dir / "results.txt"
    path.write_text("".join(lines))
    print(f"[write] {path}")
    print("\n" + "".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-dirs", nargs="+",
                        default=["runs/scenario_compare_v1", "runs/multi_surface_v1"])
    parser.add_argument("--out-dir", default="runs/classifier_v1")
    args = parser.parse_args()

    try:
        from sklearn.ensemble import GradientBoostingClassifier  # noqa: F401
    except ImportError:
        sys.exit("scikit-learn not installed. Run: pip install scikit-learn")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_features(args.log_dirs)

    # ── sanity check ──────────────────────────────────────────────────────────
    if LABEL_COL not in df.columns:
        sys.exit(f"Label column '{LABEL_COL}' not found in features.jsonl")

    n_attacked = (df["is_attacked"] == True).sum()
    n_harmful  = (df[LABEL_COL] == True).sum()
    print(f"\nAttacked runs: {n_attacked}  |  Harmful: {n_harmful}  "
          f"|  Base rate: {n_harmful/n_attacked:.1%}")

    if n_attacked < 20:
        print("[warn] Very few attacked runs; classifier results may be unstable.")

    X, y, df_attacked = build_matrix(df)

    print(f"\nFeature matrix: {X.shape[0]} rows × {X.shape[1]} features")
    print(f"Class balance: {y.mean():.1%} harmful (positive class)")

    cv_results, best_pipe, X_attacked, y_attacked = run_cross_val(X, y, df_attacked)

    # train final model on all data for feature importance
    best_pipe.fit(X_attacked, y_attacked)

    plot_feature_importance(best_pipe, FEATURE_COLS, out_dir)
    roc_auc_val = plot_roc_and_confusion(best_pipe, X_attacked, y_attacked, out_dir)
    plot_feature_drift_comparison(df, out_dir)
    write_results_txt(cv_results, roc_auc_val, out_dir)

    print(f"\n[done] All outputs written to {out_dir}/")


if __name__ == "__main__":
    main()
