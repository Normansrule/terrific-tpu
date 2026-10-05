`timescale 1ns/1ps
// =====================================================================
//  vga_view.v - a live picture of the TPU on any VGA monitor (640 x 480)
// ---------------------------------------------------------------------
//  Draws, every frame:
//    * the 4 x 4 systolic array; a PE lights magenta on the clock cycles
//      it is multiplying (the diagonal wavefront, in real hardware)
//    * the four input lanes (blue) and the four result lanes (green)
//    * five lamps: LDW, MMUL, result written, ACT, results in flight
//    * a big cycle counter, a program-counter bar, and a status banner
//  The Basys 3 has a 12-bit VGA port (4 bits each of red, green, blue).
//  Pixel clock: 25 MHz (a pixel every second tick of the 50 MHz clock),
//  close enough to the 25.175 MHz standard for every monitor we know of.
// =====================================================================
module vga_view (
    input  wire        clk,            // 50 MHz system clock
    input  wire [15:0] pe_busy,        // bit r*4+c: PE(r,c) multiplying this cycle
    input  wire [3:0]  lane_in,        // input lanes carrying data
    input  wire        result,         // a result row is being written
    input  wire [4:0]  ops,            // {in flight, ACT, result, MMUL, LDW}
    input  wire [7:0]  pc,
    input  wire [13:0] cycles,
    input  wire [2:0]  status,         // 0 idle, 1 load, 2 run, 3 pass, 4 fail, 5 uart
    output reg         hsync = 1,
    output reg         vsync = 1,
    output reg  [11:0] rgb = 0         // {red, green, blue}, 4 bits each
);
    reg pix = 0;
    reg [9:0] x = 0, y = 0;
    always @(posedge clk) begin
        pix <= ~pix;
        if (pix) begin
            x <= (x == 799) ? 0 : x + 1;
            if (x == 799) y <= (y == 524) ? 0 : y + 1;
        end
    end
    // ---- colours
    localparam BG = 12'h102, PANEL = 12'h213, DIM = 12'h325, MAG = 12'hE3F, VIO = 12'hA8F, BLU = 12'h6AF,
               GRN = 12'h3D9, AMB = 12'hFB2, RED = 12'hF54, WHT = 12'hEEF, GRY = 12'h778;
    // ---- helpers
    function inbox(input [9:0] px, py, x0, y0, w, h); inbox = px >= x0 && px < x0 + w && py >= y0 && py < y0 + h; endfunction
    // 7-segment digit inside a 32 x 56 box: returns the segment number under (dx, dy), or 7 for none
    function [2:0] segat(input [9:0] dx, dy);
        begin
            segat = 7;
            if      (dy < 6  && dx >= 4 && dx < 28)  segat = 0;                 // a
            else if (dx >= 26 && dy >= 4 && dy < 28) segat = 1;                 // b
            else if (dx >= 26 && dy >= 28 && dy < 52) segat = 2;                // c
            else if (dy >= 50 && dx >= 4 && dx < 28) segat = 3;                 // d
            else if (dx < 6  && dy >= 28 && dy < 52) segat = 4;                 // e
            else if (dx < 6  && dy >= 4 && dy < 28)  segat = 5;                 // f
            else if (dy >= 25 && dy < 31 && dx >= 4 && dx < 28) segat = 6;      // g
        end
    endfunction
    function [6:0] segs(input [3:0] d);
        case (d) 0: segs = 7'h3F; 1: segs = 7'h06; 2: segs = 7'h5B; 3: segs = 7'h4F; 4: segs = 7'h66;
                 5: segs = 7'h6D; 6: segs = 7'h7D; 7: segs = 7'h07; 8: segs = 7'h7F; default: segs = 7'h6F; endcase
    endfunction
    wire [15:0] bcd;
    bin2bcd u_bcd (.bin(cycles), .bcd(bcd));

    // ---- one pixel
    reg [11:0] c;
    reg [2:0]  s;
    reg [3:0]  dg;
    reg [6:0]  lit;
    integer r, k;
    always @(*) begin
        c = BG;
        // header band, coloured by status
        if (y < 36) c = (status == 3) ? 12'h1A5 : (status == 4) ? 12'hA22 : (status == 2) ? 12'h52A : (status == 1) ? 12'h862 : PANEL;
        // the array: 4 x 4 PEs, 72 px pitch, at (96, 84)
        for (r = 0; r < 4; r = r + 1) for (k = 0; k < 4; k = k + 1)
            if (inbox(x, y, 96 + k * 72, 84 + r * 72, 60, 60))
                c = pe_busy[r * 4 + k] ? MAG : (inbox(x, y, 98 + k * 72, 86 + r * 72, 56, 56) ? DIM : VIO);
        // input lanes (left) and result lanes (below)
        for (r = 0; r < 4; r = r + 1) if (inbox(x, y, 40, 104 + r * 72, 40, 20)) c = lane_in[r] ? BLU : PANEL;
        for (k = 0; k < 4; k = k + 1) if (inbox(x, y, 106 + k * 72, 380, 40, 24)) c = result ? GRN : PANEL;
        // right panel
        if (inbox(x, y, 400, 60, 216, 380)) c = PANEL;
        for (k = 0; k < 5; k = k + 1)
            if (inbox(x, y, 416 + k * 40, 76, 32, 32))
                c = ops[k] ? (k == 0 ? AMB : k == 1 ? VIO : k == 2 ? MAG : k == 3 ? GRN : BLU) : DIM;
        // cycle counter: four 32 x 56 digits
        for (k = 0; k < 4; k = k + 1)
            if (inbox(x, y, 424 + k * 44, 140, 32, 56)) begin
                dg = bcd[(3 - k) * 4 +: 4];
                s = segat(x - (424 + k * 44), y - 140);
                lit = segs(dg);
                if (s != 7) c = lit[s] ? WHT : 12'h324;
            end
        // program counter: 16 cells, lit up to pc
        for (k = 0; k < 16; k = k + 1) if (inbox(x, y, 416 + k * 12, 228, 10, 20)) c = (k < pc) ? BLU : DIM;
        // status banner
        if (inbox(x, y, 416, 280, 184, 60))
            c = (status == 3) ? GRN : (status == 4) ? RED : (status == 2) ? VIO : (status == 1) ? AMB : (status == 5) ? BLU : GRY;
        // PASS: a big check mark; FAIL: a cross (drawn as thick diagonals)
        if (inbox(x, y, 416, 360, 184, 70)) begin
            if (status == 3 && ((y - 360 + 0 >= (x - 470) && y - 360 <= (x - 470) + 10 && x >= 470 && x < 500) ||
                                (x >= 500 && x < 560 && (y - 360) + (x - 500) >= 30 && (y - 360) + (x - 500) <= 42))) c = GRN;
            if (status == 4 && ((x - 470 >= y - 360 && x - 470 <= y - 350 && x >= 470 && x < 540) ||
                                (x >= 470 && x < 540 && (540 - x) >= y - 360 && (540 - x) <= y - 350))) c = RED;
        end
        if (x >= 640 || y >= 480) c = 0;                  // blanking
    end
    always @(posedge clk) if (pix) begin
        rgb   <= c;
        hsync <= ~(x >= 656 && x < 752);                  // 640 + 16 front porch, 96 sync
        vsync <= ~(y >= 490 && y < 492);                  // 480 + 10 front porch, 2 sync
    end
endmodule
