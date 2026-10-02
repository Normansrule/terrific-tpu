#!/usr/bin/env python3
"""basys3_report.py - summarise Yosys synth_xilinx statistics for the Basys 3 build
against the XC7A35T's resources, and write data/basys3.csv."""
import os, re, sys
log = open(sys.argv[1]).read()
blk = log[log.index("=== design hierarchy ==="):]
blk = blk[:blk.index("Number of cells:", blk.index("Number of cells:") + 1)]
cells = {k: int(v) for k, v in re.findall(r"^\s+(\w+)\s+(\d+)$", blk, re.M)}
luts = sum(v for k, v in cells.items() if re.fullmatch(r"LUT[1-6]", k))
lutram = cells.get("RAM64M", 0) * 4 + cells.get("RAM32M", 0) * 4
ffs = sum(v for k, v in cells.items() if k.startswith("FD"))
rows = [("Lookup tables (logic)", luts, 20800), ("Lookup tables used as memory (RAM64M × 4)", lutram, 20800),
        ("Flip-flops", ffs, 41600), ("DSP48E1 multipliers", cells.get("DSP48E1", 0), 90),
        ("Block RAM (RAMB36E1)", cells.get("RAMB36E1", 0), 50), ("Global clock buffers (BUFG + BUFGCE)", cells.get("BUFG", 0) + cells.get("BUFGCE", 0), 32)]
os.makedirs("data", exist_ok=True)
with open("data/basys3.csv", "w") as fh:
    fh.write("resource,used,available_xc7a35t\n")
    for n, u, a in rows:
        fh.write(f"{n},{u},{a}\n")
        print(f"  {n:44s} {u:6,d} / {a:6,d}  ({100 * u / a:4.1f} %)")
print("  wrote data/basys3.csv  (Yosys estimate; Vivado's report_utilization is the final word)")
