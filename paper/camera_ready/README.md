# Kill-Chain Canaries: venue packages (TMLR, JAIR, USENIX ;login:)

All three packages are built from `paper/main.tex`, which is the source of arXiv
2603.28013 v4. The venue requirements were checked on 2026-10-13 against each venue's
own pages and official style files.

| Venue | Status | Upload these | Form answers |
|---|---|---|---|
| **TMLR** (double-blind, OpenReview) | Ready to submit | `tmlr/tmlr_submission.pdf`, `tmlr/tmlr_supplementary_anonymized.zip` | [`tmlr/SUBMISSION_FORM.md`](tmlr/SUBMISSION_FORM.md) |
| **JAIR** (single-blind, OJS) | Ready to submit | `jair/jair_submission.pdf` | [`jair/SUBMISSION_FORM.md`](jair/SUBMISSION_FORM.md) |
| **USENIX ;login:** | **Closed.** It stopped accepting articles in 2025. | Nothing; there is nowhere to submit | [`login/README.md`](login/README.md) |

There is also a camera-ready version for each journal, for use after acceptance:
`tmlr/tmlr_camera_ready_preview.pdf` and `jair/jair_final_preview.pdf`. Each fills in
everything except the values the journal assigns, which stay as placeholders. JAIR's
production stage also needs `jair/jair_source.zip`.

## Decide first: TMLR or JAIR, not both at once

Both journals forbid parallel submission:
- TMLR does not accept work "submitted in parallel at another archival, peer-reviewed venue".
- JAIR's checklist requires "not under review … elsewhere".

The arXiv preprint is fine for both. Submit to one journal, and send it to the other only
after a rejection or withdrawal.

| | TMLR | JAIR |
|---|---|---|
| Format | 12-page main text ("Regular"); 2-week reviews | No page limit |
| Review model | Double-blind, plus an advisory AI review | Single-blind |
| Typical time to decision | About 9 weeks | 8–12 weeks to a first decision; about 42 weeks to acceptance |
| Fees | $0 | $0; published CC BY 4.0 |
| Extra work required | Recommend 3 or more Action Editors after submitting | A reproducibility checklist (already filled in, but review it) and three answers for the editor (drafted) |

## Rebuild and check everything

```
bash paper/camera_ready/tools/build_all.sh
```

The script needs TeX Live, plus biber for JAIR and pandoc for the ;login: article. It
builds every PDF from a clean copy of the sources and checks the following:

- Each PDF compiles with no LaTeX warnings and no overfull boxes. All fonts are embedded.
- The TMLR main content ends on page 12, and References start at the top of page 13.
- The TMLR PDF text and metadata contain no names, affiliations, emails, GitHub, Hugging
  Face or arXiv references. The supplement build fails if any survive.
- Both venue sources pass the repository's own number verifier
  (`figures/killchain_figures/src/paper_data.py`). Every table cell and every count quoted
  in the text is recomputed from the run log. Each source passes 66 checks, the same as the
  arXiv source, with the same 2 known flags (see below).

## What changed relative to arXiv v4

**Both venues**
- Each venue's official, unmodified style is used:
  - TMLR: `tmlr.sty` from JmlrOrg/tmlr-style-file `7bf90ef`.
  - JAIR: the Author Kit's `jair.cls` 2025/08/15, built on `acmart` 2.12.
- Layout is single-column. The teaser moved from the title block to Figure 1 at the start
  of the Introduction.
- Citations are author-year, as both styles require:
  - TMLR: natbib with `tmlr.bst`.
  - JAIR: BibLaTeX `acmauthoryear`.
  - Citations that name the authors use `\citet`.
- The bibliography is now a verified `.bib` file. These entries were corrected against
  arXiv, Crossref, ACL Anthology, Springer, USENIX and CEUR records:
  - Greshake et al.: the title ends "…Indirect Prompt **Injection**", not "Injections". Added
    all six authors, pages 79–90 and the DOI.
  - Lee, Tiwari et al., *Prompt Infection*: now published at SECAI 2025 (ESORICS
    workshops, LNCS 16232). The published version adds a third author, **Brando Miranda**.
  - Nasr et al.: now published at **USENIX Security 2026**, pp. 1467–1486. Added all 14
    authors.
  - Hines et al. (spotlighting): now published at **CAMLIS 2024**, CEUR-WS Vol-3920.
  - Hutchins et al.: the venue is "6th International Conference on Information Warfare and
    Security (ICIW 2011)", pp. 113–125.
  - All other entries: added full author lists, DOIs and pages where they exist.
- I removed a local list-spacing override, since both venues forbid layout tweaks.

**TMLR only**
- Anonymized. The authors and the GitHub footnote are switched off unless the camera-ready
  build is used.
- Two short pieces moved to the appendix to fit the 12-page "Regular" limit:
  - the n = 4 audio and PDF-metadata pilot section, now Appendix B;
  - the per-step drift table, now Table A2, next to Figure A1, which plots it.
  Only the cross-references were reworded.
- An optional first-page LLM-use disclosure line is included but switched off. See the form guide.

**JAIR only**
- The JAIR front matter: short title, `\shortauthors`, CC BY notice, and Associate Editor
  and DOI placeholders.
- `\Description` alt text for every figure, which JAIR requires.
- One lead-in sentence for §3 and for §4. JAIR's final-copy rules say not to start a
  section directly with a subsection.
- Appendix B: the mandatory reproducibility checklist. It is compiled into the submission
  and dropped from the final copy.

## For the authors: issues found but not changed

I left these alone because they change content, which is your call:

1. **How the PDF relay is described.**
   - In the released code, the PDF relay and audio pilot runs do not parse real files.
     `agent_bench/scenarios/cross_modal_relay.py` pre-loads the text that `parse_pdf` and
     `transcribe_audio` return. The white-text variant is emulated by putting the
     directive before the benign text.
   - The paper describes it as a "1 pt white-text overlay" that is "extracted first by
     `pypdf`". That matches `datasets/inject_pdfs.py`, which is not on the relay's code
     path.
   - Reviewers who read the supplementary code may ask about this. Consider one sentence
     in §3.2 or §4.8 saying that the relay feeds the extracted text directly.
2. **Table 1, DeepSeek Chat CI.** The Wilson 95% CI for 17/68 is 16–**36**%; the table
   prints 16–37%. This is already listed in `figures/killchain_figures/README.md`.
3. **Table A1, GPT-5-mini `permission_esc`.** The table says 1/36. The `in_paper` rows of
   the log give 0/36. The only success is in batch `high_n_v2` (`in_paper = False`), and
   Table 1's 3% (4/136) follows the table. This is a known flag; please resolve it before
   journal review.
4. **No `LICENSE` file in the repository.** The README says MIT, and JAIR's checklist
   answers assume it. Add the file.
5. **Figure A1(b).** The closing parenthesis of the x-axis label "…5-fold CV)" is clipped
   at the right edge. To fix it, shorten the label in `src/fig_drift.py` (line 77) and
   rebuild the figures.
6. **ORCID iDs.** JAIR "highly recommends" them. There are commented `\orcid{}` lines in
   `jair/main.tex`.
