import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *
OUT = Path(__file__).resolve().parent.parent / "output"
OUT.mkdir(exist_ok=True)

YEL = "#F6C945"
TAINT = "#E65100"

def bird(cx, cy, s=1.0):
    return f'''<g transform="translate({cx},{cy}) scale({s})">
<path d="M-20,-2 L-36,-11 L-33,7 Z" fill="{YEL}" stroke="{INK}" stroke-width="2" stroke-linejoin="round"/>
<ellipse cx="0" cy="0" rx="22" ry="15" fill="{YEL}" stroke="{INK}" stroke-width="2"/>
<circle cx="16" cy="-12" r="11" fill="{YEL}" stroke="{INK}" stroke-width="2"/>
<path d="M25,-15 L36,-11 L25,-7 Z" fill="#F57C00" stroke="{INK}" stroke-width="1.5" stroke-linejoin="round"/>
<circle cx="19" cy="-14" r="2.2" fill="{INK}"/>
<path d="M-9,-3 Q1,6 9,-4" fill="none" stroke="{INK}" stroke-width="2" stroke-linecap="round"/>
<line x1="-4" y1="14" x2="-6" y2="22" stroke="{INK}" stroke-width="2"/><line x1="4" y1="14" x2="6" y2="22" stroke="{INK}" stroke-width="2"/>
</g>'''

def pdf_doc(cx, cy, w=58, h=74):
    x0, y0 = cx - w / 2, cy - h / 2
    c = 15
    lines = "".join(f'<line x1="{x0+9}" y1="{y0+22+i*11}" x2="{x0+w-9}" y2="{y0+22+i*11}" stroke="#9E9E9E" stroke-width="2.5" stroke-linecap="round"/>' for i in range(4))
    return (f'<path d="M{x0},{y0} H{x0+w-c} L{x0+w},{y0+c} V{y0+h} H{x0} Z" fill="white" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round"/>'
            f'<path d="M{x0+w-c},{y0} V{y0+c} H{x0+w}" fill="none" stroke="{INK}" stroke-width="2"/>' + lines +
            f'<rect x="{x0+8}" y="{y0+h-18}" width="{w-16}" height="10" rx="3" fill="{YEL}" stroke="{RED}" stroke-width="1.5"/>')

def cylinder(cx, cy, rx=44, ry=12, h=70, fill="#E8EAF6", token=False):
    top, bot = cy - h / 2, cy + h / 2
    s = (f'<path d="M{cx-rx},{top} V{bot} A{rx},{ry} 0 0,0 {cx+rx},{bot} V{top}" fill="{fill}" stroke="{INK}" stroke-width="2.5"/>'
         f'<ellipse cx="{cx}" cy="{top}" rx="{rx}" ry="{ry}" fill="#F5F6FC" stroke="{INK}" stroke-width="2.5"/>')
    if token:
        s += f'<rect x="{cx-22}" y="{cy+2}" width="44" height="14" rx="4" fill="{YEL}" stroke="{RED}" stroke-width="2"/>'
    return s

def envelope(cx, cy, w=66, h=46):
    x0, y0 = cx - w / 2, cy - h / 2
    return (f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" rx="5" fill="white" stroke="{INK}" stroke-width="2.5"/>'
            f'<path d="M{x0+2},{y0+3} L{cx},{cy+4} L{x0+w-2},{y0+3}" fill="none" stroke="{INK}" stroke-width="2.2" stroke-linejoin="round"/>')

def checkpoint(cx, cy, n, reached=True, blocked=False, r=19):
    if reached:
        s = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{YEL}" stroke="{INK}" stroke-width="2.5"/>'
        s += text_line(cx, cy + 7, [P(str(n), INK, True)], 20, "middle")
    else:
        s = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="white" stroke="#9E9E9E" stroke-width="2.5"/>'
        s += text_line(cx, cy + 7, [P(str(n), "#9E9E9E", True)], 20, "middle")
    if blocked:
        d = r * 0.95
        s += (f'<line x1="{cx-d}" y1="{cy-d}" x2="{cx+d}" y2="{cy+d}" stroke="{RED}" stroke-width="5" stroke-linecap="round"/>'
              f'<line x1="{cx-d}" y1="{cy+d}" x2="{cx+d}" y2="{cy-d}" stroke="{RED}" stroke-width="5" stroke-linecap="round"/>')
    return s

def edge(x1, x2, y, live=True):
    if live:
        return f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{TAINT}" stroke-width="5" stroke-linecap="round"/>'
    return f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="#BDBDBD" stroke-width="4" stroke-dasharray="9 8" stroke-linecap="round"/>'

def shield(cx, cy, s=1.0, fill="#7E57C2"):
    return (f'<g transform="translate({cx},{cy}) scale({s})"><path d="M0,-20 L16,-13 V1 Q16,15 0,23 Q-16,15 -16,1 V-13 Z" fill="{fill}" stroke="{INK}" stroke-width="2.2" stroke-linejoin="round"/>'
            f'<path d="M-7,1 L-2,7 L8,-5" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></g>')

def render(name, parts, w):
    import cairosvg
    svg = OUT / f"{name}.svg"
    svg.write_text("\n".join(parts))
    cairosvg.svg2png(url=str(svg), write_to=str(OUT / f"{name}.png"), output_width=w)
    cairosvg.svg2pdf(url=str(svg), write_to=str(OUT / f"{name}.pdf"))
