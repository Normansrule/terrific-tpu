`timescale 1ns/1ps
// =====================================================================
//  uart_host.v - the serial command protocol, as a reusable block
// ---------------------------------------------------------------------
//  Turns bytes from a serial port into host-port writes, a "run" request,
//  and reads of the results (protocol table in tpu_uart_top.v and
//  docs/21-fpga.md). Used by tpu_uart_top.v and by the Basys 3 top.
// =====================================================================
module uart_host #(
    parameter CLKS_PER_BIT = 104
)(
    input  wire         clk,
    input  wire         uart_rx,
    output wire         uart_tx,
    output reg          host_we = 0,
    output reg  [1:0]   host_sel = 0,
    output reg  [7:0]   host_addr = 0,
    output reg  [31:0]  host_wdata = 0,
    input  wire [31:0]  ub_rdata,
    input  wire [127:0] acc_rdata,
    output reg          tpu_rst = 1,
    input  wire         done,
    input  wire [31:0]  cycles
);
    wire       rx_valid;
    wire [7:0] rx_data;
    reg        tx_start = 0;
    reg  [7:0] tx_data = 0;
    wire       tx_busy;
    uart_rx #(.CLKS_PER_BIT(CLKS_PER_BIT)) u_rx (.clk(clk), .rx(uart_rx), .valid(rx_valid), .data(rx_data));
    uart_tx #(.CLKS_PER_BIT(CLKS_PER_BIT)) u_tx (.clk(clk), .start(tx_start), .data(tx_data), .tx(uart_tx), .busy(tx_busy));

    // ---- command state machine
    localparam S_CMD = 0, S_ADDR = 1, S_DATA = 2, S_WRITE = 3, S_RUN = 4, S_SEND = 5, S_RST = 6;
    reg [2:0]   st = S_CMD;
    reg [7:0]   cmd = 0;
    reg [2:0]   nbytes = 0;
    reg [135:0] txbuf = 0;                  // up to 17 bytes, sent from the top
    reg [4:0]   txleft = 0;
    reg [1:0]   rstcnt = 0;
    always @(posedge clk) begin
        host_we <= 0; tx_start <= 0;
        case (st)
            S_CMD: if (rx_valid) begin
                cmd <= rx_data;
                case (rx_data)
                    "P": begin txbuf[135:128] <= "K"; txleft <= 1; st <= S_SEND; end
                    "G": begin tpu_rst <= 1; rstcnt <= 3; st <= S_RST; end
                    "I", "W", "U", "R", "A": st <= S_ADDR;
                    default: ;                  // ignore unknown bytes
                endcase
            end
            S_ADDR: if (rx_valid) begin
                host_addr <= rx_data; nbytes <= 0; host_wdata <= 0;
                if (cmd == "R") st <= S_WRITE;          // reads reuse S_WRITE to wait one cycle for data
                else if (cmd == "A") st <= S_WRITE;
                else st <= S_DATA;
            end
            S_DATA: if (rx_valid) begin
                // instructions arrive big-endian; memory rows arrive lane 0 first
                if (cmd == "I") host_wdata <= {host_wdata[23:0], rx_data};
                else host_wdata <= {rx_data, host_wdata[31:8]};
                nbytes <= nbytes + 1;
                if (nbytes == 3) st <= S_WRITE;
            end
            S_WRITE: begin
                if (cmd == "R") begin txbuf[135:104] <= {ub_rdata[7:0], ub_rdata[15:8], ub_rdata[23:16], ub_rdata[31:24]}; txleft <= 4; st <= S_SEND; end
                else if (cmd == "A") begin
                    txbuf[135:8] <= {acc_rdata[31:0], acc_rdata[63:32], acc_rdata[95:64], acc_rdata[127:96]};
                    txleft <= 16; st <= S_SEND;
                end else begin
                    host_we <= 1; host_sel <= (cmd == "I") ? 2'd0 : (cmd == "W") ? 2'd1 : 2'd2; st <= S_CMD;
                end
            end
            S_RST: begin rstcnt <= rstcnt - 1; if (rstcnt == 1) begin tpu_rst <= 0; st <= S_RUN; end end
            S_RUN: if (done) begin
                tpu_rst <= 1;
                txbuf[135:96] <= {"D", cycles}; txleft <= 5; st <= S_SEND;
            end
            S_SEND: if (!tx_busy && !tx_start) begin
                if (txleft == 0) st <= S_CMD;
                else begin tx_data <= txbuf[135:128]; tx_start <= 1; txbuf <= txbuf << 8; txleft <= txleft - 1; end
            end
        endcase
    end
endmodule
