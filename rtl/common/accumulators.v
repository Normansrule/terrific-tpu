`timescale 1ns/1ps
// =====================================================================
//  accumulators.v  -  where finished dot-products land
// ---------------------------------------------------------------------
//  Each entry holds one output VECTOR (N lanes x 32 bits).
//  accumulate = 0 : entry  = new result          (fresh start)
//  accumulate = 1 : entry += new result          (add another K-tile)
//
//  The "+=" is what lets a small 4x4 array multiply BIG matrices:
//  you split the long K dimension into tiles and add them up here.
//  TPU v1 had 4 MiB of these 32-bit accumulators.
// =====================================================================
module accumulators #(
    parameter N     = 4,
    parameter AW    = 32,
    parameter DEPTH = 256
)(
    input  wire              clk,
    input  wire              wr_en,
    input  wire              accumulate,
    input  wire [7:0]        wr_addr,
    input  wire [N*AW-1:0]   wr_data,
    input  wire [7:0]        rd_addr,
    output wire [N*AW-1:0]   rd_data,
    input  wire [7:0]        rd2_addr,     // second read port, for the host
    output wire [N*AW-1:0]   rd2_data
);
    reg  [N*AW-1:0] mem [0:DEPTH-1];
    wire [N*AW-1:0] old = mem[wr_addr];
    wire [N*AW-1:0] sum;

    genvar l;
    generate
        for (l = 0; l < N; l = l + 1) begin : lane
            assign sum[l*AW +: AW] = (accumulate ? old[l*AW +: AW] : {AW{1'b0}})
                                   + wr_data[l*AW +: AW];
        end
    endgenerate

    always @(posedge clk)
        if (wr_en) mem[wr_addr] <= sum;

    assign rd_data  = mem[rd_addr];
    assign rd2_data = mem[rd2_addr];

    integer i;
    initial for (i = 0; i < DEPTH; i = i + 1) mem[i] = 0;
endmodule
