; =====================================================================
;  graph_paths.asm  -  counting walks and triangles in a graph
; ---------------------------------------------------------------------
;  A is the 8 x 8 adjacency matrix of an 8-node graph (A[i][j] = 1 if
;  there is an edge). Matrix powers count walks:
;     (A^2)[i][j] = number of 2-step walks from i to j
;     (A^3)[i][i] = 2 x (number of triangles through node i)
;  so  triangles = trace(A^3) / 6.
;
;  8 x 8 on a 4 x 4 array = 2 K-tiles x 2 column tiles per product.
;  weight memory : A[0:4,0:4] @0, A[4:8,0:4] @4, A[0:4,4:8] @8, A[4:8,4:8] @12
;  unified buf   : A[:,0:4] @0..7, A[:,4:8] @8..15, A^2 halves @16..23, @24..31
;  accumulators  : A^2 @0..15, A^3 @16..31
; =====================================================================
; ---- A^2 = A @ A ----
LDW   w=0
MMUL  ub=0  rows=8 acc=0
LDW   w=4
MMUL  ub=8  rows=8 acc=0 accumulate
LDW   w=8
MMUL  ub=0  rows=8 acc=8
LDW   w=12
MMUL  ub=8  rows=8 acc=8 accumulate
ACT   acc=0 rows=8 ub=16 shift=0            ; A^2 columns 0-3 back to 8 bits
ACT   acc=8 rows=8 ub=24 shift=0            ; A^2 columns 4-7
; ---- A^3 = A^2 @ A ----
LDW   w=0
MMUL  ub=16 rows=8 acc=16
LDW   w=4
MMUL  ub=24 rows=8 acc=16 accumulate
LDW   w=8
MMUL  ub=16 rows=8 acc=24
LDW   w=12
MMUL  ub=24 rows=8 acc=24 accumulate
HALT
