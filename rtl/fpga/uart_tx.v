`timescale 1ns/1ps
// uart_tx.v - 8N1 transmitter. Pulse `start` with `data` while `busy` is low.
module uart_tx #(parameter CLKS_PER_BIT = 104) (
    input  wire       clk,
    input  wire       start,
    input  wire [7:0] data,
    output reg        tx = 1,
    output wire       busy
);
    reg [9:0]  sh = 10'h3FF;
    reg [3:0]  left = 0;
    reg [15:0] cnt = 0;
    assign busy = left != 0;
    always @(posedge clk) begin
        if (!busy && start) begin sh <= {1'b1, data, 1'b0}; left <= 10; cnt <= 0; end
        else if (busy) begin
            if (cnt == 0) begin tx <= sh[0]; sh <= {1'b1, sh[9:1]}; left <= left - 1; cnt <= CLKS_PER_BIT - 1; end
            else cnt <= cnt - 1;
        end
    end
endmodule
