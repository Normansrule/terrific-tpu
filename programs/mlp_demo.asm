; =====================================================================
;  mlp_demo.asm  -  a 2-layer neural network on the TinyTPU
; ---------------------------------------------------------------------
;     H = ReLU( X @ W1 ) >> 3        X: 8x8, W1: 8x4  (two 4x4 tiles)
;     Y =     ( H @ W2 ) >> 5        W2: 4x4
;
;  Memory map
;    weight memory : W1 top tile @0, W1 bottom tile @4, W2 @8
;    unified buf   : X[:,0:4] @0..7, X[:,4:8] @8..15,
;                    hidden H @16..23, output Y @24..31
;    accumulators  : layer 1 @0..7, layer 2 @8..15
;
;  Scheduling note: "LDW w=8" is placed BEFORE the first ACT. ACT never
;  touches the array, so on the v2 (pipelined) chip the layer-2 weights
;  stream into the shadow registers while layer-1 results are still
;  draining. On v1 the order makes no difference. Compilers for real
;  TPUs do this kind of reordering all the time.
; =====================================================================

; ---- Layer 1 (K = 8, so two tiles added in the accumulators) ----
LDW   w=0                            ; W1 rows 0..3
MMUL  ub=0  rows=8  acc=0            ; acc  = X[:,0:4] @ W1[0:4,:]
LDW   w=4                            ; W1 rows 4..7
MMUL  ub=8  rows=8  acc=0 accumulate ; acc += X[:,4:8] @ W1[4:8,:]
LDW   w=8                            ; W2 (early: overlaps the drain on v2)
ACT   acc=0 rows=8  ub=16 relu shift=3

; ---- Layer 2 ----
MMUL  ub=16 rows=8  acc=8
ACT   acc=8 rows=8  ub=24 shift=5

HALT
