"""Numbers behind the data figures, read from the result files.

Text-surface cells (Tables 1-3) are computed from data/runs.csv, the per-run
log released with the paper (Hugging Face dataset kevinwhc/kill-chain-canaries,
rows with in_paper == True).  PDF-relay cells (Tables 5-6) come from
data/pdf_relay_cells.csv: the per-run logs of that experiment are not in the
code repository or the dataset, so that file holds the per-cell counts of
Tables 5 and 6 (arXiv 2603.28013v3).

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

# Cells where the typeset table and the released log disagree.  The figure
# follows the table so the paper stays self-consistent; verify() reports each
# one so the authors can reconcile it.  Delete an entry to plot the log value.
TABLE_OVERRIDES = {
    ("permission_esc", "gpt-5-mini"): {
        "k": 1,
        "why": "Table 3 reports 1/36; in_paper rows of runs.csv give 0/36. The only GPT-5-mini "
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
    for r in table_rows("tab:pdf_cross"):
        w, rd = _model(r[0]), _model(r[1])
        want = tuple(int(x.rstrip("%")) for x in r[2:5])
        mm = re.match(r"(\d+)-(\d+)%", r[5])
        d = pc[(pc.pairing == "cross_model") & (pc.writer == w) & (pc.reader == rd)].iloc[0]
        got = tuple(pct(d[c] / d["n"]) for c in ["persisted", "relayed", "executed"])
        lo, hi = wilson(d["executed"], d["n"])
        check(f"Table 6 {LABEL[w]} -> {LABEL[rd]} (Per, Rel, Exe %)", got == want, got, want)
        check(f"Table 6 {LABEL[w]} -> {LABEL[rd]} Exe CI", (pct(lo), pct(hi)) == tuple(map(int, mm.groups())),
              (pct(lo), pct(hi)), r[5])
    lines.append(f"== {bad} mismatch(es) / log-table disagreement(s)")
    return "\n".join(lines), bad


if __name__ == "__main__":
    report, bad = verify()
    print(report)
