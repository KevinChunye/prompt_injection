"""Numbers behind the data figures, read from the result files.

Text-surface cells (Tables 1, 2 and A1) are computed from data/runs.csv, the per-run
log released with the paper (Hugging Face dataset kevinwhc/kill-chain-canaries,
rows with in_paper == True).  PDF-relay cells (Table 4 and the Figure 5 caption) come from
data/pdf_relay_cells.csv: the per-run logs of that experiment are not in the
code repository or the dataset, so that file holds the per-cell counts of
Tables 5 and 6 of arXiv 2603.28013v3.

verify() recomputes every cell that a figure draws and compares it with the
tables as typeset in main.tex, so a figure and its table cannot drift apart
silently.  Run  python src/paper_data.py  to print the report.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MAIN_TEX = ROOT.parent.parent / "main.tex"

MODELS = ["gpt-4o-mini", "deepseek-chat", "gpt-5-mini", "claude-haiku-4-5", "claude-sonnet-4-5"]
LABEL = {"gpt-4o-mini": "GPT-4o-mini", "deepseek-chat": "DeepSeek Chat", "gpt-5-mini": "GPT-5-mini",
         "claude-haiku-4-5": "Claude Haiku 4.5", "claude-sonnet-4-5": "Claude Sonnet 4.5"}
TEXT_SCENARIOS = ["memory_poison", "tool_poison", "propagation", "permission_esc"]
# Attack surface of each scenario, named as in Section 3.2 and Figures 2 and 4.
SURFACE = {"memory_poison": "pre-seeded memory", "tool_poison": "tool result", "propagation": "web page",
           "permission_esc": "web page", "multi_surface": "web page + pre-seeded memory",
           "pdf_append": "visible PDF text", "pdf_whitefont": "white PDF text", "audio_inject": "audio transcript"}

# Cells where the typeset table and the released log disagree.  The figure
# follows the table so the paper stays self-consistent; verify() reports each
# one so the authors can reconcile it.  Delete an entry to plot the log value.
TABLE_OVERRIDES = {
    ("permission_esc", "gpt-5-mini"): {
        "k": 1,
        "why": "Table A1 (v3 Table 3) reports 1/36; in_paper rows of runs.csv give 0/36. The only GPT-5-mini "
               "permission_esc success in runs.csv is in batch high_n_v2 (in_paper == False).",
    },
}


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    d = 1 + z ** 2 / n
    c = (p + z ** 2 / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / d
    return max(0.0, c - h), min(1.0, c + h)


def pct(x):
    return int(np.floor(100 * x + 0.5))


def runs():
    df = pd.read_csv(DATA / "runs.csv")
    return df[df["in_paper"]]


def attacked_nodefense():
    df = runs()
    return df[df["is_attacked"] & (df["defense"] == "none")]


def text_cells():
    """Table 3: {(scenario, model): (k, n)} for no-defense attacked runs."""
    a = attacked_nodefense()
    out = {}
    for s in TEXT_SCENARIOS:
        for m in MODELS:
            d = a[(a["scenario"] == s) & (a["model_a"] == m)]
            k, n = int(d["attack_succeeded"].sum()), len(d)
            if (s, m) in TABLE_OVERRIDES:
                k = TABLE_OVERRIDES[(s, m)]["k"]
            out[(s, m)] = (k, n)
    return out


def text_cells_raw():
    a = attacked_nodefense()
    return {(s, m): (int(a[(a.scenario == s) & (a.model_a == m)]["attack_succeeded"].sum()),
                     int(((a.scenario == s) & (a.model_a == m)).sum()))
            for s in TEXT_SCENARIOS for m in MODELS}


def overall():
    """Table 1: per model n, k, ASR, Wilson CI (no-defense attacked runs, all
    scenarios) and task success on clean-control runs (all defense conditions)."""
    df = runs()
    a = attacked_nodefense()
    clean = df[~df["is_attacked"]]
    cells = text_cells()
    out = {}
    for m in MODELS:
        d = a[a["model_a"] == m]
        n = len(d)
        k = int(d["attack_succeeded"].sum())
        for (s, mm), v in TABLE_OVERRIDES.items():
            if mm == m:
                raw = int(d[d["scenario"] == s]["attack_succeeded"].sum())
                k += v["k"] - raw
        c = clean[clean["model_a"] == m]
        out[m] = dict(n=n, k=k, asr=k / n, ci=wilson(k, n),
                      task=c["utility_success"].mean(), n_clean=len(c))
    return out


def relay_stages():
    """Table 2 (propagation, no-defense attacked): per-model stage counts and
    the last stage each run's canary reached."""
    a = attacked_nodefense()
    a = a[a["scenario"] == "propagation"]
    out = {}
    for m in MODELS:
        d = a[a["model_a"] == m]
        ex = d["attack_succeeded"]
        rel = d["stage_relayed"] & ~ex
        per_only = d["stage_persisted"] & ~d["stage_relayed"] & ~ex
        absent = ~d["stage_persisted"] & ~d["stage_relayed"] & ~ex
        assert int(per_only.sum()) == 0, "a run persisted without relaying; K3 needs a fourth category"
        out[m] = dict(n=len(d), exposed=int(d["is_compromised"].sum()),
                      persisted=int(d["stage_persisted"].sum()), relayed=int(d["stage_relayed"].sum()),
                      executed=int(ex.sum()),
                      last_absent=int(absent.sum()), last_relayed=int(rel.sum()), last_executed=int(ex.sum()))
    return out


