#!/usr/bin/env python3
"""
tpu_compile.py - compile a small neural network into TinyTPU assembly.

The Python twin of web/assets/compiler.js (same algorithm, same random
data for the same seed). It tiles each layer's weights into 4 x 4 tiles,
places every tensor in memory, schedules LDW / MMUL / ACT, and picks each
layer's ACT shift by profiling the integer math once.

    python3 tools/tpu_compile.py --layers 8,12,8,4 --batch 16 --hoist -v
    python3 tools/tpu_compile.py --layers 16,16,8 --batch 24 --out build

With --out it writes build/*.hex (program, memories, answer key) so the
Verilog testbench can run the compiled program: see `make compile-test`.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def lcg(seed):
    s = [seed & 0xFFFFFFFF]

    def r(lo, hi):
        s[0] = (s[0] * 1664525 + 1013904223) & 0xFFFFFFFF
        return lo + ((s[0] >> 16) % (hi - lo + 1))
    return r


def mm(A, B):
    return [[sum(a[k] * B[k][j] for k in range(len(B))) for j in range(len(B[0]))] for a in A]


def make_data(widths, M, seed):
    r = lcg(seed)
    X = [[r(-8, 7) for _ in range(widths[0])] for _ in range(M)]
    Ws = [[[r(-3, 3) for _ in range(n)] for _ in range(widths[l])] for l, n in enumerate(widths[1:])]
    return X, Ws


class CompileError(Exception):
    pass


def compile_net(widths, M, relu, hoist, X, Ws):
    if any(w % 4 or w < 4 for w in widths):
        raise CompileError("every layer width must be a multiple of 4")
    if not 1 <= M <= 255:
        raise CompileError("batch size must be 1..255")
    wmem, tile = [], []
    for l, W in enumerate(Ws):
        K, N = widths[l], widths[l + 1]
        tile.append([[0] * (N // 4) for _ in range(K // 4)])
        for kt in range(K // 4):
            for ct in range(N // 4):
                tile[l][kt][ct] = len(wmem)
                wmem += [W[kt * 4 + i][ct * 4:ct * 4 + 4] for i in range(4)]
    if len(wmem) > 256:
        raise CompileError(f"weights need {len(wmem)} weight-memory rows; only 256 exist")
    base, nxt = [], 0
    for w in widths:
        base.append(nxt)
        nxt += (w // 4) * M
    if nxt > 256:
        raise CompileError(f"activations need {nxt} Unified Buffer rows; only 256 exist")
    if max((n // 4) * M for n in widths[1:]) > 256:
        raise CompileError("a layer needs more than 256 accumulator rows")
    ub = {}
    for i, x in enumerate(X):
        for kt in range(widths[0] // 4):
            ub[base[0] + kt * M + i] = x[kt * 4:kt * 4 + 4]
    A, shifts, ref, warnings = X, [], [], []
    for l, W in enumerate(Ws):
        acc = mm(A, W)
        peak = max([1] + [abs(0 if relu[l] and v < 0 else v) for row in acc for v in row])
        s = 0
        while (peak >> s) > 127 and s < 7:
            s += 1
        if (peak >> s) > 127:
            warnings.append(f"layer {l + 1}: values up to {peak} saturate even at shift 7")
        shifts.append(s)
        A = [[max(-128, min(127, (0 if relu[l] and v < 0 else v) >> s)) for v in row] for row in acc]
        ref.append(A)
    prog, pending = [], None
    for l in range(len(Ws)):
        K, N = widths[l], widths[l + 1]
        for ct in range(N // 4):
            for kt in range(K // 4):
                prog.append(f"LDW   w={tile[l][kt][ct]}")
                if pending:
                    prog.append(pending)
                    pending = None
                prog.append(f"MMUL  ub={base[l] + kt * M} rows={M} acc={ct * M}" + (" accumulate" if kt else ""))
            act = f"ACT   acc={ct * M} rows={M} ub={base[l + 1] + ct * M}" + (" relu" if relu[l] else "") + f" shift={shifts[l]}"
            if hoist:
                pending = act
            else:
                prog.append(act)
    if pending:
        prog.append(pending)
    prog.append("HALT")
    L = len(Ws)
    return dict(prog=prog, wmem=wmem, ub=ub, shifts=shifts, ref=ref, warnings=warnings,
                out_base=base[L], NO=widths[L], M=M, macs=sum(M * widths[l] * widths[l + 1] for l in range(L)))


def read_output(ubmem, c):
    return [sum((list(ubmem[c["out_base"] + ct * c["M"] + i]) for ct in range(c["NO"] // 4)), []) for i in range(c["M"])]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--layers", default="8,12,8,4", help="layer widths, multiples of 4 (first = input)")
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--hoist", action="store_true", help="move each ACT after the next LDW (helps v2)")
    ap.add_argument("--out", help="write build files for the Verilog testbench into this folder")
    ap.add_argument("-v", action="store_true", help="print the generated program")
    a = ap.parse_args()
    widths = [int(x) for x in a.layers.split(",")]
    relu = [l < len(widths) - 2 for l in range(len(widths) - 1)]
    X, Ws = make_data(widths, a.batch, a.seed)
    try:
        c = compile_net(widths, a.batch, relu, a.hoist, X, Ws)
    except CompileError as e:
        sys.exit(f"compile error: {e}")
    from tpu_asm import assemble
    from tpu_isa_sim import TinyTPU
    words = assemble("\n".join(c["prog"]))
    # check the compiled program on the instruction-level model
    t = TinyTPU(4)
    for i, r in enumerate(c["wmem"]):
        t.wmem[i] = list(r)
    for i, r in c["ub"].items():
        t.ub[i] = list(r)
    t.run(words)
    ok = read_output(t.ub, c) == c["ref"][-1]
    print(f"compiled {'-'.join(map(str, widths))}, batch {a.batch}: {len(words)} instructions, "
          f"{c['macs']} MACs, shifts {c['shifts']}, model check {'PASS' if ok else 'FAIL'}")
    for w in c["warnings"]:
        print("  warning:", w)
    if a.v:
        for i, line in enumerate(c["prog"]):
            print(f"  {i:3d}  {line}")
    if a.out:
        import golden_model as g
        ub = [[0] * 4 for _ in range(256)]
        for i, r in c["ub"].items():
            ub[i] = list(r)
        g.run_and_write(a.out, words, c["wmem"] + [[0] * 4] * (256 - len(c["wmem"])), ub)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
