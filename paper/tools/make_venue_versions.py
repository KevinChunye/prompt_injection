#!/usr/bin/env python3
"""Generate anonymous venue versions of main.tex (full paper, no content changes).

  usenix_sec27/main.tex  USENIX Security '27 (two-column, usenix.sty, numeric refs)
  tmlr/main.tex          TMLR (single-column, tmlr.sty, author-year refs)

Usage (from paper/):  python3 tools/make_venue_versions.py
The body text, tables and numbers are copied from main.tex; only the wrapper
(class, title block, citations style, float widths, end matter) differs.
"""
import re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / "main.tex").read_text()

def between(a, b, s=src):
    i = s.index(a); j = s.index(b, i)
    return s[i:j]

macros = between("% Prevent bad mid-word breaks", "\\definecolor{codebg}")
abstract = between("\\begin{abstract}", "\\end{abstract}").replace("\\begin{abstract}\n\\noindent\n", "")
rel = abstract.index("Code and run logs are publicly")
abstract = abstract[:rel] + "Code and per-run logs are released; the link is withheld for anonymous\nreview.\n"
teaser_cap = between("\\captionof{figure}{", "  \\label{fig:teaser}")[len("\\captionof{figure}{"):].rstrip()
assert teaser_cap.endswith("}"); teaser_cap = teaser_cap[:-1]
body = between("\\section{Introduction}", "% -----------------------------------------------------------------------\n\\bibliographystyle")
impact = between("\\section{Broader Impact}", "% -----------------------------------------------------------------------\n\\section{Limitations}")
body = body.replace(impact, "")
impact_text = impact.split("\\label{sec:impact}\n", 1)[1].strip()
impact_text = re.sub(r"\n% -+\s*$", "", impact_text).strip()
appendix = between("\\section{Supplementary Results}", "\\end{document}")

TITLE = ("Kill-Chain Canaries: Stage-Level Tracking of Prompt Injection\\\\\n"
         "Across Attack Surfaces and Five Production LLMs")

def teaser(env):
    return ("\\begin{%s}[t]\n  \\centering\n"
            "  \\includegraphics[width=\\textwidth]{figures/figK1_same_score_different_story.pdf}\n"
            "  \\caption{%s}\n  \\label{fig:teaser}\n\\end{%s}\n\n" % (env, teaser_cap, env))

def insert_teaser(b, env):
    key = "We address this with a kill-chain canary methodology"
    assert b.count(key) == 1
    return b.replace(key, teaser(env) + key)

for needle in ("Haochuan", "Zechen", "mit.edu", "uchicago", "github.com", "KevinChunye", "kevinwhc"):
    assert needle not in body + appendix + abstract + impact_text, needle

# ---------------------------------------------------------------- USENIX
OPEN_SCIENCE = r"""
\section*{Open Science}

We release, through the anonymous link below, the artifacts needed to
evaluate and reproduce the results of this paper:
(i)~the \agentbench{} harness (agents, MemoryStore, ToolRegistry,
orchestrator and PropagationLogger), with the scenario definitions,
payloads and defense wrappers;
(ii)~the per-run logs of the 764 text-surface runs, one row per run, with
model, scenario, defense, batch, tool-call counts and the kill-chain stage
reached;
(iii)~the scripts that recompute every count quoted in the text and every
plotted cell from those logs and that draw the figures.
For the PDF relay experiment (186 runs) we release the scenario code and
the per-cell counts reported in Table~\ref{tab:pdf_same} and
Figure~\ref{fig:pdf_relay_matrix}; its per-run logs are not part of the
release.
Rerunning the experiments requires API access to the five evaluated models,
whose providers may change or retire the model versions we used.

\noindent Anonymous artifact link: \artifacturl
"""

usenix_appendix = (appendix.replace("\\begin{figure}[h]", "\\begin{figure*}[t]")
                   .replace("\\end{figure}", "\\end{figure*}")
                   .replace("\\begin{table}[h]", "\\begin{table*}[t]")
                   .replace("\\end{table}", "\\end{table*}"))

