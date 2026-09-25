#!/usr/bin/env python3
"""
golden_model.py - builds test cases for the TinyTPU testbench.

For every test it writes the memory images the RTL loads, and the memory
contents the RTL must end with:

    build/imem.hex  build/wmem.hex  build/ub.hex        (inputs)
    build/expect_ub.hex  build/expect_acc.hex           (answer key)

The answer key comes from tools/tpu_isa_sim.py (an instruction-level
model). For the demos it is ALSO cross-checked against plain textbook
math, so the answer key itself is checked.

Demos:
    --demo mlp   2-layer neural network        (programs/mlp_demo.asm)
    --demo dft   4-point Fourier transform     (programs/dft4.asm)
    --demo fuzz  a RANDOM program on RANDOM data  (stress-tests hazards)
    --demo conv    image filtering: 4 filters on a 10x10 image  (programs/conv2d.asm)
    --demo grover  Grover's quantum search on 2 qubits          (programs/grover2.asm)
    --demo graph   walks and triangles in an 8-node graph       (programs/graph_paths.asm)

Usage:
    python3 tools/golden_model.py --demo mlp  --seed 1 --out build
"""
import argparse
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tpu_asm import assemble, disassemble          # noqa: E402
from tpu_isa_sim import TinyTPU, requant, wrap32   # noqa: E402

N = 4
HERE = os.path.dirname(os.path.abspath(__file__))


def matmul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(len(B))) for j in range(len(B[0]))]
            for i in range(len(A))]


def rand_mat(rng, r, c, lo=-8, hi=7):
    return [[rng.randint(lo, hi) for _ in range(c)] for _ in range(r)]


def pack(vec, bits):
    m = (1 << bits) - 1
    return sum((v & m) << (bits * i) for i, v in enumerate(vec))


def write_hex(path, rows, bits):
    digits = bits * N // 4
    with open(path, "w") as fh:
        for r in rows:
            fh.write(f"{pack(r, bits):0{digits}x}\n")


def run_and_write(out, program, wmem, ub):
    """Place data, run the instruction-level model, write all hex files."""
    t = TinyTPU(N)
    for i, r in enumerate(wmem):
        t.wmem[i] = list(r)
    for i, r in enumerate(ub):
        t.ub[i] = list(r)
    init_w = [list(r) for r in t.wmem]
    init_ub = [list(r) for r in t.ub]
    t.run(program)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "imem.hex"), "w") as fh:
        for w in program + [0xF0000000] * (256 - len(program)):
            fh.write(f"{w:08x}\n")
    write_hex(os.path.join(out, "wmem.hex"), init_w, 8)
    write_hex(os.path.join(out, "ub.hex"), init_ub, 8)
    write_hex(os.path.join(out, "expect_ub.hex"), t.ub, 8)
    write_hex(os.path.join(out, "expect_acc.hex"), t.acc, 32)
    return t


def asm(name):
    return assemble(open(os.path.join(HERE, "..", "programs", name)).read())

# ------------------------------------------------------------------ demos

def demo_mlp(seed, out, rows=8):
    rng = random.Random(seed)
    X = rand_mat(rng, rows, 2 * N)
    W1 = rand_mat(rng, 2 * N, N)
    W2 = rand_mat(rng, N, N)
    wmem = W1[:N] + W1[N:] + W2
    ub = [r[:N] for r in X] + [r[N:] for r in X]
    t = run_and_write(out, asm("mlp_demo.asm"), wmem, ub)
    # independent check: textbook math must agree with the ISA model
    H = [[requant(wrap32(v), True, 3) for v in r] for r in matmul(X, W1)]
    Y = [[requant(wrap32(v), False, 5) for v in r] for r in matmul(H, W2)]
    assert t.ub[16:24] == H and t.ub[24:32] == Y, "ISA model disagrees with plain math!"
    print(f"mlp demo, seed {seed}: ISA model == textbook math")
    print("  Y =", Y[:3], "...")


