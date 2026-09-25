"""concepts.py - explanatory diagrams (no simulation needed)."""
import math
from svg import Svg, C, MONO

OUT = None  # set by make_all


def P(name):
    return f"{OUT}/{name}"

# ---------------------------------------------------------------- energy

def energy_costs():
    """Horowitz, ISSCC 2014, 45 nm numbers: why data movement dominates."""
    data = [("8-bit integer add", 0.03, C["act"]), ("32-bit integer add", 0.1, C["act"]),
            ("8-bit integer multiply", 0.2, C["mxu"]), ("16-bit float multiply", 1.1, C["mxu"]),
            ("32-bit float multiply", 3.7, C["mxu"]), ("32-bit read, 8 KB SRAM", 5.0, C["wt"]),
            ("32-bit read, 1 MB SRAM", 50.0, C["wt"]), ("32-bit read, off-chip DRAM", 640.0, C["red"])]
    s = Svg(960, 560, "What costs energy inside a chip",
            ["Energy per operation in picojoules (log scale). 45 nm figures from M. Horowitz, ISSCC 2014.",
             "Fetching one number from DRAM costs as much as ~3,000 small multiplies. So: reuse every number you fetch."])
    x0, x1, y0 = 290, 900, 120
    lo, hi = math.log10(0.01), math.log10(1000)
    X = lambda v: x0 + (math.log10(v) - lo) / (hi - lo) * (x1 - x0)
    for d in range(-2, 4):
        xv = X(10 ** d)
        s.line(xv, y0 - 6, xv, y0 + 44 * len(data), C["line"], 1, dash="4 4")
        s.text(xv, y0 + 44 * len(data) + 20, f"{10 ** d:g} pJ", 12, C["muted"], anchor="middle")
    for i, (lab, v, col) in enumerate(data):
        y = y0 + 44 * i
        s.text(x0 - 12, y + 22, lab, 14, C["ink"], 600, "end")
        s.rect(x0, y + 6, X(v) - x0, 26, col, rx=5, opacity=0.9)
        s.text(X(v) + 8, y + 24, f"{v:g} pJ", 13, col, 700)
    s.text(x0, 520, "blue = add   violet = multiply   amber = on-chip memory   red = off-chip memory",
           13, C["muted"])
    s.save(P("energy_costs.svg"))

# ---------------------------------------------------------------- tiling

def tiling():
    s = Svg(1000, 610, "Tiling: how a 4 x 4 array multiplies a big matrix",
            ["Y (8 x 8) = X (8 x 12) · W (12 x 8). Cut W into 4 x 4 tiles. Each tile is one LDW; each K-tile adds into the",
             "same accumulator rows (MMUL ... accumulate). 3 K-tiles x 2 column tiles = 6 weight loads."])
    cs = 26
    def grid(x, y, r, c, fill, stroke, hl=None, label=None):
        for i in range(r):
            for j in range(c):
                f = fill
                if hl and hl(i, j):
                    f = stroke
                s.rect(x + j * cs, y + i * cs, cs - 3, cs - 3, f, stroke, 1, 4, opacity=None)
        if label:
            s.text(x + c * cs / 2, y - 12, label, 15, C["ink"], 700, "middle")
    # X
    xX, yX = 40, 220
    grid(xX, yX, 8, 12, C["act_bg"], C["act"], lambda i, j: 4 <= j < 8, "X  (8 x 12)")
    s.text(xX + 12 * cs / 2, yX + 8 * cs + 22, "highlighted: K-tile 1 (columns 4-7)", 12, C["act"], 600, "middle")
    s.text(xX + 12 * cs + 28, yX + 4 * cs, "·", 34, C["ink"], 700, "middle")
    # W
    xW, yW = 410, 168
    for kt in range(3):
        for ct in range(2):
            fill = C["wt"] if (kt, ct) == (1, 0) else C["wt_bg"]
            for i in range(4):
                for j in range(4):
                    s.rect(xW + (ct * 4 + j) * cs, yW + (kt * 4 + i) * cs, cs - 3, cs - 3, fill, C["wt"], 1, 4)
            s.text(xW + (ct * 4 + 2) * cs - 2, yW + (kt * 4 + 2) * cs + 2, f"W{kt}{ct}", 12,
                   C["white"] if (kt, ct) == (1, 0) else C["wt_dk"], 700, "middle")
    s.text(xW + 4 * cs, yW - 12, "W  (12 x 8) = 3 x 2 tiles of 4 x 4", 15, C["ink"], 700, "middle")
    s.text(xW + 8 * cs + 30, yX + 4 * cs, "=", 30, C["ink"], 700, "middle")
    # Y
    xY, yY = 680, 220
    grid(xY, yY, 8, 8, C["ps_bg"], C["ps"], lambda i, j: j < 4, "Y  (8 x 8)")
    s.text(xY + 4 * cs, yY + 8 * cs + 22, "highlighted: column tile 0 (acc rows)", 12, C["ps"], 600, "middle")
    # program
    s.rect(40, 490, 920, 100, C["white"], C["line"], 1, 10)
    s.text(60, 516, "Program for column tile 0 (repeat with W01, W11, W21 for column tile 1):", 13, C["muted"], 600)
    code = ["LDW w=W00;  MMUL ub=X_k0 rows=8 acc=0",
            "LDW w=W10;  MMUL ub=X_k1 rows=8 acc=0 accumulate      <- the highlighted tile",
            "LDW w=W20;  MMUL ub=X_k2 rows=8 acc=0 accumulate;  ACT acc=0 rows=8 ..."]
    for i, c in enumerate(code):
        s.text(60, 540 + 20 * i, c, 13, C["mxu_dk"], 600, mono=True)
    s.save(P("tiling.svg"))

