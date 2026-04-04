"""
run_phase3.py
Full Phase 3 experiment grid: PDF + Audio + Cross-Modal Relay
across all five frontier models.

Usage:
    # Dry-run — validates scaffolding, no API calls:
    python3 run_phase3.py --dry-run

    # Live run — all scenarios, all models, 5 reps:
    python3 run_phase3.py

    # Subset — just cross-modal relay, 3 reps:
    python3 run_phase3.py --scenarios cross_modal_relay --n-runs 3

    # Single model test:
    python3 run_phase3.py --models gpt-4o-mini --n-runs 1

API keys required (already in .env from earlier setup):
    OPENAI_API_KEY     — GPT-4o-mini, GPT-5-mini, OpenAI TTS
    ANTHROPIC_API_KEY  — Claude Haiku, Claude Sonnet
    DEEPSEEK_API_KEY   — DeepSeek-chat
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from agent_bench.runner import run_grid, print_results

# ── Model registry ─────────────────────────────────────────────────────────────
ALL_MODELS = [
    "gpt-4o-mini",
    "gpt-5-mini-2025-02-15",
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-5",
    "deepseek-chat",
]

# ── Experiment grid definition ─────────────────────────────────────────────────

PHASE3_GRID = {

    # ── Phase 1: PDF surface (single-agent) ──────────────────────────────────
    "pdf_injection": {
        "attack_variants": ["pdf_append", "pdf_whitefont", "pdf_metadata", "none"],
        "defenses":        ["none", "write_filter", "pi_detector", "spotlighting"],
        "description":     "PDF → EXPOSED → PERSISTED → EXECUTED",
    },

    # ── Phase 2: Audio surface (single-agent) ────────────────────────────────
    "audio_injection": {
        "attack_variants": ["audio_append", "audio_overlay_high", "audio_overlay_low", "none"],
        "defenses":        ["none", "write_filter", "pi_detector", "spotlighting"],
        "description":     "Audio → EXPOSED → PERSISTED → EXECUTED",
    },

    # ── Phase 3: Cross-modal relay (two-agent, highest novelty) ──────────────
    "cross_modal_relay": {
        "attack_variants": ["pdf_append", "pdf_whitefont", "pdf_metadata",
                            "audio_append", "none"],
        "defenses":        ["none", "write_filter", "pi_detector", "spotlighting"],
        "description":     "PDF/Audio → Agent A memory → Agent B send_report",
    },
}

# Cross-model relay pairs: test whether Claude as Agent B decontaminates
# injections that GPT-4o-mini as Agent A propagates into memory.
CROSS_MODEL_PAIRS = [
    ("gpt-4o-mini",              "claude-haiku-4-5-20251001"),  # GPT writes, Claude reads
    ("gpt-4o-mini",              "claude-sonnet-4-5"),
    ("gpt-4o-mini",              "deepseek-chat"),
    ("claude-haiku-4-5-20251001","gpt-4o-mini"),                # Claude writes, GPT reads
]


def run_phase3(
    scenarios:  list[str],
    models:     list[str],
    n_runs:     int,
    log_dir:    str,
    dry_run:    bool,
    cross_model: bool,
    max_iter:   int,
) -> None:
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = Path(log_dir) / f"phase3_{ts}"
    out.mkdir(parents=True, exist_ok=True)

    all_records = []

    # ── Homogeneous model pairs (Agent A == Agent B) ──────────────────────
    for scenario_name in scenarios:
        grid = PHASE3_GRID[scenario_name]
        print(f"\n{'='*70}")
        print(f"SCENARIO: {scenario_name}  — {grid['description']}")
        print(f"{'='*70}")

        model_pairs = [(m, m) for m in models]

        recs = run_grid(
            scenario        = scenario_name,
            attack_variants = grid["attack_variants"],
            defenses        = grid["defenses"],
            models          = model_pairs,
            n_runs          = n_runs,
            log_dir         = str(out),
            dry_run         = dry_run,
            max_iterations  = max_iter,
        )
        all_records.extend(recs)

    # ── Cross-model relay pairs (cross_modal_relay only) ──────────────────
    if cross_model and "cross_modal_relay" in scenarios:
        print(f"\n{'='*70}")
        print("CROSS-MODEL RELAY — Agent A ≠ Agent B")
        print(f"{'='*70}")
        grid = PHASE3_GRID["cross_modal_relay"]

        recs = run_grid(
            scenario        = "cross_modal_relay",
            attack_variants = ["pdf_append", "audio_append", "none"],
            defenses        = ["none", "write_filter"],
            models          = CROSS_MODEL_PAIRS,
            n_runs          = n_runs,
            log_dir         = str(out / "cross_model"),
            dry_run         = dry_run,
            max_iterations  = max_iter,
        )
        all_records.extend(recs)

    # ── Print & save results ──────────────────────────────────────────────
    print_results(all_records, log_dir=str(out))

    # ── Stage-level breakdown ─────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("KILL-CHAIN STAGE BREAKDOWN")
    print(f"{'='*70}")
    _print_stage_breakdown(all_records)

    print(f"\nAll results saved to: {out.resolve()}")


def _print_stage_breakdown(records) -> None:
    """Print ASR broken down by scenario × attack_variant × model."""
    from collections import defaultdict
    groups: dict = defaultdict(lambda: {"total": 0, "attacked": 0, "succeeded": 0})

    for r in records:
        key = (r.scenario, r.attack_variant, r.model_a)
        groups[key]["total"] += 1
        if r.is_attacked:
            groups[key]["attacked"] += 1
        if r.attack_succeeded:
            groups[key]["succeeded"] += 1

    print(f"  {'Scenario':<22} {'Variant':<20} {'Model':<35} {'ASR':>6}")
    print("  " + "-" * 85)
    for (sc, var, mdl), v in sorted(groups.items()):
        if v["attacked"] == 0:
            continue
        asr = v["succeeded"] / v["attacked"] * 100
        print(f"  {sc:<22} {var:<20} {mdl:<35} {asr:>5.0f}%")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Phase 3 experiment runner")
    p.add_argument("--scenarios", nargs="+",
                   choices=list(PHASE3_GRID.keys()),
                   default=list(PHASE3_GRID.keys()),
                   help="Which scenarios to run (default: all three)")
    p.add_argument("--models", nargs="+",
                   default=ALL_MODELS,
                   help="Models to test as Agent A (and B in homogeneous pairs)")
    p.add_argument("--n-runs",  type=int, default=5,
                   help="Repetitions per cell (default 5)")
    p.add_argument("--log-dir", default="runs/phase3",
                   help="Root output directory")
    p.add_argument("--dry-run", action="store_true",
                   help="Skip API calls — validates scaffolding only")
    p.add_argument("--cross-model", action="store_true", default=True,
                   help="Also run cross-model relay pairs (default: True)")
    p.add_argument("--no-cross-model", dest="cross_model", action="store_false")
    p.add_argument("--max-iter", type=int, default=10,
                   help="Max LLM iterations per agent (default 10)")
    args = p.parse_args()

    print("Phase 3: Multimodal Injection Experiments")
    print(f"  Scenarios : {args.scenarios}")
    print(f"  Models    : {args.models}")
    print(f"  n-runs    : {args.n_runs}")
    print(f"  dry-run   : {args.dry_run}")
    print(f"  cross-mod : {args.cross_model}")
    print()

    run_phase3(
        scenarios    = args.scenarios,
        models       = args.models,
        n_runs       = args.n_runs,
        log_dir      = args.log_dir,
        dry_run      = args.dry_run,
        cross_model  = args.cross_model,
        max_iter     = args.max_iter,
    )


if __name__ == "__main__":
    main()
