#!/usr/bin/env python3
"""Experiment 5 - Bigger array, faster chip? Not always.

The same 64 x 64 x 64 matrix multiply, tiled onto arrays of N = 2 ... 64.
Cycle counts come from TinyTPU's own timing rules (v1 and v2), which the
RTL is tested against at N = 2, 4, 8, 16 (make scale). The model is also
validated here against real Verilog runs at N = 4.
Question: when does doubling N stop paying off?
Output: experiments/results/e5_scaling.csv, diagrams/exp_scaling.svg
"""
import math
from common import *   # noqa: F401,F403
from svg import Svg, C

M = K = NOUT = 64


def cycles(N, version, M=M, K=K, NOUT=NOUT):
    """TinyTPU instruction timing, one LDW + one MMUL per weight tile."""
    tiles = math.ceil(K / N) * math.ceil(NOUT / N)
    ldw = 2 + N
    if version == "v1":
        mmul = 2 + M + 2 * N - 1
        return tiles * (ldw + mmul) + 3
    # v2: MMUL does not wait for the drain; LDW waits for the swap wave only
    # when the MMUL is shorter than 2N - 2 cycles; only the last drain shows.
    stall = max(0, (2 * N - 2) - (M + 2))
    return tiles * (ldw + 2 + M) + (tiles - 1) * stall + (2 * N - 1) + 3


# validate the formula against the real Verilog at N = 4 with a 16 x 16 x 16 case
import golden_model as g          # noqa: E402
import random                      # noqa: E402
r = random.Random(3)
prog = []
for ct in range(4):
    for kt in range(4):
        prog += [0x10000000 | ((kt * 16 + ct * 4) << 20), 0x20000000 | (kt * 16 << 20) | (16 << 12) | ((ct * 16) << 4) | (kt > 0)]
prog.append(0xF0000000)
g.run_and_write(os.path.join(WORK, "build"), prog, g.rand_mat(r, 256, 4, -8, 7), g.rand_mat(r, 256, 4, -8, 7))
for v, name in (("v1", "v1_simple"), ("v2", "v2_pipelined")):
    got, want = rtl_cycles(compile_rtl(name)), cycles(4, v, 16, 16, 16)
    print(f"  model check {name}: Verilog {got} cycles, formula {want} cycles")
    assert abs(got - want) <= 2, "timing model drifted from the RTL"

Ns = [2, 4, 8, 16, 32, 64]
rows = [(n, cycles(n, "v1"), cycles(n, "v2"), M * K * NOUT / (n * n * cycles(n, "v2"))) for n in Ns]
write_csv("e5_scaling.csv", ["N", "v1_cycles", "v2_cycles", "v2_utilization"],
          [(n, a, b, f"{u:.3f}") for n, a, b, u in rows])
s = Svg(1160, 600, "Experiment 5: bigger arrays hit diminishing returns",
        ["A fixed 64 x 64 x 64 matrix multiply on N x N arrays. Bars: cycles (log scale). Line: fraction of multipliers kept busy.",
         "The formula is checked against the Verilog first. Past N = 16, fill/drain and weight loading swamp the gain."])
x0, y0, H = 120, 520, 280
lo, hi = math.log10(min(r[2] for r in rows) / 2), math.log10(max(r[1] for r in rows) * 1.5)
Y = lambda v: y0 - (math.log10(v) - lo) / (hi - lo) * H
for d in range(math.ceil(lo), int(hi) + 1):
    s.line(x0, Y(10 ** d), 930, Y(10 ** d), C["line"], 1, dash="3 4")
    s.text(x0 - 10, Y(10 ** d) + 4, f"{10 ** d:,}", 11, C["muted"], anchor="end")
for i, (n, a, b, u) in enumerate(rows):
    x = x0 + 20 + i * 135
    for j, (v, col) in enumerate(((a, C["wt"]), (b, C["mxu"]))):
        s.rect(x + j * 44, Y(v), 40, y0 - Y(v), col, rx=3, opacity=0.9)
        s.text(x + j * 44 + 20, Y(v) - 6, f"{v:,}", 10, col, 700, "middle")
    s.text(x + 42, y0 + 20, f"N = {n}", 13, C["ink"], 700, "middle")
    s.text(x + 42, y0 + 36, f"{n * n:,} PEs", 11, C["muted"], anchor="middle")
pts = [(x0 + 62 + i * 135, 130 + (1 - u) * 100) for i, (_, _, _, u) in enumerate(rows)]
s.path("M" + " L".join(f"{a:.0f} {b:.0f}" for a, b in pts), C["out"], 3)
for (a, b), r in zip(pts, rows):
    s.circle(a, b, 6, C["out"], C["white"], 2)
    s.text(a + 10, b - 8, f"{r[3]:.0%} busy", 12, C["out"], 700)
s.legend(960, 250, [(C["wt"], "v1 cycles"), (C["mxu"], "v2 cycles"), (C["out"], "v2 utilization")], 170)
s.save(os.path.join(DIAG, "exp_scaling.svg"))