def pdf_cells():
    return pd.read_csv(DATA / "pdf_relay_cells.csv")


def text_facts():
    """(name, logs-agree, exact phrase in main.tex) for every count the text
    quotes from the logs."""
    df = runs()
    a = attacked_nodefense()
    out = []
    called = a[a["n_tool_calls_a"] > 0]
    zero = a[a["n_tool_calls_a"] == 0]
    out.append(("tool-calling runs all exposed", bool(called["is_compromised"].all()) and len(called) == 372,
                "all 372 no-defense attacked text-surface runs that made a tool call were exposed"))
    out.append(("no-tool-call runs", len(zero) == 56 and len(a) == 428, "The other 56 of the 428 made no tool call"))
    by = zero.groupby(["model_a", "scenario"]).size().to_dict()
    want = {("gpt-5-mini", "memory_poison"): 16, ("gpt-5-mini", "tool_poison"): 16,
            ("gpt-5-mini", "permission_esc"): 16, ("deepseek-chat", "permission_esc"): 4,
            ("gpt-4o-mini", "permission_esc"): 4}
    out.append(("no-tool-call runs by model and scenario", by == want,
                "48 GPT-5-mini runs (16 each in \\mempoison{}, \\toolpoison{} and \\permesc{}) and 4 runs each "
                "of DeepSeek Chat and GPT-4o-mini (\\permesc{})"))
    out.append(("no-tool-call runs in one batch", set(zero["batch"]) == {"high_n_v1"},
                "all from one collection batch (\\path{high_n_v1}"))
    out.append(("no no-tool-call run in the text relay", int((zero["scenario"] == "propagation").sum()) == 0,
                "none is in the text relay"))
    g5 = df[df["model_a"] == "gpt-5-mini"]
    g5a = a[a["model_a"] == "gpt-5-mini"]
    g5z = g5a[g5a["n_tool_calls_a"] == 0]
    hb = g5[(g5["batch"] == "high_n_v1") & g5["is_attacked"]]
    clean = g5[~g5["is_attacked"]]
    clean_batches = set(clean["batch"])
    no_zero_elsewhere = bool((g5[g5["batch"].isin(clean_batches)]["n_tool_calls_a"] > 0).all())
    out.append(("GPT-5-mini 48 of 136", len(g5z) == 48 and len(g5a) == 136,
                "its 48 of 136 attacked runs without a tool call"))
    out.append(("GPT-5-mini high_n_v1: 48 of 100, no clean controls",
                len(hb) == 100 and int((hb["n_tool_calls_a"] == 0).sum()) == 48
                and int(((g5["batch"] == "high_n_v1") & ~g5["is_attacked"]).sum()) == 0,
                "holds all 48 (out of its 100 GPT-5-mini attacked runs) and no clean controls"))
    out.append(("GPT-5-mini clean runs: 36 from three tool-calling batches",
                len(clean) == 36 and clean_batches == {"scenario_compare_v1", "gpt5mini_propagation_v1",
                                                       "multi_surface_v1"} and no_zero_elsewhere,
                "the 36 GPT-5-mini clean-control runs come from three batches (\\path{scenario_compare_v1}, "
                "\\path{gpt5mini_propagation_v1}, \\path{multi_surface_v1}) in which every GPT-5-mini run "
                "called a tool"))
    ms = a[a["scenario"] == "multi_surface"].groupby("model_a")["attack_succeeded"].agg(["sum", "count"])
    out.append(("multi_surface footnote", ms.to_dict() == {"sum": {"claude-sonnet-4-5": 0, "gpt-4o-mini": 4,
                                                                   "gpt-5-mini": 0},
                                                           "count": {"claude-sonnet-4-5": 4, "gpt-4o-mini": 4,
                                                                     "gpt-5-mini": 8}},
                "4 GPT-4o-mini runs, all executed, and 8 GPT-5-mini and 4 Claude Sonnet 4.5 runs, none executed"))
    succ = a[a["attack_succeeded"]]
    sc = succ[succ["batch"] == "scenario_compare_v1"].groupby("model_a").size().to_dict()
    per_batch = succ.groupby("batch").size()
    out.append(("22 compromised runs = scenario_compare_v1 (only batch with 22)",
                sc == {"gpt-4o-mini": 12, "deepseek-chat": 9, "gpt-5-mini": 1}
                and list(per_batch[per_batch == 22].index) == ["scenario_compare_v1"],
                "the 22 compromised runs of the first collection batch (\\path{scenario_compare_v1}: 12 "
                "GPT-4o-mini, 9 DeepSeek Chat and 1 GPT-5-mini run, all without a defense)"))
    da = df[df["in_paper"] & (df["batch"] == "defense_ablation_v1")]
    dd = da[da["is_attacked"] & (da["defense"] != "none")]
    out.append(("defense ablation: 64/64 executed", len(dd) == 64 and bool(dd["attack_succeeded"].all())
                and bool((dd.groupby(["model_a", "scenario", "defense"]).size() == 4).all()),
                "all 64 attacked runs under \\wfilter{}, \\pidetect{}, \\spotlight{} or all three combined "
                "reached Executed (4 runs per model, scenario and defense, all from the defense ablation batch"))
    pcb = df[df["in_paper"] & (df["batch"] == "defense_positive_control_v1") & df["is_attacked"]
             & (df["scenario"] == "memory_poison")]
    k = lambda m, d: (int(pcb[(pcb.model_a == m) & (pcb.defense == d)]["attack_succeeded"].sum()),
                      int(((pcb.model_a == m) & (pcb.defense == d)).sum()))
    out.append(("write_filter memory_poison control", k("gpt-4o-mini", "write_filter") == (8, 8)
                and k("gpt-4o-mini", "none") == (8, 8) and k("deepseek-chat", "write_filter") == (0, 8)
                and k("deepseek-chat", "none") == (0, 8),
                "GPT-4o-mini still executed 8/8 \\mempoison{} attacks, as it did without a defense in the same "
                "batch (DeepSeek Chat: 0/8 in both conditions)"))
    g4 = da[(da["model_a"] == "gpt-4o-mini") & da["is_attacked"]]
    u = lambda d: (int(g4[g4.defense == d]["utility_success"].sum()), int((g4.defense == d).sum()))
    out.append(("spotlighting task success 5/8 -> 4/8", u("none") == (5, 8) and u("spotlighting") == (4, 8),
                "from 63\\% without a defense (5/8, same batch) to 50\\% (4/8)"))
    return out


