# Kill-Chain Canaries: format and content revision (from arXiv v3)

Base: arXiv 2603.28013v3 source (`main.tex`, `icml2025.sty`, figures).
Build: `cd figures/killchain_figures && python build_all.py`, then `pdflatex main` three times.
Output: `main.pdf` (12 pages; v3 was 10). `review/diff_vs_v3.pdf` marks every text change
(deleted text small and red, added text blue; floats show the new version only).

The constraint was: no new runs, no new analyses, no changed numbers. Every number in the
paper is unchanged from v3. The places where v3's numbers do not reproduce from the released
logs are listed in section 6 and were **not** edited.

---

## 1. Claims reworded (old → new)

The same wording is used in the abstract, the introduction's contributions and the
conclusion's four findings.

| # | Where | Old (v3) | New |
|---|---|---|---|
| B1 | Abstract, §4.1, Table 1 caption, Conclusion | "every model is fully exposed"; "every model receives every injection: exposure rate is 100% across all 764 attacked runs. The safety gap is entirely downstream of context exposure"; "In our evaluation, exposure = 100% for all models" | "Exposure is 100% by design, because the payload sits in a tool result the agent must read; the outcomes differ downstream." §4.1 adds "Every attacked run that made a tool call was exposed; runs that made none are discussed in Section 7." (v3's "764 attacked runs" counted the 256 clean controls too.) |
| B2 | Abstract, §4.1, Discussion, Conclusion | "Claude blocks all injections at memory-write (0/164 ASR)"; "Claude's 0/164 ASR ... reflects safety behavior that activates at the summarization stage" | "Claude Haiku 4.5 and Claude Sonnet 4.5 executed none of their 164 text-surface attacks, and in the text relay the canary token never appeared in a memory write (0/40)." |
| B3 | Intro | "the injection was stripped at write_memory ... the summarizer is a decontamination stage" | "the injection never reached the memory write ... the summarizer dropped the injected text" |
| B3 | §4.2 | "Claude eliminates the injection during write_memory ... Agent B receives a semantically correct but adversarially clean summary"; "A Claude relay decontaminates for any downstream consumer" | "the canary token never appeared in a Claude memory write: 0/40 runs ... Agent B then read a summary that did not contain the token"; the decontamination sentence is replaced by the B4 claim |
| B3 | §4.8 | "Claude eliminates every injection at the Persisted stage" | "With Claude as both agents, the canary token was absent from every memory write" |
| B3 | Discussion, Conclusion | "relay decontamination rate" as a mandatory metric; "pipeline-wide decontamination" | "the rate at which the canary token is absent from memory writes"; "results at the write and read positions separately" |
| B3 | Figures | K1 "Stopped at the memory write ... Shared memory stays clean for any later reader"; K5 "clean memory" / "tainted memory"; K3 "Stopped at the memory write" | K1 "Canary token absent from the memory write in 3/3 runs. Agent B never read the token."; K5 "Persisted 0/3" / "Persisted 3/3"; K3 "Exposed only (no token in the memory write)" |
| B3 | Limitations (new) | none | "The canary token tracks copying of the payload marker. A paraphrased instruction could survive a memory write without it, so a token absent from memory does not show that the instruction is absent." |
| B4 | Abstract (1), Contribution (2), §4.2, Discussion, Finding 1 | "routing writes through a verified model eliminates propagation"; "write-node placement is the only position where this protection materializes"; "0/46 canaries ... independent of which model serves as Agent B"; "Operators can harden pipelines today by requiring safety-certified models at every inter-agent write boundary" | "A Claude writer kept the canary token out of shared memory in every relay run we report (40 text relay, 12 same-model and 3 cross-model PDF relay runs). One cross-model pairing (Claude writer, GPT-4o-mini reader, n = 3) is consistent with this protecting the reader; other pairings were not tested." See the note on "46" below. |
| B5 | Abstract (2), Contribution (3), §4.8 Observation 1, Discussion, Finding 2, Related Work (Lynch), K5/Fig 6 caption | "Claude's defense is write-time only"; "Claude's write-stage defense does not extend to read-stage resistance"; "Claude's defense fires at write, not at read"; "Claude blocks at write, propagates at read" | "As a reader, Claude executed 0/40 raw pre-seeded injections but 2/3 injections relayed by GPT-4o-mini; whether relayed injections are harder to refuse than raw ones is an open question." Observation 1 adds that the two settings also differ in payload wording and task. |
| B6 | Abstract (3), Contribution (4), §4.3, Fig 5 caption, Discussion, Finding 3 | "DeepSeek exhibits 0%/100% across surfaces"; "single-surface evaluation produces a complete mischaracterization"; "The most parsimonious explanation is channel-differentiated trust" | "DeepSeek Chat went from 0/24 on pre-seeded memory to 8/8 on tool results, scenarios that also differ in task and payload format." §4.3: "the swing cannot be attributed to the channel alone. One possible explanation is channel-differentiated trust ..." (stated once). Checked in the code: `memory_poison` and `tool_poison` use different task prompts and payload templates. |
| B7 | Abstract (4), Contribution (5), §4.4, §4.8, Finding 4, Related Work (Nasr) | "all four defenses fail on at least one surface due to channel mismatch alone, no adversarial adaptation required"; "none of those threat models cover the injection surface under test"; "write_filter is the only mechanism that blocks at the correct stage ... across all evaluated injection surfaces"; "non-adaptive attacks can achieve the same result via surface mismatch alone" | "Each defense failed on at least one channel outside the one it inspects, and write_filter blocked the PDF relay but not the text relay, a difference we cannot explain." §4.4 adds that write_filter and spotlighting also failed on the text relay, whose content both cover. |
| B8 | Title, abstract, intro, §3.3, Limitations | "frontier LLMs"; title "... Across Attack Surfaces and Model Safety Tiers" | "five production LLMs"; title "... Across Attack Surfaces and Five Production LLMs" ("safety tiers" was never defined, so it was dropped) |
| B8 | Everywhere (7 places) | "Phase 3", "Block A", "Block B" | "PDF relay experiment", "same-model pairs", "cross-model pairs" |
| B8 | Abstract, intro, conclusion | Finance: 2 sentences in the abstract, a 4-sentence intro paragraph, a conclusion paragraph | One sentence in the introduction; removed from the abstract and conclusion |
| B9 | Abstract, contributions, conclusion | Three differently-worded finding lists | One list: headline measurement plus Findings 1–4 (writer position, reader position, channel dependence, defense coverage), worded identically in all three places |

**Note on "46".** The request asked for "a Claude writer kept the token out of shared memory
in all 46 relay runs". The paper's tables list 55 Claude-writer relay runs with Persisted = 0:
40 text relay (Table 2), 12 same-model PDF relay (Table 5) and 3 cross-model (Table 6). I could
not rebuild 46 from them (v3's own Conclusion used 0/12 PDF runs, which gives 52), so the text
cites the table counts. If 46 is a deliberate subset, it changes in four places: abstract (1),
Contribution (2), §4.2, Finding 1.

### Other claims corrected where v3 contradicted its own logs or code (no numbers changed)

- **Table 1 "Task" column.** The v3 caption said no-defense attacked runs, and the text said
  "90% attacked-task success". The released logs reproduce the column only as task success on
  clean-control runs (all defense conditions), e.g. GPT-4o-mini 79/88 = 90% and GPT-5-mini
  34/36 = 94%. That also matches the v3 Fig 2(a) axis label. The caption and text now say
  clean runs.
- **Table 1 footnote / Table 7 / §4.9.** v3 said the 16 runs in Table 1 but not Table 3 were
  audio and `pdf_metadata` pilots. In `runs.csv` they are the 16 `multi_surface` runs
  (4 GPT-4o-mini, all executed; 8 GPT-5-mini; 4 Claude Sonnet 4.5). GPT-4o-mini's 32/60 = 53%
  needs those four successes. The footnote now names `multi_surface`; Table 7's caption now
  says the pilots are *not* part of Tables 1 and 3; and the §4.9 sentence claiming they explain
  the 428-vs-412 gap was removed.
- **Drift violins (v3 Fig 6, now Fig A1c).** The legend said "Clean (no injection)", but
  `scripts/generate_figures.py` draws only attacked runs, split by harmful action. The caption
  claims "Claude's attacked distribution is nearly identical to its clean baseline" and
  "GPT-4o-mini and DeepSeek shift substantially upward when attacked" were removed. Claude has
  no harmful-action violin, and GPT-4o-mini's harmful-run median sits below its non-harmful one.
- **Spotlighting.** v3 said spotlighting wraps "tool results in `<document>` XML delimiters" and
  that it failed because "our injection enters via the function-call response stream". In the
  code it wraps exactly the injected content (web page, search result or memory note in `<<< >>>`;
  `<document>` in the PDF relay). The description now matches the code, and the false mechanism
  sentence is gone.
- **Table 3 caption.** "Bolded cells replicated at n ≥ 20" was untrue (bold cells included n = 8).
  The bold was removed.
- **Nasr et al.** ">90% ASR against 12/12 defenses" → "bypass all 12 defenses they evaluate, most
  with attack success above 90%" (their abstract says "above 90% for most").
- **Zombie Agents.** The related-work sentence now describes the actual paper (see bibliography).
- Results no longer carry future-work phrasing ("further validation is required",
  "pending larger replication", "hypotheses for larger-scale follow-up"). Open questions now
  appear only in Limitations and the Conclusion.

---

## 2. Figures

| v3 | New | Data source | Placement |
|---|---|---|---|
| — | **K1** teaser (Fig 1) | Table 5 (same-model PDF relay, `pdf_append`) | page 1, full width inside the title block (`\captionof`), so it lands on page 1 |
| Fig 1 architecture | **K2** setup (Fig 2) | design counts (§3.3) | `figure*` |
| Fig 2 (a)+(b) | **Fig 3** = panel (a) only | Table 1 values computed from `runs.csv` | single column. Replotted, not cropped: a crop at column width prints the legend at about 5.6 pt |
| Figs 3 and 8 | **K3** (Fig 4) | `runs.csv` (Table 2) + Table 5 | `figure*` |
| Fig 4 heatmap | **K4** (Fig 5) | `runs.csv` (Table 3) + Table 5 | `figure*` |
| Fig 9 cross-model | **K5** (Fig 6) | Tables 5 and 6 | single column |
| Figs 5, 6, 7 (drift) | **Fig A1** (appendix, 3 panels) | (a) Table 4; (b) values printed on v3 Fig 7; (c) v3 raster plot area with vector axes and a corrected legend | one-column appendix page |

- `src/paper_data.py` reads the result files and checks every plotted cell against the tables
  typeset in `main.tex`. Result: **52 checks pass, 2 disagreements** (section 6), both reported
  in `figures/killchain_figures/output/verification.txt`.
- The PDF relay per-run logs are not in the repository or the HF dataset, so the PDF cells come
  from `data/pdf_relay_cells.csv`, transcribed from Tables 5 and 6.
- Captions now state what is plotted, n per cell, and the source table.

---

## 3. Unfinished-looking text (C)

- Searched source, captions, footnotes, tables and bibliography for: TODO, TBD, FIXME, XXX,
  verify, in progress, pending, rerun, re-run, we will, will be, to appear, placeholder, draft,
  `[KEVIN`, `??`, `[?]`, follow-up. The only remaining matches are "appending" and "blocked".
- v3 never contained "TODO: verify final venue" or "same-protocol reruns are in progress", so
  there was nothing to delete. Table 1's columns do come from different run sets, and a plain
  Limitations sentence now says so ("Run provenance"). Nothing implies pending work.
- GPT-5-mini footnote: now a plain list of the API identifiers used (the long IDs moved out of
  running text).
- Bibliography, each checked against arXiv:
  - [3] Perez & Ribeiro: now cites the NeurIPS ML Safety Workshop 2022.
  - [4] AgentDojo: NeurIPS Datasets and Benchmarks Track.
  - [5] InjecAgent: full authors; Findings of ACL 2024.
  - [6] Prompt Infection: authors are **D. Lee and M. Tiwari** (v3: S. Lee and A. Tiwari).
  - [7] Zombie Agents: v3 had the **wrong authors and title** ("R. Shi et al., ... Persistent
    memory poisoning attacks on long-context LLM agents", 2025). Correct: X. Yang, Y. He, S. Ji,
    B. Hooi, J. S. Dong, "Zombie Agents: Persistent Control of Self-Evolving LLM Agents via
    Self-Reinforcing Injections", Lifelong Agent Workshop @ ICLR 2026, arXiv:2602.15654. The
    year now matches the arXiv ID.
  - [8] Now "The Attacker Moves Second: Stronger Adaptive Attacks Bypass Defenses against LLM
    Jailbreaks and Prompt Injections", Nasr, Carlini, Sitawarin, Schulhoff, Hayes, Ilie et al.,
    arXiv:2510.09023, 2025.
  - [12] "Architecturing" → "Architecting".
  - [13] Title is "Covert Visual Prompt Injection against Commercial Multimodal Large Language
    Models".
  - [14] "on" → "with" real-world tools; FSE 2026 Ideas, Visions and Reflections track.
  - [15] Title completed ("... in Large Language Models").
  - [16] PhD thesis, UCL, 2025.

---

## 4. Overflow fixes (D)

Before, on v3 as compiled here (10 pages):

| # | Page | Log | PDF check (pdfplumber) | Fix |
|---|---|---|---|---|
| 1 | p3, right column (defense list, v3 lines 337–343) | Overfull \hbox 7.10 pt | `write_filter` runs to x = 565.4 bp, 7.4 bp into the right margin | All code literals are now `\urldef`/`\path` macros that can break after `_ . @ / , =`; the defense list was reworded. Now on p3 of the new PDF, no overflow |
| 2 | p3, left column (model list, v3 line 318) | not reported (below \hfuzz) | a line starts with `-2024-07-18),`, 3 bp into the left margin, from `gpt-4o-mini\allowbreak-2024-07-18` | API identifiers moved to a footnote (p3, footnote 2), never broken |

Found and fixed while revising (new PDF):

| # | Page | Log | Fix |
|---|---|---|---|
| 3 | p3, left column (`memory_poison` description) | Overfull 54.92 pt: `\texttt{MemoryStore.seed()}` in Courier | `\path{MemoryStore.seed()}` plus rewording so it no longer starts the line |
| 4 | p5, Table 3 | Overfull 6.98 pt (Courier scenario headers) | Table transposed (rows = models, like Fig 5), stacked headers, `\tabcolsep` 2 pt |

Also:
- Tables 5 and 6 (6 and 9 columns) became one `table*`.
- The Table 1 note moved from a caption `\footnotemark` to an ordinary footnote, and the §4.1
  title was shortened, which removed a half-empty column on p4.
- All `\FloatBarrier`s were removed; they left large gaps on pp. 3–6 once the full-width
  figures were larger.
- No global `\sloppy`. The existing `\emergencystretch 3em` is unchanged.

After: **0 overfull boxes** in `main.log`. `tools/check_layout.py main.pdf` reports
**0 words or graphics** crossing the gutter or a page margin, and **0 text spans below 7 pt**.
The only spans below 7 pt are four body-text footnote markers at 5.98 pt, which the checker
lists separately. The checker still flags both v3 spots on the v3 PDF.

---

## 5. Checklist

| | Item | Status |
|---|---|---|
| A1 | Figure zip unzipped into `figures/`; K3–K5 read `data/runs.csv` / `data/pdf_relay_cells.csv`; every value checked against Tables 2, 3, 5, 6 (and 1) | PASS: 52/52 cells match the typeset tables; 2 log-vs-table disagreements reported, not hidden (§6) |
| A2 | K1 page-1 teaser; K2 replaces Fig 1; K3 replaces Figs 3 and 8; K4 replaces Fig 4; K5 replaces Fig 9; Fig 2 keeps panel (a) only; Figs 5–7 merged into one appendix figure | PASS. K1 is full width inside the title block rather than a floating `figure*`, since a `figure*` cannot land on page 1. Fig 2(a) was replotted from the same values instead of cropped (7 pt rule) |
| A3 | Captions state what is plotted, n per cell, source table; every figure and table referenced in the body text in order; numbers in the text match the figures | PASS. Body-text first references run Fig 1–6 and Table 1–7 in order; the appendix figure is numbered A1. Figure captions cite source tables, as required. The one gap: Fig A1(c) per-violin n was never retained, and the caption says so |
| A4 | No figure text under 7 pt at print size; nothing past a column or page edge | PASS: figures drawn at print width (7.0 in / 3.375 in); smallest figure text is 7.2 pt; layout check 0 problems |
| B | Claims reworded as specified | PASS, with the "46" note and the extra corrections in §1 |
| C1–C5 | Unfinished text, Table 1 caption, bibliography, future work only in Limitations and Conclusion, GPT-5-mini footnote | PASS |
| D1 | Overfull >0.5 pt list plus pdfplumber gutter and margin check | PASS: before 1 overfull + 2 PDF hits; after 0 and 0 |
| D2 | Long literals fixed with `\path`/`\urldef`, footnotes, rewording; no `\sloppy` | PASS |
| D3 | Tables fit their column or are `table*`; no float covers a column | PASS |
| D4 | Every page rendered to PNG and both column edges inspected | PASS (12 pages at 100 dpi) |
| E1 | Abstract numbers equal results numbers | PASS: 950, 164, 0/40, 53%, n = 3, 0/40, 2/3, 0/24, 8/8 all appear in §3.3–§4.9 and Tables 1–6 |
| E2 | Model, stage and scenario names spelled the same everywhere | PASS: scripted check found no "DeepSeek" without "Chat", no bare "Haiku"/"Sonnet", no EXE/PER/REL/EXP, no `mem_poison`/`perm_esc`, no Phase/Block; figures use the same labels |
| E3 | No undefined references or citations | PASS: `main.log` has 0 warnings, 0 undefined refs, 0 undefined citations; every `\cite` key has a `\bibitem` and every `\bibitem` is cited |

---

## 6. For the authors: numbers that do not reproduce from the released logs (left unchanged)

Checked against `runs.csv` (HF `kevinwhc/kill-chain-canaries`, `in_paper == True`). None of
these were edited, because the brief said no changed numbers.

1. **GPT-5-mini `permission_esc`**: Table 3 says 1/36, the logs give 0/36. The only GPT-5-mini
   `permission_esc` success is in `high_n_v2`, the post-paper batch. This also drives Table 1's
   GPT-5-mini 3% (1–7%) (logs: 3/136 = 2%, 1–6%) and "2/132" (logs: 1/132). The figures follow
   the table through `TABLE_OVERRIDES` in `src/paper_data.py`.
2. **Confidence intervals**: DeepSeek Chat 17/68 is Wilson 16–36% (Table 1 says 16–37%); 0/40 is
   0–9% (§4.2 says 0–8%); 0/6 is 0–39% (§4.8 says 0–46%).
3. **"764 text-surface runs across 9 batches"**: the 764 `in_paper` runs come from 8 batches;
   the 9th (`high_n_v2`) is not in the paper.
4. **Zero-tool-call runs**: 56 of the 428 no-defense attacked runs (48 GPT-5-mini, 4 DeepSeek
   Chat, 4 GPT-4o-mini, all in `high_n_v1`) made no tool call and were never exposed, but count
   in the ASR denominators. A Limitations sentence now says so. `high_n_v2` looks like a re-run
   of exactly these cells.
5. **Text relay "Executed"**: Table 2's Executed is `attack_succeeded`, which scans every logged
   tool call's arguments. The logs' Agent-B outbound flag (`canary_in_b_outbound`) is 0/8
   (GPT-4o-mini), 0/8 (DeepSeek Chat) and 1/20 (GPT-5-mini). If `write_memory` calls are in the
   scanned log, Executed equals Persisted by construction in the text relay. Worth checking
   before resubmission.
6. **GPT-5-mini identifier** `gpt-5-mini-2025-02-15`: the footnote now states it plainly. Please
   confirm it is the identifier the API returned.
7. §4.8 "0/6 GPT-4o-mini `pdf_whitefont`" under `write_filter`, with n = 3 per cell. Presumably
   two cells; kept as written.
