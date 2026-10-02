# =====================================================================
#  build.tcl - Vivado non-project build for the Basys 3
#  Run from this folder:   vivado -mode batch -source build.tcl
#  Pick the chip version:  vivado -mode batch -source build.tcl -tclargs v1_simple
#  Outputs: build/tinytpu_basys3.bit (+ timing and utilization reports)
# =====================================================================
set version [expr {[llength $argv] > 0 ? [lindex $argv 0] : "v2_pipelined"}]
set rtl ../..
file mkdir build
read_verilog [glob $rtl/common/*.v] [glob $rtl/$version/*.v] \
    $rtl/fpga/uart_rx.v $rtl/fpga/uart_tx.v $rtl/fpga/uart_host.v basys3_top.v
read_xdc basys3.xdc
synth_design -top basys3_top -part xc7a35tcpg236-1
opt_design
place_design
route_design
report_utilization    -file build/utilization.rpt
report_timing_summary -file build/timing.rpt
write_bitstream -force build/tinytpu_basys3.bit
puts "\n  bitstream: [pwd]/build/tinytpu_basys3.bit  (TinyTPU $version)\n"
