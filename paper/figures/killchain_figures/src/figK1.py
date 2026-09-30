import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kc_common import *
W, H = 1400, 790
p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">', f'<rect width="{W}" height="{H}" fill="white"/>']
p.append(text_line(230, 52, [P("(a) Outcome-only scoring", INK, True)], 27, "middle"))
p.append(text_line(915, 52, [P("(b) The kill-chain canary", INK, True)], 27, "middle"))
p.append(f'<line x1="452" y1="28" x2="452" y2="640" stroke="#444" stroke-width="3" stroke-dasharray="12 9"/>')

rows = [(235, "Claude Haiku 4.5", 1), (500, "GPT-4o-mini", 3)]
for ry, name, reached in rows:
    # left panel
    p.append(robot(80, ry - 38, 38))
    p.append(text_line(132, ry - 46, [P(name, INK, True)], 23))
    p.append(text_line(132, ry - 16, [P("Agent A and B, visible-text PDF", "#666")], 20))
    p.append(f'<rect x="40" y="{ry+18}" width="372" height="64" rx="14" fill="#E8F5E9" stroke="#43A047" stroke-width="2.5"/>')
    p.append(text_line(62, ry + 60, [P("Attack success: 0/3", INK, True), P("  looks safe", "#2E7D32")], 22))
    p.append(check_badge(392, ry + 22, 17))
    # right panel pipeline
    y = ry - 20
    nodes = [530, 700, 880, 1060, 1240]
    cps = [615, 790, 970, 1150]
    p.append(text_line(482, ry - 95, [P(name + " as Agent A and B", "#555", True)], 20))
    for i in range(4):
        live = (i + 1) <= reached
        p.append(edge(nodes[i] + 38, nodes[i + 1] - 38, y, live))
    p.append(pdf_doc(nodes[0], y))
    p.append(robot(nodes[1], y - 4, 32))
    p.append(cylinder(nodes[2], y, token=(reached >= 2)))
    p.append(robot(nodes[3], y - 4, 32))
    p.append(envelope(nodes[4], y))
    for lab, x in zip(["PDF", "Agent A", "memory", "Agent B", "email out"], nodes):
        p.append(text_line(x, y + 62, [P(lab, "#444")], 20, "middle"))
    for i, x in enumerate(cps):
        n = i + 1
        p.append(checkpoint(x, y, n, reached=n <= reached, blocked=(n == reached + 1)))
    p.append(bird(cps[reached - 1] - 4, y - 48, 0.85))
    if reached == 1:
        verdict = [[P("Canary token absent from the memory write in 3/3 runs.", "#2E7D32", True)],
                   [P("Agent B never read the token.")]]
    else:
        verdict = [[P("Token reached shared memory and Agent B in 3/3 runs.", RED, True)],
                   [P("Only the last step held; the token stays in shared memory.")]]
    p.append(lines_block(482, y + 104, verdict, 21, maxw=880, tag=name))

# legend
p.append(f'<rect x="30" y="656" width="{W-60}" height="112" rx="16" fill="#F7F7F2" stroke="#CCCCCC" stroke-width="2"/>')
p.append(bird(90, 712, 0.8))
p.append(lines_block(126, 705, [[P("canary token", INK, True)], [P("SECRET-[A-F0-9]{8}", "#666")]], 20, maxw=200))
leg = [(1, "Exposed: in a tool result"), (2, "Persisted: in a memory write"), (3, "Relayed: read by Agent B"), (4, "Executed: in an outbound call")]
for i, (n, lab) in enumerate(leg):
    x = 380 + (i % 2) * 470
    y = 690 + (i // 2) * 46
    p.append(checkpoint(x, y, n))
    p.append(text_line(x + 30, y + 7, [P(lab)], 20))
p.append("</svg>")
render("figK1_same_score_different_story", p, W)
print("ok")
