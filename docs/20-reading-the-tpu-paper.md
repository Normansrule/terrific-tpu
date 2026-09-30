# 20 · Reading the TPU v1 paper with this repo

> **In one sentence:** "In-Datacenter Performance Analysis of a Tensor Processing Unit" (Jouppi et al., ISCA 2017, [arXiv 1704.04760](https://arxiv.org/abs/1704.04760)) is the paper TinyTPU is modeled on; this guide walks through it section by section and points to where each idea lives in the repo.

Read the paper with this page open next to it. Each row says what to look for, and where to see it running.

## The map

| Paper section | What to look for | See it here |
|---|---|---|
| **Introduction** | Why Google built a chip: projected growth in neural-network inference would have required far more datacenter capacity on CPUs alone. The chip went from start to deployment in about 15 months. | [Lesson 1](01-what-is-a-tpu.md) |
| **TPU origin, architecture, implementation** | The block diagram: host interface, Unified Buffer, Matrix Multiply Unit, accumulators, activation pipeline, weight FIFO fed from off-chip weight memory. | [3-D tour](../web/tour.html), [lesson 7](07-architecture.md), `rtl/v1_simple/tpu_top.v` |
| (same) | The Matrix Multiply Unit: 256 × 256 8-bit multiply-accumulate cells, 32-bit accumulators. | [lesson 4](04-systolic-arrays.md), `rtl/v1_simple/pe.v` |
| (same) | Weights are staged tile by tile and **double-buffered**, so shifting in the next tile overlaps computation. | [lesson 10](10-pipelining-v2.md), `rtl/v2_pipelined/pe_db.v` |
| (same) | A handful of CISC instructions (read host memory, read weights, matrix multiply or convolve, activate, write host memory) that each run for many cycles. | [lesson 9](09-instruction-set.md), `tools/tpu_asm.py` |
| (same) | Data moves through the array in a diagonal wavefront; the paper's systolic-dataflow figure is the same picture as TinyTPU's. | [systolic playground](../web/playground.html), `diagrams/systolic_wavefront.svg` |
| (same) | The floor plan: Unified Buffer and matrix unit dominate; control is tiny. | `diagrams/tpu_v1_area.svg`, [chip X-ray](../web/xray.html) |
| **CPU, GPU, and TPU platforms** | The comparison machines (a server CPU and a GPU of the same era), and how they were measured. | [the race](../web/race.html) (a simplified version of the same comparison) |
| **Performance: rooflines, response time, throughput** | The roofline plot: several production networks sit left of the ridge, **memory-bound** on 34 GB/s DDR3 weight memory. Also why response-time limits (tail latency) force small batches. | [lesson 11](11-performance.md), [roofline explorer](../web/explorers.html) |
| **Cost-performance, TCO, performance/Watt** | Performance per watt, the metric that justified the chip; total cost of ownership (TCO) rather than peak speed. | [experiment 3](16-experiments.md#experiment-3--where-the-energy-goes) |
| **Energy proportionality** | How power scales with load; the TPU wasted energy when lightly loaded. | experiment 4 (idle PEs in the space-time map) |
| **Evaluation of alternative TPU designs** | What-if studies: faster memory helps most; a bigger clock or bigger array helps far less. | [experiment 5](16-experiments.md#experiment-5--bigger-arrays-hit-diminishing-returns), [lesson 19 §4](19-research-frontiers.md#4--feeding-the-array-memory-and-interconnect) |
| **Discussion, fallacies and pitfalls** | Lessons such as "architects neglected important neural networks" and the danger of optimizing for peak TOPS instead of real workloads. | [lesson 14](14-new-applications.md) |

## Five questions to answer while reading

1. The paper reports that several applications are memory-bound on TPU v1. Using the [roofline explorer](../web/explorers.html) with the TPU v1 preset, what arithmetic intensity would they need to become compute-bound?
2. Why does double-buffering the weights matter more for small batches than large ones? (Check against `diagrams/utilization_vs_batch.svg`.)
3. TinyTPU's `ACT` uses a 3-bit shift for requantization. What does the TPU v1 activation pipeline do, and why does experiment 2 suggest TinyTPU's choice is too simple?
4. The paper's alternative-design study favors faster memory over more multipliers. Reproduce that conclusion qualitatively with experiment 5 by changing the timing model.
5. List three things TPU v1 did **not** need because it only did inference, which TPU v2 had to add for training. (Compare with the CACM 2020 paper in the [research library](../web/research.html).)

## After this paper

Read the successors in order: "A Domain-Specific Supercomputer for Training Deep Neural Networks" (TPU v2/v3, 2020), "Ten Lessons From Three Generations Shaped Google's TPUv4i" (2021), and "TPU v4: An Optically Reconfigurable Supercomputer" (2023). All are in the research library with links.

**Next → [21 · Running TinyTPU on a real FPGA](21-fpga.md)**
