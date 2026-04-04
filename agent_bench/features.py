"""
FILE: agent_bench/features.py
Behavioral feature extractor for trajectory-level agent security analysis.

Reads JSONL trace files produced by RunLogger, computes one feature vector
per run, and writes a features.jsonl file for downstream ML / statistical
analysis.

FEATURE CATEGORIES
──────────────────
  Generic behavioral (task-agnostic):
    trajectory_length     — total steps logged
    tool_call_count       — number of tool_event records
    unique_tool_count     — distinct tool names called
    tool_entropy          — Shannon entropy of tool-name distribution
    tool_repeat_rate      — fraction of tool calls where same tool used consecutively
    tool_switch_rate      — 1 - tool_repeat_rate (normalized alternation)
    mean_args_length      — average JSON-serialized length of tool_args
    resource_set_size     — number of distinct resource targets in tool args
    resource_expansion_slope — linear slope of cumulative resource count over steps
    memory_access_rate    — fraction of steps touching memory surfaces
    perm_violation_rate   — fraction of steps where tool permission > run permission

  Security-specific:
    canary_in_result_any  — did canary appear in any tool result? (0/1)
    canary_in_args_any    — did canary appear in any tool args? (0/1)
    first_canary_exposure_step — step# (None → NaN if never)
    first_canary_in_args_step  — step# (None → NaN if never)
    steps_to_compromise   — args_step - exposure_step (None → NaN)
    compromise_fraction   — args_step / total_steps (None → NaN)

  Early-window (EW-N = features computed over first N% of steps):
    ew10_tool_entropy
    ew20_tool_entropy
    ew30_tool_entropy
    ew10_memory_access_rate
    ew20_memory_access_rate
    ew30_memory_access_rate
    ew10_tool_repeat_flag   — 1 if any repeated consecutive tool in window
    ew20_tool_repeat_flag
    ew30_tool_repeat_flag
    ew10_resource_count     — distinct resources seen in window
    ew20_resource_count
    ew30_resource_count
    ew10_canary_exposed     — 1 if canary appeared in result within window
    ew20_canary_exposed
    ew30_canary_exposed

USAGE
─────
  # Extract features from a single scenario log dir:
  python3 -m agent_bench.features --log-dir runs/memory_poison

  # Merge multiple scenario dirs:
  python3 -m agent_bench.features --log-dir runs/memory_poison runs/propagation runs/permission_esc

  # Custom output path:
  python3 -m agent_bench.features --log-dir runs/memory_poison --out runs/features.jsonl

  # Print feature table to console instead of writing:
  python3 -m agent_bench.features --log-dir runs/memory_poison --print
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# ── Edit-distance helpers (for subtask_order_deviation) ──────────────────────

def _edit_distance(a: list, b: list) -> int:
    """Wagner-Fischer Levenshtein distance (O(n) space)."""
    m, n = len(a), len(b)
    dp   = list(range(n + 1))
    for i in range(1, m + 1):
        prev   = dp[0]
        dp[0]  = i
        for j in range(1, n + 1):
            temp  = dp[j]
            dp[j] = prev if a[i - 1] == b[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
            prev  = temp
    return dp[n]


def _normalized_edit_distance(a: list, b: list) -> float:
    """Edit distance divided by max length — returns value in [0, 1]."""
    max_len = max(len(a), len(b), 1)
    return round(_edit_distance(a, b) / max_len, 4)


# ── Constants ─────────────────────────────────────────────────────────────────

MEMORY_SURFACES = {"memory_read", "memory_write"}
EARLY_WINDOWS   = [10, 20, 30]   # percentages of trajectory to analyse

NaN = float("nan")   # sentinel for missing numeric values in JSON


# ── Low-level helpers ──────────────────────────────────────────────────────────

def _shannon_entropy(counts: Counter) -> float:
    """Shannon entropy (bits) of a distribution represented as a Counter."""
    total = sum(counts.values())
    if total == 0:
        return 0.0
    entropy = 0.0
    for n in counts.values():
        p = n / total
        if p > 0:
            entropy -= p * math.log2(p)
    return round(entropy, 4)


def _consecutive_repeat_rate(seq: list) -> float:
    """Fraction of adjacent pairs (a,b) in seq where a == b."""
    if len(seq) < 2:
        return 0.0
    repeats = sum(1 for a, b in zip(seq, seq[1:]) if a == b)
    return round(repeats / (len(seq) - 1), 4)


def _resource_targets(tool_events: list[dict]) -> list[str]:
    """
    Extract resource identifiers from tool args.
    Looks for common arg keys: url, key, recipient, query, path.
    Returns one string per tool call (or "" if none found).
    """
    keys = ("url", "key", "recipient", "query", "path", "target")
    result = []
    for ev in tool_events:
        args = ev.get("tool_args", {})
        if isinstance(args, dict):
            for k in keys:
                val = args.get(k)
                if val:
                    result.append(str(val))
                    break
            else:
                result.append("")
        else:
            result.append("")
    return result


def _linear_slope(ys: list[float]) -> float:
    """Slope of best-fit line through (0..n-1, ys) using closed-form OLS."""
    n = len(ys)
    if n < 2:
        return 0.0
    xs = list(range(n))
    x_mean = (n - 1) / 2.0
    y_mean = sum(ys) / n
    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    den = sum((x - x_mean) ** 2 for x in xs)
    if den == 0:
        return 0.0
    return round(num / den, 6)


def _none_to_nan(v: "int | float | None") -> float:
    """Convert None to NaN so the feature vector always has a number."""
    return NaN if v is None else float(v)


# ── Per-run feature extraction ─────────────────────────────────────────────────

def _extract_features(
    run_id:       str,
    events:       list[dict],
    summary:      "dict | None",
    ref_sequence: "list[str] | None" = None,   # Part 6: modal clean tool sequence
) -> dict:
    """
    Given parsed events from one JSONL trace and the run_summary dict (or None),
    return a flat feature dict for this run.
    """
    tool_events = [e for e in events if e.get("type") == "tool_event"]

    # ── Trajectory length ──────────────────────────────────────────────────────
    trajectory_length = summary.get("total_steps", len(events)) if summary else len(events)
    tool_call_count   = len(tool_events)

    # ── Tool name distribution ─────────────────────────────────────────────────
    tool_names    = [e["tool_name"] for e in tool_events]
    tool_counts   = Counter(tool_names)
    unique_tool_count = len(tool_counts)
    tool_entropy      = _shannon_entropy(tool_counts)
    tool_repeat_rate  = _consecutive_repeat_rate(tool_names)
    tool_switch_rate  = round(1.0 - tool_repeat_rate, 4)

    # ── Argument length ────────────────────────────────────────────────────────
    args_lengths = [
        len(json.dumps(e.get("tool_args", {}))) for e in tool_events
    ]
    mean_args_length = round(
        sum(args_lengths) / len(args_lengths), 2
    ) if args_lengths else 0.0

    # ── Resource targets ───────────────────────────────────────────────────────
    resource_targets = _resource_targets(tool_events)
    resource_set_size = len(set(t for t in resource_targets if t))

    # Cumulative unique resource count per step → slope
    seen_resources: set[str] = set()
    cumulative_counts: list[float] = []
    for t in resource_targets:
        if t:
            seen_resources.add(t)
        cumulative_counts.append(float(len(seen_resources)))
    resource_expansion_slope = _linear_slope(cumulative_counts)

    # ── Memory access rate ─────────────────────────────────────────────────────
    memory_steps   = sum(1 for e in tool_events if e.get("surface") in MEMORY_SURFACES)
    memory_access_rate = round(memory_steps / tool_call_count, 4) if tool_call_count else 0.0

    # ── Permission violation rate ──────────────────────────────────────────────
    # Use run_permission from summary if present, else infer from events
    run_perm = summary.get("result", {}).get("run_permission", None) if summary else None
    if run_perm is None:
        # Infer as the minimum permission level seen — conservative
        perms_seen = [e.get("permission", 0) for e in tool_events]
        run_perm = min(perms_seen) if perms_seen else 0
    perm_violations = sum(
        1 for e in tool_events if e.get("permission", 0) > run_perm
    )
    perm_violation_rate = round(
        perm_violations / tool_call_count, 4
    ) if tool_call_count else 0.0

    # ── Security fields (from run_summary timing) ──────────────────────────────
    canary_in_result_any = int(any(e.get("canary_in_result", False) for e in tool_events))
    canary_in_args_any   = int(any(e.get("canary_in_args",   False) for e in tool_events))

    if summary:
        first_exp  = _none_to_nan(summary.get("first_canary_exposure_step"))
        first_exec = _none_to_nan(summary.get("first_canary_in_args_step"))
        stc        = _none_to_nan(summary.get("steps_to_compromise"))
        cf         = _none_to_nan(summary.get("compromise_fraction"))
    else:
        # Reconstruct from events if summary missing (older traces)
        first_exp  = NaN
        first_exec = NaN
        for e in tool_events:
            if e.get("canary_in_result") and math.isnan(first_exp):
                first_exp = float(e["step"])
            if e.get("canary_in_args") and math.isnan(first_exec):
                first_exec = float(e["step"])
        stc = (first_exec - first_exp) if (not math.isnan(first_exp) and not math.isnan(first_exec)) else NaN
        cf  = (first_exec / trajectory_length) if (not math.isnan(first_exec) and trajectory_length > 0) else NaN

    # ── Early-window features ──────────────────────────────────────────────────
    ew_features: dict[str, float] = {}
    for pct in EARLY_WINDOWS:
        window_size = max(1, int(math.ceil(tool_call_count * pct / 100)))
        window = tool_events[:window_size]

        w_names    = [e["tool_name"] for e in window]
        w_counts   = Counter(w_names)
        w_entropy  = _shannon_entropy(w_counts)

        w_mem_rate = round(
            sum(1 for e in window if e.get("surface") in MEMORY_SURFACES) / len(window), 4
        ) if window else 0.0

        w_repeat_flag = int(_consecutive_repeat_rate(w_names) > 0)

        w_res_targets = _resource_targets(window)
        w_res_count   = len(set(t for t in w_res_targets if t))

        w_canary_exposed = int(any(e.get("canary_in_result", False) for e in window))

        prefix = f"ew{pct}"
        ew_features[f"{prefix}_tool_entropy"]       = w_entropy
        ew_features[f"{prefix}_memory_access_rate"] = w_mem_rate
        ew_features[f"{prefix}_tool_repeat_flag"]   = float(w_repeat_flag)
        ew_features[f"{prefix}_resource_count"]     = float(w_res_count)
        ew_features[f"{prefix}_canary_exposed"]     = float(w_canary_exposed)

    # ── Part 6: Additional features ────────────────────────────────────────────

    # memory_dependency_ratio: fraction of tool calls where the immediately
    # prior call was a memory read (the agent pulled from memory then acted).
    _mem_read_tools = {"read_memory", "list_memory_keys"}
    mem_dep_count = sum(
        1 for i in range(1, len(tool_events))
        if tool_events[i - 1]["tool_name"] in _mem_read_tools
    )
    memory_dependency_ratio = round(
        mem_dep_count / tool_call_count, 4
    ) if tool_call_count > 1 else 0.0

    # first_memory_read_fraction: where in the trajectory the agent first
    # reads from memory (normalised by trajectory length).
    _first_mem_step = next(
        (e["step"] for e in tool_events if e["tool_name"] == "read_memory"),
        None,
    )
    first_memory_read_fraction = (
        _none_to_nan(None) if _first_mem_step is None
        else round(_first_mem_step / trajectory_length, 4)
        if trajectory_length > 0 else NaN
    )

    # objective drift aggregates — read from run_summary if drift was logged,
    # else default to NaN (traces from before Part 2 was deployed).
    objective_drift_max = _none_to_nan(
        summary.get("max_objective_drift") if summary else None
    )
    objective_drift_mean_after_exposure = _none_to_nan(
        summary.get("mean_drift_after_exposure") if summary else None
    )

    # subtask_order_deviation: normalised edit distance vs modal clean sequence.
    # ref_sequence is injected by extract_features() after a two-pass analysis.
    if ref_sequence and tool_names:
        subtask_order_deviation: "float | None" = _normalized_edit_distance(
            tool_names, ref_sequence
        )
    else:
        subtask_order_deviation = None

    # canary_exposure_to_execution_lag: alias for steps_to_compromise
    # (already available — included for naming clarity in the paper).
    canary_exposure_to_execution_lag = stc   # NaN when canary never executed

    # ── Metadata from summary ──────────────────────────────────────────────────
    meta: dict[str, Any] = {}
    if summary:
        res = summary.get("result", {})
        for k in ("scenario", "attack_variant", "defense", "model_a", "model_b",
                  "utility", "security", "propagation_occurred",
                  "defense_applicable", "run_permission",
                  # Part 5: expanded label structure
                  "is_attacked", "is_compromised", "harmful_action"):
            if k in res:
                meta[k] = res[k]
        # Top-level summary fields
        for k in ("propagation_occurred", "surface_crossings"):
            if k in summary and k not in meta:
                meta[k] = summary[k]

    # ── Assemble feature vector ────────────────────────────────────────────────
    features: dict[str, Any] = {
        "run_id": run_id,
        # Generic behavioral
        "trajectory_length":          trajectory_length,
        "tool_call_count":            tool_call_count,
        "unique_tool_count":          unique_tool_count,
        "tool_entropy":               tool_entropy,
        "tool_repeat_rate":           tool_repeat_rate,
        "tool_switch_rate":           tool_switch_rate,
        "mean_args_length":           mean_args_length,
        "resource_set_size":          resource_set_size,
        "resource_expansion_slope":   resource_expansion_slope,
        "memory_access_rate":         memory_access_rate,
        "perm_violation_rate":        perm_violation_rate,
        # Part 6: additional behavioral features
        "memory_dependency_ratio":             memory_dependency_ratio,
        "first_memory_read_fraction":          first_memory_read_fraction,
        "subtask_order_deviation":             subtask_order_deviation,
        # Objective drift (Part 2 / Part 6)
        "objective_drift_max":                 objective_drift_max,
        "objective_drift_mean_after_exposure": objective_drift_mean_after_exposure,
        # Security
        "canary_in_result_any":       canary_in_result_any,
        "canary_in_args_any":         canary_in_args_any,
        "first_canary_exposure_step": first_exp,
        "first_canary_in_args_step":  first_exec,
        "steps_to_compromise":        stc,
        "compromise_fraction":        cf,
        "canary_exposure_to_execution_lag": canary_exposure_to_execution_lag,
    }
    features.update(ew_features)
    features.update(meta)

    return features


# ── JSONL trace reader ────────────────────────────────────────────────────────

def load_trace(path: Path) -> tuple[list[dict], "dict | None"]:
    """
    Parse a JSONL trace file.  Returns (events, summary) where summary is
    the run_summary record (last line) or None if not present.
    """
    events: list[dict] = []
    summary: "dict | None" = None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("type") == "run_summary":
                summary = record
            else:
                events.append(record)
    return events, summary


# ── Main extraction pipeline ──────────────────────────────────────────────────

def extract_features(log_dirs: "list[str | Path]") -> list[dict]:
    """
    Extract feature vectors from all *.jsonl traces in the given directories.
    Returns a list of feature dicts, one per run.

    Two-pass approach (Part 6: subtask_order_deviation):
      Pass 1 — load all traces; collect tool sequences for clean runs.
      Pass 2 — extract features with per-scenario modal reference sequence.
    """
    # ── Pass 1: load all traces ───────────────────────────────────────────────
    all_data: list[tuple[str, list[dict], "dict | None"]] = []

    for log_dir in log_dirs:
        log_dir = Path(log_dir)
        if not log_dir.exists():
            print(f"[features] WARNING: log_dir not found: {log_dir}", file=sys.stderr)
            continue

        trace_files = sorted(log_dir.glob("*.jsonl"))
        trace_files = [f for f in trace_files if f.stem not in ("features", "results")]

        if not trace_files:
            print(f"[features] WARNING: no trace files in {log_dir}", file=sys.stderr)
            continue

        for path in trace_files:
            try:
                events, summary = load_trace(path)
                all_data.append((path.stem, events, summary))
            except Exception as exc:  # noqa: BLE001
                print(f"[features] ERROR loading {path.name}: {exc}", file=sys.stderr)

    if not all_data:
        return []

    # ── Compute modal clean sequence per scenario (for subtask_order_deviation)
    # Only clean (attack_variant == "none") runs contribute to the reference.
    clean_seqs: dict[str, list[list[str]]] = {}
    for run_id, events, summary in all_data:
        if not summary:
            continue
        res      = summary.get("result", {})
        scenario = res.get("scenario", "?")
        variant  = res.get("attack_variant", "none")
        if variant == "none":
            tool_seq = [e["tool_name"] for e in events if e.get("type") == "tool_event"]
            clean_seqs.setdefault(scenario, []).append(tool_seq)

    # Modal = the most common tool sequence (by length first, then first occurrence)
    modal_seq: dict[str, list[str]] = {}
    for sc, seqs in clean_seqs.items():
        if seqs:
            by_len    = Counter(len(s) for s in seqs)
            modal_len = by_len.most_common(1)[0][0]
            modal_seq[sc] = next(s for s in seqs if len(s) == modal_len)

    # ── Pass 2: extract features ──────────────────────────────────────────────
    features_list: list[dict] = []
    for run_id, events, summary in all_data:
        try:
            sc  = (summary or {}).get("result", {}).get("scenario", "?") if summary else "?"
            ref = modal_seq.get(sc)
            feat = _extract_features(run_id, events, summary, ref_sequence=ref)
            features_list.append(feat)
        except Exception as exc:  # noqa: BLE001
            print(f"[features] ERROR processing {run_id}: {exc}", file=sys.stderr)

    return features_list


def write_features(features: list[dict], out_path: "str | Path") -> None:
    """Write feature vectors to a JSONL file, one dict per line."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        for feat in features:
            # Replace NaN with None for clean JSON output
            clean = {
                k: (None if isinstance(v, float) and math.isnan(v) else v)
                for k, v in feat.items()
            }
            fh.write(json.dumps(clean) + "\n")
    print(f"[features] Wrote {len(features)} feature vectors → {out_path}")