# ---------------------------------------------------------------- dataflows

def dataflows():
    s = Svg(980, 470, "Three dataflows: what stays still inside the array?",
            ["Every accelerator picks one value to keep in the PEs and streams the other two past it."])
    specs = [("Weight-stationary", "weights stay, inputs and sums move", "TPU v1, TinyTPU", "wt",
              [("act", "→", "inputs flow right"), ("ps", "↓", "sums flow down")]),
             ("Output-stationary", "sums stay, inputs and weights move", "many research chips", "ps",
              [("act", "→", "inputs flow right"), ("wt", "↓", "weights flow down")]),
             ("Row-stationary", "rows of a convolution stay, reuse maximized", "MIT Eyeriss", "out",
              [("act", "↘", "inputs flow diagonally"), ("ps", "↑", "sums flow up")])]
    for k, (name, sub, who, kind, flows) in enumerate(specs):
        x0 = 30 + k * 320
        s.rect(x0, 100, 300, 350, C["white"], C["line"], 1.5, 14)
        s.text(x0 + 150, 132, name, 18, C["ink"], 700, "middle")
        s.text(x0 + 150, 154, sub, 12, C["muted"], anchor="middle")
        for i in range(4):
            for j in range(4):
                xx, yy = x0 + 62 + j * 46, 176 + i * 46
                s.rect(xx, yy, 38, 38, C[f"{kind}_bg"], C[kind], 2, 7)
                s.circle(xx + 19, yy + 19, 6, C[kind])
        for fi, (fk, sym, lab) in enumerate(flows):
            s.text(x0 + 30, 390 + 22 * fi, sym, 18, C[fk], 700, "middle")
            s.text(x0 + 48, 395 + 22 * fi, lab, 13, C[fk], 600)
        s.text(x0 + 150, 440, f"used by: {who}", 12, C["muted"], anchor="middle", italic=True)
        if kind == "wt":
            for i in range(4):
                s.line(x0 + 42, 195 + i * 46, x0 + 60, 195 + i * 46, C["act"], 2.5, True)
            for j in range(4):
                s.line(x0 + 81 + j * 46, 360, x0 + 81 + j * 46, 372, C["ps"], 2.5, True)
        if kind == "ps":
            for i in range(4):
                s.line(x0 + 42, 195 + i * 46, x0 + 60, 195 + i * 46, C["act"], 2.5, True)
            for j in range(4):
                s.line(x0 + 81 + j * 46, 162, x0 + 81 + j * 46, 174, C["wt"], 2.5, True)
    s.save(P("dataflows.svg"))

# ---------------------------------------------------------------- quantization

