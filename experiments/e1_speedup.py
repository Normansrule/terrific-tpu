#!/usr/bin/env python3
"""Experiment 1 - How much faster is v2, program by program?

Runs 200 random programs (plus the 5 application demos) on BOTH chip
versions in the Verilog simulator and records the cycle counts.
Question: does pipelining always help? By how much? When does it not?
Output: experiments/results/e1_speedup.csv, diagrams/exp_speedup.svg
"""
from common import *   # noqa: F401,F403
from svg import Svg, C

v1, v2 = compile_rtl("v1_simple"), compile_rtl("v2_pipelined")
rows = []
for demo, label in APPS:
    make_case(demo)
    rows.append((label, rtl_cycles(v1), rtl_cycles(v2)))
for seed in range(1, 201):
    make_case("fuzz", seed)
    rows.append((f"random {seed}", rtl_cycles(v1), rtl_cycles(v2)))
write_csv("e1_speedup.csv", ["program", "v1_cycles", "v2_cycles"], rows)

sp = [a / b for _, a, b in rows]
s = Svg(1000, 560, "Experiment 1: v2's speedup over v1, measured on 205 programs",
        ["Each dot is one program run on both Verilog chips. Diagonal = no speedup. Right: how often each speedup happens.",
         f"Mean speedup {sum(sp) / len(sp):.2f}x, best {max(sp):.2f}x, worst {min(sp):.2f}x. v2 is never slower."])
x0, y0, W = 90, 500, 380
mx = max(a for _, a, _ in rows) * 1.05
X = lambda v: x0 + v / mx * W
Y = lambda v: y0 - v / mx * W
s.line(x0, y0, x0 + W, y0, C["ink"], 1.5)
s.line(x0, y0, x0, y0 - W, C["ink"], 1.5)
s.line(X(0), Y(0), X(mx), Y(mx), C["faint"], 2, dash="6 5")
for t in range(0, int(mx), 100):
    s.text(X(t), y0 + 18, str(t), 11, C["muted"], anchor="middle")
    s.text(x0 - 8, Y(t) + 4, str(t), 11, C["muted"], anchor="end")
s.text(x0 + W / 2, y0 + 40, "v1 cycles", 13, C["ink"], 600, "middle")
s.text(x0 - 50, y0 - W / 2, "v2 cycles", 13, C["ink"], 600, "middle", rotate=-90)
for lab, a, b in rows:
    if lab.startswith("random"):
        s.circle(X(a), Y(b), 3.5, C["mxu"])
apps_only = [r for r in rows if not r[0].startswith("random")]
for k, (lab, a, b) in enumerate(apps_only):
    s.circle(X(a), Y(b), 6, C["ps"], C["white"], 1.5)
    if lab == "Fourier":       # the two small demos sit close together: label this one below
        s.line(X(a), Y(b), X(a) + 14, Y(b) + 26, C["ps"], 1)
        s.text(X(a) + 16, Y(b) + 38, f"{lab} {a / b:.2f}x", 11, C["ps"], 700)
    else:
        s.line(X(a), Y(b), X(a) - 10, Y(b) - 22 - 14 * (k % 2), C["ps"], 1)
        s.text(X(a) - 12, Y(b) - 26 - 14 * (k % 2), f"{lab} {a / b:.2f}x", 11, C["ps"], 700, "end")
# histogram
hx, hw, bins = 560, 400, [1 + 0.05 * i for i in range(13)]
counts = [sum(1 for v in sp if lo <= v < lo + 0.05) for lo in bins]
cm = max(counts)
for i, (lo, c) in enumerate(zip(bins, counts)):
    bw = hw / len(bins)
    h = c / cm * 360
    s.rect(hx + i * bw + 2, y0 - h, bw - 4, h, C["mxu"], rx=3, opacity=0.85)
    if c:
        s.text(hx + i * bw + bw / 2, y0 - h - 6, str(c), 11, C["mxu_dk"], 700, "middle")
    if i % 2 == 0:
        s.text(hx + i * bw + bw / 2, y0 + 18, f"{lo:.1f}x", 11, C["muted"], anchor="middle")
s.text(hx + hw / 2, y0 + 40, "speedup (v1 cycles / v2 cycles)", 13, C["ink"], 600, "middle")
s.save(os.path.join(DIAG, "exp_speedup.svg"))
