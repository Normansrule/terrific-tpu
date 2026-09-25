; =====================================================================
;  conv2d.asm  -  image filtering (a convolution) as one matrix multiply
; ---------------------------------------------------------------------
;  "im2col" trick: every 3x3 patch of a 10x10 image becomes one ROW of a
;  64 x 9 matrix (64 output pixels, 9 pixels per patch). Four 3x3 filters
;  become the 9 x 4 weight matrix (one COLUMN per filter). Then
;
;        feature maps (64 x 4) = patches (64 x 9) @ filters (9 x 4)
;
;  K = 9 is padded to 12 = three 4-wide K-tiles.
;
;  weight memory : filter rows 0-3 @0, 4-7 @4, 8 (+zeros) @8
;  unified buf   : patch columns 0-3 @0..63, 4-7 @64..127, 8 @128..191
;                  output feature maps @192..255 (one row per pixel)
;  filters       : lane 0 Sobel-x, lane 1 Sobel-y, lane 2 blur, lane 3 Laplacian
; =====================================================================
LDW   w=0
MMUL  ub=0   rows=64 acc=0
LDW   w=4
MMUL  ub=64  rows=64 acc=0 accumulate
LDW   w=8
MMUL  ub=128 rows=64 acc=0 accumulate
ACT   acc=0  rows=64 ub=192 relu shift=1   ; keep positive responses, halve
HALT