def quantization():
    s = Svg(980, 520, "Quantization: squeezing real numbers into 8 bits",
            ["Pick a scale so the biggest value maps to 127, then round. TinyTPU does the reverse trip with a shift."])
    x0, x1, y = 80, 900, 170
    s.line(x0, y, x1, y, C["ink"], 2)
    s.text(40, y + 5, "real", 13, C["muted"], 600)
    for v in [-1.0, -0.5, 0.0, 0.5, 1.0]:
        xv = x0 + (v + 1) / 2 * (x1 - x0)
        s.line(xv, y - 8, xv, y + 8, C["ink"], 2)
        s.text(xv, y - 16, f"{v:+.1f}" if v else "0.0", 13, C["ink"], anchor="middle", mono=True)
    y2 = 300
    s.line(x0, y2, x1, y2, C["mxu"], 2)
    s.text(40, y2 + 5, "int8", 13, C["mxu"], 600)
    for q in range(-128, 128, 8):
        xv = x0 + (q + 128) / 255 * (x1 - x0)
        s.line(xv, y2 - 5, xv, y2 + 5, C["mxu"], 1)
    for q in [-128, -64, 0, 64, 127]:
        xv = x0 + (q + 128) / 255 * (x1 - x0)
        s.line(xv, y2 - 10, xv, y2 + 10, C["mxu"], 2)
        s.text(xv, y2 + 28, str(q), 13, C["mxu"], 700, "middle", mono=True)
    for v, col in [(-0.83, C["act"]), (-0.21, C["act"]), (0.37, C["act"]), (0.9, C["act"])]:
        q = round(v * 127)
        xa = x0 + (v + 1) / 2 * (x1 - x0)
        xb = x0 + (q + 128) / 255 * (x1 - x0)
        s.circle(xa, y, 6, col)
        s.line(xa, y + 8, xb, y2 - 12, col, 2, True)
        s.text((xa + xb) / 2 + 8, (y + y2) / 2, f"{v:+.2f} → {q}", 12, col, 700, mono=True)
    s.rect(80, 360, 820, 130, C["white"], C["line"], 1, 12)
    s.text(100, 388, "Inside TinyTPU", 15, C["ink"], 700)
    steps = [("int8 x int8", "act"), ("int32 accumulate", "ps"), ("ReLU", "out"), ("shift right s", "out"), ("clamp to int8", "mxu")]
    for i, (lab, k) in enumerate(steps):
        bx = 100 + i * 160
        s.rect(bx, 408, 140, 44, C[f"{k}_bg"], C[k], 2, 8)
        s.text(bx + 70, 435, lab, 13, C.get(f"{k}_dk", C["ink"]), 700, "middle")
        if i < 4:
            s.line(bx + 142, 430, bx + 158, 430, C[k], 2, True)
    s.text(100, 475, "scale = max|value| / 127.   Error per value ≤ scale / 2.   Networks shrug this off; that is why TPUs use 8-bit and bfloat16.",
           12, C["muted"])
    s.save(P("quantization.svg"))

# ---------------------------------------------------------------- memory hierarchy

def memory_hierarchy():
    s = Svg(980, 520, "Memory hierarchy: big and slow below, tiny and fast on top",
            ["The systolic array only works if data flows up this pyramid fast enough. TPU v1 numbers vs TinyTPU."])
    levels = [("PE registers", "65,536 PEs", "4 x 4 PEs", "mxu"),
              ("Accumulators (SRAM)", "4 MiB", "256 x 4 x 32 bit", "ps"),
              ("Unified Buffer (SRAM)", "24 MiB", "256 x 4 bytes", "act"),
              ("Weight memory (DDR3 DRAM, off-chip)", "8 GiB @ 34 GB/s", "256 x 4 bytes", "wt"),
              ("Host server memory (over PCIe)", "the whole datacenter server", "testbench $readmemh", "ctl")]
    cx, top, h = 400, 110, 70
    for i, (name, v1, tiny, k) in enumerate(levels):
        half = 90 + i * 70
        y = top + i * (h + 8)
        s.add(f'<path d="M{cx - half} {y + h} L{cx - half + 35} {y} L{cx + half - 35} {y} L{cx + half} {y + h} Z" '
              f'fill="{C[f"{k}_bg"]}" stroke="{C[k]}" stroke-width="2"/>')
        s.text(cx, y + 30, name, 14, C.get(f"{k}_dk", C["ink"]), 700, "middle")
        s.text(cx, y + 50, f"TPU v1: {v1}", 12, C.get(f"{k}_dk", C["ink"]), anchor="middle")
        s.text(760, y + 42, tiny, 13, C["muted"], 600, mono=True)
    s.text(760, 96, "TinyTPU", 14, C["ink"], 700)
    s.line(930, 480, 930, 120, C["out"], 3, True)
    s.text(945, 300, "faster, closer, more energy-efficient", 12, C["out"], 700, "middle", rotate=-90)
    s.save(P("memory_hierarchy.svg"))

# ---------------------------------------------------------------- controller FSM

