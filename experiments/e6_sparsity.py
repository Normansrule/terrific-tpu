#!/usr/bin/env python3
"""Experiment 6 - How much of the work is multiplying by zero?

A dense systolic array multiplies every weight by every input, even when
one of them is zero. This experiment instruments the instruction-level
model to count, for each application, how many multiply-accumulates had
a zero weight, a zero input, or both. Zero products are wasted energy,
and they are the opportunity that sparse accelerators (EIE, NVIDIA's
2:4 structured sparsity) exploit.
Output: experiments/results/e6_sparsity.csv, diagrams/exp_sparsity.svg
"""
from common import *   # noqa: F401,F403
from svg import Svg, C
import apps                        # noqa: E402
import golden_model as gm          # noqa: E402
from tpu_isa_sim import TinyTPU    # noqa: E402


class CountingTPU(TinyTPU):
    """Same semantics as TinyTPU; also counts zero operands inside MMUL."""
    def run(self, program, max_instr=10000):
        self.stats = dict(total=0, zero_w=0, zero_x=0, both=0)
        n = self.n
        for word in program[:max_instr]:
            op, a, b = word >> 28, (word >> 20) & 255, (word >> 12) & 255
            if op == 0x1:
                w = [list(self.wmem[(a + k) & 255]) for k in range(n)]
            if op == 0x2:
                for r in range(b):
                    x = self.ub[(a + r) & 255]
                    for k in range(n):
                        for j in range(n):
                            zw, zx = self.w[k][j] == 0, x[k] == 0
                            self.stats["total"] += 1
                            self.stats["both"] += zw and zx
                            self.stats["zero_w"] += zw and not zx
                            self.stats["zero_x"] += zx and not zw
            super().run([word])        # execute this instruction normally
            if op == 0xF:
                break
        return self


def run(builder, prog_file, **kw):
    t = CountingTPU(4)
    if builder:
        pf, wmem, ub, _ = getattr(apps, builder)(**kw)
        prog_file = pf
    else:
        import random
        r = random.Random(1)
        X, W = gm.rand_mat(r, 8, 8), gm.rand_mat(r, 12, 4)
        wmem, ub = W, [row[:4] for row in X] + [row[4:] for row in X]
    for i, v in enumerate(wmem):
        t.wmem[i] = list(v)
    for i, v in enumerate(ub):
        t.ub[i] = list(v)
    t.run(gm.asm(prog_file))
    return t.stats


cases = [("Neural net", None, "mlp_demo.asm"), ("Image filter", "conv_build", None),
         ("Quantum search", "grover_build", None), ("Graph triangles", "graph_build", None)]
rows = []
for label, b, pf in cases:
    st = run(b, pf)
    useful = st["total"] - st["zero_w"] - st["zero_x"] - st["both"]
    rows.append((label, st["total"], useful, st["zero_w"], st["zero_x"], st["both"]))
    print(f"  {label:16s} {st['total']:5d} MACs, {100 * (1 - useful / st['total']):4.1f}% had a zero operand")
write_csv("e6_sparsity.csv", ["app", "macs", "useful", "zero_weight_only", "zero_input_only", "both_zero"], rows)

s = Svg(1000, 530, "Experiment 6: how much work is multiplying by zero?",
        ["Every multiply-accumulate each application performs on the instruction-level model, split by whether an operand",
         "was zero. A dense array does them all anyway; sparse accelerators skip them."])
x0, W, y0 = 200, 700, 120
parts = [(2, "useful", C["mxu"]), (3, "zero weight", C["wt"]), (4, "zero input", C["act"]), (5, "both zero", C["red"])]
for i, row in enumerate(rows):
    y = y0 + i * 70
    s.text(x0 - 14, y + 24, row[0], 14, C["ink"], 700, "end")
    s.text(x0 - 14, y + 42, f"{row[1]:,} MACs", 11, C["muted"], anchor="end")
    x = x0
    for idx, name, col in parts:
        w = row[idx] / row[1] * W
        if w > 0:
            s.rect(x, y + 6, w, 34, col, rx=3, opacity=0.9)
            if w > 44:
                s.text(x + w / 2, y + 28, f"{100 * row[idx] / row[1]:.0f}%", 12, "#FFFFFF", 700, "middle")
        x += w
s.legend(x0, 400, [(c, n) for _, n, c in parts], 200)
s.text(430, 425, "Graphs are mostly zeros; that is why graph analytics needs sparse hardware.", 13, C["muted"])
s.save(os.path.join(DIAG, "exp_sparsity.svg"))
