#!/usr/bin/env python3
"""
tpu_isa_sim.py - an INSTRUCTION-LEVEL model of TinyTPU.

It knows nothing about clocks, skew, pipelines or wavefronts. It only
knows what each instruction MEANS:

    LDW  w=A                 weights  <- wmem[A .. A+N-1]
    MMUL ub=A rows=B acc=C   acc[C+r] (+)= ub[A+r] @ weights   for r < B
    ACT  acc=A rows=B ub=C   ub[C+r]   = requant(acc[A+r])     for r < B
    HALT

Both hardware versions (v1_simple and v2_pipelined) must end with exactly
the memories this model produces, for ANY program. That is the contract
the pipelined version has to honor while it overlaps instructions.

Addresses are 8 bits and wrap around, just like in the RTL.
"""


def wrap32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def requant(v, relu, shift):
    if relu and v < 0:
        v = 0
    v >>= shift
    return max(-128, min(127, v))


class TinyTPU:
    def __init__(self, n=4):
        self.n = n
        self.wmem = [[0] * n for _ in range(256)]
        self.ub = [[0] * n for _ in range(256)]
        self.acc = [[0] * n for _ in range(256)]
        self.w = [[0] * n for _ in range(n)]
        self.trace = []

    def run(self, program, max_instr=10000):
        n = self.n
        for pc, word in enumerate(program[:max_instr]):
            op = word >> 28
            a, b, c, f = (word >> 20) & 255, (word >> 12) & 255, (word >> 4) & 255, word & 15
            if op == 0x1:
                self.w = [list(self.wmem[(a + k) & 255]) for k in range(n)]
            elif op == 0x2:
                for r in range(b):
                    x = self.ub[(a + r) & 255]
                    y = [sum(x[k] * self.w[k][j] for k in range(n)) for j in range(n)]
                    dst = (c + r) & 255
                    old = self.acc[dst] if f & 1 else [0] * n
                    self.acc[dst] = [wrap32(o + v) for o, v in zip(old, y)]
            elif op == 0x3:
                for r in range(b):
                    self.ub[(c + r) & 255] = [requant(v, f & 1, f >> 1)
                                              for v in self.acc[(a + r) & 255]]
            elif op == 0xF:
                self.trace.append((pc, "HALT"))
                return self
            self.trace.append((pc, op))
        return self