def controller_fsm():
    s = Svg(980, 560, "Controller state machine (v1, and what v2 adds)",
            ["Circles are states. Arrows show what happens at a clock edge. Dashed red = v2's stall loop (hazard check)."])
    pos = {"FETCH": (200, 300), "DECODE": (430, 300), "LDW": (720, 150), "MMUL": (760, 300),
           "ACT": (720, 450), "HALT": (430, 480)}
    kinds = {"FETCH": "ctl", "DECODE": "ctl", "LDW": "wt", "MMUL": "mxu", "ACT": "out", "HALT": "red"}
    notes = {"FETCH": "ir = imem[pc]", "DECODE": "look at opcode", "LDW": "N cycles", "MMUL": "rows + 2N-1 cycles (v1)",
             "ACT": "rows cycles", "HALT": "done = 1"}
    def arrow(a, b, lab, col=C["ctl"], bend=0, dash=None):
        (x1, y1), (x2, y2) = pos[a], pos[b]
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        sx, sy, ex, ey = x1 + ux * 52, y1 + uy * 52, x2 - ux * 56, y2 - uy * 56
        mx, my = (sx + ex) / 2 - uy * bend, (sy + ey) / 2 + ux * bend
        s.path(f"M{sx:.0f} {sy:.0f} Q{mx:.0f} {my:.0f} {ex:.0f} {ey:.0f}", col, 2.2, arrow=True, dash=dash)
        s.text(mx, my - 6, lab, 12, col, 600, "middle")
    arrow("FETCH", "DECODE", "pc = pc + 1")
    arrow("DECODE", "LDW", "opcode 1", C["wt"])
    arrow("DECODE", "MMUL", "opcode 2", C["mxu"])
    arrow("DECODE", "ACT", "opcode 3", C["out"])
    arrow("DECODE", "HALT", "opcode F", C["red"])
    arrow("LDW", "FETCH", "done loading", C["ctl"], 80)
    arrow("MMUL", "FETCH", "", C["ctl"], -40)
    arrow("ACT", "FETCH", "done", C["ctl"], -80)
    for n, (x, y) in pos.items():
        k = kinds[n]
        s.circle(x, y, 50, C[f"{k}_bg"], C[k], 3)
        s.text(x, y + 2, n, 16, C.get(f"{k}_dk", C["ink"]), 700, "middle")
        s.text(x, y + 20, notes[n], 10, C["muted"], anchor="middle")
    s.path("M405 255 C 360 180, 500 180, 455 255", C["red"], 2.2, arrow=True, dash="6 4")
    s.text(430, 186, "v2: stall while a hazard is pending", 12, C["red"], 700, "middle")
    s.save(P("controller_fsm.svg"))

# ---------------------------------------------------------------- v2 swap wavefront

def swap_wavefront():
    s = Svg(980, 520, "v2: the swap wavefront (double-buffered weights)",
            ["Snapshot 3 cycles into a new MMUL. The swap flag rides with the first new vector, so PEs it has reached",
             "already use the NEW weights (green) while PEs behind it still finish the OLD vectors (amber)."])
    t = 3
    for i in range(4):
        for j in range(4):
            x, y = 90 + j * 110, 140 + i * 85
            new = i + j <= t
            front = i + j == t
            k = "out" if new else "wt"
            s.rect(x, y, 96, 70, C[f"{k}_bg"], C["ps"] if front else C[k], 4 if front else 2, 10)
            s.text(x + 48, y + 28, "active: NEW" if new else "active: old", 12, C[f"{k}_dk"], 700, "middle")
            s.text(x + 48, y + 48, "shadow: next" if new else "shadow: new", 11, C["muted"], anchor="middle")
    s.path("M 60 470 L 560 120", C["ps"], 3, dash="8 6")
    s.text(560, 110, "swap wavefront (moves one diagonal per cycle)", 13, C["ps"], 700, "end")
    s.rect(580, 140, 370, 330, C["white"], C["line"], 1, 12)
    lines = [("Why it works", 15, C["ink"], 700),
             ("Vector v is in PE(row k, col n) at cycle v+k+n.", 13, C["muted"], 400),
             ("The swap flag travels WITH vector 0, so PE(k,n)", 13, C["muted"], 400),
             ("swaps exactly when that vector arrives.", 13, C["muted"], 400),
             ("", 8, C["muted"], 400),
             ("The hazard", 15, C["ink"], 700),
             ("The next LDW rewrites the shadow registers.", 13, C["muted"], 400),
             ("It must wait until the wave reaches the last", 13, C["muted"], 400),
             ("PE: 2N-2 cycles. v2's controller counts this", 13, C["muted"], 400),
             ("(swap_wait) and stalls LDW if needed.", 13, C["muted"], 400),
             ("", 8, C["muted"], 400),
             ("Two mutants in tools/mutation_test.sh break", 13, C["red"], 600),
             ("this rule. The random-program tests catch both.", 13, C["red"], 600)]
    yy = 170
    for txt, sz, col, w in lines:
        s.text(600, yy, txt, sz, col, w)
        yy += sz + 10
    s.save(P("swap_wavefront.svg"))

# ---------------------------------------------------------------- generations timeline

