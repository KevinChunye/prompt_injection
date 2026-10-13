# TMLR — submission package and OpenReview form answers

Venue: Transactions on Machine Learning Research (https://jmlr.org/tmlr/). No fees. Rolling
submission on OpenReview: https://openreview.net/group?id=TMLR. Review is **double-blind**.
Requirements checked 2026-10-13 against jmlr.org/tmlr (author guide, submissions page,
editorial policies, FAQ), the live OpenReview submission invitation, and the official style
repo https://github.com/JmlrOrg/tmlr-style-file (commit `7bf90ef`).

## Files to upload

| Form field | File | Notes |
|---|---|---|
| **PDF** | `tmlr_submission.pdf` | Anonymous (`\usepackage{tmlr}`), unmodified TMLR style. 16 pages: main content pp. 1–12, references pp. 13–14, appendix pp. 15–16. |
| **Supplementary Material** (optional) | `tmlr_supplementary_anonymized.zip` (≈0.2 MB, limit 100 MB) | Benchmark code, analysis scripts, the per-run log (`runs.csv`), figure code, and a verifier that rechecks every number in the paper. All author names, the GitHub URL, the Hugging Face dataset name and the arXiv ID are removed (the build script fails if any remain). |

Source: `main.tex`, `references.bib`, `figures/`, and the unmodified `tmlr.sty`, `tmlr.bst`,
`fancyhdr.sty`. Build with `bash ../tools/build_all.sh`.

## Form fields (in OpenReview's order)

**Title** (max 250 chars)
```
Kill-Chain Canaries: Stage-Level Tracking of Prompt Injection Across Attack Surfaces and Five Production LLMs
```

**Abstract** (max 5000 chars; this is 1,792). Paste as is:
```
Multi-agent LLM systems now read documents, web pages and tool results on behalf of users, yet their resistance to prompt injection is usually reported as one number: did the attack succeed? We introduce a kill-chain canary method that plants a unique token in every injected payload and records the furthest of four stages it reaches (Exposed → Persisted → Relayed → Executed), across 950 runs, five production LLMs, six attack surfaces, and five defense conditions. Exposure was 100% among runs that called the tool; the outcomes differ downstream. Claude Haiku 4.5 and Claude Sonnet 4.5 executed none of their 164 text-surface attacks, and in the text relay the canary token never appeared in a memory write (0/40); GPT-4o-mini executed 53% of its attacks. Four findings follow. (1) A Claude writer kept the canary token out of shared memory in every relay run we report; one cross-model pairing (Claude writer, GPT-4o-mini reader, n=3) is consistent with this protecting the reader, and other pairings were not tested. (2) As readers, the Claude models executed 0/40 raw pre-seeded injections, but Claude Haiku 4.5 executed 2/3 injections relayed by GPT-4o-mini; whether relayed injections are harder to refuse than raw ones is an open question. (3) DeepSeek Chat went from 0/24 on pre-seeded memory to 8/8 on tool results, scenarios that also differ in task and payload format; white-text PDF payloads, invisible on the rendered page, succeeded at least as often as visible ones. (4) pi_detector and write_filter failed on channels they do not inspect, spotlighting failed on content it wraps, and write_filter blocked the PDF relay but not the text relay, a difference we cannot explain. Code and run logs are provided as anonymized supplementary material and will be publicly released.
```

**Authors / Authorids.** `Haochuan Kevin Wang`, `Zechen Zhang`. Add each author by OpenReview
profile ID (`~First_Last1`). Both authors need complete, active OpenReview profiles before you
submit. Only TMLR, the assigned editors and the authors can see this field. **Authors cannot be
added or removed after submission** (editorial policies), so finalize the list first.

**Submission Type.** Select **Regular submission (no more than 12 pages of main content)**.
Main content ends on page 12, and References start at the top of page 13. To fit 12 pages, two short
pieces moved to the appendix, with only their cross-references reworded: the audio and PDF-metadata
pilot section (former §4.9, now Appendix B) and the per-step drift table (now Table A2, next to
Figure A1, which plots it). If you add text, recheck the page count; past 12 pages, choose
"Long submission", which gets 4-week reviews instead of 2-week reviews.

**Supplementary Material.** Upload `tmlr_supplementary_anonymized.zip`. Reviewers and the public
can see it during and after review.

**Previous TMLR Submission URL / Changes Since Last Submission.** Leave both blank. This is a
first TMLR submission.

**Competing Interests** (required; enter `N/A` if none). Suggested answer, if true:
```
N/A
```
The paper evaluates models from OpenAI, Anthropic and DeepSeek. In the 36 months before
submission, did any author have employment, internships, stipends, consulting, honoraria, or
donated API or cloud credits from these or other relevant companies? If so, disclose it here
instead of N/A.

**Human Subjects Reporting** (required)
```
N/A. The study involves no human subjects: all experiments are automated runs of LLM agents in a sandboxed harness with synthetic data and no external network access.
```

## Right after submitting: recommend Action Editors

TMLR emails you a request to recommend **at least 3 Action Editors**. The deadline is usually
about a week. These current AEs list expertise that matches the paper (from
https://jmlr.org/tmlr/editorial-board.html, 2026-10-13). Check for conflicts of interest before
choosing:

- **Zhen Tan** (Stevens Institute of Technology): AI safety and security, LLMs, multi-agent systems. Best fit.
- **Pin-Yu Chen** (IBM): adversarial ML, ML and security, AI safety.
- **Jinghui Chen** (Penn State): LLM safety, adversarial ML.
- **Lichao Sun** (Lehigh): LLMs, trustworthy AI, security and privacy.
- **Sijia Liu** (Michigan State): adversarial ML, trustworthy AI.
- **Sanghyun Hong** (Oregon State): computer security and privacy, ML.
- **Muhao Chen** (UC Davis): robustness, AI safety.
- **Yali Du** (King's College London): LLM agents, robust ML.

## Before you click submit

- [ ] **Dual submission.** TMLR rejects papers that are "submitted in parallel at another archival,
      peer-reviewed venue". **Do not submit to TMLR and JAIR at the same time.** Pick one. Submit
      to the other only after a rejection or withdrawal. The arXiv preprint (2603.28013) is fine:
      TMLR allows preprints, as long as the submission does not link to them.
- [ ] **LLM-use disclosure.** The TMLR FAQ asks authors who used LLM tools to say so in a
      first-page footnote. If that applies, uncomment the `\llmdisclosure{...}` line after
      `\maketitle` in `main.tex`, edit the wording, and rebuild. The paper stays at 12 pages
      either way; this was tested.
- [ ] **Author quota.** TMLR limits submissions per author per year: about 3 papers per author for
      2-author papers under the current rule. Check both authors at
      https://www.cs.cmu.edu/~nihars/quota/author.html?rule=generalized&N1=2&A=9&NA=9.
      Desk-rejected papers count toward the quota.
- [ ] **AI review.** Since 2026, each submission also gets one advisory AI-generated soundness
      review, and you can respond to it.
- [ ] **Anonymity.** Checked: the PDF text and metadata contain no names, affiliations, emails,
      GitHub, Hugging Face or arXiv references, and neither does the supplement. Keep it that way
      in any OpenReview comments, and do not post the OpenReview link next to the arXiv version.

## After acceptance (camera-ready)

1. In `main.tex`, set `\def\month{MM}` (2 digits), `\def\year{YYYY}` and
   `\def\openreview{\url{https://openreview.net/forum?id=<ID>}}`.
2. Build the de-anonymized version: `bash ../tools/build_all.sh` writes
   `tmlr_camera_ready_preview.pdf`. That command uses `\usepackage[accepted]{tmlr}`, which prints
   the authors, "Published in Transactions on Machine Learning Research (MM/YYYY)", "Reviewed on
   OpenReview: …", and the GitHub footnote in the abstract. The preview in this folder still shows
   the MM/YYYY/XXXX placeholders.
3. Optional sections go after the Conclusion and before the References, as unnumbered
   `\subsubsection*`: Author Contributions, Acknowledgments. Make any revisions the AE requires.
4. Upload the PDF in the camera-ready revision on OpenReview. That form also takes an optional
   **code** link (https://github.com/KevinChunye/prompt_injection) and an optional **video** link.
5. If you replace the arXiv version, use `\usepackage[preprint]{tmlr}`.
