`timescale 1ns/1ps
// =====================================================================
//  controller.v  -  reads instructions and drives the whole chip
// ---------------------------------------------------------------------
//  Instruction word (32 bits):
//
//   31    28 27        20 19        12 11         4 3      0
//  +--------+------------+------------+------------+--------+
//  | opcode |     A      |     B      |     C      | flags  |
//  +--------+------------+------------+------------+--------+
//
//  opcode  name  meaning
//  ------  ----  --------------------------------------------------------
//   0x0    NOP   do nothing
//   0x1    LDW   load an N x N weight tile from weight memory [A .. A+N-1]
//   0x2    MMUL  stream B vectors from unified buffer [A..] through the
//                array; write results to accumulators [C..]
//                flags[0] = 1 -> add to what is already there (accumulate)
//   0x3    ACT   read B accumulator rows [A..], apply activation,
//                write int8 vectors to unified buffer [C..]
//                flags[0] = ReLU on/off, flags[3:1] = right-shift amount
//   0xF    HALT  stop, raise 'done'
//
//  State machine:
//     FETCH -> DECODE -> { LDW | MMUL | ACT } -> FETCH ...  -> HALT
// =====================================================================
module controller #(
    parameter N = 4
)(
    input  wire        clk,
    input  wire        rst,
    // instruction memory
    output reg  [7:0]  pc,
    input  wire [31:0] instr,
    // weight path
    output reg         w_load,
    output reg  [7:0]  wmem_addr,
    // input streaming (MMUL)
    output reg         in_valid,
    output reg  [7:0]  ub_rd_addr,
    // accumulator write side (driven by results coming out of the array)
    input  wire        out_valid,
    output reg  [7:0]  acc_wr_addr,
    output reg         acc_accumulate,
    // activation side (ACT)
    output reg  [7:0]  acc_rd_addr,
    output reg         ub_wr_en,
    output reg  [7:0]  ub_wr_addr,
    output reg         act_relu,
    output reg  [2:0]  act_shift,
    // status
    output reg         done,
    output reg  [31:0] cycles
);
    localparam LAT = 2*N - 1;   // cycles from "vector in" to "vector out"

    localparam OP_NOP = 4'h0, OP_LDW = 4'h1, OP_MMUL = 4'h2,
               OP_ACT = 4'h3, OP_HALT = 4'hF;

    localparam S_FETCH = 3'd0, S_DECODE = 3'd1, S_LDW = 3'd2,
               S_MMUL = 3'd3, S_ACT = 3'd4, S_HALT = 3'd5;

    reg [2:0]  state;
    reg [31:0] ir;          // instruction register
    reg [8:0]  cnt;         // step counter inside an instruction

    wire [3:0] op    = ir[31:28];
    wire [7:0] fA    = ir[27:20];
    wire [7:0] fB    = ir[19:12];
    wire [7:0] fC    = ir[11:4];
    wire [3:0] flags = ir[3:0];

    // ---------------- combinational outputs ----------------
    always @(*) begin
        w_load      = 1'b0;
        wmem_addr   = 8'd0;
        in_valid    = 1'b0;
        ub_rd_addr  = 8'd0;
        acc_rd_addr = 8'd0;
        ub_wr_en    = 1'b0;
        ub_wr_addr  = 8'd0;
        act_relu    = flags[0];
        act_shift   = flags[3:1];
        case (state)
            S_LDW: begin
                // push the LAST row first so row 0 ends up at the top
                w_load    = 1'b1;
                wmem_addr = fA + (N - 1 - cnt[7:0]);
            end
            S_MMUL: begin
                in_valid   = (cnt < {1'b0, fB});
                ub_rd_addr = fA + cnt[7:0];
            end
            S_ACT: begin
                acc_rd_addr = fA + cnt[7:0];
                ub_wr_en    = 1'b1;
                ub_wr_addr  = fC + cnt[7:0];
            end
            default: ;
        endcase
    end

    // ---------------- sequential state machine ----------------
    always @(posedge clk) begin
        if (rst) begin
            state          <= S_FETCH;
            pc             <= 8'd0;
            ir             <= 32'd0;
            cnt            <= 9'd0;
            acc_wr_addr    <= 8'd0;
            acc_accumulate <= 1'b0;
            done           <= 1'b0;
            cycles         <= 32'd0;
        end else begin
            if (!done) cycles <= cycles + 1;

            // results leaving the array are written in any state
            if (out_valid) acc_wr_addr <= acc_wr_addr + 1;

            case (state)
                S_FETCH: begin
                    ir    <= instr;
                    pc    <= pc + 1;
                    cnt   <= 0;
                    state <= S_DECODE;
                end
                S_DECODE: begin
                    case (op)
                        OP_LDW:  state <= S_LDW;
                        OP_MMUL: begin
                            acc_wr_addr    <= fC;
                            acc_accumulate <= flags[0];
                            state          <= S_MMUL;
                        end
                        OP_ACT:  state <= (fB == 0) ? S_FETCH : S_ACT;
                        OP_HALT: state <= S_HALT;
                        default: state <= S_FETCH;   // NOP / unknown
                    endcase
                end
                S_LDW: begin
                    cnt <= cnt + 1;
                    if (cnt == N - 1) state <= S_FETCH;
                end
                S_MMUL: begin
                    // keep going until the last vector has drained out
                    cnt <= cnt + 1;
                    if (cnt == {1'b0, fB} + LAT - 1) state <= S_FETCH;
                end
                S_ACT: begin
                    cnt <= cnt + 1;
                    if (cnt == {1'b0, fB} - 1) state <= S_FETCH;
                end
                S_HALT: done <= 1'b1;
                default: state <= S_FETCH;
            endcase
        end
    end
endmodule