def tpu_timeline():
    gens = [("2015", "TPU v1", "inference · 92 TOPS", "wt"),
            ("2017", "TPU v2", "training · bfloat16", "act"),
            ("2018", "TPU v3", "liquid · 1,024 chips", "act"),
            ("2018", "Edge TPU", "~4 TOPS · ~2 W", "out"),
            ("2021", "TPU v4", "optical · 4,096 chips", "mxu"),
            ("2023", "v5e / v5p", "lean / big", "mxu"),
            ("2024", "Trillium v6e", "256² MXUs", "ps"),
            ("2025", "Ironwood 7x", "inference · 192 GB", "ps"),
            ("2026", "TPU 8t / 8i", "train / serve split", "red")]
    s = Svg(1020, 470, "A decade of TPUs", ["Year first used or announced. Details and sources: docs/13-real-tpus.md"])
    y = 250
    s.line(40, y, 960, y, C["ink"], 3)
    for i, (yr, name, note, k) in enumerate(gens):
        x = 70 + i * 108
        up = i % 2 == 0
        s.circle(x, y, 9, C[k], C["white"], 3)
        s.text(x, y + (30 if up else -18), yr, 14, C[k], 700, "middle")
        by = 110 if up else 290
        s.line(x, y - 10 if up else y + 10, x, by + 70 if up else by, C[k], 2)
        s.rect(x - 52, by, 104, 70, C.get(f"{k}_bg", C["white"]), C[k], 2, 10)
        s.text(x, by + 22, name, 13, C.get(f"{k}_dk", C["ink"]), 700, "middle")
        words, line_, lines = note.split(" · "), "", []
        for wd in words:
            lines.append(wd)
        for j, ln in enumerate(lines[:2]):
            s.text(x, by + 42 + 14 * j, ln, 10, C["muted"], anchor="middle")
    s.save(P("tpu_timeline.svg"))

# ---------------------------------------------------------------- pod torus

def pod_torus():
    s = Svg(980, 520, "Scaling out: chips wired into a torus (a TPU pod)",
            ["Each chip talks only to its neighbors through the Inter-Chip Interconnect (ICI), a systolic idea at building",
             "scale. Edges wrap around, so the grid has no ends. TPU v2/v3 pods: 2-D torus. TPU v4 onward: 3-D torus."])
    n, x0, y0, d = 5, 130, 170, 66
    for i in range(n):
        for j in range(n):
            x, y = x0 + j * d, y0 + i * d
            if j < n - 1:
                s.line(x + 20, y, x + d - 20, y, C["act"], 3)
            if i < n - 1:
                s.line(x, y + 20, x, y + d - 20, C["ps"], 3)
    for i in range(n):                                   # wrap-around stubs
        y, x = y0 + i * d, x0 + i * d
        s.line(x0 - 20, y, x0 - 48, y, C["act"], 2.5, dash="5 3")
        s.line(x0 + (n - 1) * d + 20, y, x0 + (n - 1) * d + 48, y, C["act"], 2.5, dash="5 3")
        s.line(x, y0 - 20, x, y0 - 48, C["ps"], 2.5, dash="5 3")
        s.line(x, y0 + (n - 1) * d + 20, x, y0 + (n - 1) * d + 48, C["ps"], 2.5, dash="5 3")
    s.text(x0 + (n - 1) * d / 2, y0 + (n - 1) * d + 72, "dashed stubs: each edge link wraps to the opposite side",
           12, C["muted"], 600, "middle")
    for i in range(n):
        for j in range(n):
            x, y = x0 + j * d, y0 + i * d
            s.rect(x - 20, y - 20, 40, 40, C["mxu_bg"], C["mxu"], 2, 6)
            s.text(x, y + 5, "TPU", 10, C["mxu_dk"], 700, "middle")
    s.rect(560, 140, 390, 300, C["white"], C["line"], 1, 12)
    rows = [("Why a torus?", 15, C["ink"], 700), ("Big models are split across chips, and each", 13, C["muted"], 400),
            ("step, chips swap slices of activations and", 13, C["muted"], 400), ("gradients with neighbors.", 13, C["muted"], 400),
            ("", 6, C["muted"], 400), ("Wrap-around links halve the worst-case", 13, C["muted"], 400),
            ("distance across the grid.", 13, C["muted"], 400), ("", 6, C["muted"], 400),
            ("TPU v4 adds optical circuit switches that", 13, C["muted"], 400),
            ("rewire groups of 64 chips into different", 13, C["muted"], 400),
            ("3-D shapes on demand.", 13, C["muted"], 400)]
    yy = 170
    for t, sz, col, w in rows:
        s.text(580, yy, t, sz, col, w)
        yy += sz + 11
    s.save(P("pod_torus.svg"))

# ---------------------------------------------------------------- area budget of TPU v1

def tpu_v1_area():
    s = Svg(980, 330, "Where TPU v1 spent its silicon",
            ["Share of die area, from the floor plan in Jouppi et al., ISCA 2017 (Figure 2). Control logic is only ~2 %.",
             "A CPU spends a large share on control and caches; the TPU spends most of it on math and on-chip memory."])
    parts = [("Unified Buffer", 29, "act"), ("Matrix Multiply Unit", 24, "mxu"), ("Control", 2, "red"),
             ("everything else", 45, "ctl")]
    x, y, W = 40, 130, 900
    for name, pct, k in parts:
        w = W * pct / 100
        s.rect(x, y, w - 2, 70, C[f"{k}_bg"], C[k], 2, 6)
        if pct >= 20:
            s.text(x + w / 2, y + 32, name, 14, C.get(f"{k}_dk", C["ink"]), 700, "middle")
            s.text(x + w / 2, y + 52, f"{pct} %", 13, C.get(f"{k}_dk", C["ink"]), anchor="middle")
        else:
            s.text(x + w / 2, y + 42, f"{pct}%", 11, C[k], 700, "middle")
            s.line(x + w / 2, y + 72, x + w / 2, y + 100, C[k], 1.5)
            s.text(x + w / 2, y + 116, name, 12, C[k], 700, "middle")
        x += w
    s.text(40, 270, "\"Everything else\" = accumulators, activation pipeline, DRAM ports, PCIe and host interfaces, and I/O.", 12, C["muted"])
    s.text(40, 292, "Roughly half the die is the Unified Buffer plus the Matrix Multiply Unit. See the paper for the exact floor plan.", 12, C["muted"])
    s.save(P("tpu_v1_area.svg"))

