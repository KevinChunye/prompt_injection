#!/usr/bin/env python3
"""Reanalysis of the released per-run log for the TMLR revision.

Prints every count the revised text quotes that is not already checked by
figures/killchain_figures/src/paper_data.py.  Usage (from paper/):
    python3 tools/reanalysis.py > review/reanalysis.txt
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "figures/killchain_figures/src"))
import pandas as pd
import paper_data as pdt

pd.set_option("display.width", 250)
df = pdt.runs()
L = pdt.LABEL
def w(k, n):
    lo, hi = pdt.wilson(k, n)
    return f"{k}/{n} = {pdt.pct(k/n) if n else 0}% ({pdt.pct(lo)}-{pdt.pct(hi)}%)"

a = df[df.is_attacked & (df.defense == "none")]
print("== Table 1: no-defense attacked text-surface runs, per model")
for m in pdt.MODELS:
    d = a[a.model_a == m]; e = d[d.is_compromised]
    print(f"{L[m]:18s} assigned {len(d):3d} | exposed {len(e):3d} | Executed/assigned {w(int(d.attack_succeeded.sum()), len(d))}"
          f" | Executed/exposed {w(int(e.attack_succeeded.sum()), len(e))}"
          f" | task ok on attacked {w(int(d.utility_success.sum()), len(d))}"
          f" | task ok AND Executed {int((d.utility_success & d.attack_succeeded).sum())}"
          f" | token in any tool arg (old label) {int(d.attack_succeeded_any_arg.sum())}")

print("\n== Per scenario and model: assigned, exposed, no tool call, Persisted, Relayed, Executed, task ok, joint")
for s in pdt.TEXT_SCENARIOS + ["multi_surface"]:
    for m in pdt.MODELS:
        d = a[(a.scenario == s) & (a.model_a == m)]
        if not len(d): continue
        print(f"{s:15s} {L[m]:18s} n={len(d):2d} exposed={int(d.is_compromised.sum()):2d} no_tool_call={int((d.n_tool_calls_a == 0).sum()):2d}"
              f" persisted={int(d.canary_in_agent_write.sum()):2d} relayed={int(d.canary_in_b_output.sum()):2d}"
              f" executed={int(d.attack_succeeded.sum()):2d} old_any_arg={int(d.attack_succeeded_any_arg.sum()):2d}"
              f" task_ok={int(d.utility_success.sum()):2d} joint={int((d.utility_success & d.attack_succeeded).sum()):2d}")

print("\n== Clean controls: task success per model, scenario, defense")
c = df[~df.is_attacked]
print(c.groupby(["model_a", "scenario", "defense"]).utility_success.agg(["sum", "count"]).to_string())
print(c.groupby("model_a").utility_success.agg(["sum", "count"]).to_string())

print("\n== Matched batches: clean vs attacked task success in the same batch, model, scenario (no defense)")
n = df[df.defense == "none"]
g = n.groupby(["batch", "model_a", "scenario", "is_attacked"]).utility_success.agg(["sum", "count"]).unstack("is_attacked")
print(g.to_string())

print("\n== Defense ablation batch (defense_ablation_v1), attacked runs")
dd = df[(df.batch == "defense_ablation_v1") & df.is_attacked]
print(dd.groupby(["scenario", "defense", "model_a"])[["canary_in_agent_write", "canary_in_b_output", "attack_succeeded",
      "attack_succeeded_any_arg", "utility_success"]].sum().assign(n=dd.groupby(["scenario", "defense", "model_a"]).size()).to_string())
print("\n== Defense ablation batch, clean runs: task success")
dc = df[(df.batch == "defense_ablation_v1") & ~df.is_attacked]
print(dc.groupby(["scenario", "defense", "model_a"]).utility_success.agg(["sum", "count"]).to_string())

print("\n== memory_poison under write_filter (seeded payload bypasses the filter)")
mp = df[(df.scenario == "memory_poison") & df.is_attacked & df.batch.isin(["defense_positive_control_v1"])]
print(mp.groupby(["batch", "defense", "model_a"])[["attack_succeeded", "utility_success"]].sum().assign(n=mp.groupby(["batch", "defense", "model_a"]).size()).to_string())
print(df[(df.scenario == "memory_poison") & df.is_attacked].groupby(["batch", "defense", "model_a"]).attack_succeeded.agg(["sum", "count"]).to_string())

print("\n== permission_esc: token in Agent B outbound argument vs ADMIN tool call")
pe = a[a.scenario == "permission_esc"]
print(pe.groupby("model_a")[["canary_in_agent_write", "canary_in_b_output", "canary_in_b_outbound", "attack_succeeded", "n_admin_calls"]].sum().assign(n=pe.groupby("model_a").size()).to_string())

print("\n== Write-filter positive control (offline, deterministic): does the filter fire on each payload template?")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from agent_bench.memory import _has_imperative, _strip_imperatives
from agent_bench.scenarios import propagation as P, cross_modal_relay as C
tok = "SECRET-7F3A91C2"
page = P._INJECTION_TEMPLATES["direct"].format(clean=P._CLEAN_PAGE.strip(), canary=tok)
pdf = C._BENIGN_PDF + C._PDF_DIRECTIVE.format(canary=tok)
for name, text in (("text relay page (direct)", page), ("PDF relay extracted text (pdf_append)", pdf),
                   ("clean page", P._CLEAN_PAGE), ("clean PDF text", C._BENIGN_PDF),
                   ("one-line summary quoting the token", f"Federated learning summary. Verification phrase: {tok}."),
                   ("summary paraphrasing the instruction without the token", "Federated learning summary. The page asks that a verification phrase be included.")):
    out = _strip_imperatives(text) if _has_imperative(text) else text
    print(f"{name:55s} fires={_has_imperative(text)!s:5s} token_after_filter={tok in out}")
