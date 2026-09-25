#!/usr/bin/env python3
"""Experiment 2 - How many bits does a neural network really need?

A 2-layer network with real-valued weights is quantized to b bits
(b = 2..8), run through TinyTPU's exact integer semantics (the
instruction-level model, which the RTL is proven to match), and compared
with the same network in floating point on 500 random inputs.
Metrics: relative output error, and how often the int and float networks
pick the same winning output ("top-1 agreement").

It runs every width twice: with an ideal rescale ("any shift") and with
TinyTPU's real ACT instruction, whose shift field is only 3 bits (0..7).
The gap between the two is a genuine hardware finding: full-range 8-bit
data needs a bigger rescale than 3 bits allow, which is why real TPUs
rescale with a 32-bit multiplier instead of a small shift.
Output: experiments/results/e2_quantization.csv, diagrams/exp_quantization.svg
"""
import random
from common import *   # noqa: F401,F403
from svg import Svg, C
from tpu_isa_sim import TinyTPU, requant  # noqa: F401

rng = random.Random(7)
W1 = [[rng.gauss(0, 0.5) for _ in range(4)] for _ in range(8)]
W2 = [[rng.gauss(0, 0.5) for _ in range(4)] for _ in range(4)]
X = [[rng.uniform(-1, 1) for _ in range(8)] for _ in range(500)]


def fmm(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(len(B))) for j in range(len(B[0]))] for i in range(len(A))]


Hf = [[max(0.0, v) for v in r] for r in fmm(X, W1)]
Yf = fmm(Hf, W2)


def q(M, bits, scale):
    lim = 2 ** (bits - 1) - 1
    return [[max(-lim, min(lim, round(v / scale))) for v in r] for r in M]


def run_int(bits, max_shift=99):
    lim = 2 ** (bits - 1) - 1
    sx = 1.0 / lim
    s1 = max(abs(v) for r in W1 for v in r) / lim
    s2 = max(abs(v) for r in W2 for v in r) / lim
    Xq, W1q, W2q = q(X, bits, sx), q(W1, bits, s1), q(W2, bits, s2)
    # choose shifts so layer outputs use the available range (a compiler's job)
    acc1 = fmm(Xq, W1q)
    peak1 = max(max(0, v) for r in acc1 for v in r)
    sh1 = min(max_shift, max(0, (peak1 // lim).bit_length()))
    H = [[min(lim, max(0, v) >> sh1) for v in r] for r in acc1]
    acc2 = fmm(H, W2q)
    scale_out = sx * s1 * (2 ** sh1) * s2
    Y = [[v * scale_out for v in r] for r in acc2]
    # cross-check the first batch of 8 against TinyTPU's instruction semantics
    if bits == 8 and max_shift == 7:
        t = TinyTPU(4)
        prog = [0x10000000, 0x20008000, 0x10400000, 0x20808001, 0x10800000,
                0x30008100 | (sh1 << 1) | 1, 0x21008080, 0xF0000000]
        for i in range(4):
            t.wmem[i], t.wmem[4 + i], t.wmem[8 + i] = W1q[i], W1q[4 + i], W2q[i]
        for i in range(8):
            t.ub[i], t.ub[8 + i] = Xq[i][:4], Xq[i][4:]
        t.run(prog)
        assert t.acc[8:16] == acc2[:8], "integer path disagrees with TinyTPU semantics"
    err = sum(abs(a - b) for ra, rb in zip(Y, Yf) for a, b in zip(ra, rb)) / \
        sum(abs(b) for rb in Yf for b in rb)
    agree = sum(1 for ra, rb in zip(Y, Yf) if ra.index(max(ra)) == rb.index(max(rb))) / len(Y)
    return err, agree, sh1


rows, tiny = [], []
for b in range(2, 9):
    e, a, sh1 = run_int(b)
    e7, a7, sh7 = run_int(b, 7)
    rows.append((b, f"{e:.4f}", f"{a:.3f}", sh1))
    tiny.append((b, f"{e7:.4f}", f"{a7:.3f}", sh7))
    print(f"  {b} bits: ideal err {e:6.1%} agree {a:6.1%} (shift {sh1}) | TinyTPU err {e7:6.1%} agree {a7:6.1%} (shift {sh7})")
write_csv("e2_quantization.csv", ["bits", "ideal_error", "ideal_top1", "ideal_shift", "tinytpu_error", "tinytpu_top1", "tinytpu_shift"],
          [r + t[1:] for r, t in zip(rows, tiny)])

s = Svg(1000, 520, "Experiment 2: how many bits does a network need?",
        ["A 2-layer network (8 → 4 → 4) quantized to b bits vs. floating point, 500 random inputs. Solid: ideal rescaling.",
         "Dashed: TinyTPU's real ACT (shift 0..7 only). Its 8-bit run is cross-checked against the instruction-level model."])
x0, x1, y0, y1 = 110, 900, 440, 120
X_ = lambda b: x0 + (b - 2) / 6 * (x1 - x0)
Y_ = lambda v: y0 - v * (y0 - y1)
for v in [0, .25, .5, .75, 1]:
    s.line(x0, Y_(v), x1, Y_(v), C["line"], 1, dash="3 4")
    s.text(x0 - 10, Y_(v) + 4, f"{int(v * 100)}%", 12, C["muted"], anchor="end")
for b in range(2, 9):
    s.text(X_(b), y0 + 22, f"{b} bits", 12, C["muted"], anchor="middle")
for data, dash, lbl in ((rows, None, True), (tiny, "7 5", False)):
    for idx, col in ((2, C["out"]), (1, C["red"])):
        pts = [(X_(r[0]), Y_(min(1, float(r[idx])))) for r in data]
        s.path("M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pts), col, 3.5 if lbl else 2.5, dash=dash)
        for (a, b), r in zip(pts, data):
            s.circle(a, b, 5 if lbl else 4, col, C["white"], 2)
            if lbl:
                s.text(a, b - 12, f"{float(r[idx]) * 100:.0f}%", 12, col, 700, "middle")
s.legend(600, 230, [(C["out"], "same top answer as float"), (C["red"], "relative output error"),
                    (C["faint"], "dashed = TinyTPU's 3-bit shift limit")], 320)
s.save(os.path.join(DIAG, "exp_quantization.svg"))