# ---------------------------------------------------------------- roofline

def roofline():
    s = Svg(980, 600, "The roofline: is a workload limited by math or by memory?",
            ["Attainable performance = min(peak compute, bandwidth x arithmetic intensity). Log-log axes.",
             "Points: n x n x n int8 matrix multiplies (ops = 2n³, bytes = 3n²) on TPU v1's 34 GB/s weight memory."])
    x0, x1, y0, y1 = 110, 930, 540, 120
    lx0, lx1, ly0, ly1 = 0, 5, 9, 15.5       # log10 ranges
    X = lambda ai: x0 + (math.log10(ai) - lx0) / (lx1 - lx0) * (x1 - x0)
    Y = lambda p: y0 - (math.log10(p) - ly0) / (ly1 - ly0) * (y0 - y1)
    for d in range(lx0, lx1 + 1):
        s.line(X(10 ** d), y0, X(10 ** d), y1, C["line"], 1, dash="3 4")
        s.text(X(10 ** d), y0 + 20, f"{10 ** d:g}", 12, C["muted"], anchor="middle")
    for d in range(9, 16):
        s.line(x0, Y(10 ** d), x1, Y(10 ** d), C["line"], 1, dash="3 4")
        lab = {9: "1 G", 10: "10 G", 11: "100 G", 12: "1 T", 13: "10 T", 14: "100 T", 15: "1 P"}[d]
        s.text(x0 - 10, Y(10 ** d) + 4, lab, 12, C["muted"], anchor="end")
    s.text((x0 + x1) / 2, y0 + 44, "arithmetic intensity (operations per byte from memory)", 13, C["ink"], 600, "middle")
    s.text(40, (y0 + y1) / 2, "operations per second", 13, C["ink"], 600, "middle", rotate=-90)
    def roof(peak, bw, col, label):
        ridge = peak / bw
        pts = [(1, bw * 1), (ridge, peak), (10 ** lx1, peak)]
        d = "M" + " L".join(f"{X(a):.1f} {Y(p):.1f}" for a, p in pts)
        s.path(d, col, 3.5)
        s.circle(X(ridge), Y(peak), 5, col)
        s.text(X(ridge) + 8, Y(peak) - 10, f"{label}: ridge at {ridge:,.0f} ops/byte", 13, col, 700)
    roof(92e12, 34e9, C["wt"], "TPU v1")
    roof(275e12, 1200e9, C["mxu"], "TPU v4 (bfloat16, HBM)")
    for n in [16, 64, 256, 1024, 4096]:
        ai = 2 * n ** 3 / (3 * n * n)
        perf = min(92e12, 34e9 * ai)
        s.circle(X(ai), Y(perf), 7, C["act"], C["white"], 2)
        s.text(X(ai), Y(perf) + 24, f"n={n}", 12, C["act"], 700, "middle")
    s.text(X(3), Y(2e11) - 12, "memory-bound", 14, C["red"], 700, "middle", rotate=-38)
    s.text(X(3e4), Y(92e12) + 22, "compute-bound", 14, C["out"], 700, "middle")
    s.save(P("roofline.svg"))

# ---------------------------------------------------------------- application fit heat map

