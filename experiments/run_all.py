#!/usr/bin/env python3
"""Run every experiment:  make experiments   (takes a couple of minutes)"""
import runpy, os, time
here = os.path.dirname(os.path.abspath(__file__))
for name in ["e1_speedup", "e2_quantization", "e3_energy", "e4_spacetime", "e5_scaling"]:
    t = time.time()
    print(f"== {name}")
    runpy.run_path(os.path.join(here, name + ".py"), run_name="__main__")
    print(f"   ({time.time() - t:.0f} s)")
