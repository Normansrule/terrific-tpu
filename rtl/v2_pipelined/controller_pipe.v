`timescale 1ns/1ps
// =====================================================================
//  controller_pipe.v  -  v2 controller: overlaps instructions safely
// ---------------------------------------------------------------------
//  Same instruction set and encoding as v1.  What changed:
//
//   * MMUL no longer waits for its results to drain out of the array.
//     It streams its B vectors and moves on.  The destination address
//     and accumulate flag ride down a pipeline next to each vector
//     (see tpu_top.v), so the controller can forget about them.
//
//   * LDW loads the SHADOW weights, so it can run while an earlier MMUL
//     is still inside the array ... but only after that MMUL's swap
//     wavefront has reached the last PE (2N-2 cycles after it started).
//     Counter: swap_wait.
//
//   * ACT and HALT must see finished results, so they wait until no
//     result is still in flight.  Signal: pipe_busy.
//
//  These three rules are a tiny "scoreboard": the same kind of hazard
//  checking every pipelined processor does.
// =====================================================================
module controller_pipe #(
    parameter N = 4
)(
    input  wire        clk,
    input  wire        rst,
    output reg  [7:0]  pc,
    input  wire [31:0] instr,
    output reg         w_load,
    output reg  [7:0]  wmem_addr,
    output reg         in_valid,
    output reg         in_swap,        // first vector of a MMUL
    output reg  [7:0]  ub_rd_addr,
    output reg  [7:0]  in_acc_addr,    // where this vector's result goes
    output reg         in_accumulate,
    input  wire        pipe_busy,      // any result still in flight?
    output reg  [7:0]  acc_rd_addr,
    output reg         ub_wr_en,
    output reg  [7:0]  ub_wr_addr,
    output reg         act_relu,
    output reg  [2:0]  act_shift,
    output reg         done,
    output reg  [31:0] cycles,
    output reg  [31:0] stall_cycles
);
    localparam OP_LDW = 4'h1, OP_MMUL = 4'h2, OP_ACT = 4'h3, OP_HALT = 4'hF;
    localparam S_FETCH = 3'd0, S_DECODE = 3'd1, S_LDW = 3'd2,
               S_MMUL = 3'd3, S_ACT = 3'd4, S_HALT = 3'd5;
    localparam SWAP_SPAN = 2*N - 3;      // cycles until the last PE has swapped

    reg [2:0]  state;
    reg [31:0] ir;
    reg [8:0]  cnt;
    reg [7:0]  swap_wait;

    wire [3:0] op    = ir[31:28];
    wire [7:0] fA    = ir[27:20];
    wire [7:0] fB    = ir[19:12];
    wire [7:0] fC    = ir[11:4];
    wire [3:0] flags = ir[3:0];

    // hazard check for the instruction sitting in DECODE
    wire stall = (op == OP_LDW  && swap_wait != 0) ||
                 ((op == OP_ACT || op == OP_HALT) && pipe_busy);

    always @(*) begin
        w_load = 0; wmem_addr = 0;
        in_valid = 0; in_swap = 0; ub_rd_addr = 0;
        in_acc_addr = fC + cnt[7:0]; in_accumulate = flags[0];
        acc_rd_addr = 0; ub_wr_en = 0; ub_wr_addr = 0;
        act_relu = flags[0]; act_shift = flags[3:1];
        case (state)
            S_LDW:  begin w_load = 1; wmem_addr = fA + (N - 1 - cnt[7:0]); end
            S_MMUL: begin in_valid = 1; in_swap = (cnt == 0); ub_rd_addr = fA + cnt[7:0]; end
            S_ACT:  begin acc_rd_addr = fA + cnt[7:0]; ub_wr_en = 1; ub_wr_addr = fC + cnt[7:0]; end
            default: ;
        endcase
    end

    always @(posedge clk) begin
        if (rst) begin
            state <= S_FETCH; pc <= 0; ir <= 0; cnt <= 0; swap_wait <= 0;
            done <= 0; cycles <= 0; stall_cycles <= 0;
        end else begin
            if (!done) cycles <= cycles + 1;
            if (swap_wait != 0) swap_wait <= swap_wait - 1;
            case (state)
                S_FETCH: begin ir <= instr; pc <= pc + 1; cnt <= 0; state <= S_DECODE; end
                S_DECODE: begin
                    if (stall) stall_cycles <= stall_cycles + 1;
                    else case (op)
                        OP_LDW:  state <= S_LDW;
                        OP_MMUL: state <= (fB == 0) ? S_FETCH : S_MMUL;
                        OP_ACT:  state <= (fB == 0) ? S_FETCH : S_ACT;
                        OP_HALT: state <= S_HALT;
                        default: state <= S_FETCH;
                    endcase
                end
                S_LDW: begin cnt <= cnt + 1; if (cnt == N - 1) state <= S_FETCH; end
                S_MMUL: begin
                    if (cnt == 0) swap_wait <= SWAP_SPAN;
                    cnt <= cnt + 1;
                    if (cnt == {1'b0, fB} - 1) state <= S_FETCH;
                end
                S_ACT: begin cnt <= cnt + 1; if (cnt == {1'b0, fB} - 1) state <= S_FETCH; end
                S_HALT: done <= 1;
                default: state <= S_FETCH;
            endcase
        end
    end
endmodule
