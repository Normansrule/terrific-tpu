# 📖 Glossary

Every acronym in this repo, spelled out.

| Term | Meaning |
|---|---|
| **Accumulator** | memory that holds 32-bit running sums; in TinyTPU it can "add to" what it already holds |
| **Activation** | the data flowing through a neural network; also the function (like ReLU) applied after a matrix multiply |
| **Adjacency matrix** | a matrix with a 1 where two graph nodes are connected; its powers count walks |
| **Amplitude** | one of the numbers describing a quantum state; its square is the probability of measuring that outcome |
| **Application-Specific Integrated Circuit (ASIC)** | a chip designed for one job; every TPU is one |
| **Arithmetic intensity** | operations performed per byte moved from memory |
| **Batch** | many inputs processed together; bigger batches keep a systolic array busier |
| **bfloat16 (brain floating point, 16-bit)** | a 16-bit number format with the same range as 32-bit float but less precision; introduced with TPU v2 |
| **Bitstream** | the configuration file that programs an FPGA |
| **BUFGCE** | a Xilinx global clock buffer with an enable: used to gate the TPU clock for single-stepping |
| **Central Processing Unit (CPU)** | a general-purpose processor |
| **Complex Instruction Set Computer (CISC)** | an instruction style where one instruction does a lot of work; TPU v1 used it |
| **Constraints file (XDC)** | tells Vivado which FPGA pin each signal uses and how fast the clocks are |
| **De-skew** | delaying earlier output columns so a result vector comes out all at once |
| **Discrete Fourier Transform (DFT)** | converts a signal into its frequencies; a matrix multiply in disguise |
| **Double buffering** | two copies of a register or memory: fill one while the other is in use; v2's shadow weights |
| **Double Data Rate 3 (DDR3)** | a type of off-chip memory; TPU v1 kept its weights there |
| **DSP slice (DSP48E1)** | a hard multiply-accumulate block inside the FPGA; each TinyTPU PE maps onto one |
| **Edge TPU** | Google's small, low-power TPU for devices (sold as Coral) |
| **Field-Programmable Gate Array (FPGA)** | a chip whose logic can be reconfigured; a common way to test RTL in hardware |
| **Field-programmable gate array (FPGA)** | a chip whose logic can be rewired after manufacture; lets you run RTL as real hardware without a tapeout |
| **FP8** | 8-bit floating point, in two variants (E4M3 and E5M2) used by recent tensor hardware |
| **Fuzzing** | testing with many randomly generated inputs (here: random programs) |
| **Golden model** | a simple, trusted software version of the math used to check the hardware |
| **Graphics Processing Unit (GPU)** | a processor with thousands of small cores running in lockstep groups |
| **Grover's algorithm** | a quantum search that finds a marked item among N in about √N steps |
| **Hazard** | a situation where overlapped instructions would read data before it is ready |
| **High Bandwidth Memory (HBM)** | stacked memory placed right next to the processor die; used since TPU v2 |
| **High Level Operations (HLO)** | the XLA compiler's intermediate representation of a program |
| **Host port** | extra memory ports that let an outside controller load programs and read results |
| **im2col (image to columns)** | turning every sliding window of an image into a matrix row, so a convolution becomes a matrix multiply |
| **im2col** | "image to columns": rearranging image patches so a convolution becomes a matrix multiply |
| **Instruction-level model** | a simulator that knows what each instruction means but nothing about clock cycles (`tools/tpu_isa_sim.py`) |
| **Inter-Chip Interconnect (ICI)** | the direct links that join TPU chips into a pod |
| **JTAG** | the debug/programming port used to load a bitstream into the FPGA |
| **Matrix Multiply Unit (MXU)** | Google's name for the systolic array inside a TPU |
| **MMCM (mixed-mode clock manager)** | the Xilinx block that makes new clock frequencies from the board oscillator |
| **Multiply-Accumulate (MAC)** | `total = total + a × b`; the one operation a TPU is built around |
| **Mutation testing** | planting deliberate bugs to prove a test would catch them |
| **Optical circuit switch** | a switch that steers light beams with tiny mirrors; TPU v4 uses them to rewire its pods |
| **Peripheral Component Interconnect Express (PCIe)** | the slot/bus that connects TPU v1 to its host server |
| **Pod** | many TPU chips networked into one machine |
| **Process Design Kit (PDK)** | a chip factory's rules and cell libraries; SkyWater's sky130 PDK is open source |
| **Processing Element (PE)** | one cell of the systolic array: a multiplier, an adder, and three registers |
| **Quantization** | representing numbers with fewer bits (e.g. 8-bit integers) |
| **Qubit** | a quantum bit; n qubits are described by 2ⁿ amplitudes |
| **Rectified Linear Unit (ReLU)** | `max(0, x)`: turns negatives into zero |
| **Register-Transfer Level (RTL)** | hardware described as registers and the logic between them (Verilog, VHDL) |
| **Roofline model** | a chart of performance versus arithmetic intensity showing whether a program is limited by compute or memory |
| **Scoreboard** | hardware that tracks which results are still in flight so dependent instructions can wait |
| **Serial Peripheral Interface (SPI)** | a simple 4-wire bus microcontrollers use to talk to chips |
| **Shadow register** | the second copy in a double buffer; v2 loads new weights into it |
| **Skew** | delaying input row k by k cycles so data meets the right partial sums |
| **Space-time diagram** | a chart of which hardware unit is busy on which clock cycle |
| **SparseCore** | a unit in TPU v4 and later for embedding lookups |
| **Standard cell** | a pre-designed logic gate or flip-flop from a PDK's library, placed by the synthesis tools |
| **Static Random-Access Memory (SRAM)** | fast on-chip memory; the Unified Buffer is SRAM |
| **Structured sparsity** | zeros in a fixed pattern (such as 2 of every 4 weights) that hardware can skip cheaply |
| **Synthesis** | converting RTL into a network of standard cells (Yosys does this here) |
| **Systolic array** | a grid of PEs that pass data only to neighbors, in rhythm with the clock |
| **Tail latency** | the response time of the slowest requests (for example the 99th percentile), which limits batch size in serving |
| **Tapeout** | sending a finished chip layout to be manufactured |
| **Tensor Processing Unit (TPU)** | Google's family of chips specialized for tensor (matrix) math |
| **Tensor** | a grid of numbers with any number of dimensions |
| **Tera-operations per second (TOPS)** | trillions of operations per second; teraFLOPS counts floating-point operations |
| **Total cost of ownership (TCO)** | purchase price plus power and operating costs over a machine's lifetime |
| **Unified Buffer** | TPU v1's big on-chip memory for activations; TinyTPU keeps the name |
| **Unitary matrix** | the kind of matrix every quantum gate is; it preserves total probability |
| **Universal asynchronous receiver-transmitter (UART)** | a simple serial link (start bit, 8 data bits, stop bit); how tools/tpu_host.py talks to the FPGA |
| **Utilization** | the fraction of the multipliers doing useful work |
| **Weight** | a learned number in a neural network; stays inside the PE in a weight-stationary design |
| **Weight-stationary** | a dataflow where weights stay still in the array and data moves |
| **XLA (Accelerated Linear Algebra)** | Google's compiler that turns JAX/TensorFlow/PyTorch code into TPU programs |

**Back → [README](../README.md)**
