`timescale 1ns/1ps
// =====================================================================
//  activation.v  -  Rectified Linear Unit (ReLU) + requantize to int8
// ---------------------------------------------------------------------
//  32-bit sum ──► ReLU? ──► arithmetic shift right ──► clamp to [-128,127]
//
//     relu = 1 :  negative numbers become 0      (the "bend" in a neural net)
//     shift    :  divide by 2^shift so big sums fit back into 8 bits
//     clamp    :  saturate instead of wrapping around
//
//  Purely combinational: results are ready in the same clock cycle.
// =====================================================================
module activation #(
    parameter N  = 4,
    parameter AW = 32
)(
    input  wire [N*AW-1:0] acc_in,
    input  wire            relu,
    input  wire [2:0]      shift,
    output wire [N*8-1:0]  q_out
);
    genvar l;
    generate
        for (l = 0; l < N; l = l + 1) begin : lane
            wire signed [AW-1:0] v = acc_in[l*AW +: AW];
            wire signed [AW-1:0] r = (relu && v < 0) ? {AW{1'b0}} : v;
            wire signed [AW-1:0] s = r >>> shift;
            assign q_out[l*8 +: 8] = (s > 127)  ? 8'sh7F :
                                     (s < -128) ? 8'sh80 : s[7:0];
        end
    endgenerate
endmodule
