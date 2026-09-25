"""Shared helpers for the experiments: run a demo on the RTL or the JS model."""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "diagrams"))
RESULTS = os.path.join(ROOT, "experiments", "results")
DIAG = os.path.join(ROOT, "diagrams")
WORK = os.path.join(ROOT, "build", "exp")
os.makedirs(RESULTS, exist_ok=True)
os.makedirs(os.path.join(WORK, "build"), exist_ok=True)

APPS = [("mlp", "Neural net"), ("dft", "Fourier"), ("conv", "Image filter"),
        ("grover", "Quantum search"), ("graph", "Graph triangles")]


def sh(cmd, cwd=WORK):
    return subprocess.run(cmd, shell=True, cwd=cwd, check=True, capture_output=True, text=True).stdout


def compile_rtl(version):
    vvp = os.path.join(ROOT, "build", f"{version}.vvp")
    sh(f"iverilog -g2012 -o {vvp} tb/tb_tpu_top.v rtl/common/*.v rtl/{version}/*.v", cwd=ROOT)
    return vvp


def make_case(demo, seed=1):
    sh(f"python3 {ROOT}/tools/golden_model.py --demo {demo} --seed {seed} --out build")


def rtl_cycles(vvp):
    log = sh(f"vvp -n {vvp} +novcd")
    assert "PASS" in log, log
    return int(re.search(r"finished in (\d+)", log).group(1))


def js_trace():
    return json.loads(sh(f"node {ROOT}/tools/trace_js.js build"))


def write_csv(name, header, rows):
    path = os.path.join(RESULTS, name)
    with open(path, "w") as fh:
        fh.write(",".join(header) + "\n")
        for r in rows:
            fh.write(",".join(str(x) for x in r) + "\n")
    print("  wrote", os.path.relpath(path, ROOT))
