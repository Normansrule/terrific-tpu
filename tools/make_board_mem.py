#!/usr/bin/env python3
"""make_board_mem.py - build the demo programs baked into the Basys 3 bitstream.

Writes rtl/fpga/basys3/mem/{imem,wmem,ub,expect}.hex: four demos, 256 rows
each (demo d occupies rows d*256 .. d*256+255). Switches 1:0 on the board pick
the demo; the board checks its own results against expect.hex.

    python3 tools/make_board_mem.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "rtl", "fpga", "basys3", "mem")
DEMOS = ["mlp", "dft", "conv", "grover"]          # switch 1:0 = 0, 1, 2, 3

os.makedirs(OUT, exist_ok=True)
rows = {k: [] for k in ("imem", "wmem", "ub", "expect")}
for d in DEMOS:
    tmp = tempfile.mkdtemp()
    subprocess.run([sys.executable, os.path.join(HERE, "golden_model.py"), "--demo", d, "--seed", "1", "--out", tmp],
                   check=True, stdout=subprocess.DEVNULL)
    for k, f in (("imem", "imem.hex"), ("wmem", "wmem.hex"), ("ub", "ub.hex"), ("expect", "expect_ub.hex")):
        lines = [l.strip() for l in open(os.path.join(tmp, f)) if l.strip() and not l.startswith("//")]
        assert len(lines) == 256, (d, f, len(lines))
        rows[k] += [l.zfill(8) for l in lines]
    shutil.rmtree(tmp)
for k, v in rows.items():
    with open(os.path.join(OUT, f"{k}.hex"), "w") as fh:
        fh.write("\n".join(v) + "\n")
print(f"wrote {len(DEMOS)} demos ({', '.join(DEMOS)}) to rtl/fpga/basys3/mem/")
