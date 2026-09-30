#!/usr/bin/env bash
# fpga_report.sh - how much of an FPGA does the serial-port TinyTPU need?
# Synthesizes rtl/fpga/tpu_uart_top.v (with v1 or v2 inside) for a Lattice
# ECP5 with Yosys and writes data/fpga.csv. Place-and-route and bitstream
# generation are separate steps (docs/21-fpga.md).
set -eu
cd "$(dirname "$0")/.."
mkdir -p build/fpga data
echo "version,LUT4,distributed_RAM_DPR16X4,block_RAM_DP16KD,multipliers_MULT18X18D,flip_flops,carry_CCU2C" > data/fpga.csv
for v in v1_simple v2_pipelined; do
  yosys -q -l build/fpga/ecp5_$v.log -p "read_verilog rtl/fpga/uart_rx.v rtl/fpga/uart_tx.v rtl/fpga/tpu_uart_top.v rtl/common/*.v rtl/$v/*.v; synth_ecp5 -top tpu_uart_top; stat" > /dev/null 2>&1
  get () { awk '/=== tpu_uart_top ===/ {f=1} f && $1=="'"$1"'" {print $2; exit}' build/fpga/ecp5_$v.log; }
  row="$v,$(get LUT4),$(get TRELLIS_DPR16X4),$(get DP16KD),$(get MULT18X18D),$(get TRELLIS_FF),$(get CCU2C)"
  echo "$row" >> data/fpga.csv
  echo "  $row"
done
echo "wrote data/fpga.csv   (an LFE5U-25F has 24,288 LUTs, 56 DP16KD block RAMs and 28 MULT18X18D multipliers)"
