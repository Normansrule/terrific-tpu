`timescale 1ns/1ps
// =====================================================================
//  pe.v  -  Processing Element (PE): one "cell" of the systolic array
// ---------------------------------------------------------------------
//  Every clock tick a PE does exactly ONE Multiply-Accumulate (MAC):
//
//        partial_sum_out = partial_sum_in + activation_in * weight
//
//             weight (loaded from above, then STAYS here)
//                        |
//                        v
//   activation_in --> [ x ] --> activation_out   (to the PE on the right)
//                        |
//   partial_sum_in ---> [ + ]
//                        |
//                        v
//                  partial_sum_out               (to the PE below)
//
//  This is a WEIGHT-STATIONARY design, the same idea used by the first
//  Google Tensor Processing Unit (TPU v1): weights sit still, data flows.
// =====================================================================
module pe #(
    parameter DW = 8,    // Data Width of activations and weights (int8)
    parameter AW = 32    // Accumulator Width of partial sums      (int32)
)(
    input  wire                 clk,
    input  wire                 rst,
    // ---- weight loading path (shifts DOWN the column) ----
    input  wire                 w_load,   // 1 = take a new weight from above
    input  wire signed [DW-1:0] w_in,     // weight arriving from the PE above
    output reg  signed [DW-1:0] w_out,    // the weight stored in THIS PE
    // ---- activation path (flows LEFT -> RIGHT) ----
    input  wire signed [DW-1:0] a_in,
    output reg  signed [DW-1:0] a_out,
    // ---- partial-sum path (flows TOP -> BOTTOM) ----
    input  wire signed [AW-1:0] p_in,
    output reg  signed [AW-1:0] p_out
);
    always @(posedge clk) begin
        if (rst) begin
            w_out <= 0;
            a_out <= 0;
            p_out <= 0;
        end else begin
            if (w_load) w_out <= w_in;          // weight shift register
            a_out <= a_in;                       // pass activation right
            p_out <= p_in + a_in * w_out;        // the MAC
        end
    end
endmodule
