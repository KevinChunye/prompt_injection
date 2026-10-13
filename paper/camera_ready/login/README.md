# USENIX ;login: — status and condensed article

## ;login: no longer accepts submissions

;login: Online has closed. As of 2026-10-13, these pages say so:

- **Writing guidelines page** (https://www.usenix.org/publications/loginonline/writing): "**;login: Online is no longer accepting new article submissions.** Please see the 2024 USENIX Annual Meeting Report for information about the conclusion of ;login: Online in 2025."
- **Main ;login: pages** (https://www.usenix.org/publications/login and /loginonline): "In 2025, ;login: Online concluded publication."
- **Last article.** The editor's farewell column ("Musings", Rik Farrow, 2 Oct 2025) is the last thing published. It says the USENIX Board decided that "having a magazine is not on purpose" for the organization.
- **Board minutes.** The April 2025 minutes record disbanding the ;login: committee. Minutes through August 2026 do not mention reviving it.

There is no form to fill in and no address that still accepts articles. Nothing in this folder can be submitted to ;login:.

## What is here anyway

The condensed article follows the last published ;login: guidelines, so you can reuse it for another practitioner venue.

**Files**

- `article.md`: the article source, about 1,850 words of body text, plus four figures and one short code listing.
- `login_article.pdf`: rendered manuscript.
- `login_article.docx`: Word version, which editors often ask for.
- `figures/*.png`: the four figures as separate raster files.
- `proposal.txt`: the plain-text proposal ;login: used to require. It answers their six questions: topic, type, audience, why now, non-text elements and length.
- `build.sh`: rebuilds the PDF and DOCX with pandoc.

**Format choices, following the old ;login: guidelines**

- Length: 2–5 magazine pages at about 600 words per page.
- Tone: conversational, not formal paper style.
- Figures: PNG or JPG, at least 1400 px wide.
- Proposals: plain text.
- Structure, taken from recent ;login: security articles:
  - a short teaser
  - an opening that names the source paper
  - 4–8 sections
  - "Conclusion: <takeaway>"
  - numbered references
  - third-person author bios

**Fill in before you use it**

- The author bios: replace `[ROLE]` and `[RESEARCH FOCUS]` with each author's actual position and research focus.
- Optionally, 138×138 headshots, if the venue uses them.

**Fact check.** Every number in the article comes from the paper, and it was checked against
`main.tex`. Where the paper qualifies a claim (n = 3, a single task family, untested
pairings), the article keeps the qualification.

## If you want a practitioner venue that is open

These are suggestions only. I have not checked their current calls, fees or review
models.

- **IEEE Security & Privacy** (magazine): practitioner-facing security articles.
- **ACM Queue** or **Communications of the ACM**, Practice section: pitch an editor.

Check each venue's dual-submission rules against the TMLR/JAIR submission. A magazine article
based on a published paper is usually fine once the paper is accepted, but not always while
it is under review.
