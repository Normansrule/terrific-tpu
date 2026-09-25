`timescale 1ns/1ps
// =====================================================================
//  systolic_array.v  -  N x N grid of Processing Elements (PEs)
// ---------------------------------------------------------------------
//  This is the "Matrix Multiply Unit" (MXU) - the heart of a TPU.
//
//         w_in[0]  w_in[1]  w_in[2]  w_in[3]     (weights enter at top)
//            |        |        |        |
//   a[0] -> PE00 --> PE01 --> PE02 --> PE03
//            |        |        |        |
//   a[1] -> PE10 --> PE11 --> PE12 --> PE13
//            |        |        |        |
//   a[2] -> PE20 --> PE21 --> PE22 --> PE23
//            |        |        |        |
//   a[3] -> PE30 --> PE31 --> PE32 --> PE33
//            |        |        |        |
//          y[0]     y[1]     y[2]     y[3]      (results leave at bottom)
//
//  PE(r,c) holds weight W[r][c].  Row r receives input element x[r].
//  Column c produces y[c] = sum over r of x[r] * W[r][c].
//  Google's TPU v1 used exactly this idea at 256 x 256 = 65,536 PEs.
// =====================================================================
module systolic_array #(
    parameter N  = 4,
    parameter DW = 8,
    parameter AW = 32
)(
    input  wire              clk,
    input  wire              rst,
    input  wire              w_load,
    input  wire [N*DW-1:0]   w_top,     // one weight per column, enters at top
    input  wire [N*DW-1:0]   a_left,    // one activation per row, enters at left
    output wire [N*AW-1:0]   p_bottom   // one partial sum per column, exits bottom
);
    // Flattened wire grids. Index helpers:
    //   a_bus : (N rows) x (N+1 horizontal hops)
    //   p_bus : (N+1 vertical hops) x (N columns)
    //   w_bus : (N+1 vertical hops) x (N columns)
    wire [N*(N+1)*DW-1:0] a_bus;
    wire [(N+1)*N*AW-1:0] p_bus;
    wire [(N+1)*N*DW-1:0] w_bus;

    genvar r, c;
    generate
        for (r = 0; r < N; r = r + 1) begin : edge_left
            assign a_bus[(r*(N+1)+0)*DW +: DW] = a_left[r*DW +: DW];
        end
        for (c = 0; c < N; c = c + 1) begin : edge_top
            assign p_bus[(0*N+c)*AW +: AW] = {AW{1'b0}};           // nothing above row 0
            assign w_bus[(0*N+c)*DW +: DW] = w_top[c*DW +: DW];
            assign p_bottom[c*AW +: AW]    = p_bus[(N*N+c)*AW +: AW];
        end
        for (r = 0; r < N; r = r + 1) begin : row
            for (c = 0; c < N; c = c + 1) begin : col
                pe #(.DW(DW), .AW(AW)) u_pe (
                    .clk   (clk),
                    .rst   (rst),
                    .w_load(w_load),
                    .w_in  (w_bus[( r   *N+c)*DW +: DW]),
                    .w_out (w_bus[((r+1)*N+c)*DW +: DW]),
                    .a_in  (a_bus[(r*(N+1)+c  )*DW +: DW]),
                    .a_out (a_bus[(r*(N+1)+c+1)*DW +: DW]),
                    .p_in  (p_bus[( r   *N+c)*AW +: AW]),
                    .p_out (p_bus[((r+1)*N+c)*AW +: AW])
                );
            end
        end
    endgenerate
endmodule
