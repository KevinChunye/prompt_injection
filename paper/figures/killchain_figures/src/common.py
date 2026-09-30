from PIL import ImageFont
from xml.sax.saxutils import escape

FONT = "Comic Neue"
from pathlib import Path as _P
import matplotlib as _mpl
_FONTS = _P(__file__).resolve().parent.parent / "fonts"
REG = str(_FONTS / "ComicNeue-Regular.ttf")
BOLD = str(_FONTS / "ComicNeue-Bold.ttf")
INK = "#2B2B2B"
RED = "#E53935"
GREEN = "#2E7D32"

SYM = str(_P(_mpl.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf")
ARROWS = "\u2192\u2190\u21c4\u2713\u2715"

def _split(t):
    out, buf = [], ""
    for ch in t:
        if ch in ARROWS:
            if buf: out.append((buf, False))
            out.append((ch, True)); buf = ""
        else:
            buf += ch
    if buf: out.append((buf, False))
    return out

def width(text, size, bold=False):
    total = 0
    for piece, sym in _split(text):
        path = SYM if sym else (BOLD if bold else REG)
        total += ImageFont.truetype(path, size).getlength(piece)
    return total

def seg_width(segs, size):
    return sum(width(t, size, b) for t, c, b in segs)

# K1 and K2 are 1400 px wide and printed at \textwidth (504 bp), i.e. 0.36 bp/px.
# 20 px is therefore 7.2 pt on paper; nothing may be set smaller.
MIN_PX = 20


def text_line(x, y, segs, size=22, anchor="start"):
    """segs: list of (text, color, bold)."""
    assert size >= MIN_PX, f"{size}px text prints below 7pt: {segs}"
    if anchor == "middle":
        x = x - seg_width(segs, size) / 2
    out = [f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" xml:space="preserve">']
    for t, c, b in segs:
        for piece, sym in _split(t):
            fam = ' font-family="DejaVu Sans"' if sym else ""
            out.append(f'<tspan fill="{c}"{fam} font-weight="{"bold" if b else "normal"}">{escape(piece)}</tspan>')
    out.append("</text>")
    return "".join(out)

def lines_block(x, y, lines, size=22, lh=None, anchor="start", maxw=None, tag=""):
    lh = lh or size * 1.32
    out = []
    for i, segs in enumerate(lines):
        if maxw is not None:
            w = seg_width(segs, size)
            assert w <= maxw, f"{tag}: line too wide ({w:.0f}>{maxw}): {''.join(s[0] for s in segs)}"
        out.append(text_line(x, y + i * lh, segs, size, anchor))
    return "\n".join(out)

def P(t, c=INK, b=False):
    return (t, c, b)

def user_avatar(cx, cy, r, uid, hair="#3A2C24", shirt="#7E9CC9", skin="#F2C8A2"):
    return f'''
<clipPath id="clip{uid}"><circle cx="{cx}" cy="{cy}" r="{r-2}"/></clipPath>
<circle cx="{cx}" cy="{cy}" r="{r}" fill="#F6EFE4" stroke="{INK}" stroke-width="2.5"/>
<g clip-path="url(#clip{uid})">
  <ellipse cx="{cx}" cy="{cy+r*0.92}" rx="{r*0.72}" ry="{r*0.52}" fill="{shirt}" stroke="{INK}" stroke-width="2"/>
  <rect x="{cx-r*0.12}" y="{cy+r*0.18}" width="{r*0.24}" height="{r*0.28}" fill="{skin}"/>
</g>
<circle cx="{cx}" cy="{cy-r*0.1}" r="{r*0.36}" fill="{skin}" stroke="{INK}" stroke-width="2"/>
<path d="M{cx-r*0.37},{cy-r*0.12} Q{cx-r*0.38},{cy-r*0.56} {cx},{cy-r*0.52} Q{cx+r*0.38},{cy-r*0.56} {cx+r*0.37},{cy-r*0.12} Q{cx+r*0.2},{cy-r*0.36} {cx-r*0.05},{cy-r*0.3} Q{cx-r*0.25},{cy-r*0.28} {cx-r*0.37},{cy-r*0.12} Z" fill="{hair}" stroke="{INK}" stroke-width="1.5"/>
<circle cx="{cx-r*0.13}" cy="{cy-r*0.08}" r="{r*0.095}" fill="none" stroke="{INK}" stroke-width="1.6"/>
<circle cx="{cx+r*0.13}" cy="{cy-r*0.08}" r="{r*0.095}" fill="none" stroke="{INK}" stroke-width="1.6"/>
<line x1="{cx-r*0.035}" y1="{cy-r*0.08}" x2="{cx+r*0.035}" y2="{cy-r*0.08}" stroke="{INK}" stroke-width="1.6"/>
<circle cx="{cx-r*0.13}" cy="{cy-r*0.08}" r="{r*0.03}" fill="{INK}"/>
<circle cx="{cx+r*0.13}" cy="{cy-r*0.08}" r="{r*0.03}" fill="{INK}"/>
<path d="M{cx-r*0.1},{cy+r*0.08} Q{cx},{cy+r*0.15} {cx+r*0.1},{cy+r*0.08}" fill="none" stroke="{INK}" stroke-width="1.6" stroke-linecap="round"/>
'''

def robot(cx, cy, r):
    return f'''
<circle cx="{cx}" cy="{cy}" r="{r}" fill="#DCEAF7" stroke="{INK}" stroke-width="2.5"/>
<line x1="{cx}" y1="{cy-r*0.5}" x2="{cx}" y2="{cy-r*0.72}" stroke="{INK}" stroke-width="2.5"/>
<circle cx="{cx}" cy="{cy-r*0.74}" r="{r*0.08}" fill="#EF6C6C" stroke="{INK}" stroke-width="1.5"/>
<rect x="{cx-r*0.66}" y="{cy-r*0.22}" width="{r*0.14}" height="{r*0.3}" rx="3" fill="#7FA7CF" stroke="{INK}" stroke-width="1.8"/>
<rect x="{cx+r*0.52}" y="{cy-r*0.22}" width="{r*0.14}" height="{r*0.3}" rx="3" fill="#7FA7CF" stroke="{INK}" stroke-width="1.8"/>
<rect x="{cx-r*0.54}" y="{cy-r*0.5}" width="{r*1.08}" height="{r*0.86}" rx="{r*0.22}" fill="#7FA7CF" stroke="{INK}" stroke-width="2.2"/>
<rect x="{cx-r*0.4}" y="{cy-r*0.36}" width="{r*0.8}" height="{r*0.52}" rx="{r*0.14}" fill="#22384E"/>
<circle cx="{cx-r*0.17}" cy="{cy-r*0.12}" r="{r*0.09}" fill="#7FE3F2"/>
<circle cx="{cx+r*0.17}" cy="{cy-r*0.12}" r="{r*0.09}" fill="#7FE3F2"/>
<path d="M{cx-r*0.14},{cy+r*0.04} Q{cx},{cy+r*0.12} {cx+r*0.14},{cy+r*0.04}" fill="none" stroke="#7FE3F2" stroke-width="2" stroke-linecap="round"/>
<path d="M{cx-r*0.5},{cy+r*0.86} Q{cx-r*0.5},{cy+r*0.42} {cx},{cy+r*0.42} Q{cx+r*0.5},{cy+r*0.42} {cx+r*0.5},{cy+r*0.86}" fill="#7FA7CF" stroke="{INK}" stroke-width="2"/>
'''

def bubble(x, y, w, h, fill, tail="right", ty=None):
    ty = ty if ty is not None else y + h / 2
    if tail == "right":
        t = f'<path d="M{x+w-4},{ty-14} L{x+w+26},{ty} L{x+w-4},{ty+14} Z" fill="{fill}"/>'
    else:
        t = f'<path d="M{x+4},{ty-14} L{x-26},{ty} L{x+4},{ty+14} Z" fill="{fill}"/>'
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="24" fill="{fill}"/>' + t

def check_badge(cx, cy, r=19):
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#43A047" stroke="white" stroke-width="3"/>'
            f'<path d="M{cx-r*0.45},{cy+r*0.02} L{cx-r*0.1},{cy+r*0.36} L{cx+r*0.5},{cy-r*0.34}" fill="none" stroke="white" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')

def warn_badge(cx, cy, r=19):
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#FB8C00" stroke="white" stroke-width="3"/>'
            f'<line x1="{cx}" y1="{cy-r*0.5}" x2="{cx}" y2="{cy+r*0.12}" stroke="white" stroke-width="4" stroke-linecap="round"/>'
            f'<circle cx="{cx}" cy="{cy+r*0.45}" r="2.8" fill="white"/>')

def wrench(x, y, s=1.0, color=INK):
    return (f'<g transform="translate({x},{y}) scale({s}) rotate(-45)">'
            f'<rect x="-3" y="-2" width="6" height="18" rx="3" fill="{color}"/>'
            f'<path d="M-8,-10 A9,9 0 1,0 8,-10 L4,-10 L4,-4 L-4,-4 L-4,-10 Z" fill="{color}"/></g>')

def tool_card(x, y, w, h, name, body, header_fill, state=None, slot=None, size=21, uid=""):
    out = []
    stroke, sw = ("#2E7D32", 5) if state == "chosen" else ("#4A4A4A", 2.5)
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="white" stroke="{stroke}" stroke-width="{sw}"/>')
    out.append(f'<clipPath id="hc{uid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16"/></clipPath>')
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="44" fill="{header_fill}" clip-path="url(#hc{uid})"/>')
    out.append(f'<line x1="{x}" y1="{y+44}" x2="{x+w}" y2="{y+44}" stroke="#4A4A4A" stroke-width="1.5"/>')
    out.append(wrench(x + 28, y + 24, 0.9))
    out.append(text_line(x + 48, y + 30, [P(name, INK, True)], 23))
    out.append(lines_block(x + 18, y + 80, body, size, maxw=w - 34, tag=name))
    if slot:
        out.append(text_line(x + w / 2, y - 12, [P(slot, "#666666", True)], 19, "middle"))
    if state == "chosen":
        out.append(check_badge(x + w - 8, y + 6))
    if state == "warn":
        out.append(warn_badge(x + w - 8, y + 6))
    return "\n".join(out)

def chip(x, y, w, h, lines, size=20):
    lh = size * 1.32
    top = y + (h - len(lines) * lh) / 2 + size * 0.85
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="#FFF6D5" stroke="#E0B000" stroke-width="2"/>'
            + lines_block(x + 22, top, lines, size, maxw=w - 40, tag="chip"))
