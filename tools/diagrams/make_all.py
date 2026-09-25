#!/usr/bin/env python3
"""make_all.py - regenerate every generated SVG in diagrams/.

    python3 tools/diagrams/make_all.py          (or: make diagrams)

Concept diagrams are drawn directly; measured diagrams RUN the Verilog
(and read data/synth.csv) first, so they always match the hardware.
Hand-drawn SVGs (block diagrams, schematics) are not touched.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "diagrams"))

import concepts   # noqa: E402
import measured   # noqa: E402
import wavefront  # noqa: E402
import apps_figs  # noqa: E402

concepts.OUT = measured.OUT = apps_figs.OUT = OUT
print("concept diagrams")
for f in concepts.ALL:
    f()
print("wavefront")
wavefront.main()
print("measured diagrams (running the Verilog)")
for f in measured.ALL:
    r = f()
    if r:
        print("   ", r)
print("application pictures (drawn from the chip's own final memories)")
for f in apps_figs.ALL:
    f()
