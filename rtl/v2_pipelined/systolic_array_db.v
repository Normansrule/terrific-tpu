`timescale 1ns/1ps
// =====================================================================
//  systolic_array_db.v  -  N x N grid of double-buffered PEs
// ---------------------------------------------------------------------
//  Identical wiring to v1, plus a 1-bit swap flag that flows left->right
//  next to every activation.
// =====================================================================
module systolic_array_db #(
    parameter N  = 4,
    parameter DW = 8,
    parameter AW = 32
)(
    input  wire              clk,
    input  wire              rst,
    input  wire              w_load,
    input  wire [N*DW-1:0]   w_top,
    input  wire [N*DW-1:0]   a_left,
    input  wire [N-1:0]      s_left,     // swap flag per row (already skewed)
    output wire [N*AW-1:0]   p_bottom
);
    wire [N*(N+1)*DW-1:0] a_bus;
    wire [N*(N+1)-1:0]    s_bus;
    wire [(N+1)*N*AW-1:0] p_bus;
    wire [(N+1)*N*DW-1:0] w_bus;

    genvar r, c;
    generate
        for (r = 0; r < N; r = r + 1) begin : edge_left
            assign a_bus[(r*(N+1))*DW +: DW] = a_left[r*DW +: DW];
            assign s_bus[r*(N+1)]            = s_left[r];
        end
        for (c = 0; c < N; c = c + 1) begin : edge_top
            assign p_bus[c*AW +: AW]    = {AW{1'b0}};
            assign w_bus[c*DW +: DW]    = w_top[c*DW +: DW];
            assign p_bottom[c*AW +: AW] = p_bus[(N*N+c)*AW +: AW];
        end
        for (r = 0; r < N; r = r + 1) begin : row
            for (c = 0; c < N; c = c + 1) begin : col
                pe_db #(.DW(DW), .AW(AW)) u_pe (
                    .clk(clk), .rst(rst), .w_load(w_load),
                    .w_in (w_bus[( r   *N+c)*DW +: DW]),
                    .w_out(w_bus[((r+1)*N+c)*DW +: DW]),
                    .a_in (a_bus[(r*(N+1)+c  )*DW +: DW]),
                    .s_in (s_bus[ r*(N+1)+c  ]),
                    .a_out(a_bus[(r*(N+1)+c+1)*DW +: DW]),
                    .s_out(s_bus[ r*(N+1)+c+1]),
                    .p_in (p_bus[( r   *N+c)*AW +: AW]),
                    .p_out(p_bus[((r+1)*N+c)*AW +: AW])
                );
            end
        end
    endgenerate
endmodule
