#!/usr/bin/env python3
"""
tpu_asm.py - assembler for the TinyTPU instruction set.

Turns human-readable lines like

    LDW   w=0
    MMUL  ub=0  rows=8  acc=0  accumulate
    ACT   acc=0 rows=8  ub=16  relu shift=2
    HALT

into 32-bit machine words (one hex word per line) that the RTL reads
with $readmemh.

Instruction word layout (32 bits):

    31    28 27     20 19     12 11      4 3     0
   +--------+---------+---------+---------+-------+
   | opcode |    A    |    B    |    C    | flags |
   +--------+---------+---------+---------+-------+

Usage:
    python3 tools/tpu_asm.py programs/mlp_demo.asm build/imem.hex
"""
import sys

OPCODES = {"NOP": 0x0, "LDW": 0x1, "MMUL": 0x2, "ACT": 0x3, "HALT": 0xF}


def encode(op, a=0, b=0, c=0, flags=0):
    for name, v, hi in (("A", a, 255), ("B", b, 255), ("C", c, 255), ("flags", flags, 15)):
        if not 0 <= v <= hi:
            raise ValueError(f"field {name}={v} out of range 0..{hi}")
    return (OPCODES[op] << 28) | (a << 20) | (b << 12) | (c << 4) | flags


def parse_line(line):
    """Return a 32-bit word, or None for blank/comment lines."""
    line = line.split(";")[0].split("#")[0].strip()
    if not line:
        return None
    parts = line.split()
    op = parts[0].upper()
    if op not in OPCODES:
        raise ValueError(f"unknown instruction '{op}'")
    kv, words = {}, set()
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            kv[k.lower()] = int(v, 0)
        else:
            words.add(p.lower())

    if op in ("NOP", "HALT"):
        return encode(op)
    if op == "LDW":
        return encode(op, a=kv["w"])
    if op == "MMUL":
        return encode(op, a=kv["ub"], b=kv["rows"], c=kv["acc"],
                      flags=1 if "accumulate" in words else 0)
    if op == "ACT":
        shift = kv.get("shift", 0)
        if not 0 <= shift <= 7:
            raise ValueError("shift must be 0..7")
        flags = (shift << 1) | (1 if "relu" in words else 0)
        return encode(op, a=kv["acc"], b=kv["rows"], c=kv["ub"], flags=flags)
    raise AssertionError(op)


def assemble(text):
    words = []
    for n, line in enumerate(text.splitlines(), 1):
        try:
            w = parse_line(line)
        except (ValueError, KeyError) as e:
            raise SystemExit(f"line {n}: {e}\n    {line}")
        if w is not None:
            words.append(w)
    return words


def disassemble(word):
    op = {v: k for k, v in OPCODES.items()}.get(word >> 28, "???")
    a, b, c, f = (word >> 20) & 0xFF, (word >> 12) & 0xFF, (word >> 4) & 0xFF, word & 0xF
    if op == "LDW":
        return f"LDW   w={a}"
    if op == "MMUL":
        return f"MMUL  ub={a} rows={b} acc={c}" + (" accumulate" if f & 1 else "")
    if op == "ACT":
        return f"ACT   acc={a} rows={b} ub={c}" + (" relu" if f & 1 else "") + f" shift={f >> 1}"
    return op


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    words = assemble(open(sys.argv[1]).read())
    with open(sys.argv[2], "w") as fh:
        for w in words:
            fh.write(f"{w:08x}\n")
    for i, w in enumerate(words):
        print(f"  {i:3d}: {w:08x}   {disassemble(w)}")
