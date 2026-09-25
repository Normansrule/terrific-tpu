; =====================================================================
;  grover2.asm  -  Grover's quantum search on 2 qubits, on a TPU
; ---------------------------------------------------------------------
;  A quantum computer's state is a vector; every gate is a matrix. So a
;  small quantum circuit is just a chain of matrix multiplies, which is
;  exactly what TinyTPU does. Amplitudes are scaled so 64 means 1.0.
;
;  Circuit:  H(x)H  ->  oracle  ->  H(x)H  ->  (2|00><00| - I)  ->  H(x)H
;  H(x)H is stored as its +-1 pattern; its 1/2 factor is the "shift=1".
;
;  Batch trick: the 4 input rows are the 4 basis states |00>..|11>, so the
;  4 output rows are the 4 columns of the whole circuit's matrix.
;
;  weight memory : H(x)H @0, oracle (marks one item) @4, 2|00><00|-I @8
;  unified buf   : inputs @0..3, after each stage @8, 12, 16, 20, 24
; =====================================================================
LDW   w=0                              ; H(x)H: equal superposition
MMUL  ub=0  rows=4 acc=0
ACT   acc=0  rows=4 ub=8  shift=1
LDW   w=4                              ; oracle: flip the sign of the marked item
MMUL  ub=8  rows=4 acc=4
ACT   acc=4  rows=4 ub=12 shift=0
LDW   w=0                              ; diffusion = H(x)H . (2|00><00| - I) . H(x)H
MMUL  ub=12 rows=4 acc=8
ACT   acc=8  rows=4 ub=16 shift=1
LDW   w=8
MMUL  ub=16 rows=4 acc=12
ACT   acc=12 rows=4 ub=20 shift=0
LDW   w=0
MMUL  ub=20 rows=4 acc=16
ACT   acc=16 rows=4 ub=24 shift=1      ; row 0 = final state starting from |00>
HALT
