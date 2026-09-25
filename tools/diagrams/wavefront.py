#!/usr/bin/env python3
"""
wavefront.py - draws diagrams/systolic_wavefront.svg

Shows a 4x4 weight-stationary systolic array multiplying THREE input
vectors x0, x1, x2 by a weight matrix W, one clock cycle per panel.

Timing rule (the same one the RTL follows):
    vector v is inside PE(row k, column n) during cycle  t = v + k + n
so each vector moves through the grid as a diagonal "wavefront".

Run:  make diagrams   (or python3 tools/diagrams/make_all.py)
"""
import os

N = 4
W = [[1, 2, 0, -1],
     [0, 1, 3, 2],
     [2, 0, 1, 1],
     [1, -1, 2, 0]]
X = [[1, 2, 3, 4],
     [2, 0, 1, 1],
     [-1, 1, 0, 2]]
COLORS = ["#2563EB", "#0891B2", "#7C3AED"]      # x0, x1, x2
LIGHT = ["#DBEAFE", "#CFFAFE", "#EDE9FE"]
CYCLES = (len(X) - 1) + 2 * (N - 1)              # last busy cycle


def psum(v, k, n):
    return sum(X[v][i] * W[i][n] for i in range(k + 1))


def panel(t, ox, oy):
    cell, gap = 60, 8
    out = [f'<g transform="translate({ox},{oy})">',
           f'<text x="0" y="0" font-size="16" font-weight="700" fill="#1E293B">cycle {t}</text>']
    top = 16
    for k in range(N):
        for n in range(N):
            x = 26 + n * (cell + gap)
            y = top + k * (cell + gap)
            v = t - k - n
            if 0 <= v < len(X):
                out.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="7" '
                           f'fill="{LIGHT[v]}" stroke="{COLORS[v]}" stroke-width="2.5"/>')
                out.append(f'<text x="{x + cell/2}" y="{y + 20}" text-anchor="middle" font-size="12" '
                           f'fill="{COLORS[v]}" font-weight="700">x={X[v][k]}</text>')
                out.append(f'<text x="{x + cell/2}" y="{y + 39}" text-anchor="middle" font-size="13" '
                           f'fill="#A21CAF" font-weight="700">Σ={psum(v, k, n)}</text>')
            else:
                out.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="7" '
                           f'fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.5"/>')
                out.append(f'<text x="{x + cell/2}" y="{y + 30}" text-anchor="middle" font-size="11" '
                           f'fill="#94A3B8">w={W[k][n]}</text>')
        # the input entering row k this cycle (from the skew registers)
        v = t - k
        if 0 <= v < len(X):
            out.append(f'<text x="18" y="{top + k*(cell+gap) + 30}" text-anchor="end" font-size="12" '
                       f'font-weight="700" fill="{COLORS[v]}">{X[v][k]}▶</text>')
    # finished results leaving the bottom this cycle
    for n in range(N):
        v = t - (N - 1) - n
        if 0 <= v < len(X):
            x = 26 + n * (cell + gap) + cell / 2
            y = top + N * (cell + gap) + 12
            out.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-size="12" font-weight="700" '
                       f'fill="#059669">▼ y{v}[{n}]</text>')
            out.append(f'<text x="{x}" y="{y + 16}" text-anchor="middle" font-size="13" font-weight="700" '
                       f'fill="#059669">{psum(v, N-1, n)}</text>')
    out.append('</g>')
    return "\n".join(out)


def main():
    cols = 3
    pw, ph = 320, 340
    rows = (CYCLES + cols) // cols
    width, height = cols * pw + 40, rows * ph + 150
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
             f'font-family="Segoe UI, Helvetica, Arial, sans-serif">',
             f'<rect width="{width}" height="{height}" fill="#F8FAFC"/>',
             '<text x="24" y="40" font-size="24" font-weight="700" fill="#1E293B">'
             'The wavefront: 3 vectors flowing through a 4 x 4 systolic array</text>',
             '<text x="24" y="64" font-size="14" fill="#475569">Each colored cell is doing a multiply-accumulate '
             'for that vector this cycle. Grey cells are idle and show their stored weight.</text>',
             '<text x="24" y="86" font-size="14" fill="#475569">Inputs enter from the left one row later each '
             '(the skew). Green results fall out of the bottom, one column later each.</text>']
    for i, (c, name) in enumerate(zip(COLORS, ["x0", "x1", "x2"])):
        parts.append(f'<rect x="{24 + i*90}" y="100" width="16" height="16" rx="3" fill="{c}"/>'
                     f'<text x="{46 + i*90}" y="113" font-size="13" fill="#334155">vector {name}</text>')
    for t in range(CYCLES + 1):
        r, c = divmod(t, cols)
        parts.append(panel(t, 24 + c * pw, 150 + r * ph))
    parts.append("</svg>")
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "..", "diagrams", "systolic_wavefront.svg")
    with open(path, "w") as fh:
        fh.write("\n".join(parts))
    print("wrote", os.path.normpath(path))
    print("check: y = x @ W =", [[psum(v, N-1, n) for n in range(N)] for v in range(len(X))])


if __name__ == "__main__":
    main()
