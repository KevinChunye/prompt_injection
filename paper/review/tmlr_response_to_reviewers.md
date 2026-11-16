# Response to reviewers — TMLR Paper13259 (draft)

We thank the three reviewers. Their central questions (what Executed measures, what each defense
sees, why the write filter differed between the two relays) led us to re-read the harness code and
the per-run log line by line. That audit found two errors in the submitted version, which we
correct in the revision and state here first.

## Two corrections that came out of the reviews

**1. Executed was over-counted in the two-agent text relays.** On text surfaces the submitted
version scored Executed as "the token is in the arguments of any tool call". That includes Agent
A's `write_memory` call, so in the text relay a memory write was labelled an execution. Executed is
now scored on outbound action arguments of the acting agent (`send_report`; Agent B's tool
arguments in the relays; an ADMIN call in `permission_esc`). The two rules agree in the
single-agent scenarios. The cells that change (Appendix C of the revision):

| Cell | Submitted | Revised |
|---|---|---|
| Text relay, GPT-4o-mini | 8/8 | 0/8 |
| Text relay, DeepSeek Chat | 8/8 | 0/8 |
| Text relay, GPT-5-mini | 3/20 | 1/20 |
| `multi_surface`, GPT-4o-mini | 4/4 | 1/4 |
| `permission_esc`, GPT-5-mini (now follows the released log) | 1/36 | 0/36 |
| Pooled ASR, GPT-4o-mini | 53% (32/60) | 35% (21/60) |
| Pooled ASR, DeepSeek Chat | 25% (17/68) | 13% (9/68) |
| Pooled ASR, GPT-5-mini | 3% (4/136) | 1% (1/136) |

