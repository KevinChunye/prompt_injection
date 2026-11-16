# AAAI-27 LAUT workshop submission

Anonymous, AAAI two-column version of `../main.tex` for the AAAI-27 workshop
*LLM Agents Under Threat in Cyberspace* (deadline 2026-11-20 AoE, OpenReview).

- `main.pdf`: the file to upload. 8 pages: 7 pages of content, references on page 8.
- Build: `bash build.sh` (pdflatex + bibtex; needs `newtx` fonts).
- `aaai2027.sty` / `aaai2027.bst`: unmodified, from the official AuthorKit27.

Content is condensed from `../main.tex` and carries the same corrections as the TMLR revision
(action-level Executed, defense conditions described as implemented; see `../review/tmlr_response_to_reviewers.md`).

Changes from the arXiv version:
- AAAI-27 style with the `submission` option; authors, affiliations, emails and the repository URL removed.
- References moved to `refs.bib` (author-year, `aaai2027.bst`).
- Figure 1 and Figure 2 are cropped with `trim` (stage legend / summary boxes, whose content is in the captions and text).
- Removed to fit 7 pages: the last-stage figure, the text-relay table (now a sentence in Section 4.2),
  the per-step drift table, the pilot table, the appendix (heatmap table and drift figure), and the
  four-finding recap in the conclusion. Sections 4.5-4.7 of the arXiv version are merged into Section 4.6.
- "Broader Impact" became the "Ethical Statement".
