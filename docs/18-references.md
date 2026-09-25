# 18 · References

Everything here is in English. Links go to the original source. Where a stable link wasn't certain, there is a Google Scholar or YouTube search link instead of a guessed URL.

## Start here (the essentials)

| Type | Resource | Why read it |
|---|---|---|
| 📄 paper | N. P. Jouppi et al., "In-Datacenter Performance Analysis of a Tensor Processing Unit," International Symposium on Computer Architecture (ISCA) 2017. [arXiv 1704.04760](https://arxiv.org/abs/1704.04760) | **The** TPU v1 paper. TinyTPU is modeled on its Figure 1. |
| 📰 blog | K. Sato, C. Young, D. Patterson, "An in-depth look at Google's first Tensor Processing Unit (TPU)," Google Cloud blog, 2017. [link](https://cloud.google.com/blog/products/ai-machine-learning/an-in-depth-look-at-googles-first-tensor-processing-unit-tpu) | Friendly tour with photos and animated diagrams. |
| 📄 paper | H. T. Kung, "Why Systolic Architectures?" IEEE Computer, 1982. [Scholar](https://scholar.google.com/scholar?q=Why+Systolic+Architectures+Kung+1982) | Where the idea comes from; short and very readable. |
| 📘 book | J. Hennessy and D. Patterson, *Computer Architecture: A Quantitative Approach*, 6th ed., Chapter 7 "Domain-Specific Architectures" | A textbook case study of TPU v1 alongside other accelerators. |

## Later generations

| Resource | Covers |
|---|---|
| N. P. Jouppi et al., "A Domain-Specific Supercomputer for Training Deep Neural Networks," Communications of the ACM, 2020. [Scholar](https://scholar.google.com/scholar?q=A+Domain-Specific+Supercomputer+for+Training+Deep+Neural+Networks) | TPU v2 and v3, bfloat16, pods |
| N. P. Jouppi et al., "TPU v4: An Optically Reconfigurable Supercomputer for Machine Learning with Hardware Support for Embeddings," ISCA 2023. [arXiv 2304.01433](https://arxiv.org/abs/2304.01433) | optical switches, SparseCore |
| Google Cloud, [TPU system architecture](https://cloud.google.com/tpu/docs/system-architecture-tpu-vm) and [release notes](https://docs.cloud.google.com/tpu/docs/release-notes) | current versions, chips, slices, pods |
| ServeTheHome, [Google's TPU v8s for Training and Inference at Hot Chips 2026](https://www.servethehome.com/googles-tpuv8s-for-training-and-inference-at-hot-chips-2026/) | TPU 8t / 8i with slides and package photos |

## Energy, numbers, silicon

| Resource | Why |
|---|---|
| M. Horowitz, "Computing's Energy Problem (and what we can do about it)," International Solid-State Circuits Conference (ISSCC) 2014. [Scholar](https://scholar.google.com/scholar?q=Horowitz+Computing%27s+energy+problem+and+what+we+can+do+about+it) | the energy-per-operation numbers in [lesson 5](05-dataflow-and-energy.md) |
| S. Wang and P. Kanwar, "BFloat16: The secret to high performance on Cloud TPUs," Google Cloud blog, 2019. [Search](https://www.google.com/search?q=BFloat16+secret+to+high+performance+on+Cloud+TPUs) | why TPUs use bfloat16 ([lesson 3](03-numbers-and-quantization.md)) |
| B. Jacob et al., "Quantization and Training of Neural Networks for Efficient Integer-Arithmetic-Only Inference," CVPR 2018. [arXiv 1712.05877](https://arxiv.org/abs/1712.05877) | the standard int8 quantization scheme |
| [SkyWater SKY130 PDK documentation](https://skywater-pdk.readthedocs.io/) | the open 130 nm process used in [lesson 12](12-rtl-to-silicon.md) |
| [OpenLane](https://github.com/The-OpenROAD-Project/OpenLane) / [OpenROAD](https://theopenroadproject.org/) | open-source place and route, RTL to GDS |

## Systolic arrays and accelerator design

| Resource | Why |
|---|---|
| Y.-H. Chen et al., "Eyeriss: A Spatial Architecture for Energy-Efficient Dataflow for Convolutional Neural Networks," ISCA 2016. [Scholar](https://scholar.google.com/scholar?q=Eyeriss+spatial+architecture+energy-efficient+dataflow) | compares weight-, output-, and row-stationary dataflows |
| V. Sze, Y.-H. Chen, T.-J. Yang, J. Emer, *Efficient Processing of Deep Neural Networks* (book, 2020) | the best single reference on accelerator design trade-offs |
| [Gemmini](https://github.com/ucb-bar/gemmini) (UC Berkeley) | open-source systolic array generator connected to RISC-V cores; the natural next step after TinyTPU |
| S. Williams, A. Waterman, D. Patterson, "Roofline: An Insightful Visual Performance Model for Multicore Architectures," Communications of the ACM, 2009. [Scholar](https://scholar.google.com/scholar?q=Roofline+insightful+visual+performance+model) | the roofline model in [lesson 11](11-performance.md) |

## Programming TPUs

| Resource | Why |
|---|---|
| [JAX documentation](https://docs.jax.dev/) | the main way researchers program TPUs today |
| [OpenXLA / XLA](https://openxla.org/) | the compiler that turns your array code into TPU programs |
| [Pallas documentation](https://docs.jax.dev/en/latest/pallas/index.html) | writing your own TPU kernels |
| [Coral documentation](https://coral.ai/docs/) | Edge TPU model compilation and deployment |

## Tools used in this repo

| Tool | Link |
|---|---|
| Icarus Verilog (simulator) | [steveicarus.github.io/iverilog](https://steveicarus.github.io/iverilog/) |
| GTKWave (waveform viewer) | [gtkwave.github.io/gtkwave](https://gtkwave.github.io/gtkwave/) |
| Yosys (synthesis) | [yosyshq.net/yosys](https://yosyshq.net/yosys/) |
| Tiny Tapeout (make a real chip cheaply) | [tinytapeout.com](https://tinytapeout.com/) |

## Videos (English)

Rather than risk dead links, these are channels plus exact searches that find the talks:

| Channel / source | Search for | What you get |
|---|---|---|
| Hot Chips (official YouTube channel) | [`Hot Chips Google TPU`](https://www.youtube.com/results?search_query=Hot+Chips+Google+TPU) | the architects presenting each generation |
| Google Cloud Tech | [`Google Cloud Tech TPU explained`](https://www.youtube.com/results?search_query=Google+Cloud+Tech+TPU+explained) | short official explainers |
| ACM / ISCA talks | [`Jouppi TPU talk`](https://www.youtube.com/results?search_query=Norm+Jouppi+TPU+talk) | Norm Jouppi on TPU design lessons |
| University lectures | [`systolic array lecture computer architecture`](https://www.youtube.com/results?search_query=systolic+array+lecture+computer+architecture) | whiteboard derivations of the wavefront timing |
| Onur Mutlu lectures (ETH Zürich / CMU) | [`Onur Mutlu systolic arrays`](https://www.youtube.com/results?search_query=Onur+Mutlu+systolic+arrays) | full university lectures on systolic arrays and accelerators |

**Next → [Glossary](glossary.md)**
