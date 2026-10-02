# program.tcl - load the bitstream into a Basys 3 over USB (volatile: lost at power-off)
# Run from this folder:  vivado -mode batch -source program.tcl
open_hw_manager
connect_hw_server
open_hw_target
set dev [lindex [get_hw_devices xc7a35t*] 0]
current_hw_device $dev
set_property PROGRAM.FILE build/tinytpu_basys3.bit $dev
program_hw_devices $dev
puts "\n  programmed. Set the switches, press the centre button.\n"
close_hw_manager
