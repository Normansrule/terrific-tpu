"""apps.py - data and independent reference math for the application demos.

Each builder returns (program_file, wmem_rows, ub_rows, check) where
check(tpu) compares the instruction-level model's final memories with
math done a completely different way (plain loops, floats, graph code).
"""
import math

N = 4

# --------------------------------------------------------------- conv2d
FILTERS = {
    "Sobel x (vertical edges)":   [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]],
    "Sobel y (horizontal edges)": [[-1, -2, -1], [0, 0, 0], [1, 2, 1]],
    "Blur (box)":                 [[1, 1, 1], [1, 1, 1], [1, 1, 1]],
    "Laplacian (outlines)":       [[0, -1, 0], [-1, 4, -1], [0, -1, 0]],
}


def default_image():
    """10 x 10, 4-bit grayscale: a bright square, a dim bar, a diagonal."""
    img = [[0] * 10 for _ in range(10)]
    for r in range(2, 7):
        for c in range(1, 5):
            img[r][c] = 15
    for r in range(1, 9):
        img[r][7] = 8
    for i in range(10):
        img[i][9 - i] = max(img[i][9 - i], 5)
    return img


def conv_build(img=None):
    img = img or default_image()
    patches = []
    for r in range(8):
        for c in range(8):
            patches.append([img[r + i][c + j] for i in range(3) for j in range(3)] + [0, 0, 0])
    ub = [p[0:4] for p in patches] + [p[4:8] for p in patches] + [p[8:12] for p in patches]
    W = [[f[k // 3][k % 3] for f in FILTERS.values()] for k in range(9)] + [[0] * 4] * 3
    wmem = W[0:4] + W[4:8] + W[8:12]

    def check(t):
        for r in range(8):
            for c in range(8):
                for ch, f in enumerate(FILTERS.values()):
                    s = sum(f[i][j] * img[r + i][c + j] for i in range(3) for j in range(3))
                    exp = max(-128, min(127, max(0, s) >> 1))
                    assert t.ub[192 + r * 8 + c][ch] == exp, (r, c, ch)
        return "conv2d: 4 feature maps == direct sliding-window convolution"
    return "conv2d.asm", wmem, ub, check

# --------------------------------------------------------------- grover

HH = [[1, 1, 1, 1], [1, -1, 1, -1], [1, 1, -1, -1], [1, -1, -1, 1]]


def grover_build(marked=3):
    oracle = [[(-1 if (i == j == marked) else 1) if i == j else 0 for j in range(4)] for i in range(4)]
    z0 = [[(1 if i == 0 else -1) if i == j else 0 for j in range(4)] for i in range(4)]
    wmem = HH + oracle + z0
    ub = [[64 if i == j else 0 for j in range(4)] for i in range(4)]

    def check(t):
        # float state-vector simulation with the real 1/2 factors
        def apply(G, v, s=1.0):
            return [s * sum(G[i][k] * v[k] for k in range(4)) for i in range(4)]
        for start in range(4):
            v = [1.0 if k == start else 0.0 for k in range(4)]
            for G, s in ((HH, .5), (oracle, 1), (HH, .5), (z0, 1), (HH, .5)):
                v = apply(G, v, s)
            assert t.ub[24 + start] == [round(64 * x) for x in v], (start, t.ub[24 + start], v)
        final = t.ub[24]
        prob = [a * a / 4096 for a in final]
        assert abs(prob[marked] - 1.0) < 1e-9
        return f"grover: found item |{marked:02b}> with probability {prob[marked]:.0%} (float simulation agrees)"
    return "grover2.asm", wmem, ub, check

# --------------------------------------------------------------- graph

EDGES = [(0, 1), (1, 2), (2, 0), (2, 3), (3, 4), (4, 5), (5, 3), (5, 6), (6, 7), (7, 4), (1, 6), (0, 7)]


def adjacency(edges=EDGES):
    A = [[0] * 8 for _ in range(8)]
    for a, b in edges:
        A[a][b] = A[b][a] = 1
    return A


def graph_build(edges=EDGES):
    A = adjacency(edges)
    wmem = [A[k][0:4] for k in range(0, 4)] + [A[k][0:4] for k in range(4, 8)] + \
           [A[k][4:8] for k in range(0, 4)] + [A[k][4:8] for k in range(4, 8)]
    ub = [A[i][0:4] for i in range(8)] + [A[i][4:8] for i in range(8)]

    def check(t):
        A2 = [[sum(A[i][k] * A[k][j] for k in range(8)) for j in range(8)] for i in range(8)]
        A3 = [[sum(A2[i][k] * A[k][j] for k in range(8)) for j in range(8)] for i in range(8)]
        for i in range(8):
            assert t.acc[i] == A2[i][0:4] and t.acc[8 + i] == A2[i][4:8]
            assert t.acc[16 + i] == A3[i][0:4] and t.acc[24 + i] == A3[i][4:8]
        tri_tpu = sum(t.acc[16 + i][i] if i < 4 else t.acc[24 + i][i - 4] for i in range(8)) // 6
        tri_direct = sum(1 for a in range(8) for b in range(a + 1, 8) for c in range(b + 1, 8)
                         if A[a][b] and A[b][c] and A[a][c])
        assert tri_tpu == tri_direct
        return f"graph: A^2, A^3 correct; {tri_tpu} triangles (brute-force search agrees)"
    return "graph_paths.asm", wmem, ub, check
