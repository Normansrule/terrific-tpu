"""apps_figs.py - pictures of the application demos, drawn from the CHIP'S OWN
final memories (build/final_ub.hex, final_acc.hex written by the testbench
after running v2_pipelined in the Verilog simulator)."""
import math
import os
import sys
from svg import Svg, C
import measured

ROOT = measured.ROOT
sys.path.insert(0, os.path.join(ROOT, "tools"))
import apps  # noqa: E402

OUT = None


def run_app(demo, extra=""):
    vvp = os.path.join(measured.BUILD, "v2_pipelined.vvp")
    os.makedirs(measured.BUILD, exist_ok=True)
    measured.sh(f"iverilog -g2012 -o {vvp} tb/tb_tpu_top.v rtl/common/*.v rtl/v2_pipelined/*.v")
    d = os.path.join(measured.BUILD, f"app_{demo}")
    os.makedirs(os.path.join(d, "build"), exist_ok=True)
    measured.sh(f"python3 {ROOT}/tools/golden_model.py --demo {demo} {extra} --out build", cwd=d)
    log = measured.sh(f"vvp -n {vvp} +novcd", cwd=d)
    assert "PASS" in log
    cyc = int(log.split("finished in ")[1].split()[0])

    def load(name, bits):
        rows = []
        for line in open(os.path.join(d, "build", name)):
            h = line.split("//")[0].strip()
            if not h:
                continue
            h = h.replace("x", "0").replace("X", "0")
            v, m, lanes = int(h, 16), (1 << bits) - 1, []
            for i in range(4):
                x = (v >> (bits * i)) & m
                lanes.append(x - (1 << bits) if x >> (bits - 1) else x)
            rows.append(lanes)
        return rows
    return load("final_ub.hex", 8), load("final_acc.hex", 32), cyc


def ramp(t):
    """dark violet -> magenta -> amber -> near white (t in 0..1)."""
    stops = [(0, (30, 27, 75)), (.35, (124, 58, 237)), (.65, (192, 38, 211)), (.85, (245, 158, 11)), (1, (254, 243, 199))]
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if t <= b:
            f = (t - a) / (b - a) if b > a else 0
            return "#%02x%02x%02x" % tuple(int(x + (y - x) * f) for x, y in zip(ca, cb))
    return "#fef3c7"


