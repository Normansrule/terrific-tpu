`timescale 1ns/1ps
// =====================================================================
//  pe_db.v  -  Processing Element with DOUBLE-BUFFERED weights
// ---------------------------------------------------------------------
//  Same multiply-accumulate as v1's pe.v, plus a second weight register.
//
//      w_in (from above)                     TPU v1 did this too: the next
//          |                                 weight tile shifts into the
//          v                                 SHADOW register while the
//    +-------------+   swap    +--------+    array is still computing
//    |  w_shadow   | --------> | w_active|   with the ACTIVE one.
//    +-------------+           +--------+
//          |  (w_out, to PE below)   |
//                                    v
//   a_in, s_in --> [ x ] --> a_out, s_out   (s = "swap" flag riding with
//                    |                         the first vector of a MMUL)
//   p_in -------> [ + ] --> p_out
//
//  The swap flag travels through the array EXACTLY like the data, so
//  every PE switches to the new weights at the moment the first new
//  vector reaches it: a diagonal "swap wavefront".  Old vectors still in
//  flight keep using the old weights.
// =====================================================================
module pe_db #(
    parameter DW = 8,
    parameter AW = 32
)(
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 w_load,
    input  wire signed [DW-1:0] w_in,
    output wire signed [DW-1:0] w_out,     // shadow register, shifts down
    input  wire signed [DW-1:0] a_in,
    input  wire                 s_in,      // swap flag arriving with a_in
    output reg  signed [DW-1:0] a_out,
    output reg                  s_out,
    input  wire signed [AW-1:0] p_in,
    output reg  signed [AW-1:0] p_out
);
    reg signed [DW-1:0] w_shadow, w_active;
    // the vector carrying the swap flag must already use the NEW weight
    wire signed [DW-1:0] w_use = s_in ? w_shadow : w_active;
    assign w_out = w_shadow;

    always @(posedge clk) begin
        if (rst) begin
            w_shadow <= 0; w_active <= 0;
            a_out <= 0; s_out <= 0; p_out <= 0;
        end else begin
            if (w_load) w_shadow <= w_in;
            if (s_in)   w_active <= w_shadow;
            a_out <= a_in;
            s_out <= s_in;
            p_out <= p_in + a_in * w_use;
        end
    end
endmodule