# ----------------------------------------------------------------------------- verification
_MODEL_ALIASES = {"gpt-4o-mini": "gpt-4o-mini", "deepseek chat": "deepseek-chat", "deepseek": "deepseek-chat",
                  "gpt-5-mini": "gpt-5-mini", "claude haiku 4.5": "claude-haiku-4-5",
                  "claude haiku": "claude-haiku-4-5", "claude sonnet 4.5": "claude-sonnet-4-5",
                  "claude sonnet": "claude-sonnet-4-5"}


def _plain(cell):
    s = cell
    for _ in range(3):
        s = re.sub(r"\\(?:textbf|texttt|emph|textsc|mbox|path|nolinkurl)\{([^{}]*)\}", r"\1", s)
    s = s.replace("\\_", "_").replace("\\%", "%").replace("~", " ").replace("--", "-")
    s = re.sub(r"\\[a-zA-Z]+\*?", "", s)
    s = s.replace("{", "").replace("}", "").replace("$", "")
    return " ".join(s.split())


def table_rows(label):
    tex = MAIN_TEX.read_text()
    i = tex.index("\\label{%s}" % label)
    j = tex.index("\\end{tabular}", i)
    body = tex[tex.index("\\midrule", i) + len("\\midrule"):j]
    rows = []
    for line in body.split("\\\\"):
        line = re.sub(r"\\(midrule|bottomrule|addlinespace)(\[[^\]]*\])?", "", line)
        line = re.sub(r"(?<!\\)%.*", "", line).strip()
        if line:
            rows.append([_plain(c) for c in line.split("&")])
    return rows


def _model(s):
    return _MODEL_ALIASES[s.strip().lower()]