def app_conv():
    ub, _, cyc = run_app("conv")
    img = apps.default_image()
    s = Svg(1100, 470, "Image filtering on the TPU: 4 filters, one matrix multiply",
            [f"Left: the 10 x 10 input. Right: the 4 feature maps as read back from the chip's Unified Buffer after the Verilog run",
             f"(rows 192-255, v2_pipelined, {cyc} cycles). im2col turned 64 sliding 3 x 3 windows into 64 rows of one matrix."])
    cs = 22
    for r in range(10):
        for c in range(10):
            g = int(img[r][c] / 15 * 235) + 20
            s.rect(40 + c * cs, 130 + r * cs, cs - 1, cs - 1, f"rgb({g},{g},{g})", rx=2)
    s.text(40 + 5 * cs, 120, "input image", 14, C["ink"], 700, "middle")
    s.rect(40 + 2 * cs - 1, 130 + 2 * cs - 1, 3 * cs + 1, 3 * cs + 1, "none", C["ps"], 2.5, 3)
    s.text(40 + 5 * cs, 370, "one 3 x 3 window → one row", 12, C["ps"], 700, "middle")
    s.line(270, 240, 318, 240, C["ink"], 2.5, True)
    names = list(apps.FILTERS)
    for ch in range(4):
        x0 = 330 + ch * 190
        vals = [ub[192 + i][ch] for i in range(64)]
        mx = max(1, max(vals))
        for i, v in enumerate(vals):
            s.rect(x0 + (i % 8) * 20, 130 + (i // 8) * 20, 19, 19, ramp(v / mx), rx=2)
        s.text(x0 + 80, 120, names[ch].split(" (")[0], 14, C["ink"], 700, "middle")
        s.text(x0 + 80, 312, "(" + names[ch].split(" (")[1], 12, C["muted"], anchor="middle")
        k = apps.FILTERS[names[ch]]
        for i in range(3):
            for j in range(3):
                s.rect(x0 + 50 + j * 20, 330 + i * 20, 19, 19, C["wt_bg"], C["wt"], 1, 3)
                s.text(x0 + 60 + j * 20, 344 + i * 20, str(k[i][j]), 11, C["wt_dk"], 700, "middle", mono=True)
    s.text(330, 420, "Amber grids: the filter weights (one column of W each). Colors: 0 = dark, largest value = light.", 12, C["muted"])
    s.save(os.path.join(OUT, "app_conv.svg"))


def app_grover():
    ub, _, cyc = run_app("grover", "--marked 3")
    stages = [("start", [64, 0, 0, 0]), ("H ⊗ H", ub[8]), ("oracle", ub[12]), ("H ⊗ H", ub[16]),
              ("2|00⟩⟨00| − I", ub[20]), ("H ⊗ H", ub[24])]
    s = Svg(1100, 560, "Grover's quantum search, run as matrix multiplies",
            ["2 qubits, 4 possible answers. The oracle secretly marks |11⟩. Bars: amplitude of each basis state after each gate,",
             f"read from the chip's Unified Buffer after the Verilog run ({cyc} cycles). One Grover step finds the answer with certainty."])
    # circuit
    y1, y2 = 120, 160
    for y, q in ((y1, "q0"), (y2, "q1")):
        s.text(40, y + 5, q, 14, C["ink"], 700)
        s.line(70, y, 1060, y, C["ink"], 2)
    gx = [150, 330, 510, 690, 870]
    for x, (lab, kind) in zip(gx, [("H", "act"), ("Oracle", "red"), ("H", "act"), ("2|0⟩⟨0|−I", "ps"), ("H", "act")]):
        if lab == "H":
            for y in (y1, y2):
                s.rect(x - 18, y - 16, 36, 32, C["act_bg"], C["act"], 2, 6)
                s.text(x, y + 6, "H", 15, C["act_dk"], 700, "middle")
        else:
            s.rect(x - 60, y1 - 18, 120, y2 - y1 + 36, C[f"{kind}_bg"], C[kind], 2, 8)
            s.text(x, (y1 + y2) / 2 + 5, lab, 13, C.get(f"{kind}_dk", "#7F1D1D"), 700, "middle")
    # bars
    base, scale = 360, 120
    for i, (lab, amp) in enumerate(stages):
        x0 = 50 + i * 172
        s.rect(x0, 210, 160, 300, C["white"], C["line"], 1, 10)
        s.text(x0 + 80, 232, lab, 13, C["ink"], 700, "middle")
        s.line(x0 + 10, base, x0 + 150, base, C["line"], 1.5)
        for k, a in enumerate(amp):
            h = a / 64 * scale
            col = C["red"] if k == 3 else C["mxu"]
            y = base - h if h > 0 else base
            s.rect(x0 + 18 + k * 34, y, 26, abs(h), col, rx=3)
            s.text(x0 + 31 + k * 34, base + (-h - 6 if h > 0 else -h + 14) if h else base - 6, f"{a / 64:+.2f}".replace("+0.00", "0"),
                   10, col, 700, "middle")
            s.text(x0 + 31 + k * 34, 500, f"|{k:02b}⟩", 11, C["muted"], anchor="middle")
    p = [a * a / 4096 for a in ub[24]]
    s.text(550, 540, "Final measurement probabilities: " + "   ".join(f"|{k:02b}⟩ {v:.0%}" for k, v in enumerate(p)),
           14, C["red"], 700, "middle")
    s.save(os.path.join(OUT, "app_grover.svg"))


def app_graph():
    _, acc, cyc = run_app("graph")
    A = apps.adjacency()
    A2 = [acc[i] + acc[8 + i] for i in range(8)]
    A3 = [acc[16 + i] + acc[24 + i] for i in range(8)]
    tri = sum(A3[i][i] for i in range(8)) // 6
    s = Svg(1100, 500, "Counting triangles in a graph with matrix powers",
            [f"A² and A³ read back from the chip's accumulators after the Verilog run ({cyc} cycles).",
             f"(A²)[i][j] = 2-step walks from i to j. trace(A³) / 6 = {tri} triangles, highlighted."])
    cx, cy, R = 200, 290, 150
    pos = [(cx + R * math.cos(2 * math.pi * k / 8 - math.pi / 2), cy + R * math.sin(2 * math.pi * k / 8 - math.pi / 2)) for k in range(8)]
    tris = [(a, b, c) for a in range(8) for b in range(a + 1, 8) for c in range(b + 1, 8) if A[a][b] and A[b][c] and A[a][c]]
    for t in tris:
        s.add(f'<polygon points="{" ".join(f"{pos[v][0]:.0f},{pos[v][1]:.0f}" for v in t)}" fill="{C["ps_bg"]}" stroke="none"/>')
    for a, b in apps.EDGES:
        s.line(*pos[a], *pos[b], C["ps"] if any(a in t and b in t for t in tris) else C["faint"], 3)
    for k, (x, y) in enumerate(pos):
        s.circle(x, y, 18, C["mxu_bg"], C["mxu"], 2.5)
        s.text(x, y + 5, str(k), 14, C["mxu_dk"], 700, "middle")
    def heat(x0, M, title, mx):
        s.text(x0 + 120, 125, title, 15, C["ink"], 700, "middle")
        for i in range(8):
            for j in range(8):
                v = M[i][j]
                s.rect(x0 + j * 30, 140 + i * 30, 28, 28, ramp(v / mx), rx=3)
                s.text(x0 + j * 30 + 14, 140 + i * 30 + 19, str(v), 11, "#FFFFFF" if v / mx < .6 else C["ink"], 700, "middle")
            s.text(x0 - 8, 140 + i * 30 + 19, str(i), 11, C["muted"], anchor="end")
    heat(420, A2, "A²: 2-step walks", max(max(r) for r in A2))
    heat(730, A3, "A³: 3-step walks (diagonal → triangles)", max(max(r) for r in A3))
    for i in range(8):
        s.rect(730 + i * 30, 140 + i * 30, 28, 28, "none", C["red"], 2.5, 3)
    s.save(os.path.join(OUT, "app_graph.svg"))


ALL = [app_conv, app_grover, app_graph]
