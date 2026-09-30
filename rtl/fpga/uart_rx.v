`timescale 1ns/1ps
// uart_rx.v - 8N1 receiver: 1 start bit, 8 data bits (LSB first), 1 stop bit.
// CLKS_PER_BIT = clock frequency / baud rate (e.g. 12 MHz / 115200 ≈ 104).
module uart_rx #(parameter CLKS_PER_BIT = 104) (
    input  wire       clk,
    input  wire       rx,
    output reg        valid,      // one-cycle pulse with a new byte
    output reg  [7:0] data
);
    reg rx1 = 1, rx2 = 1;                       // two-flop synchronizer
    always @(posedge clk) begin rx1 <= rx; rx2 <= rx1; end
    localparam IDLE = 0, START = 1, BITS = 2, STOP = 3;
    reg [1:0]  st = IDLE;
    reg [15:0] cnt = 0;
    reg [2:0]  bitn = 0;
    always @(posedge clk) begin
        valid <= 0;
        case (st)
            IDLE:  if (!rx2) begin st <= START; cnt <= CLKS_PER_BIT / 2; end
            START: if (cnt == 0) begin
                       if (!rx2) begin st <= BITS; cnt <= CLKS_PER_BIT - 1; bitn <= 0; end
                       else st <= IDLE;                          // glitch, not a start bit
                   end else cnt <= cnt - 1;
            BITS:  if (cnt == 0) begin
                       data <= {rx2, data[7:1]}; cnt <= CLKS_PER_BIT - 1;
                       if (bitn == 7) st <= STOP; bitn <= bitn + 1;
                   end else cnt <= cnt - 1;
            STOP:  if (cnt == 0) begin valid <= rx2; st <= IDLE; end
                   else cnt <= cnt - 1;
        endcase
    end
endmodule
