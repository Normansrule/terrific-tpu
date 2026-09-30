// =====================================================================
//  tb_scale.v  -  proves the RTL really is parameterized
// ---------------------------------------------------------------------
//  Builds an N x N TinyTPU (N set with -Ptb_scale.N=...), fills it with
//  random signed weights and 5 random input vectors, runs LDW + MMUL,
//  and checks every accumulator lane against a dot product computed
//  right here in the testbench.   Run:  make scale
// =====================================================================
`timescale 1ns/1ps
module tb_scale;
    parameter N = 8;
    localparam ROWS = 5;
    reg clk = 0, rst = 1;
    wire done; wire [31:0] cycles;
    tpu_top #(.N(N)) dut (.clk(clk), .rst(rst), .done(done), .cycles(cycles),
                  .host_we(1'b0), .host_sel(2'd0), .host_addr(8'd0), .host_wdata(), .host_ub_rdata(), .host_acc_rdata());
    always #5 clk = ~clk;

    reg signed [7:0] X [0:ROWS-1][0:N-1];
    reg signed [7:0] W [0:N-1][0:N-1];
    integer i, j, k, s, err;

    initial begin
        #1;
        for (i = 0; i < ROWS; i = i + 1) for (k = 0; k < N; k = k + 1) X[i][k] = $random % 100;
        for (k = 0; k < N; k = k + 1)    for (j = 0; j < N; j = j + 1) W[k][j] = $random % 100;
        for (k = 0; k < N; k = k + 1)    for (j = 0; j < N; j = j + 1) dut.wmem[k][j*8 +: 8] = W[k][j];
        for (i = 0; i < ROWS; i = i + 1) for (k = 0; k < N; k = k + 1) dut.ub[i][k*8 +: 8]  = X[i][k];
        dut.imem[0] = {4'h1, 8'd0, 8'd0,    8'd0, 4'd0};   // LDW  w=0
        dut.imem[1] = {4'h2, 8'd0, 8'(ROWS), 8'd0, 4'd0};  // MMUL ub=0 rows=ROWS acc=0
        dut.imem[2] = 32'hF000_0000;                       // HALT
        repeat (3) @(posedge clk); rst = 0;
        wait (done);
        err = 0;
        for (i = 0; i < ROWS; i = i + 1) for (j = 0; j < N; j = j + 1) begin
            s = 0;
            for (k = 0; k < N; k = k + 1) s = s + X[i][k] * W[k][j];
            if ($signed(dut.u_acc.mem[i][j*32 +: 32]) !== s) err = err + 1;
        end
        if (err == 0) $display("  N=%0d: PASS  (%0d x %0d array, %0d cycles)", N, N, N, cycles);
        else          $display("  N=%0d: FAIL  (%0d wrong lanes)", N, err);
        $finish;
    end
endmodule
