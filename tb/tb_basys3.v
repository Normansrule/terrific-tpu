// =====================================================================
//  tb_basys3.v - presses the Basys 3 buttons and flips its switches in
//  simulation, exactly as you would on the real board:
//    * each of the 4 baked-in demos: load, run, self-check -> PASS LED
//    * single-step mode: the TPU must not move until btnU is pressed
//    * slow motion and the result display
//  Build with -DSIM (behavioural clock gate) and run from rtl/fpga/basys3/.
// =====================================================================
`timescale 1ns/1ps
module tb_basys3;
    reg clk = 0; always #5 clk = ~clk;                 // 100 MHz
    reg [15:0] sw = 0;
    reg btnC = 0, btnU = 0, btnL = 0, btnR = 0, btnD = 0;
    wire [15:0] led; wire [6:0] seg; wire dp; wire [3:0] an; wire tx;
    basys3_top #(.DEB(4), .SLOW(40), .CLKS_PER_BIT(8), .REFRESH_BITS(4)) dut (
        .clk_100mhz(clk), .sw(sw), .btnC(btnC), .btnU(btnU), .btnL(btnL), .btnR(btnR), .btnD(btnD),
        .led(led), .seg(seg), .dp(dp), .an(an), .RsRx(1'b1), .RsTx(tx));
    integer fails = 0, i, d, c0;
    integer expect_v1 [0:3], expect_v2 [0:3];
    // (a task can't drive a reg passed by argument while it runs, so pick the button by number)
    task press(input integer which); begin
        case (which) 0: btnC = 1; 1: btnU = 1; 2: btnL = 1; 3: btnR = 1; 4: btnD = 1; endcase
        repeat (20) @(posedge clk);
        btnC = 0; btnU = 0; btnL = 0; btnR = 0; btnD = 0;
        repeat (20) @(posedge clk);
    end endtask
    task wait_done(output ok); integer t; begin
        ok = 0; for (t = 0; t < 200000 && !(led[15] || led[14]); t = t + 1) @(posedge clk);
        ok = led[15];
    end endtask
    reg ok;
    initial begin
        repeat (10) @(posedge clk);
        // ---- 1. every demo passes its own self-check
        for (d = 0; d < 4; d = d + 1) begin
            sw = d; press(0); wait_done(ok);
            $display("  demo %0d: %s after %0d TPU cycles (LEDs %b)", d, ok ? "PASS" : "FAIL", dut.cycles, led);
            if (!ok) fails = fails + 1;
        end
        // ---- 2. single step: nothing moves until btnU
        sw = 16'h8000; press(0);
        repeat (2000) @(posedge clk);
        c0 = dut.cycles;
        if (dut.st != 3 || c0 != 0) begin $display("  step mode: TPU ran without a button press (cycles = %0d)", c0); fails = fails + 1; end
        for (i = 0; i < 10; i = i + 1) press(1);
        if (dut.cycles != 10) begin $display("  step mode: 10 presses gave %0d cycles", dut.cycles); fails = fails + 1; end
        else $display("  step mode: 10 presses of btnU = exactly 10 TPU clock cycles");
        // ---- 3. slow motion finishes the program on its own
        sw = 16'h4000; wait_done(ok);
        $display("  slow motion: %s (%0d cycles)", ok ? "PASS" : "FAIL", dut.cycles); if (!ok) fails = fails + 1;
        // ---- 4. result view shows a non-zero Unified Buffer row of the neural network, lane 0
        for (i = 16; i < 32; i = i + 1) if (dut.u_tpu.ub[i][7:0] != 0 && sw == 16'h4000) sw = i;   // a non-zero result
        press(3); press(3); press(3);                                                         // view 3
        repeat (5) @(posedge clk);
        $display("  display view %0d shows ub[%0d] lane 0 = %0d (Unified Buffer holds %0d)", dut.view, sw[7:0], dut.neg ? -dut.mag : dut.mag, $signed(dut.ub_rdata[7:0]));
        if ((dut.neg ? -dut.mag : dut.mag) != $signed(dut.ub_rdata[7:0])) fails = fails + 1;
        // ---- 5. the self-check really checks: corrupt the answer key mid-check, expect FAIL
        sw = 0; press(0);
        while (dut.st != 4) @(posedge clk);
        force dut.q_e = 32'hDEADBEEF; wait_done(ok); release dut.q_e;
        $display("  sabotaged answer key: board shows %s (LED 14 = %b)", led[14] ? "FAIL, as it should" : "PASS (self-check is broken!)", led[14]);
        if (!led[14]) fails = fails + 1;
        $display("-------------------------------------------------");
        if (fails == 0) $display("  PASS  - Basys 3 top: demos, single step, slow motion, display");
        else            $display("  FAIL  - %0d problems", fails);
        $finish;
    end
endmodule