def demo_dft(seed, out):
    rng = random.Random(seed)
    Xs = rand_mat(rng, 8, N, lo=-31, hi=31)
    C = [[round(math.cos(2 * math.pi * k * n / N)) for n in range(N)] for k in range(N)]
    S = [[round(-math.sin(2 * math.pi * k * n / N)) + 0 for n in range(N)] for k in range(N)]
    t = run_and_write(out, asm("dft4.asm"), C + S, Xs)
    for i, x in enumerate(Xs):                       # compare with complex math
        spec = [sum(x[k] * complex(math.cos(2*math.pi*k*m/N), -math.sin(2*math.pi*k*m/N))
                    for k in range(N)) for m in range(N)]
        assert t.acc[i] == [round(z.real) for z in spec]
        assert t.acc[8 + i] == [round(z.imag) for z in spec]
    print(f"dft demo, seed {seed}: ISA model == complex-number DFT")
    print(f"  signal {Xs[0]} -> real {t.acc[0]} imag {t.acc[8]}")


def demo_fuzz(seed, out, verbose=False):
    """Random program + random data, with DEPENDENCIES made likely.

    Purely random addresses almost never make one instruction read what the
    previous one wrote, and that is exactly where a pipelined design breaks.
    So half the time we point an instruction at the previous one's output:
      ACT  reads the accumulator rows the last MMUL just wrote   (RAW hazard)
      MMUL reads the Unified Buffer rows the last ACT just wrote
      MMUL accumulates into the rows the last MMUL wrote
      LDW  right after a short MMUL (swap wavefront still moving)
    """
    rng = random.Random(seed)
    prog, last_mmul_c, last_act_c = [], rng.randrange(256), rng.randrange(256)
    dep = lambda last: last if rng.random() < 0.5 else rng.randrange(256)
    for _ in range(rng.randint(6, 16)):
        k = rng.random()
        if k < 0.30:
            prog.append(0x1 << 28 | rng.randrange(256) << 20)
        elif k < 0.65:
            b = rng.choice([1, 2, 3, rng.randint(1, 12)])
            c = dep(last_mmul_c)
            prog.append(0x2 << 28 | dep(last_act_c) << 20 | b << 12 | c << 4 | rng.randint(0, 1))
            last_mmul_c = c
        elif k < 0.95:
            c = rng.randrange(256)
            prog.append(0x3 << 28 | dep(last_mmul_c) << 20 | rng.randint(1, 12) << 12
                        | c << 4 | rng.randrange(16))
            last_act_c = c
        else:
            prog.append(0)                                   # NOP
    prog.append(0xF0000000)
    wmem = rand_mat(rng, 256, N, -128, 127)
    ub = rand_mat(rng, 256, N, -128, 127)
    run_and_write(out, prog, wmem, ub)
    if verbose:
        for i, w in enumerate(prog):
            print(f"  {i:2d}: {w:08x}  {disassemble(w)}")


def demo_app(builder, out, **kw):
    import apps
    prog_file, wmem, ub, check = getattr(apps, builder)(**kw)
    t = run_and_write(out, asm(prog_file), wmem, ub)
    print(check(t))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", choices=["mlp", "dft", "fuzz", "conv", "grover", "graph"], default="mlp")
    ap.add_argument("--marked", type=int, default=3, help="grover: which item (0-3) the oracle marks")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default="build")
    ap.add_argument("-v", action="store_true")
    a = ap.parse_args()
    if a.demo == "conv":
        demo_app("conv_build", a.out)
    elif a.demo == "grover":
        demo_app("grover_build", a.out, marked=a.marked)
    elif a.demo == "graph":
        demo_app("graph_build", a.out)
    else:
        {"mlp": demo_mlp, "dft": demo_dft}.get(a.demo, lambda s, o: demo_fuzz(s, o, a.v))(a.seed, a.out)
