`timescale 1ns/1ps
// =====================================================================
//  tpu_uart_top.v - TinyTPU (v1 or v2) behind a serial port
// ---------------------------------------------------------------------
//  Put this on an FPGA board, connect its USB serial port, and drive it
//  from tools/tpu_host.py. Every command is one ASCII letter:
//
//    'P'                      ping                      -> 'K'
//    'I' addr b3 b2 b1 b0     instruction[addr] = 32-bit word (big-endian)
//    'W' addr l0 l1 l2 l3     weight memory[addr] = four int8 lanes
//    'U' addr l0 l1 l2 l3     Unified Buffer[addr] = four int8 lanes
//    'G'                      run from pc = 0 until HALT -> 'D' + cycles (4 bytes)
//    'R' addr                 read Unified Buffer[addr]  -> 4 bytes (lane 0 first)
//    'A' addr                 read accumulators[addr]    -> 16 bytes (4 lanes, big-endian)
//
//  The TPU is held in reset except during 'G', so memory writes never
//  race with a running program. Simulated by tb/tb_uart.v (make uart).
// =====================================================================
module tpu_uart_top #(
    parameter CLKS_PER_BIT = 104            // 12 MHz clock, 115200 baud
)(
    input  wire clk,
    input  wire uart_rx,
    output wire uart_tx,
    output wire led_busy                    // lit while a program runs
);
    localparam N = 4;
    wire        tpu_rst, host_we, done;
    wire [1:0]  host_sel;
    wire [7:0]  host_addr;
    wire [31:0] host_wdata, ub_rdata, cycles;
    wire [127:0] acc_rdata;
    uart_host #(.CLKS_PER_BIT(CLKS_PER_BIT)) u_host (.clk(clk), .uart_rx(uart_rx), .uart_tx(uart_tx),
        .host_we(host_we), .host_sel(host_sel), .host_addr(host_addr), .host_wdata(host_wdata),
        .ub_rdata(ub_rdata), .acc_rdata(acc_rdata), .tpu_rst(tpu_rst), .done(done), .cycles(cycles));
    tpu_top #(.N(N)) u_tpu (.clk(clk), .rst(tpu_rst), .done(done), .cycles(cycles),
        .host_we(host_we), .host_sel(host_sel), .host_addr(host_addr), .host_wdata(host_wdata),
        .host_ub_rdata(ub_rdata), .host_acc_rdata(acc_rdata), .dbg());
    assign led_busy = !tpu_rst;
endmodule