def application_fit():
    crit = ["matmul-heavy", "dense", "batchable", "low precision OK", "fixed shapes"]
    apps = [("Neural network training / inference", [3, 3, 3, 3, 3]),
            ("Ising / lattice Monte Carlo", [3, 3, 3, 2, 3]),
            ("Dense linear algebra (QR, eigen)", [3, 3, 2, 1, 3]),
            ("Radio beamforming", [3, 3, 3, 3, 3]),
            ("Batched short DFTs", [3, 3, 3, 2, 3]),
            ("Quantum circuit simulation", [3, 2, 2, 1, 3]),
            ("Weather ML models", [3, 3, 3, 3, 3]),
            ("Graph analytics", [2, 1, 2, 2, 1]),
            ("Homomorphic encryption", [2, 3, 3, 1, 3]),
            ("Branchy code (compilers, databases)", [1, 1, 1, 1, 1])]
    s = Svg(980, 590, "Does it fit a TPU? A quick score card",
            ["3 = strong fit, 2 = workable with tricks, 1 = poor fit. Judgment calls for discussion; see docs/14-new-applications.md."])
    col = {3: (C["out_bg"], C["out_dk"], "strong"), 2: (C["wt_bg"], C["wt_dk"], "tricks"), 1: (C["red_bg"], "#7F1D1D", "poor")}
    x0, y0, cw, rh = 330, 130, 120, 40
    for j, c in enumerate(crit):
        s.text(x0 + j * cw + cw / 2, y0 - 12, c, 13, C["ink"], 700, "middle")
    for i, (name, sc) in enumerate(apps):
        y = y0 + i * rh
        s.text(x0 - 12, y + 26, name, 13, C["ink"], 600, "end")
        for j, v in enumerate(sc):
            f, t, lab = col[v]
            s.rect(x0 + j * cw + 2, y + 3, cw - 4, rh - 6, f, None, 0, 6)
            s.text(x0 + j * cw + cw / 2, y + 26, lab, 12, t, 700, "middle")
    s.save(P("application_fit.svg"))


ALL = [energy_costs, tiling, dataflows, quantization, memory_hierarchy, controller_fsm, swap_wavefront,
       tpu_timeline, pod_torus, tpu_v1_area, roofline, application_fit]


def hero():
    """README banner: a chip package whose die is a systolic array mid-wavefront."""
    s = Svg(1200, 360)
    s.rect(0, 0, 1200, 360, "#1B2238", rx=0)
    # package + pins
    px, py, pw = 880, 40, 280
    for i in range(12):
        for side in range(4):
            if side == 0: s.rect(px + 18 + i * 21.5, py - 14, 10, 16, "#94A3B8", rx=2)
            if side == 1: s.rect(px + 18 + i * 21.5, py + pw - 2, 10, 16, "#94A3B8", rx=2)
            if side == 2: s.rect(px - 14, py + 18 + i * 21.5, 16, 10, "#94A3B8", rx=2)
            if side == 3: s.rect(px + pw - 2, py + 18 + i * 21.5, 16, 10, "#94A3B8", rx=2)
    s.rect(px, py, pw, pw, "#334155", "#475569", 3, 16)
    cols = {0: C["mxu"], 1: C["ps"], 2: C["act"]}
    for r in range(8):
        for c in range(8):
            d = r + c
            fill = {5: C["mxu"], 4: C["ps"], 6: "#A78BFA"}.get(d, "#EDE9FE" if d < 4 else "#C4B5FD")
            op = 1 if d in (4, 5, 6) else 0.35 if d > 6 else 0.9
            s.rect(px + 24 + c * 30, py + 24 + r * 30, 24, 24, fill, rx=5, opacity=op)
    s.text(60, 120, "terrific-tpu", 64, "#FFFFFF", 800)
    s.text(62, 170, "How a Tensor Processing Unit works: from the math,", 24, "#CBD5E1")
    s.text(62, 202, "to the Verilog, to real chips, to new ideas.", 24, "#CBD5E1")
    chips = [("2 Verilog chips", C["mxu"]), ("30+ diagrams", C["ps"]), ("6 web pages", C["act"]),
             ("5 applications", C["wt"]), ("5 experiments", C["out"]), ("sky130", C["red"])]
    x = 62
    for lab, col in chips:
        w = 11 + len(lab) * 8.2
        s.rect(x, 240, w, 34, col, rx=17)
        s.text(x + w / 2, 262, lab, 14, "#FFFFFF", 700, "middle")
        x += w + 10
    s.save(P("hero.svg"))


ALL.append(hero)


