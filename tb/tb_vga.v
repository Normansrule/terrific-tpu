// =====================================================================
//  tb_vga.v - captures what the Basys 3's VGA port would put on a
//  monitor, as image files: one frame mid-run (single-stepped into the
//  wavefront) and one after PASS. Run from rtl/fpga/basys3/ with -DSIM.
//  Output: ../../../build/vga_run.ppm and ../../../build/vga_pass.ppm
// =====================================================================
`timescale 1ns/1ps
module tb_vga;
    reg clk = 0; always #5 clk = ~clk;
    reg [15:0] sw = 0;
    reg btnC = 0, btnU = 0;
    wire [15:0] led; wire [6:0] seg; wire dp; wire [3:0] an, r, g, b; wire tx, hs, vs;
    basys3_top #(.DEB(4), .SLOW(40), .CLKS_PER_BIT(8), .REFRESH_BITS(4)) dut (
        .clk_100mhz(clk), .sw(sw), .btnC(btnC), .btnU(btnU), .btnL(1'b0), .btnR(1'b0), .btnD(1'b0),
        .led(led), .seg(seg), .dp(dp), .an(an), .RsRx(1'b1), .RsTx(tx), .vgaRed(r), .vgaGreen(g), .vgaBlue(b), .Hsync(hs), .Vsync(vs));
    reg [11:0] frame [0:640*480-1];
    integer i, fd, hs_count = 0, last_hs = 1, lines = 0;
    task grab(input [8*40-1:0] name); integer px; begin
        while (!(dut.u_vga.x == 0 && dut.u_vga.y == 0 && dut.u_vga.pix)) @(posedge clk);
        hs_count = 0;
        for (px = 0; px < 800 * 525; px = px + 1) begin
            @(posedge clk); while (!dut.u_vga.pix) @(posedge clk);
            if (dut.u_vga.x < 640 && dut.u_vga.y < 480) frame[dut.u_vga.y * 640 + dut.u_vga.x] = dut.u_vga.c;
        end
        fd = $fopen(name, "w"); $fwrite(fd, "P3\n640 480\n15\n");
        for (i = 0; i < 640 * 480; i = i + 1) $fwrite(fd, "%0d %0d %0d\n", frame[i][11:8], frame[i][7:4], frame[i][3:0]);
        $fclose(fd); $display("  wrote %0s", name);
    end endtask
    task press_c; begin btnC = 1; repeat (20) @(posedge clk); btnC = 0; repeat (20) @(posedge clk); end endtask
    task press_u; begin btnU = 1; repeat (20) @(posedge clk); btnU = 0; repeat (20) @(posedge clk); end endtask
    always @(posedge clk) begin if (last_hs && !hs) hs_count = hs_count + 1; last_hs = hs; end
    initial begin
        sw = 16'h8000; press_c;                          // demo 0, single-step
        while (dut.st != 3) @(posedge clk);
        repeat (12) press_u;                             // into the MMUL wavefront
        $display("  stepped to cycle %0d; PEs busy: %b", dut.cycles, dut.pe_busy);
        grab("../../../build/vga_run.ppm");
        $display("  one frame = %0d hsync pulses (a 640 x 480 frame has 525 lines)", hs_count);
        if (hs_count != 525) $display("  FAIL: wrong line count"); else $display("  PASS  - VGA timing: 525 lines per frame, 800 pixels per line");
        sw = 0; while (!led[15] && !led[14]) @(posedge clk);
        grab("../../../build/vga_pass.ppm");
        $finish;
    end
endmodule
