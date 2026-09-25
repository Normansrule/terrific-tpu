#!/usr/bin/env python3
"""Experiment 3 - Where does the energy go?

Counts every event in each application on the cycle-exact model
(multiply-accumulates, Unified Buffer reads/writes, accumulator
reads/writes, weight-row reads), then prices them with 45 nm energy
figures (Horowitz, ISSCC 2014). Two scenarios for the weights:
on-chip SRAM (TinyTPU as built) vs off-chip DRAM (like TPU v1).
These are ESTIMATES that show proportions, not a sign-off power number.
Output: experiments/results/e3_energy.csv, diagrams/exp_energy.svg
"""
from common import *   # noqa: F401,F403
from svg import Svg, C

PJ = dict(mac=0.3, ub_read=5, ub_write=5, acc_read=20, acc_write=20)
W_SRAM, W_DRAM = 5, 640          # per 4-byte weight row
rows = []
for demo, label in APPS:
    make_case(demo)
    ev = js_trace()["events"]
    rows.append((label, ev))
write_csv("e3_energy.csv", ["app", "macs", "ub_reads", "ub_writes", "acc_reads", "acc_writes", "weight_rows"],
          [(l, e["mac"], e["ub_read"], e["ub_write"], e["acc_read"], e["acc_write"], e["w_read"]) for l, e in rows])

parts = [("multiply-accumulate", lambda e, w: e["mac"] * PJ["mac"], C["mxu"]),
         ("Unified Buffer", lambda e, w: (e["ub_read"] + e["ub_write"]) * 5, C["act"]),
         ("accumulators", lambda e, w: (e["acc_read"] + e["acc_write"]) * 20, C["ps"]),
         ("weights", lambda e, w: e["w_read"] * w, C["wt"])]
s = Svg(1000, 640, "Experiment 3: where the energy goes (estimated)",
        ["Event counts from the cycle-exact model, priced with 45 nm figures. Left bar of each pair: weights in on-chip SRAM.",
         "Right bar: weights in off-chip DRAM, like TPU v1. Labels: energy per useful multiply-accumulate."])
x0, y0, H = 90, 540, 330
tot = [(sum(f(e, w) for _, f, _ in parts)) for _, e in rows for w in (W_SRAM, W_DRAM)]
mx = max(tot)
for i, (label, e) in enumerate(rows):
    for j, w in enumerate((W_SRAM, W_DRAM)):
        x = x0 + i * 180 + j * 62
        y = y0
        for name, f, col in parts:
            v = f(e, w)
            h = v / mx * H
            s.rect(x, y - h, 54, h, col, rx=2, opacity=0.9)
            y -= h
        total = sum(f(e, w) for _, f, _ in parts)
        s.text(x + 27, y - 22, f"{total / 1000:.1f} nJ", 11, C["ink"], 700, "middle")
        s.text(x + 27, y - 8, f"{total / e['mac']:.1f} pJ/MAC", 10, C["muted"], anchor="middle")
        s.text(x + 27, y0 + 16, "SRAM" if j == 0 else "DRAM", 10, C["muted"], anchor="middle")
    s.text(x0 + i * 180 + 58, y0 + 36, label, 13, C["ink"], 700, "middle")
    s.text(x0 + i * 180 + 58, y0 + 52, f"{e['mac']:,} MACs", 11, C["muted"], anchor="middle")
s.legend(90, 110, [(c, n) for n, _, c in parts], 220)
s.save(os.path.join(DIAG, "exp_energy.svg"))
