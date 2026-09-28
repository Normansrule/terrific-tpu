# 17 · Hands-on labs

Each lab has a goal, the files you touch, hints, and a clear "done" test. Run `make test` after every lab; it runs the demos, 200 random programs per chip version, the size sweep, the browser-model check, and the mutation test.

| Lab | Topic | Difficulty |
|---|---|---|
| 1 | Grow the array | 🟢 |
| 2 | Add an instruction | 🟡 |
| 3 | Break v2 on purpose | 🟢 |
| 4 | Overlap `ACT` with `MMUL` | 🔴 |
| 5 | A Fourier transform on TinyTPU (worked example) | 🟢 |
| 6 | Toward silicon | 🟡 |
| 7 | Output-stationary array | 🔴 |
| 8 | Your own application | 🟡 |

---

## Lab 1 · Grow the array

**Goal:** see what changes (and what doesn't) when N goes from 4 to 8.

1. Run `make scale`. Both chip versions already pass at N = 2, 4, 8, 16 ([`tb/tb_scale.v`](../tb/tb_scale.v)).
2. Predict the v1 cycle counts first: `(2 + N)` for `LDW` + `(2 + rows + 2N − 1)` for `MMUL` + `3` for `HALT`, with rows = 5. Then check.
3. Make the neural-network demo run at N = 8: change `N` in `tools/golden_model.py` and `tb/tb_tpu_top.v`, and rewrite `programs/mlp_demo.asm`. (With an 8-wide array, layer 1 needs only one tile.)

**Done when:** `make` passes at N = 8 and you can explain why the program got shorter.

## Lab 2 · Add an instruction

**Goal:** add `CLR acc=A rows=B` (opcode `0x4`) that zeroes accumulator rows.

Touch, in order:
1. [`tools/tpu_isa_sim.py`](../tools/tpu_isa_sim.py): define what `CLR` means. **Always start with the model.**
2. [`tools/tpu_asm.py`](../tools/tpu_asm.py) and [`web/tinytpu-core.js`](../web/tinytpu-core.js): assembler and disassembler.
3. `rtl/common/accumulators.v`: a clear path. `rtl/v1_simple/controller.v` and `rtl/v2_pipelined/controller_pipe.v`: a new state. (On v2: must `CLR` wait for `pipe_busy`? Why?)
4. `tools/golden_model.py`: let the fuzzer generate `CLR`.
5. `tools/mutation_test.sh`: add a mutant that breaks `CLR`, and make sure it is killed.

**Done when:** `make test` passes, including your new mutant.

## Lab 3 · Break v2 on purpose

**Goal:** feel why hazard checks exist.

1. In `rtl/v2_pipelined/controller_pipe.v`, delete the `pipe_busy` part of `stall`.
2. Run `make fuzz V=v2_pipelined`. Pick a failing seed and print its program: `python3 tools/golden_model.py --demo fuzz --seed <N> -v`.
3. Find the `ACT` that follows an `MMUL` writing the same accumulator rows. Draw its timeline by hand, cycle by cycle.
4. Put the check back. Now try the smallest legal change that would let that `ACT` start *earlier*: it only needs to wait for **its own** rows, not for every result in flight.

**Done when:** you can explain the failure in two sentences, and your smarter check (if you built one) still passes `make test`.

## Lab 4 · Overlap `ACT` with `MMUL`

**Goal:** go beyond v2.

v2 overlaps `LDW` with a draining `MMUL`, but `ACT` still waits for everything. Real TPUs run the activation pipeline in parallel with the matrix unit. Design a v3 where the controller can **issue an `ACT` and an `MMUL` at the same time** when they touch different memory rows.

Hints: you need two execution "slots" in the controller, a way to check row ranges for overlap (a scoreboard), and the Unified Buffer must accept a read (for `MMUL`) and a write (for `ACT`) in the same cycle (it already can).

**Done when:** `make fuzz V=v3_yours` passes and the demo beats 77 cycles.

## Lab 5 · A Fourier transform on TinyTPU

**This one is built. Read it as a worked example of a "new application".**

A 4-point Discrete Fourier Transform (DFT) is a matrix multiply by a matrix of cosines and a matrix of minus-sines. For 4 points every entry is −1, 0, or 1, so an 8-bit machine computes it **exactly**:

```
C (cosine)            S (minus sine)
[ 1  1  1  1 ]        [ 0  0  0  0 ]
[ 1  0 -1  0 ]        [ 0 -1  0  1 ]
[ 1 -1  1 -1 ]        [ 0  0  0  0 ]
[ 1  0 -1  0 ]        [ 0  1  0 -1 ]
```

```bash
make dft
```

The answer key is checked against Python's complex-number DFT, then both chips are checked against the answer key. Check one by hand: the first real output is just the sum of the signal.

Run it in the browser too: the [whole-chip simulator](../web/chip.html) has a "Fourier" preset.

**Extend it:** an 8-point DFT on an N = 8 array. The entries become cos(45°) ≈ 0.707, so scale by 64 and use `shift=6`. How big is the rounding error compared with exact math?

## Lab 6 · Toward silicon

**Goal:** turn the synthesis numbers from [lesson 12](12-rtl-to-silicon.md) into a real Tiny Tapeout plan.

1. Run `make synth` with the sky130 library (see lesson 12). Confirm you get the same areas as `data/synth.csv`.
2. Shrink the memories to 16 entries and synthesize `tpu_top` for N = 2. How many cells now?
3. Design a Serial Peripheral Interface (SPI) front end so a microcontroller can write programs and data and read results.
4. Read the [Tiny Tapeout](https://tinytapeout.com/) docs: how many tiles would your design need?

**Done when:** you have a table of cell counts and area for your tapeout candidate, and a pin list.

## Lab 7 · Output-stationary array

**Goal:** build the other famous dataflow ([lesson 5](05-dataflow-and-energy.md)).

Each PE keeps its own running total `y[i][j]`. Activations flow right, **weights flow down**, and after K steps each PE holds a finished output that you shift out.

Write `pe_os.v` and `systolic_array_os.v` and a testbench that compares against a plain-Python matrix multiply. Then synthesize both with `tools/synth_report.sh` (add your design to it) and compare area.

**Done when:** your array passes a random-matrix test and you can name one advantage of each dataflow, with numbers.

## Lab 8 · Your own application

**Goal:** use the [fit checklist](14-new-applications.md) on a problem you care about.

1. Pick one idea from [lesson 14](14-new-applications.md) (or your own).
2. Write the core math as `Y = X · W` with 4-wide chunks.
3. Add a `--demo yours` to `tools/golden_model.py` that checks the instruction-level model against plain math, like `demo_dft` does.
4. Write the `.asm` program, run it on both chips, and measure utilization.

**Done when:** `make` passes with your demo, and you have written one paragraph: would this be fast on a real TPU, and why or why not?

**Next → [18 · References](18-references.md)** · For bigger projects, see [19 · Research frontiers](19-research-frontiers.md).
