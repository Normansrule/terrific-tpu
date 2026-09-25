#!/usr/bin/env python3
"""Experiment 4 - Space-time map: which PE is busy on which cycle?

For each application, one row per processing element (16 rows) and one
column per clock cycle, straight from the cycle-exact model. Violet =
doing a useful multiply-accumulate, amber = loading weights, pale = idle.
The diagonal staircases ARE the systolic wavefront.
Output: experiments/results/e4_utilization.csv, diagrams/exp_spacetime.svg
"""
from common import *   # noqa: F401,F403
from svg import Svg, C

traces = []
for demo, label in APPS:
    make_case(demo)
    traces.append((label, js_trace()))
maxc = max(t["cycles"] for _, t in traces)
cw, rh, x0 = 2.7, 4.2, 170
band = 16 * rh + 46
s = Svg(int(x0 + maxc * cw + 40), int(120 + band * len(traces)), "Experiment 4: the chip in space and time",
        ["Each band: 16 rows = the 16 processing elements; columns = clock cycles (cycle-exact model of v1).",
         "Violet = useful multiply-accumulate, amber = loading weights, pale = idle. Diagonal staircases are the wavefront."])
rows = []
for i, (label, t) in enumerate(traces):
    y0 = 110 + i * band
    busy_total = 0
    s.rect(x0, y0, t["cycles"] * cw, 16 * rh, "#EEF2F7", rx=2)
    for cyc, (mask, ld) in enumerate(zip(t["busy"], t["load"])):
        if ld:
            s.rect(x0 + cyc * cw, y0, cw, 16 * rh, C["wt_bg"], rx=0)
        if mask:
            for pe in range(16):
                if mask >> pe & 1:
                    busy_total += 1
                    s.rect(x0 + cyc * cw, y0 + pe * rh, cw + 0.3, rh + 0.3, C["mxu"], rx=0)
    util = busy_total / (16 * t["cycles"])
    rows.append((label, t["cycles"], busy_total, f"{util:.3f}"))
    s.text(x0 - 12, y0 + 26, label, 13, C["ink"], 700, "end")
    s.text(x0 - 12, y0 + 44, f"{t['cycles']} cycles", 11, C["muted"], anchor="end")
    s.text(x0 - 12, y0 + 60, f"{util:.0%} busy", 11, C["mxu"], 700, "end")
write_csv("e4_utilization.csv", ["app", "cycles", "busy_pe_cycles", "utilization"], rows)
s.save(os.path.join(DIAG, "exp_spacetime.svg"))
