`timescale 1ns/1ps
// =====================================================================
//  tpu_top.v  -  "TinyTPU": a complete, teachable Tensor Processing Unit
// ---------------------------------------------------------------------
//
//   +------------------+        +-------------------+
//   | Instruction Mem  |------->|    Controller     |------ done
//   +------------------+        +-------------------+
//                                 | control signals everywhere
//   +------------------+          v
//   |  Weight Memory   |----> [ weight row ] -----------+
//   +------------------+                                v (top)
//   +------------------+   +------+   +--------------------------+
//   | Unified Buffer   |-->| skew |-->|  Systolic Array  N x N   |
//   | (int8 vectors)   |   +------+   |  (Matrix Multiply Unit)  |
//   +------------------+  (left side) +--------------------------+
//            ^                                     | (bottom)
//            |                              +------------+
//            |                              |  de-skew   |
//            |                              +------------+
//            |                                     v
//   +------------------+      +----------------------------+
//   |   Activation     |<-----|   Accumulators (int32)     |
//   | ReLU + requant   |      +----------------------------+
//   +------------------+
//
//  Same block structure as Google's TPU v1 (2015), shrunk from
//  256 x 256 to N x N so a human can follow every wire.
// =====================================================================
module tpu_top #(
    parameter N  = 4,
    parameter DW = 8,
    parameter AW = 32
)(
    input  wire        clk,
    input  wire        rst,
    output wire        done,
    output wire [31:0] cycles
);
    localparam LAT = 2*N - 1;

    // ------------------ memories (loaded by the host / testbench) -----
    reg [31:0]     imem [0:255];   // program
    reg [N*DW-1:0] wmem [0:255];   // weight rows: word k = W[k][0..N-1]
    reg [N*DW-1:0] ub   [0:255];   // Unified Buffer: int8 vectors

    // ------------------ controller ------------------------------------
    wire [7:0] pc, wmem_addr, ub_rd_addr, acc_wr_addr, acc_rd_addr, ub_wr_addr;
    wire       w_load, in_valid, acc_accumulate, ub_wr_en, act_relu;
    wire [2:0] act_shift;
    wire       out_valid;

    controller #(.N(N)) u_ctrl (
        .clk(clk), .rst(rst),
        .pc(pc), .instr(imem[pc]),
        .w_load(w_load), .wmem_addr(wmem_addr),
        .in_valid(in_valid), .ub_rd_addr(ub_rd_addr),
        .out_valid(out_valid), .acc_wr_addr(acc_wr_addr),
        .acc_accumulate(acc_accumulate),
        .acc_rd_addr(acc_rd_addr), .ub_wr_en(ub_wr_en), .ub_wr_addr(ub_wr_addr),
        .act_relu(act_relu), .act_shift(act_shift),
        .done(done), .cycles(cycles)
    );

    // ------------------ input side: buffer -> skew -> array -----------
    wire [N*DW-1:0] in_vec = in_valid ? ub[ub_rd_addr] : {N*DW{1'b0}};
    wire [N*DW-1:0] a_skewed;

    skew #(.N(N), .W(DW), .REVERSE(0)) u_in_skew (
        .clk(clk), .rst(rst), .din(in_vec), .dout(a_skewed)
    );

    wire [N*AW-1:0] p_bottom;
    systolic_array #(.N(N), .DW(DW), .AW(AW)) u_mxu (
        .clk(clk), .rst(rst),
        .w_load(w_load), .w_top(wmem[wmem_addr]),
        .a_left(a_skewed), .p_bottom(p_bottom)
    );

    // ------------------ output side: de-skew -> accumulators ----------
    wire [N*AW-1:0] result_vec;
    skew #(.N(N), .W(AW), .REVERSE(1)) u_out_deskew (
        .clk(clk), .rst(rst), .din(p_bottom), .dout(result_vec)
    );

    // a "valid" bit travels alongside the data with the same latency
    reg [LAT-1:0] valid_pipe;
    always @(posedge clk)
        if (rst) valid_pipe <= 0;
        else     valid_pipe <= {valid_pipe[LAT-2:0], in_valid};
    assign out_valid = valid_pipe[LAT-1];

    wire [N*AW-1:0] acc_rd_data;
    accumulators #(.N(N), .AW(AW)) u_acc (
        .clk(clk),
        .wr_en(out_valid), .accumulate(acc_accumulate),
        .wr_addr(acc_wr_addr), .wr_data(result_vec),
        .rd_addr(acc_rd_addr), .rd_data(acc_rd_data)
    );

    // ------------------ activation -> back into the Unified Buffer ----
    wire [N*DW-1:0] act_out;
    activation #(.N(N), .AW(AW)) u_act (
        .acc_in(acc_rd_data), .relu(act_relu), .shift(act_shift), .q_out(act_out)
    );

    always @(posedge clk)
        if (ub_wr_en) ub[ub_wr_addr] <= act_out;

    // start every memory at zero so unused locations are clean
    integer i;
    initial for (i = 0; i < 256; i = i + 1) begin
        imem[i] = 32'hF000_0000;   // HALT
        wmem[i] = 0;
        ub[i]   = 0;
    end
endmodule
