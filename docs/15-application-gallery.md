# 15 · Application gallery: three problems that aren't neural networks

> **In one sentence:** anything you can phrase as "multiply a batch of vectors by a fixed matrix" runs on a TPU, and that covers far more than neural networks: image processing, quantum computing, and graph analysis all fit.

Each application below is a real program in [`programs/`](../programs/), runs on **both** Verilog chips, and is checked against math done a completely different way ([`tools/apps.py`](../tools/apps.py)). Every picture on this page is drawn from the chip's **own memories**, dumped by the testbench after the Verilog run. Try all three live in the [applications page](../web/apps.html).

```bash
make apps        # runs all three on v1 and v2, checks them, prints cycle counts
```

| Application | Program | v1 cycles | v2 cycles | Useful MACs | Checked against |
|---|---|---|---|---|---|
| Image filtering | `conv2d.asm` | 306 | 291 | 3,072 | direct sliding-window convolution |
| Quantum search | `grover2.asm` | 128 | 123 | 320 | floating-point state-vector simulation |
| Graph triangles | `graph_paths.asm` | 207 | 163 | 1,024 | brute-force triangle search |

---

## 1 · Image filtering (convolution via im2col)

<img src="../diagrams/app_conv.svg" alt="Four feature maps computed on the chip" width="900">

A convolution slides a small filter over an image. It doesn't look like a matrix multiply, until you use the **im2col** trick ("image to columns"):

1. Cut out every 3 × 3 window of the image and flatten it into a row of 9 numbers. A 10 × 10 image has 8 × 8 = 64 windows, so you get a 64 × 9 matrix.
2. Flatten each filter into a column of 9 weights. Four filters make a 9 × 4 matrix.
3. Multiply: `(64 × 9) · (9 × 4) = 64 × 4`. Row i, column j is filter j's response at window i.

K = 9 isn't a multiple of 4, so it is padded to 12 and split into three K-tiles that add up in the accumulators (the same tiling as [lesson 6](06-tiling.md)). `ACT ... relu shift=1` keeps positive responses and halves them so they fit in 8 bits.

**Why it matters:** this is exactly how convolutional neural networks ran on TPU v1, and it is 63 % utilization in [experiment 4](16-experiments.md), the best of all the demos, because 64 windows is a big batch.

**The cost of the trick:** each pixel appears in up to 9 windows, so im2col copies the image up to 9 times. Real accelerators avoid this duplication in hardware.

## 2 · Grover's quantum search on 2 qubits

<img src="../diagrams/app_grover.svg" alt="Grover's algorithm amplitudes after each gate" width="900">

A quantum computer with 2 qubits is described by 4 numbers (amplitudes), one per basis state |00⟩, |01⟩, |10⟩, |11⟩. Every quantum gate is a 4 × 4 matrix. So simulating a quantum circuit **is** a chain of matrix multiplies:

| Gate | Matrix | What it does |
|---|---|---|
| H ⊗ H | ½ × (a ±1 pattern) | spread the state evenly over all 4 answers |
| Oracle | diagonal, −1 on the marked item | secretly flip the sign of the right answer |
| 2\|00⟩⟨00\| − I | diagonal (1, −1, −1, −1) | together with the H's: "reflect about the average" |

After one oracle and one reflection, all the amplitude has piled onto the marked item: measuring gives it **100 %** of the time, where a classical search of 4 items needs up to 3 guesses.

TinyTPU details:
* Amplitudes are scaled so **64 means 1.0**. The ½ in H ⊗ H becomes `shift=1` in `ACT`. Every intermediate value happens to be an exact multiple of ½ · 64, so there is **no rounding error at all**.
* **Batch trick:** the 4 input rows are the 4 basis states. So the 4 output rows are the 4 columns of the whole circuit's unitary matrix, computed in one pass.
* Try other marked items: `python3 tools/golden_model.py --demo grover --marked 1`.

**Where this goes:** quantum circuit simulators (for example Google's qsim and TensorFlow Quantum) really do run on TPUs and GPUs, because a circuit of n qubits is a chain of 2ⁿ × 2ⁿ matrix products. Beyond ~40 qubits the vectors no longer fit in memory, which is one reason people build quantum computers at all.

## 3 · Walks and triangles in a graph

<img src="../diagrams/app_graph.svg" alt="Adjacency matrix powers and triangles" width="900">

Write a graph as its **adjacency matrix** A: `A[i][j] = 1` if there is an edge between node i and node j. Then matrix powers count walks:

* `(A²)[i][j]` = number of 2-step walks from i to j. The diagonal of A² is each node's degree.
* `(A³)[i][i]` = number of 3-step walks from i back to itself = 2 × (triangles through i), since each triangle can be walked in two directions.
* So **triangles = trace(A³) ÷ 6**.

The 8-node graph needs 8 × 8 matrices on a 4 × 4 array: 2 K-tiles × 2 column tiles per product. A² goes back to the Unified Buffer through `ACT` (shift 0, the numbers are small) and becomes the input for A³.

**Where this goes:** "graph analytics as linear algebra" is a whole field (the GraphBLAS standard). Triangle counts measure clustering in social networks; matrix powers rank web pages (PageRank) and find shortest paths. Real graphs are **sparse** (mostly zeros), which is where dense TPUs struggle; see the fit checklist in [lesson 14](14-new-applications.md).

**Next → [16 · Experiments](16-experiments.md)**