def isometric_array():
    """An 8 x 8 systolic array in isometric 3-D, mid-computation.
    Tower height = size of the partial sum inside each PE at that moment."""
    import random
    rng = random.Random(4)
    n, t, M = 8, 9, 6
    s = Svg(1100, 640, "Inside the array, in 3-D",
            ["An 8 x 8 weight-stationary array, 9 cycles into a batch of 6 vectors. Tower height = partial sum inside each PE.",
             "Sums grow as they fall down each column (toward the front). Blue marbles = activations entering from the left."])
    W = [[rng.randint(1, 7) for _ in range(n)] for _ in range(n)]
    X = [[rng.randint(1, 7) for _ in range(n)] for _ in range(M)]
    ox, oy, a, b = 600, 150, 44, 25

    def iso(r, c, z=0):
        return ox + (c - r) * a, oy + (c + r) * b - z

    def cube(r, c, h, top, left, right, stroke):
        x, y = iso(r, c)
        pts_top = [(x, y - h - b + b), (x + a, y - h + b - b + b), (x, y - h + 2 * b), (x - a, y - h + b)]
        pts_top = [(x, y - h), (x + a, y - h + b), (x, y - h + 2 * b), (x - a, y - h + b)]
        lf = [(x - a, y - h + b), (x, y - h + 2 * b), (x, y + 2 * b), (x - a, y + b)]
        rt = [(x + a, y - h + b), (x, y - h + 2 * b), (x, y + 2 * b), (x + a, y + b)]
        for pts, col in ((lf, left), (rt, right), (pts_top, top)):
            s.add('<polygon points="' + " ".join(f"{p:.1f},{q:.1f}" for p, q in pts) +
                  f'" fill="{col}" stroke="{stroke}" stroke-width="1"/>')

    # draw back-to-front (painter's algorithm)
    for r, c in sorted(((r, c) for r in range(n) for c in range(n)), key=lambda rc: (rc[0] + rc[1], rc[1])):
        if True:
            v = t - r - c
            active = 0 <= v < M
            psum = sum(X[v][k] * W[k][c] for k in range(r + 1)) if active else 0
            h = 10 + psum * 0.55
            if active:
                cube(r, c, h, "#E879F9", "#A21CAF", "#C026D3", "#701A75")
            else:
                cube(r, c, 10, "#EDE9FE", "#C4B5FD", "#DDD6FE", "#A78BFA")
            x, y = iso(r, c)
            s.add(f'<ellipse cx="{x:.1f}" cy="{y - h + b:.1f}" rx="9" ry="5" fill="{C["wt"]}" opacity="0.9"/>')
            if active and r + c == t - M + 1 + 0 and False:
                pass
    # activations entering on the left edge
    for r in range(n):
        v = t - r
        if 0 <= v < M:
            x, y = iso(r, -1)
            s.circle(x, y + b - 14, 11, C["act"], C["white"], 2)
            s.text(x, y + b - 10, str(X[v][r]), 11, "#FFFFFF", 700, "middle")
    s.legend(40, 130, [(C["ps"], "active PE (tower = partial sum)"), ("#C4B5FD", "idle PE"),
                       (C["wt"], "stored weight"), (C["act"], "activation entering")], 270)
    s.text(40, 600, "Front edge = bottom of the array, where finished sums leave. The magenta band is the wavefront.", 13, C["muted"])
    s.save(P("isometric_array.svg"))


def animated_wavefront():
    """SMIL-animated SVG (animates on GitHub, in browsers, in <img> tags)."""
    n, dur = 6, 4.0
    s = Svg(760, 460)
    s.text(30, 40, "The systolic heartbeat (animated)", 22, C["ink"], 700)
    s.text(30, 64, "Each wave crosses the array diagonally, one step per clock tick; sums flow down, data flows right.", 13, C["muted"])
    x0, y0, cs = 200, 90, 56
    for r in range(n):
        for c in range(n):
            x, y = x0 + c * cs, y0 + r * cs
            delay = (r + c) * 0.18
            s.add(f'<rect x="{x}" y="{y}" width="{cs - 8}" height="{cs - 8}" rx="9" fill="{C["mxu_bg"]}" stroke="{C["mxu"]}" stroke-width="1.5">'
                  f'<animate attributeName="fill" values="{C["mxu_bg"]};{C["mxu"]};{C["ps"]};{C["mxu_bg"]};{C["mxu_bg"]}" '
                  f'keyTimes="0;0.08;0.18;0.32;1" dur="{dur}s" begin="{delay:.2f}s" repeatCount="indefinite"/></rect>')
        # activation marble travelling right along row r
        s.add(f'<circle cx="{x0 - 30}" cy="{y0 + r * cs + (cs - 8) / 2}" r="9" fill="{C["act"]}">'
              f'<animate attributeName="cx" values="{x0 - 30};{x0 + n * cs}" dur="{n * 0.18 + 0.2:.2f}s" begin="{r * 0.18:.2f}s" '
              f'repeatCount="indefinite"/><animate attributeName="opacity" values="1;1;0" keyTimes="0;0.85;1" '
              f'dur="{n * 0.18 + 0.2:.2f}s" begin="{r * 0.18:.2f}s" repeatCount="indefinite"/></circle>')
    for c in range(n):
        s.add(f'<rect x="{x0 + c * cs + 10}" y="{y0 + n * cs + 6}" width="{cs - 28}" height="16" rx="4" fill="{C["out"]}" opacity="0">'
              f'<animate attributeName="opacity" values="0;0;1;0" keyTimes="0;0.35;0.45;0.7" dur="{dur}s" begin="{c * 0.18:.2f}s" repeatCount="indefinite"/></rect>')
    s.text(x0 - 40, y0 - 12, "activations →", 12, C["act"], 700)
    s.text(x0 + n * cs + 10, y0 + n * cs + 18, "results", 12, C["out"], 700)
    s.save(P("animated_wavefront.svg"))


ALL += [isometric_array, animated_wavefront]
