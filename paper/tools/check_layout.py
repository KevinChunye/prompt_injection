"""PDF layout audit for the two-column paper.

Flags
  * any word whose bounding box crosses the page margin,
  * any word in single-column text that crosses into the column gutter,
  * any image, rule or vector graphic that extends past its column or the
    page edge,
  * (with --fonts) any text span set below --min-pt at print size, including
    text inside included figures.

Usage:  python tools/check_layout.py main.pdf [--fonts] [--min-pt 7]
Needs:  pip install pdfplumber pymupdf

Geometry follows icml2025.sty: letter paper, 0.75in side margins, 1in top and
bottom, 0.25in column separation.  microtype hangs punctuation (hyphens,
commas, periods, quotes) slightly into the margin on purpose; those characters
are stripped from the ends of a word before its extent is measured, so only
letters, digits and code characters count as overflow.
"""
import argparse
import sys

import pdfplumber

PAGE_W, PAGE_H = 612.0, 792.0
LEFT, RIGHT = 54.0, PAGE_W - 54.0            # 0.75in side margins
TOP, BOTTOM = 72.0, PAGE_H - 72.0            # 1in top/bottom
COLSEP = 18.0                                 # 0.25in
COL_W = (RIGHT - LEFT - COLSEP) / 2           # 243bp
GUT_L, GUT_R = LEFT + COL_W, LEFT + COL_W + COLSEP   # 297 .. 315
MID = (GUT_L + GUT_R) / 2
TOL = 1.0                                     # bp slack for glyph side bearings
TRAIL_HANG = set(",.;:-–—)]}'\"’”!?")
LEAD_HANG = set("([{'\"“‘")   # a line-initial hyphen is a defect, not hanging


def core_extent(word):
    """x-extent of a word without the punctuation microtype may hang."""
    chars = word["chars"]
    i, j = 0, len(chars)
    while i < j and chars[i]["text"] in LEAD_HANG:
        i += 1
    while j > i and chars[j - 1]["text"] in TRAIL_HANG:
        j -= 1
    if i == j:
        return None
    return min(c["x0"] for c in chars[i:j]), max(c["x1"] for c in chars[i:j])


def rows_of(words):
    rows = {}
    for w in words:
        rows.setdefault(round(w["bottom"]), []).append(w)
    return sorted((sorted(r, key=lambda w: w["x0"]) for r in rows.values()),
                  key=lambda r: r[0]["top"])


def full_width_top(page, rows):
    """figure* and table* floats sit at the top of a page (the page-1 teaser
    sits under the title block).  Return the y down to which the page is
    full-width material: the lowest full-width caption row ("Figure"/"Table"
    rows that run through the gutter) or graphic wider than one column."""
    def spans_gutter(r):
        """Row text runs through the gutter with ordinary word spacing (a
        two-column row leaves a gap of at least ~16bp there)."""
        if not any(w["x1"] <= MID for w in r) or not any(w["x0"] >= MID for w in r):
            return False
        if any(w["x0"] < MID - 3 and w["x1"] > MID + 3 for w in r):
            return True
        gaps = [b["x0"] - a["x1"] for a, b in zip(r, r[1:])
                if b["x0"] > GUT_L - 2 and a["x1"] < GUT_R + 2]
        return bool(gaps) and max(gaps) < 10
    # a one-column page (e.g. the appendix): most text rows run through the gutter
    long_rows = [r for r in rows if len(r) >= 4]
    if long_rows and sum(spans_gutter(r) for r in long_rows) >= 0.5 * len(long_rows):
        return PAGE_H
    bottom = 0.0
    for obj in page.images + page.rects + page.curves + page.lines:
        if obj["x1"] - obj["x0"] > COL_W + COLSEP:
            bottom = max(bottom, obj["bottom"])
    in_block = True            # rows at the very top: title block (page 1)
    in_caption = False
    for r in rows:
        span = spans_gutter(r)
        if in_block and span:
            bottom = max(bottom, max(w["bottom"] for w in r))
            continue
        in_block = False
        if r[0]["text"].startswith(("Figure", "Table")) and span:
            in_caption = True
        elif not span:
            in_caption = False
        if in_caption:
            bottom = max(bottom, max(w["bottom"] for w in r))
    return bottom


def audit(path):
    problems = []
    with pdfplumber.open(path) as pdf:
        for pno, page in enumerate(pdf.pages, start=1):
            words = [w for w in page.extract_words(x_tolerance=1.0, return_chars=True)
                     if w["top"] < BOTTOM + 2]          # skip footer page number
            rows = rows_of(words)
            fw_bottom = full_width_top(page, rows)
            for w in words:
                ext = core_extent(w)
                if ext is None:
                    continue
                x0, x1 = ext
                if x0 < LEFT - TOL or x1 > RIGHT + TOL:
                    problems.append((pno, "text-page-margin", w["text"], x0, x1, w["top"]))
                elif x1 > GUT_L + TOL and x0 < GUT_R - TOL and w["bottom"] > fw_bottom + 2:
                    problems.append((pno, "text-gutter", w["text"], x0, x1, w["top"]))
            for obj in page.images + page.rects + page.curves + page.lines:
                x0, x1 = obj["x0"], obj["x1"]
                if obj["top"] > BOTTOM + 2:
                    continue
                if x0 < LEFT - TOL or x1 > RIGHT + TOL:
                    problems.append((pno, "graphic-page-edge", obj["object_type"], x0, x1, obj["top"]))
                elif (x1 - x0 <= COL_W + COLSEP and x1 > GUT_L + TOL and x0 < GUT_R - TOL
                      and obj["bottom"] > fw_bottom + 2):
                    problems.append((pno, "graphic-gutter", obj["object_type"], x0, x1, obj["top"]))
    return problems


def small_text(path, min_pt):
    """Effective size of every text span, after any figure scaling."""
    import pymupdf
    out = []
    for pno, page in enumerate(pymupdf.open(path), start=1):
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    t = span["text"].strip()
                    if t and span["size"] < min_pt - 0.05:
                        marker = t.isdigit() and len(t) <= 2      # footnote mark in body text
                        out.append((pno, span["size"], span["font"], t[:70], span["bbox"], marker))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--min-pt", type=float, default=7.0)
    ap.add_argument("--fonts", action="store_true", help="also list text below --min-pt")
    a = ap.parse_args()
    probs = audit(a.pdf)
    print(f"== geometry: column {COL_W:.0f}bp, gutter {GUT_L:.0f}-{GUT_R:.0f}bp, "
          f"text block {LEFT:.0f}-{RIGHT:.0f}bp, tolerance {TOL}bp")
    for p in probs:
        print(f"p{p[0]:>2} {p[1]:<18} x0={p[3]:7.2f} x1={p[4]:7.2f} top={p[5]:7.2f}  {p[2]!r}")
    print(f"== {len(probs)} layout problem(s)")
    bad = 0
    if a.fonts:
        sm = small_text(a.pdf, a.min_pt)
        for s in sm:
            tag = "footnote mark" if s[5] else "TOO SMALL"
            print(f"p{s[0]:>2} {s[1]:5.2f}pt {s[2]:<24} y={s[4][1]:6.1f} {tag:<13} {s[3]!r}")
        bad = sum(1 for s in sm if not s[5])
        print(f"== {bad} text span(s) below {a.min_pt}pt (footnote marks listed, not counted)")
    sys.exit(1 if (probs or bad) else 0)
