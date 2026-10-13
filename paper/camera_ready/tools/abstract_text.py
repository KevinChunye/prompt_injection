"""Print the paper's abstract as plain text for a submission form.
Usage: python tools/abstract_text.py <main.tex> [--anon]"""
import re, sys
from pathlib import Path
t = Path(sys.argv[1]).read_text()
a = t[t.index("\\begin{abstract}") + 16:t.index("\\end{abstract}")]
anon = "--anon" in sys.argv
# keep one branch of \ifanonymous ... \else ... \fi
m = re.search(r"\\ifanonymous(.*?)\\else(.*?)\\fi", a, re.S)
if m:
    a = a.replace(m.group(0), m.group(1) if anon else m.group(2))
macros = dict(re.findall(r"\\urldef\{\\(\w+)\}\\path[{|]([^}|]*)[}|]", t))
a = re.sub(r"\\footnote\{\\url\{([^}]*)\}\}", r" (\1)", a)
a = re.sub(r"\\url\{([^}]*)\}", r"\1", a)
a = re.sub(r"\\(\w+)\{\}", lambda m: macros.get(m.group(1), m.group(0)), a)
a = a.replace("\\noindent", "").replace("~", " ").replace("\\%", "%").replace("---", "—")
a = a.replace("$\\to$", "→").replace("$n=3$", "n=3")
a = " ".join(a.split())
assert "\\" not in a, a
print(a)
print(f"\n[{len(a)} characters, {len(a.split())} words]", file=sys.stderr)
