// =====================================================================
//  tb_uart.v - drives tpu_uart_top exactly like tools/tpu_host.py does:
//  loads a program and data over the serial line, runs it, reads every
//  result back over the serial line, and checks them against the answer key.
// =====================================================================
`timescale 1ns/1ps
module tb_uart;
    localparam CPB = 4;                       // short bits keep the simulation fast
    reg clk = 0, rx = 1;
    wire tx, busy;
    tpu_uart_top #(.CLKS_PER_BIT(CPB)) dut (.clk(clk), .uart_rx(rx), .uart_tx(tx), .led_busy(busy));
    always #5 clk = ~clk;

    reg [31:0]  imem [0:255];
    reg [31:0]  wmem [0:255], ub [0:255], eub [0:255];
    reg [127:0] eacc [0:255];
    integer i, k, errors = 0, halt_at;
    reg [7:0] b;
    reg [31:0] word, cyc;
    reg [127:0] big;

    task send(input [7:0] v); integer j; begin
        rx = 0; repeat (CPB) @(posedge clk);
        for (j = 0; j < 8; j = j + 1) begin rx = v[j]; repeat (CPB) @(posedge clk); end
        rx = 1; repeat (CPB * 2) @(posedge clk);
    end endtask
    task recv(output [7:0] v); integer j; begin
        @(negedge tx); repeat (CPB + CPB / 2) @(posedge clk);
        for (j = 0; j < 8; j = j + 1) begin v[j] = tx; repeat (CPB) @(posedge clk); end
    end endtask
    task send_row(input [7:0] c, input [7:0] a, input [31:0] d); begin
        send(c); send(a); send(d[7:0]); send(d[15:8]); send(d[23:16]); send(d[31:24]);
    end endtask

    initial begin
        $readmemh("build/imem.hex", imem); $readmemh("build/wmem.hex", wmem); $readmemh("build/ub.hex", ub);
        $readmemh("build/expect_ub.hex", eub); $readmemh("build/expect_acc.hex", eacc);
        repeat (10) @(posedge clk);
        send("P"); recv(b); if (b !== "K") begin $display("FAIL: ping answered %h", b); $finish; end
        halt_at = 255;
        for (i = 255; i >= 0; i = i - 1) if (imem[i][31:28] != 4'hF) begin halt_at = i + 1; i = -1; end
        for (i = 0; i <= halt_at && i < 256; i = i + 1) begin
            send("I"); send(i); send(imem[i][31:24]); send(imem[i][23:16]); send(imem[i][15:8]); send(imem[i][7:0]);
        end
        for (i = 0; i < 256; i = i + 1) if (wmem[i] != 0) send_row("W", i, wmem[i]);
        for (i = 0; i < 256; i = i + 1) if (ub[i] != 0) send_row("U", i, ub[i]);
        send("G"); recv(b);
        if (b !== "D") begin $display("FAIL: expected 'D' after run, got %h", b); $finish; end
        for (k = 0; k < 4; k = k + 1) begin recv(b); cyc = {cyc[23:0], b}; end
        for (i = 0; i < 256; i = i + 1) begin
            send("R"); send(i);
            for (k = 0; k < 4; k = k + 1) begin recv(b); word = {b, word[31:8]}; end
            if (word !== eub[i]) begin if (errors < 5) $display("  ub[%0d] got %h expected %h", i, word, eub[i]); errors = errors + 1; end
            send("A"); send(i);
            for (k = 0; k < 16; k = k + 1) begin recv(b); big = {big[119:0], b}; end
            // lanes arrive lane 0 first, each big-endian: reorder to {lane3, lane2, lane1, lane0}
            big = {big[31:0], big[63:32], big[95:64], big[127:96]};
            if (big !== eacc[i]) begin if (errors < 5) $display("  acc[%0d] got %h expected %h", i, big, eacc[i]); errors = errors + 1; end
        end
        $display("-------------------------------------------------");
        $display("  over UART: TinyTPU finished in %0d clock cycles", cyc);
        if (errors == 0) $display("  PASS  - all 512 memory words read back over the serial port match");
        else $display("  FAIL  - %0d mismatches", errors);
        $finish;
    end
    initial begin #400000000; $display("TIMEOUT"); $finish; end
endmodule
