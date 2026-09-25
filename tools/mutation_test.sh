#!/usr/bin/env bash
# =====================================================================
#  mutation_test.sh - "does the test actually catch bugs?"
# ---------------------------------------------------------------------
#  Each mutant is ONE deliberate, realistic bug planted in a copy of the
#  RTL. The test suite (neural net + Fourier + 25 random programs) must
#  FAIL on every one ("kill the mutant"). A survivor means the TESTS are
#  too weak. The fix is always a stronger test, never a weaker check.
#
#  usage: tools/mutation_test.sh            (both versions)
# =====================================================================
set -u
cd "$(dirname "$0")/.."
mkdir -p build/mut

# version | file | original | buggy replacement | what the bug means
MUTANTS=(
"v1_simple|rtl/v1_simple/pe.v|p_in + a_in \\* w_out|p_in + a_in|PE forgets to multiply"
"v1_simple|rtl/v1_simple/pe.v|a_out <= a_in;|a_out <= 0;|activations stop flowing right"
"v1_simple|rtl/common/skew.v|(N - 1 - k) : k|k : k|output de-skew uses the wrong staircase"
"v1_simple|rtl/v1_simple/controller.v|fA + (N - 1 - cnt\\[7:0\\])|fA + cnt[7:0]|weights loaded upside-down"
"v1_simple|rtl/v1_simple/tpu_top.v|localparam LAT = 2\\*N - 1;|localparam LAT = 2*N - 2;|results captured one cycle early"
"v1_simple|rtl/v1_simple/controller.v|{1'b0, fB} + LAT - 1)|{1'b0, fB} - 1)|MMUL ends before results drain out"
"v1_simple|rtl/common/accumulators.v|accumulate ? old|1'b0 ? old|accumulate flag ignored"
"v1_simple|rtl/common/activation.v|(relu \\&\\& v < 0)|(1'b0)|ReLU never applied"
"v1_simple|rtl/common/activation.v|r >>> shift|r >> shift|logical instead of arithmetic shift"
"v1_simple|rtl/common/activation.v|(s > 127)  ? 8'sh7F|(s > 127)  ? s[7:0]|no saturation on overflow"
"v2_pipelined|rtl/v2_pipelined/controller_pipe.v|(op == OP_LDW  \\&\\& swap_wait != 0)|(1'b0)|LDW overwrites shadow before the swap wave finishes"
"v2_pipelined|rtl/v2_pipelined/controller_pipe.v|((op == OP_ACT |((1'b0 |ACT reads results still in flight"
"v2_pipelined|rtl/v2_pipelined/controller_pipe.v|localparam SWAP_SPAN = 2\\*N - 3;|localparam SWAP_SPAN = 2*N - 5;|swap wait two cycles too short"
"v2_pipelined|rtl/v2_pipelined/pe_db.v|s_in ? w_shadow : w_active|w_active|first new vector uses the old weight"
"v2_pipelined|rtl/v2_pipelined/tpu_top.v|.wr_addr(addr_pipe\\[LAT-1\\])|.wr_addr(in_acc_addr)|result address not carried with the data"
"v2_pipelined|rtl/v2_pipelined/tpu_top.v|{in_swap \\& in_valid, in_vec|{in_swap \\& 1'b0, in_vec|swap flag never sent"
)


killed=0; total=0
for m in "${MUTANTS[@]}"; do
  IFS='|' read -r ver file from to why <<< "$m"
  total=$((total+1))
  rm -rf build/mut/rtl && cp -r rtl build/mut/rtl
  sed -i "s/${from}/${to}/" "build/mut/${file}"
  if cmp -s "$file" "build/mut/${file}"; then echo "  [NO-APPLY] $ver: $why"; continue; fi
  iverilog -g2012 -o build/mut/sim.vvp tb/tb_tpu_top.v build/mut/rtl/common/*.v build/mut/rtl/$ver/*.v 2>/dev/null \
    || { echo "  [KILLED  ] $ver: $why (does not compile)"; killed=$((killed+1)); continue; }
  # the testbench reads build/*.hex, so run the suite from a sandbox copy
  ( cd build/mut && mkdir -p build && cp -r ../../tools ../../programs . 2>/dev/null
    python3 tools/golden_model.py --demo mlp --seed 3 --out build > /dev/null; vvp -n sim.vvp +novcd | grep -q PASS || exit 1
    python3 tools/golden_model.py --demo dft --seed 3 --out build > /dev/null; vvp -n sim.vvp +novcd | grep -q PASS || exit 1
    for s in $(seq 1 25); do
      python3 tools/golden_model.py --demo fuzz --seed $s --out build > /dev/null
      vvp -n sim.vvp +novcd | grep -q PASS || exit 1
    done; exit 0 )
  if [ $? -ne 0 ]; then echo "  [KILLED  ] $ver: $why"; killed=$((killed+1))
  else echo "  [SURVIVED] $ver: $why   <-- the tests need strengthening"; fi
done
echo "-------------------------------------------------"
echo "  $killed / $total mutants killed"
[ $killed -eq $total ]