usenix = r"""%% Kill-Chain Canaries -- USENIX Security '27 anonymous submission.
%% Generated from ../main.tex by tools/make_venue_versions.py; edit there.
%% Compile: pdflatex main && bibtex main && pdflatex main && pdflatex main
\documentclass[letterpaper,twocolumn,10pt]{article}
\usepackage{usenix}
\usepackage{url}
\usepackage{booktabs}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{graphicx}
\usepackage{multirow}
\usepackage{array}
\usepackage{microtype}

% Anonymous artifact repository (https://anonymous.4open.science, conference
% ID SEC27).  REPLACE the placeholder before submitting.
\newcommand{\artifacturl}{\url{https://anonymous.4open.science/r/REPLACE-BEFORE-SUBMISSION}}

""" + macros + r"""
\begin{document}
\setlength{\emergencystretch}{3em}

\date{}
\title{\Large \bf """ + TITLE + r"""}
\author{{\rm Anonymous Author(s)}}
\maketitle

\begin{abstract}
""" + abstract + r"""\end{abstract}

""" + insert_teaser(body, "figure*") + r"""
% -----------------------------------------------------------------------
\section*{Ethical Considerations}

""" + impact_text + r"""
The models we tested are commercial products, but the behaviors we report
follow from attack techniques that are already public, and we report no
previously unknown vulnerability in a deployed product.
""" + OPEN_SCIENCE + r"""
\bibliographystyle{plain}
\bibliography{refs}

\appendix
\renewcommand{\thefigure}{A\arabic{figure}}
\renewcommand{\thetable}{A\arabic{table}}
\setcounter{figure}{0}
\setcounter{table}{0}
""" + usenix_appendix + r"""
\end{document}
"""

# ---------------------------------------------------------------- TMLR
def to_natbib(s):
    # "Name et al.~\cite{k}" / "Lynch~\cite{k}" -> \citet{k}; other \cite -> \citep
    s = re.sub(r"\b(?:[A-Z][a-z]+ et(?:\s|~)+al\.|Lynch)~\\cite\{([^}]+)\}", r"\\citet{\1}", s)
    return re.sub(r"~?\\cite\{", lambda m: (" " if m.group(0).startswith("~") else "") + "\\citep{", s)

def single_col(s):
    s = s.replace("figure*", "figure").replace("table*", "table")
    s = s.replace("\\includegraphics[width=\\columnwidth]", "\\includegraphics[width=0.55\\textwidth]")
    return s.replace("\\begin{figure}[h]", "\\begin{figure}[t]").replace("\\begin{table}[h]", "\\begin{table}[t]")

tmlr = r"""%% Kill-Chain Canaries -- TMLR anonymous submission.
%% Generated from ../main.tex by tools/make_venue_versions.py; edit there.
%% Compile: pdflatex main && bibtex main && pdflatex main && pdflatex main
\documentclass[10pt]{article}
\usepackage{tmlr}
\usepackage{hyperref}
\hypersetup{colorlinks=true,linkcolor=blue,citecolor=blue,urlcolor=blue}
\usepackage{url}
\usepackage{booktabs}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{graphicx}
\usepackage{multirow}
\usepackage{array}
\usepackage{microtype}

""" + macros + r"""
\title{""" + TITLE.replace("\\\\\n", " ") + r"""}

\author{\name Anonymous authors\\
      \addr Paper under double-blind review}

\newcommand{\fix}{\marginpar{FIX}}
\newcommand{\new}{\marginpar{NEW}}

\begin{document}

\maketitle

\begin{abstract}
""" + abstract + r"""\end{abstract}

""" + single_col(to_natbib(insert_teaser(body, "figure"))) + r"""
% -----------------------------------------------------------------------
\subsubsection*{Broader Impact Statement}

""" + to_natbib(impact_text) + r"""

\bibliography{refs}
\bibliographystyle{tmlr}

\appendix
\renewcommand{\thefigure}{A\arabic{figure}}
\renewcommand{\thetable}{A\arabic{table}}
\setcounter{figure}{0}
\setcounter{table}{0}
""" + single_col(to_natbib(appendix)) + r"""
\end{document}
"""

for name, tex in (("usenix_sec27", usenix), ("tmlr", tmlr)):
    d = ROOT / name
    (d / "figures").mkdir(parents=True, exist_ok=True)
    (d / "main.tex").write_text(tex)
    shutil.copy2(ROOT / "aaai27_laut" / "refs.bib", d / "refs.bib")
    for f in sorted((ROOT / "figures").glob("*.pdf")):
        shutil.copy2(f, d / "figures" / f.name)
    print("wrote", d / "main.tex")
