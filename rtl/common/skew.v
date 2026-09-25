`timescale 1ns/1ps
// =====================================================================
//  skew.v  -  staircase delay lines
// ---------------------------------------------------------------------
//  A systolic array needs data to arrive DIAGONALLY ("a wavefront").
//  Lane k is delayed by k clock cycles (REVERSE=0), or by N-1-k cycles
//  (REVERSE=1, used to line the outputs back up = "de-skew").
//
//     REVERSE=0 (input skew)          REVERSE=1 (output de-skew)
//     lane0 ----------------->        lane0 -[]-[]-[]->
//     lane1 -[]-------------->        lane1 -[]-[]---->
//     lane2 -[]-[]----------->        lane2 -[]------->
//     lane3 -[]-[]-[]-------->        lane3 ---------->
// =====================================================================
module skew #(
    parameter N       = 4,
    parameter W       = 8,
    parameter REVERSE = 0
)(
    input  wire           clk,
    input  wire           rst,
    input  wire [N*W-1:0] din,
    output wire [N*W-1:0] dout
);
    genvar k;
    generate
        for (k = 0; k < N; k = k + 1) begin : lane
            localparam D = (REVERSE != 0) ? (N - 1 - k) : k;
            if (D == 0) begin : pass
                assign dout[k*W +: W] = din[k*W +: W];
            end else begin : delay
                reg [W-1:0] sr [0:D-1];
                integer i;
                always @(posedge clk) begin
                    if (rst) begin
                        for (i = 0; i < D; i = i + 1) sr[i] <= 0;
                    end else begin
                        sr[0] <= din[k*W +: W];
                        for (i = 1; i < D; i = i + 1) sr[i] <= sr[i-1];
                    end
                end
                assign dout[k*W +: W] = sr[D-1];
            end
        end
    endgenerate
endmodule