def print_features_table(features: list[dict]) -> None:
    """Print a compact human-readable summary table."""
    if not features:
        print("[features] No features to display.")
        return

    # Select columns for display
    display_cols = [
        "run_id", "scenario", "attack_variant", "defense",
        "trajectory_length", "tool_call_count", "tool_entropy",
        "memory_access_rate", "canary_in_result_any", "canary_in_args_any",
        "steps_to_compromise", "compromise_fraction",
        "utility", "security",
    ]

    def fmt(v: Any) -> str:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "-"
        if isinstance(v, float):
            return f"{v:.3f}"
        if isinstance(v, bool):
            return "Y" if v else "N"
        return str(v)

    # Determine which columns are actually present
    present = [c for c in display_cols if any(c in f for f in features)]
    # Compute column widths
    widths = {c: max(len(c), max(len(fmt(f.get(c))) for f in features)) for c in present}

    header = "  ".join(c.ljust(widths[c]) for c in present)
    sep    = "  ".join("-" * widths[c] for c in present)
    print(header)
    print(sep)
    for feat in features:
        row = "  ".join(fmt(feat.get(c)).ljust(widths[c]) for c in present)
        print(row)


# ── CLI entry point ───────────────────────────────────────────────────────────

def _parse_args(argv: list[str]) -> "argparse.Namespace":
    import argparse
    parser = argparse.ArgumentParser(
        prog="python3 -m agent_bench.features",
        description="Extract behavioral feature vectors from agent trace files.",
    )
    parser.add_argument(
        "--log-dir", nargs="+", required=True, metavar="DIR",
        help="One or more directories containing *.jsonl trace files.",
    )
    parser.add_argument(
        "--out", default=None, metavar="PATH",
        help=(
            "Output JSONL path.  Defaults to features.jsonl inside the "
            "first --log-dir.  Set to - to skip writing."
        ),
    )
    parser.add_argument(
        "--print", dest="print_table", action="store_true",
        help="Print a human-readable feature table to stdout.",
    )
    return parser.parse_args(argv)


def main(argv: "list[str] | None" = None) -> None:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    features = extract_features(args.log_dir)
    if not features:
        print("[features] No features extracted.  Check --log-dir paths.")
        sys.exit(1)

    # Determine output path
    if args.out is None:
        out_path = Path(args.log_dir[0]) / "features.jsonl"
    elif args.out == "-":
        out_path = None
    else:
        out_path = Path(args.out)

    if out_path is not None:
        write_features(features, out_path)

    if args.print_table:
        print_features_table(features)
    elif out_path is None:
        # --out - and no --print: dump raw JSON to stdout
        for feat in features:
            clean = {
                k: (None if isinstance(v, float) and math.isnan(v) else v)
                for k, v in feat.items()
            }
            print(json.dumps(clean))


if __name__ == "__main__":
    main()
