# JAIR: submission package and OJS form answers

**Venue.** Journal of Artificial Intelligence Research (https://www.jair.org/).
- No submission or publication fees; it is diamond open access, and articles are published under CC BY 4.0.
- Submissions are rolling, through the OJS wizard: https://jair.org/index.php/jair/submission/wizard (register first at https://jair.org/index.php/jair/user/register).
- Review is effectively single-blind: no page asks authors to anonymise, and the official class prints the author names.
- Receipt is acknowledged within 3 business days; otherwise email editors@jair.org.

**Sources checked on 2026-10-13:**
- jair.org/about/submissions, /formatting, /authorinstrs and /PublicationAgreement
- the JAIR Author Kit (`jair.cls` 2025/08/15 on `acmart` 2.12, template dated 2025-09-15), downloaded from https://www.jair.org/index.php/jair/libraryFiles/downloadPublic/6

## Files to upload

| Upload as | File | Notes |
|---|---|---|
| Article text (PDF) | `jair_submission.pdf` | Built with the unmodified JAIR class `\documentclass[manuscript, screen, review]{jair}` (line numbers, Libertine font, BibLaTeX `acmauthoryear`). The main text and Appendix A come first; Appendix B is the required **Reproducibility Checklist for JAIR**. Submissions without the checklist are desk rejected. |

You do not upload the source at submission time. It is in this folder: `main.tex`,
`reproducibility_checklist.tex`, `references.bib`, `figures/`, and the kit's `jair.cls`,
`acmart.cls`, `acmauthoryear.bbx`, `acmauthoryear.cbx` and `acmdatamodel.dbx`.
- Build both versions: `bash ../tools/build_all.sh`
- Or build by hand: `latexmk -pdf main` (this runs pdflatex, then biber, then pdflatex again).

**How this version was adapted to JAIR:**
- Every figure has the `\Description{}` alt text JAIR requires.
- Tables have captions above them and figures have captions below.
- There are no keywords and no ACM CCS concepts in the PDF.
- The class prints its CC BY notice.
- Sections 3 and 4 each gained one sentence before their first subsection, to follow the final-copy rule "do not start a section directly with a subsection".
- Otherwise the text and section structure match the arXiv v4 source. JAIR has no page limit, so nothing moved to the appendix.

## Step 1: Start

**Section:** **Articles**.

**Submission requirements:** tick all ten checkboxes. They are true for this paper on these two conditions:
- **Item 6, "not under review or published elsewhere".** This holds only if the paper is not submitted to TMLR, or any other venue, at the same time. Submit to one journal at a time. The arXiv preprint is not a publication, but disclose it in Question 3.
- **Item 2, the JAIR Open Access Publication Agreement.** Read the agreement before ticking.
  - The authors keep copyright and grant a non-exclusive license.
  - The article is published under CC BY 4.0.
  - Your arXiv version uses CC BY-NC-ND 4.0. Because you hold the copyright, you can still license the JAIR version under CC BY.

**Comments for the Editor:** paste the three answers below. JAIR requires all three, and submissions that do not answer them clearly are not considered.

> **1. Why is your work important to other researchers in AI, and how could they use your results? (≤150 words)**
>
> LLM agents now read untrusted documents, web pages and tool outputs and pass content to other agents, yet robustness to prompt injection is usually reported as one attack-success rate. We show that this number hides where an injection stops. Our kill-chain canary method plants a unique token in each payload and records whether it was exposed, persisted to shared memory, relayed to a second agent, or executed. Across 950 runs with five production LLMs, six attack surfaces and five defense conditions, models with the same outcome score stop injections at different stages, apparent safety depends on the injection channel evaluated, and three lightweight defenses fail on channels they do not inspect. Researchers can reuse the method (a regular expression over tool calls, usable with any API model), the released harness and per-run logs, and our reporting recommendations for agent security evaluations.
>
> *(141 words)*
>
> **2. 1–3 closest papers previously published in JAIR, and how this work differs (≤150 words)**
>
> (1) Lin et al. (2025), "Against The Achilles' Heel: A Survey on Red Teaming for Generative Models" (JAIR 82, doi:10.1613/jair.1.17654), surveys attack strategies and automatic red teaming, including risks around LLM-based agents. It is a survey; our paper is an empirical measurement study that introduces stage-level instrumentation for indirect prompt injection in multi-agent pipelines and reports new results for five production LLMs. (2) Plaat et al. (2025), "Agentic Large Language Models, a Survey" (JAIR 84, doi:10.1613/jair.1.18675), reviews LLMs that reason, act with tools and interact in multi-agent systems. We evaluate the security of exactly such tool-using, multi-agent pipelines, which that survey does not study empirically.
>
> *(105 words. Both papers were found via Crossref and checked on 2026-10-13. A search of JAIR's archive found no JAIR paper on prompt injection itself.)*
>
> **3. Prior publication / under review elsewhere / resubmission**
>
> No part of this paper has been published in, or accepted by, a peer-reviewed venue, and it is not under review elsewhere. A preprint of the same work is on arXiv (arXiv:2603.28013; latest version v4, 30 September 2026; not peer reviewed). This submission is that work formatted for JAIR. This is a first submission to JAIR, not a resubmission.

Before you submit, make sure Question 3 is still true: no TMLR or other submission in parallel.

## Step 2: Upload Submission

Upload `jair_submission.pdf` as the article text component. No other files are needed. The
code and data are public and are linked in the abstract.

## Step 3: Enter Metadata

**Title**
```
Kill-Chain Canaries: Stage-Level Tracking of Prompt Injection Across Attack Surfaces and Five Production LLMs
```

**Abstract** (1,785 characters, 281 words). JAIR renders the abstract as HTML, so this version uses plain text and no math:
```
Multi-agent LLM systems now read documents, web pages and tool results on behalf of users, yet their resistance to prompt injection is usually reported as one number: did the attack succeed? We introduce a kill-chain canary method that plants a unique token in every injected payload and records the furthest of four stages it reaches (Exposed → Persisted → Relayed → Executed), across 950 runs, five production LLMs, six attack surfaces, and five defense conditions. Exposure was 100% among runs that called the tool; the outcomes differ downstream. Claude Haiku 4.5 and Claude Sonnet 4.5 executed none of their 164 text-surface attacks, and in the text relay the canary token never appeared in a memory write (0/40); GPT-4o-mini executed 53% of its attacks. Four findings follow. (1) A Claude writer kept the canary token out of shared memory in every relay run we report; one cross-model pairing (Claude writer, GPT-4o-mini reader, n=3) is consistent with this protecting the reader, and other pairings were not tested. (2) As readers, the Claude models executed 0/40 raw pre-seeded injections, but Claude Haiku 4.5 executed 2/3 injections relayed by GPT-4o-mini; whether relayed injections are harder to refuse than raw ones is an open question. (3) DeepSeek Chat went from 0/24 on pre-seeded memory to 8/8 on tool results, scenarios that also differ in task and payload format; white-text PDF payloads, invisible on the rendered page, succeeded at least as often as visible ones. (4) pi_detector and write_filter failed on channels they do not inspect, spotlighting failed on content it wraps, and write_filter blocked the PDF relay but not the text relay, a difference we cannot explain. Code and run logs are publicly released at https://github.com/KevinChunye/prompt_injection.
```

**Contributors** (add each author separately)

| Given name | Family name | Email | Affiliation | Country | ORCID |
|---|---|---|---|---|---|
| Haochuan Kevin | Wang | hcw@mit.edu | Massachusetts Institute of Technology | United States | add yours (JAIR "highly recommends" it) |
| Zechen | Zhang | zechenz@uchicago.edu | University of Chicago | United States | add yours |

Mark one author as principal contact. If you add ORCIDs, also uncomment the `\orcid{...}` lines in
`main.tex` and rebuild, so that the PDF and the metadata match.

**Keywords** (free text in OJS; they must not appear in the PDF):
```
prompt injection; LLM security; agent safety; multi-agent systems; red-teaming
```

## Reproducibility checklist: review before submitting

The answers in `reproducibility_checklist.tex` (Appendix B of the PDF) come from the paper and
the repository. Please confirm these five, because only you can:

- **Code license.** The answer is "yes" because the README says MIT. The repository has no `LICENSE` file, though. Add one, or change the answer.
- **Cherry-picking: "yes".**
  - The released log has one batch (`high_n_v2`, 56 runs) marked `in_paper = False`, and the checklist explanation discloses it.
  - The only GPT-5-mini `permission_esc` success that Table A1 counts (1/36) comes from that batch. The figure README already lists this as a known log-versus-table disagreement.
  - If you excluded the batch on purpose, say why in the explanation.
- **Raw data: "partially".** The PDF relay is released only as per-cell counts, not per-run logs.
- **Data sets: "NA" for third-party data.**
  - In the code, the PDF relay and audio pilot runs do not parse real files. `cross_modal_relay.py` pre-loads the text that `parse_pdf` / `transcribe_audio` return. The white-text variant is emulated by placing the directive before the benign text.
  - The arXiv-PDF and LibriSpeech scripts in `datasets/` are not on that code path.
  - If some reported runs did use real PDF or audio files, change these answers. See also the note in `../README.md`.
- **Statistics: "no" for hypothesis tests.** The paper reports Wilson CIs instead, and the explanation says so.

## After acceptance (final copy, due within 2 months)

1. Build the final version with `\documentclass[]{jair}` (no line numbers, no checklist):
   `bash ../tools/build_all.sh` writes `jair_final_preview.pdf`.
2. In `main.tex`, fill in the values JAIR gives you:
   - `\JAIRAE{...}`, the Associate Editor
   - `\acmVolume`, `\acmArticle`, `\acmMonth`, `\acmYear`
   - `\acmDOI{10.1613/jair.1.<submission id>}`
   - `\received{...}` and `\received[accepted]{...}`
3. Add acknowledgments, if any, in `\begin{acks}...\end{acks}` before `\printbibliography`. Do not use a `\section` for them.
4. Upload the final PDF in the Copyediting stage under "Add a Discussion". Then, for production, upload:
   - the PDF
   - a zip of all source files: `bash ../tools/build_all.sh` writes `jair_source.zip`
5. If you update arXiv afterwards, add the JAIR volume, pages and DOI to its metadata.