def verify():
    lines, bad = [], 0

    def check(name, ok, got, want):
        nonlocal bad
        bad += (not ok)
        lines.append(f"{'OK ' if ok else 'MISMATCH'}  {name}: figure/log {got}  |  table {want}")

    # Table 1
    ov = overall()
    for r in table_rows("tab:overall"):
        m = _model(r[0])
        n, task = int(r[1]), int(r[2].rstrip("%"))
        mm = re.match(r"(\d+)% \((\d+)-(\d+)%\)", r[3])
        asr, lo, hi = map(int, mm.groups())
        o = ov[m]
        got = (o["n"], pct(o["task"]), pct(o["asr"]), pct(o["ci"][0]), pct(o["ci"][1]))
        check(f"Table 1 {LABEL[m]} (n, task%, ASR%, CI)", got == (n, task, asr, lo, hi), got, (n, task, asr, lo, hi))
    # Table 2
    rs = relay_stages()
    for r in table_rows("tab:propagation"):
        m = _model(r[0])
        want = (int(r[1]),) + tuple(int(x.rstrip("%")) for x in r[2:5])
        o = rs[m]
        got = (o["n"], pct(o["persisted"] / o["n"]), pct(o["relayed"] / o["n"]), pct(o["executed"] / o["n"]))
        check(f"Table 2 {LABEL[m]} (n, Pers%, Rel%, Exec%)", got == want, got, want)
        check(f"Table 2 {LABEL[m]} Exposed = 100%", o["exposed"] == o["n"], f"{o['exposed']}/{o['n']}", "100%")
    # Table 3: rows = models, columns = TEXT_SCENARIOS
    tc, raw = text_cells(), text_cells_raw()
    for r in table_rows("tab:heatmap"):
        m = _model(r[0])
        for sc, cell in zip(TEXT_SCENARIOS, r[1:]):
            k, n = map(int, cell.split("/"))
            check(f"Table 3 {sc} {LABEL[m]}", tc[(sc, m)] == (k, n), f"{tc[(sc, m)][0]}/{tc[(sc, m)][1]}", cell)
            if raw[(sc, m)] != tc[(sc, m)]:
                bad += 1
                lines.append(f"LOG≠TABLE {sc} {LABEL[m]}: runs.csv gives {raw[(sc, m)][0]}/{raw[(sc, m)][1]}; "
                             f"figure follows the table. {TABLE_OVERRIDES[(sc, m)]['why']}")
    # Table 5: rows = models; Exposed/Persisted/Relayed/Executed for pdf_append, then pdf_whitefont
    pc = pdf_cells()
    for r in table_rows("tab:pdf_same"):
        m = _model(r[0])
        vals = [c for c in r[1:] if c.strip()]
        for v, want in (("pdf_append", vals[0:4]), ("pdf_whitefont", vals[4:8])):
            want = tuple(int(x.rstrip("%")) for x in want)
            d = pc[(pc.pairing == "same_model") & (pc.writer == m) & (pc.variant == v)].iloc[0]
            got = tuple(pct(d[c] / d["n"]) for c in ["exposed", "persisted", "relayed", "executed"])
            check(f"Table 5 {LABEL[m]} {v} (Exp, Per, Rel, Exe %)", got == want, got, want)
    # Figure 5 caption: cross-model pairs (formerly Table 6), Executed k/n with Wilson CI
    tex = MAIN_TEX.read_text()
    i = tex.index("\\label{fig:pdf_relay_matrix}")
    cap = tex[tex.rfind("\\caption{", 0, i):i]
    pat = re.compile(r"(?:^|[;:.])\s*([A-Z][\w\-~\. ]*?) writer and ([A-Z][\w\-~\. ]*?) reader (\d+)/(\d+) "
                     r"\((\d+)--(\d+)\\%\)", re.M)
    found = 0
    for m in pat.finditer(cap):
        found += 1
        w, rd = _model(m.group(1).replace("~", " ")), _model(m.group(2).replace("~", " "))
        k, n, lo_t, hi_t = map(int, m.groups()[2:])
        d = pc[(pc.pairing == "cross_model") & (pc.writer == w) & (pc.reader == rd)].iloc[0]
        lo, hi = wilson(d["executed"], d["n"])
        got = (int(d["executed"]), int(d["n"]), pct(lo), pct(hi))
        check(f"Fig 5 caption {LABEL[w]} -> {LABEL[rd]} (k, n, CI)", got == (k, n, lo_t, hi_t), got, (k, n, lo_t, hi_t))
        check(f"Fig 5 caption {LABEL[w]} -> {LABEL[rd]} Relayed = Persisted", d["relayed"] == d["persisted"],
              (int(d["persisted"]), int(d["relayed"])), "equal")
    check("Fig 5 caption lists all cross-model pairs", found == int((pc.pairing == "cross_model").sum()),
          found, int((pc.pairing == "cross_model").sum()))
    # Counts quoted in the text, recomputed from the logs
    norm = re.sub(r"\s+", " ", tex.replace("~", " "))
    for name, ok, phrase in text_facts():
        present = re.sub(r"\s+", " ", phrase) in norm
        check(f"text: {name}", ok and present, f"logs {'agree' if ok else 'DISAGREE'}, "
              f"phrase {'found' if present else 'MISSING'}", phrase[:70])
    lines.append(f"== {bad} mismatch(es) / log-table disagreement(s)")
    return "\n".join(lines), bad


if __name__ == "__main__":
    report, bad = verify()
    print(report)
