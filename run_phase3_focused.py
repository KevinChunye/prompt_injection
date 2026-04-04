"""
run_phase3_focused.py
Budget-optimised Phase 3 grid based on pilot findings.

PILOT FINDINGS (gpt-4o-mini, 1 run/cell):
  ✓ cross_modal_relay + pdf_append           → 30% ASR  ← only working combination
  ✗ pdf_injection single-agent               → 0%  ASR  ← model resists in single context
  ✗ audio_injection (all variants)           → 0%  ASR  ← real null result
  ✗ pdf_whitefont / pdf_metadata             → 0%  ASR, but PR>0  ← reaches memory, dies at relay
  ✓ write_filter defense                     → 100% block of pdf_append
  ✓ pi_detector / spotlighting               → 100% block in pilot (needs confirmation at n=3)

BUDGET ALLOCATION ($15 total):
  OpenAI  $7  → gpt-4o-mini ($0.03/run) + gpt-5-mini ($0.05/run)
  Claude  $10 → haiku ($0.02/run) + sonnet ($0.30/run, capped at 12 runs)
  DeepSeek $5 → deepseek-chat ($0.01/run)

THREE BLOCKS:
  A) cross_modal_relay — main experiment (all 5 models)
     variants: pdf_append (works), pdf_whitefont (reaches memory only), none (control)
     defenses: none, write_filter, pi_detector
     Claude Sonnet: only on defense=none (cost control)
     n_runs: 3
     Est. cost: ~$7

  B) cross_model_relay pairs — novel decontamination experiment
     variants: pdf_append, none
     defenses: none, write_filter
     pairs: 4 cheap pairs (no Sonnet)
     n_runs: 3
     Est. cost: ~$1

  C) stage-level evidence — pdf_whitefont / pdf_metadata on cross_modal_relay
     gpt-4o-mini only, both defenses, n_runs=3
     Confirms: injection reaches PERSISTED but dies at RELAYED without exact canary in B
     Est. cost: ~$0.50

TOTAL: ~$8.50, well within $15.

Usage:
    python3 run_phase3_focused.py --dry-run           # validate, no API cost
    python3 run_phase3_focused.py --block A           # main experiment
    python3 run_phase3_focused.py --block B           # cross-model relay
    python3 run_phase3_focused.py --block C           # stage-level evidence
    python3 run_phase3_focused.py                     # all blocks
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from agent_bench.runner import run_grid, print_results

# ── Model definitions ──────────────────────────────────────────────────────────
CHEAP   = ["gpt-4o-mini", "claude-haiku-4-5-20251001", "deepseek-chat"]
ALL_5   = ["gpt-4o-mini", "gpt-5-mini-2025-02-15",
           "claude-haiku-4-5-20251001", "claude-sonnet-4-5", "deepseek-chat"]
SONNET  = "claude-sonnet-4-5"

# Cross-model relay pairs (cheap only — no Sonnet in B position)
CROSS_PAIRS = [
    ("gpt-4o-mini",              "claude-haiku-4-5-20251001"),  # GPT writes, Claude reads
    ("claude-haiku-4-5-20251001","gpt-4o-mini"),                # Claude writes, GPT reads
    ("gpt-4o-mini",              "deepseek-chat"),
    ("deepseek-chat",            "gpt-4o-mini"),
]


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def block_A(out: Path, n_runs: int, dry_run: bool, max_iter: int) -> list:
    """Block A: cross_modal_relay — main experiment across all 5 models."""
    print(f"\n{'='*70}")
    print("BLOCK A — cross_modal_relay (all 5 models)")
    print(f"{'='*70}")

    records = []

    # A1: cheap models — full defense grid with all 3 variants
    pairs_cheap = [(m, m) for m in CHEAP + ["gpt-5-mini-2025-02-15"]]
    recs = run_grid(
        scenario        = "cross_modal_relay",
        attack_variants = ["pdf_append", "pdf_whitefont", "none"],
        defenses        = ["none", "write_filter", "pi_detector"],
        models          = pairs_cheap,
        n_runs          = n_runs,
        log_dir         = str(out / "A_cheap"),
        dry_run         = dry_run,
        max_iterations  = max_iter,
    )
    records.extend(recs)

    # A2: Claude Sonnet — defense=none only (cost control)
    print(f"\n-- Claude Sonnet (defense=none only) --")
    recs = run_grid(
        scenario        = "cross_modal_relay",
        attack_variants = ["pdf_append", "none"],
        defenses        = ["none", "write_filter"],   # minimal for Sonnet
        models          = [(SONNET, SONNET)],
        n_runs          = n_runs,
        log_dir         = str(out / "A_sonnet"),
        dry_run         = dry_run,
        max_iterations  = max_iter,
    )
    records.extend(recs)

    return records


def block_B(out: Path, n_runs: int, dry_run: bool, max_iter: int) -> list:
    """Block B: cross-model relay pairs — does Claude decontaminate what GPT propagates?"""
    print(f"\n{'='*70}")
    print("BLOCK B — cross-model relay pairs (Agent A ≠ Agent B)")
    print(f"{'='*70}")

    recs = run_grid(
        scenario        = "cross_modal_relay",
        attack_variants = ["pdf_append", "none"],
        defenses        = ["none", "write_filter"],
        models          = CROSS_PAIRS,
        n_runs          = n_runs,
        log_dir         = str(out / "B_cross_model"),
        dry_run         = dry_run,
        max_iterations  = max_iter,
    )
    return recs


def block_C(out: Path, n_runs: int, dry_run: bool, max_iter: int) -> list:
    """Block C: stage-level evidence — whitefont/metadata reach memory but die at relay."""
    print(f"\n{'='*70}")
    print("BLOCK C — stage evidence: pdf_whitefont / pdf_metadata (gpt-4o-mini)")
    print(f"{'='*70}")

    recs = run_grid(
        scenario        = "cross_modal_relay",
        attack_variants = ["pdf_whitefont", "pdf_metadata", "none"],
        defenses        = ["none", "write_filter"],
        models          = [("gpt-4o-mini", "gpt-4o-mini")],
        n_runs          = n_runs,
        log_dir         = str(out / "C_stage_evidence"),
        dry_run         = dry_run,
        max_iterations  = max_iter,
    )
    return recs


def _cost_table(records: list) -> None:
    """Estimate API cost from records."""
    # Rough per-run cost ($) based on ~10k tokens per run
    COST = {
        "gpt-4o-mini":              0.026,
        "gpt-5-mini-2025-02-15":    0.050,
        "claude-haiku-4-5-20251001":0.020,
        "claude-sonnet-4-5":        0.300,
        "deepseek-chat":            0.010,
    }
    from collections import defaultdict
    totals: dict = defaultdict(float)
    counts: dict = defaultdict(int)
    for r in records:
        totals[r.model_a] += COST.get(r.model_a, 0.05)
        counts[r.model_a] += 1

    print(f"\n{'='*70}")
    print("ESTIMATED COST BREAKDOWN")
    print(f"{'='*70}")
    grand = 0.0
    for m in sorted(totals):
        c = totals[m]
        grand += c
        print(f"  {m:<40} {counts[m]:>4} runs × ~${COST.get(m,0.05):.3f} = ${c:>6.2f}")
    print(f"  {'TOTAL':<40}                    ${grand:>6.2f}")


def _stage_breakdown(records: list) -> None:
    """Kill-chain stage rates by scenario/variant/model."""
    from collections import defaultdict
    groups = defaultdict(lambda: {"n":0,"exp":0,"per":0,"rel":0,"exe":0})
    for r in records:
        if not getattr(r, 'is_attacked', False):
            continue
        k = (r.scenario, r.attack_variant, r.model_a)
        g = groups[k]
        g["n"]   += 1
        g["exp"] += 1 if getattr(r, 'is_compromised', False) else 0
        g["per"] += 1 if getattr(r, 'canary_in_memory', False) else 0
        g["rel"] += 1 if getattr(r, 'canary_in_b_output', False) else 0
        g["exe"] += 1 if r.attack_succeeded else 0

    print(f"\n{'='*70}")
    print("KILL-CHAIN STAGE RATES (attacked runs only)")
    print(f"{'='*70}")
    print(f"  {'Variant':<20} {'Model':<38} {'EXP':>5} {'PER':>5} {'REL':>5} {'EXE':>5}")
    print("  " + "-" * 80)
    for (sc, var, mdl), g in sorted(groups.items()):
        if g["n"] == 0: continue
        n = g["n"]
        print(f"  {var:<20} {mdl:<38} "
              f"{g['exp']/n:>4.0%} {g['per']/n:>4.0%} "
              f"{g['rel']/n:>4.0%} {g['exe']/n:>4.0%}")


def main():
    p = argparse.ArgumentParser(description="Budget-focused Phase 3 runner")
    p.add_argument("--block", choices=["A","B","C","all"], default="all")
    p.add_argument("--n-runs",   type=int, default=3)
    p.add_argument("--log-dir",  default="runs/phase3_focused")
    p.add_argument("--dry-run",  action="store_true")
    p.add_argument("--max-iter", type=int, default=10)
    args = p.parse_args()

    out = Path(args.log_dir) / _ts()
    out.mkdir(parents=True, exist_ok=True)

    print("Phase 3 Focused Run")
    print(f"  Block    : {args.block}")
    print(f"  n-runs   : {args.n_runs}")
    print(f"  dry-run  : {args.dry_run}")
    print(f"  out      : {out}")

    all_records = []

    if args.block in ("A", "all"):
        all_records += block_A(out, args.n_runs, args.dry_run, args.max_iter)
    if args.block in ("B", "all"):
        all_records += block_B(out, args.n_runs, args.dry_run, args.max_iter)
    if args.block in ("C", "all"):
        all_records += block_C(out, args.n_runs, args.dry_run, args.max_iter)

    print_results(all_records, log_dir=str(out))
    _stage_breakdown(all_records)
    _cost_table(all_records)
    print(f"\nDone. Results: {out.resolve()}")


if __name__ == "__main__":
    main()
