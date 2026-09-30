`timescale 1ns/1ps
// =====================================================================
//  tpu_top.v (v2)  -  TinyTPU with double-buffered weights and
//                     overlapped instructions
// ---------------------------------------------------------------------
//  Same memories, same instruction set, same testbench as v1.
//  New: pe_db (shadow weights), a swap flag that rides through the skew
//  with the data, and a METADATA PIPELINE that carries each vector's
//  destination address and accumulate flag alongside it:
//
//   controller --{valid, acc_addr, accumulate}--> [ 2N-1 stage pipe ] --> accumulators
//   controller --{data, swap}--> skew --> array --> de-skew ------------^
// =====================================================================
module tpu_top #(
    parameter N  = 4,
    parameter DW = 8,
    parameter AW = 32,
    parameter HW = (N * DW > 32) ? N * DW : 32    // host data width
)(
    input  wire        clk,
    input  wire        rst,
    output wire        done,
    output wire [31:0] cycles,
    // ---- host port: lets a wrapper (UART, SPI, a CPU) load memories and read
    //      results. Write while the TPU is held in reset. Testbenches tie host_we = 0.
    input  wire                 host_we,
    input  wire [1:0]           host_sel,     // 0 = instruction, 1 = weight memory, 2 = Unified Buffer
    input  wire [7:0]           host_addr,
    input  wire [HW-1:0]        host_wdata,
    output wire [N*DW-1:0]      host_ub_rdata,
    output wire [N*AW-1:0]      host_acc_rdata
);
    localparam LAT = 2*N - 1;

    reg [31:0]     imem [0:255];
    reg [N*DW-1:0] wmem [0:255];
    reg [N*DW-1:0] ub   [0:255];

    wire [7:0] pc, wmem_addr, ub_rd_addr, in_acc_addr, acc_rd_addr, ub_wr_addr;
    wire       w_load, in_valid, in_swap, in_accumulate, ub_wr_en, act_relu;
    wire [2:0] act_shift;
    wire [31:0] stall_cycles;

    reg  [LAT-1:0] valid_pipe;
    reg  [LAT-1:0] accum_pipe;
    reg  [7:0]     addr_pipe [0:LAT-1];
    wire           pipe_busy = |valid_pipe;

    controller_pipe #(.N(N)) u_ctrl (
        .clk(clk), .rst(rst), .pc(pc), .instr(imem[pc]),
        .w_load(w_load), .wmem_addr(wmem_addr),
        .in_valid(in_valid), .in_swap(in_swap), .ub_rd_addr(ub_rd_addr),
        .in_acc_addr(in_acc_addr), .in_accumulate(in_accumulate),
        .pipe_busy(pipe_busy),
        .acc_rd_addr(acc_rd_addr), .ub_wr_en(ub_wr_en), .ub_wr_addr(ub_wr_addr),
        .act_relu(act_relu), .act_shift(act_shift),
        .done(done), .cycles(cycles), .stall_cycles(stall_cycles)
    );

    // ---- input: pack {swap, data} per lane so both get the same skew ----
    wire [N*DW-1:0]     in_vec = in_valid ? ub[ub_rd_addr] : {N*DW{1'b0}};
    wire [N*(DW+1)-1:0] in_packed, skewed_packed;
    wire [N*DW-1:0]     a_skewed;
    wire [N-1:0]        s_skewed;
    genvar l;
    generate
        for (l = 0; l < N; l = l + 1) begin : pack
            assign in_packed[l*(DW+1) +: DW+1] = {in_swap & in_valid, in_vec[l*DW +: DW]};
            assign a_skewed[l*DW +: DW]        = skewed_packed[l*(DW+1) +: DW];
            assign s_skewed[l]                 = skewed_packed[l*(DW+1) + DW];
        end
    endgenerate

    skew #(.N(N), .W(DW+1), .REVERSE(0)) u_in_skew (
        .clk(clk), .rst(rst), .din(in_packed), .dout(skewed_packed));

    wire [N*AW-1:0] p_bottom, result_vec;
    systolic_array_db #(.N(N), .DW(DW), .AW(AW)) u_mxu (
        .clk(clk), .rst(rst), .w_load(w_load), .w_top(wmem[wmem_addr]),
        .a_left(a_skewed), .s_left(s_skewed), .p_bottom(p_bottom));

    skew #(.N(N), .W(AW), .REVERSE(1)) u_out_deskew (
        .clk(clk), .rst(rst), .din(p_bottom), .dout(result_vec));

    // ---- metadata pipeline: travels with the data, 2N-1 stages ----
    integer i;
    always @(posedge clk) begin
        if (rst) begin
            valid_pipe <= 0; accum_pipe <= 0;
            for (i = 0; i < LAT; i = i + 1) addr_pipe[i] <= 0;
        end else begin
            valid_pipe <= {valid_pipe[LAT-2:0], in_valid};
            accum_pipe <= {accum_pipe[LAT-2:0], in_accumulate};
            addr_pipe[0] <= in_acc_addr;
            for (i = 1; i < LAT; i = i + 1) addr_pipe[i] <= addr_pipe[i-1];
        end
    end

    wire [N*AW-1:0] acc_rd_data;
    accumulators #(.N(N), .AW(AW)) u_acc (
        .clk(clk),
        .wr_en(valid_pipe[LAT-1]), .accumulate(accum_pipe[LAT-1]),
        .wr_addr(addr_pipe[LAT-1]), .wr_data(result_vec),
        .rd_addr(acc_rd_addr), .rd_data(acc_rd_data),
        .rd2_addr(host_addr), .rd2_data(host_acc_rdata));

    wire [N*DW-1:0] act_out;
    activation #(.N(N), .AW(AW)) u_act (
        .acc_in(acc_rd_data), .relu(act_relu), .shift(act_shift), .q_out(act_out));

    always @(posedge clk)
        if (ub_wr_en) ub[ub_wr_addr] <= act_out;
        else if (host_we && host_sel == 2'd2) ub[host_addr] <= host_wdata[N*DW-1:0];

    always @(posedge clk) begin
        if (host_we && host_sel == 2'd0) imem[host_addr] <= host_wdata[31:0];
        if (host_we && host_sel == 2'd1) wmem[host_addr] <= host_wdata[N*DW-1:0];
    end
    assign host_ub_rdata = ub[host_addr];

    initial for (i = 0; i < 256; i = i + 1) begin
        imem[i] = 32'hF000_0000; wmem[i] = 0; ub[i] = 0;
    end
endmodule
