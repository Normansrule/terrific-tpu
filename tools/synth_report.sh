#!/usr/bin/env bash
# =====================================================================
#  synth_report.sh - how big is TinyTPU as real logic gates?
# ---------------------------------------------------------------------
#  Synthesizes one PE and the whole systolic array (v1 and v2) at several
#  sizes with Yosys. If the SkyWater sky130 standard-cell library is found
#  it maps to real cells and reports AREA in square micrometers; otherwise
#  it reports generic gate counts.
#
#  Library search order:  $SKY130_LIB, then
#    ~/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
#  Output: data/synth.csv  (read by tools/diagrams/make_all.py)
# =====================================================================
set -eu
cd "$(dirname "$0")/.."
LIB="${SKY130_LIB:-$HOME/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib}"
mkdir -p build/synth data
echo "design,version,N,cells,flops,area_um2" > data/synth.csv
[ -f "$LIB" ] && echo "using sky130 library: $LIB" || { echo "sky130 library not found: generic gate counts only"; LIB=""; }

synth_one () {  # $1 top  $2 version  $3 N  $4.. files
  local top=$1 ver=$2 n=$3; shift 3
  local log=build/synth/${top}_${ver}_N${n}.log
  local map=""
  [ -n "$LIB" ] && map="dfflibmap -liberty $LIB; abc -liberty $LIB; stat -liberty $LIB" || map="abc -g AND,NAND,OR,NOR,XOR,XNOR,MUX; stat"
  yosys -q -l "$log" -p "read_verilog $*; chparam -set N $n $top; synth -flatten -top $top; $map" >/dev/null 2>&1 \
     || yosys -q -l "$log" -p "read_verilog $*; synth -flatten -top $top; $map" >/dev/null 2>&1
  local cells=$(grep -E "Number of cells:" "$log" | tail -1 | awk '{print $NF}')
  # count flip-flops in the LAST statistics report only (the mapped netlist)
  local flops=$(awk '/Printing statistics/ {buf=""} {buf=buf"\n"$0} END {print buf}' "$log" \
                | grep -Eo "(sky130_fd_sc_hd__df[a-z0-9_]*|\\\$_[A-Z]*DFF[A-Z_0-9]*_) +[0-9]+" | awk '{s+=$NF} END {print s+0}')
  local area=$(grep -E "Chip area" "$log" | tail -1 | awk '{print $NF}')
  printf "  %-22s %-13s N=%-3s cells=%-7s flops=%-6s area=%s um^2\n" "$top" "$ver" "$n" "$cells" "$flops" "${area:-n/a}"
  echo "$top,$ver,$n,$cells,$flops,${area:-}" >> data/synth.csv
}

synth_one pe            v1_simple    1 rtl/v1_simple/pe.v
synth_one pe_db         v2_pipelined 1 rtl/v2_pipelined/pe_db.v
for n in 2 4 8; do
  synth_one systolic_array    v1_simple    $n rtl/v1_simple/pe.v rtl/v1_simple/systolic_array.v
  synth_one systolic_array_db v2_pipelined $n rtl/v2_pipelined/pe_db.v rtl/v2_pipelined/systolic_array_db.v
done
echo "wrote data/synth.csv"
