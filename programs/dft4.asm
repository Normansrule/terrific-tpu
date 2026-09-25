; =====================================================================
;  dft4.asm  -  a Discrete Fourier Transform (DFT) on the TinyTPU
; ---------------------------------------------------------------------
;  A 4-point DFT is just a matrix multiply:
;      real part  = x @ C      C[k][n] =  cos(2*pi*k*n/4)
;      imag part  = x @ S      S[k][n] = -sin(2*pi*k*n/4)
;  For 4 points every entry is -1, 0 or 1, so the answer is exact.
;
;  Memory map
;    weight memory : C @0..3, S @4..7
;    unified buf   : 8 signals @0..7 (and @8..15 unused, zero)
;                    real spectra @16..23, imaginary spectra @24..31
;    accumulators  : real @0..7, imaginary @8..15
; =====================================================================
LDW   w=0                    ; cosine matrix
MMUL  ub=0  rows=8 acc=0     ; real parts for all 8 signals
LDW   w=4                    ; minus-sine matrix
MMUL  ub=0  rows=8 acc=8     ; imaginary parts
ACT   acc=0 rows=8 ub=16 shift=0
ACT   acc=8 rows=8 ub=24 shift=0
HALT