The earlier counts are the Persisted counts of those cells. The Claude rows (0/80, 0/84), the
single-agent cells (including DeepSeek Chat's 0/24 and 8/8) and all PDF relay numbers are
unchanged.

**2. The defense conditions were described incorrectly.** In the released harness `pi_detector` is
a reminder appended to Agent A's system prompt in the PDF relay, not a classifier of outgoing
queries, and on text surfaces neither `pi_detector` nor `all` is connected to any mechanism. The 32
attacked text-surface runs under those two names are therefore no-defense runs. We withdraw the
statements that these conditions "failed on channels they do not inspect" and that all 64 defended
runs reached Executed, and we now describe each condition as implemented (new Table 2, Section 3.3,
Appendix B).

The same audit resolves the write-filter question all three reviewers raised: see R-all.4 below.

## Points raised by all reviewers

**R-all.1 Canary propagation versus instruction propagation (ZVwM; Vvus critical 3; P9yQ 1).**
We agree that the stages follow a marker. The revision (Section 3.2, "What the stages do and do
not measure"; new Table 1) now states, per scenario, what the payload asks for and what Executed
checks.
- In both relays the injected instruction is itself "include this exact token", so a summary
  without the token has not carried the instruction out and a reader cannot carry it out. Marker
  and instruction coincide there by construction.
- That is not true of `memory_poison` and `tool_poison`: their payloads name an attacker
  recipient, and Executed checks for the token in `send_report` arguments but not for the
  recipient.
- We could not do the requested comparison against semantic labels. The released log keeps stage
  flags and tool-call counts per run, not the text of memory writes or tool arguments. We say so
  and report no false-positive or false-negative rate (Limitations, first item).
- We removed language implying detection or protection ("filtered", "protecting the reader",
  "resistance") and describe results as locations of the token. Figure 1's caption says the same.
- Persisted and Executed are now defined on specific interfaces (committed memory content after any
  filter; outbound action arguments), and Section 3.1 states that all tools are mocks, so a stage
  means a call was issued and accepted, not that an effect occurred.

**R-all.2 Uncontrolled comparisons across surfaces (ZVwM; Vvus critical 2; P9yQ 4).** We did not
run matched experiments. We narrowed the claims instead: the DeepSeek Chat 0/24 versus 8/8 result
is presented as a difference between two scenarios whose payloads ask for different actions (a
separate `send_report` to an attacker address versus the token inside the report the task already
requires), the "channel-differentiated trust" explanation is removed, and the missing matched
comparison is named as an open question. The visible/white PDF comparison is no longer described
as "succeeded at least as often"; we state that the variants also differ in the position of the
directive in the extracted text, that three runs per cell cannot separate them, and that the PDF
relay is an extracted-text injection, not a test of visual understanding.

**R-all.3 Small cross-model cells (ZVwM; Vvus critical 1; P9yQ 4).** No new runs were added. The
cross-model observations are now labelled hypotheses for a larger study, the abstract and
conclusion say each rests on one pairing at n = 3, and "consistent with this protecting the
reader" is replaced by the mechanical statement that a reader cannot emit a token it never
received.

**R-all.4 The write-filter discrepancy (ZVwM; Vvus critical 4; P9yQ 5).** Resolved; there is no
discrepancy. In the text relay under `write_filter` (8 attacked runs), Agent A's `write_memory`
content contained the token in 8/8, the committed summary in 0/8, Agent B's `read_memory` result
in 0/8, and no run reached Executed. The filter stopped the token at the memory commit, as in the
PDF relay. The submitted version reported a failure only because of the scoring rule in correction
1. We also report an offline positive control of the filter on the payload templates, and we state
that the filter matches the canary pattern itself, so it is a control on the memory-commit
interface and not an evaluation of a detector. For the PDF relay we cannot report filter decisions
or committed content because its per-run logs are not in the release; we say so.

**R-all.5 Task success and ASR on the same runs; dual completion (ZVwM; Vvus 6; P9yQ 2).** Table 3
(formerly Table 1) is rebuilt on one population, the no-defense attacked runs: assigned runs,
exposed runs, ASR over each, task success on those same runs, and runs with both. Every run that
reached Executed also met the task proxy (21 GPT-4o-mini, 9 DeepSeek Chat, 1 GPT-5-mini). Clean
task success is reported separately, with the statement that the clean controls are not matched to
most attacked runs (one batch holds 252 of the 428 attacked runs, all 56 runs without a tool call,
and no clean controls), so no utility–security tradeoff is read from them. We also state that the
pooled rows are not like-for-like model scores, and that the task proxies are lenient.

## Reviewer P9yQ

- **2 (exposure-conditional ASR, tool-use failures).** Added to Table 3 and, per cell, to Table A1.
- **3 (experimental specification).** New Appendix B gives the system prompts, user tasks, payload
  templates, tool sets, API settings, stopping rule, error handling and defense implementations,
  with the files that define them, and a batch manifest (Table A2). Section 3.3 now states that
  each cell repeats one fixed task, document and payload template, that n counts repeated
  executions, and that the Wilson intervals describe run-to-run variation only. Two settings were
  misreported and are corrected: GPT-5-mini ran at the API default temperature (it rejects 0), and
  no 2048-token limit was set.
- **5 (spotlighting).** Results are attributed to the delimiter variant, and we note that
  datamarking and encoding were not tested.
- **6 (secondary claims).** The drift section is retitled and now concludes only that the tested
  classifier does not transfer across scenarios; the "accurate forensic signal" claim is removed
  and the dependence of the top feature on knowing when the token entered context is stated. The
  provenance result is scoped to 22 compromised runs with no benign cases and is no longer called
  a zero-false-attribution result. The statement that outcome-level monitoring misses dual
  completion is replaced: an endpoint evaluation that checks utility and unauthorized actions
  separately detects both; what the stages add is intermediate localization.
- **Non-critical 2 (contribution).** The contribution is restated as the stage decomposition and
  its empirical use, with the write-filter diagnosis as the worked example of a stage guiding a
  conclusion.
- **Non-critical 3 (accounting).** 950 = 764 + 186; the 20 pilot runs are additional and are now
  labelled so in the text, Figure 2's caption and the pilot table. Inapplicable stages per scenario
  are listed in Table 1.
- **Broader impact.** "No external network access" is replaced by an exact statement: tools are
  mocks, and the only external connections are the model API calls. We add that the null results
  are not deployment safety guarantees.

## Reviewer Vvus

- **5 (novelty).** New paragraph "Relation to existing instrumentation" in Related Work.
- **7 (generalizability).** Added to Limitations ("Single task family"): what the decomposition
  assumes about a pipeline and how checkpoints extend to longer workflows, with the statement that
  none of our observations is tested there.

## What we did not do

- No new model runs: no matched-task comparison across surfaces, no additional cross-model pairs,
  no larger PDF relay cells.
- No semantic annotation of trajectories, because the released logs do not contain them.

We believe the revised paper is the "carefully validated and more narrowly framed empirical
instrumentation paper" Reviewer P9yQ describes, with the first of those two adjectives still only
partly earned; we say so in the Limitations.
