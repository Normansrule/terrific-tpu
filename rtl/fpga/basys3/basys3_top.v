`timescale 1ns/1ps
// =====================================================================
//  basys3_top.v - TinyTPU on a Digilent Basys 3 (Artix-7 XC7A35T)
// ---------------------------------------------------------------------
//  Works with no computer attached: four demo programs are baked into
//  block RAM. Pick one with the switches, press the centre button, and
//  the board loads it, runs it, checks every result itself, and shows
//  PASS or FAIL on the 7-segment display.
//
//  SWITCHES  sw[1:0]   demo: 0 neural net, 1 Fourier, 2 image filter, 3 Grover
//            sw[7:0]   (after a run) Unified Buffer row to show on the display
//            sw[9:8]   (after a run) which lane of that row
//            sw[13]    UART mode: the PC drives the chip (tools/tpu_host.py)
//            sw[14]    slow motion: the TPU clock ticks 4 times a second
//            sw[15]    single step: the TPU clock ticks once per press of btnU
//  BUTTONS   btnC load + run + check     btnU one clock tick (step mode)
//            btnL / btnR previous / next display view      btnD back to idle
//  DISPLAY   view 0 status (idLE, LOAd, run, PASS, FAIL)   view 1 clock cycles
//            view 2 pc and current operation                view 3 result value
//  LEDS      0 LDW   1 MMUL streaming   2 result written   3 ACT   4 results in flight
//            11:5 pc   12 running   13 done   14 FAIL   15 PASS
//
//  The TPU runs on a gated copy of the system clock (one BUFGCE), so
//  slow motion and single-stepping show every real clock edge on the LEDs.
// =====================================================================
module basys3_top #(
    parameter MEMDIR       = "mem/",
    parameter CLK_MHZ      = 50,                     // system clock made by the MMCM: 50 (safe) or 100
    parameter DEB          = CLK_MHZ * 10_000,       // button debounce: 10 ms
    parameter SLOW         = CLK_MHZ * 250_000,      // slow motion: one TPU tick every 0.25 s
    parameter CLKS_PER_BIT = CLK_MHZ * 1_000_000 / 115_200,   // UART at 115200 baud
    parameter REFRESH_BITS = 17                      // 7-segment scan: a few hundred Hz per digit
)(
    input  wire        clk_100mhz,         // board oscillator, pin W5
    input  wire [15:0] sw,
    input  wire        btnC, btnU, btnL, btnR, btnD,
    output reg  [15:0] led,
    output wire [6:0]  seg,                // segments a..g, active low
    output wire        dp,
    output wire [3:0]  an,                 // digit enables, active low
    input  wire        RsRx,               // USB-UART: PC -> FPGA
    output wire        RsTx                // USB-UART: FPGA -> PC
);
    // ------------------------------------------------------------ system clock
    //  An MMCM turns the 100 MHz oscillator into CLK_MHZ. 50 MHz leaves plenty of
    //  timing margin; try 100 once Vivado's timing report shows positive slack.
    wire clk;
`ifdef SIM
    assign clk = clk_100mhz;
`else
    wire clk_fb, clk_mmcm, locked;
    MMCME2_BASE #(.CLKIN1_PERIOD(10.0), .CLKFBOUT_MULT_F(10.0), .CLKOUT0_DIVIDE_F(1000.0 / CLK_MHZ)) u_mmcm (
        .CLKIN1(clk_100mhz), .CLKFBIN(clk_fb), .CLKFBOUT(clk_fb), .CLKOUT0(clk_mmcm),
        .LOCKED(locked), .PWRDWN(1'b0), .RST(1'b0));
    BUFG u_bufg (.I(clk_mmcm), .O(clk));
`endif

    // ------------------------------------------------------------ buttons
    wire pC, pU, pL, pR, pD;
    debounce #(.N(DEB)) dC (.clk(clk), .in(btnC), .press(pC));
    debounce #(.N(DEB)) dU (.clk(clk), .in(btnU), .press(pU));
    debounce #(.N(DEB)) dL (.clk(clk), .in(btnL), .press(pL));
    debounce #(.N(DEB)) dR (.clk(clk), .in(btnR), .press(pR));
    debounce #(.N(DEB)) dD (.clk(clk), .in(btnD), .press(pD));

    // ------------------------------------------------------------ demo ROMs (block RAM)
    reg [31:0] rom_i [0:1023], rom_w [0:1023], rom_u [0:1023], rom_e [0:1023];
    initial begin
        $readmemh({MEMDIR, "imem.hex"}, rom_i);  $readmemh({MEMDIR, "wmem.hex"}, rom_w);
        $readmemh({MEMDIR, "ub.hex"}, rom_u);    $readmemh({MEMDIR, "expect.hex"}, rom_e);
    end
    reg  [9:0]  rom_addr = 0;
    reg  [31:0] q_i = 0, q_w = 0, q_u = 0, q_e = 0;
    always @(posedge clk) begin                 // synchronous reads, so these become block RAM
        q_i <= rom_i[rom_addr]; q_w <= rom_w[rom_addr]; q_u <= rom_u[rom_addr]; q_e <= rom_e[rom_addr];
    end

    // ------------------------------------------------------------ the TPU, on a gated clock
    wire        uart_mode = sw[13];
    reg         ce = 1;
    wire        tclk;
`ifdef SIM
    reg ce_l = 1; always @(negedge clk) ce_l <= ce;     // behavioural clock gate for simulation
    assign tclk = clk & ce_l;
`else
    BUFGCE u_gate (.I(clk), .CE(ce), .O(tclk));         // glitch-free clock gate (one global buffer)
`endif
    reg         b_rst = 1, b_we = 0;
    reg  [1:0]  b_sel = 0;
    reg  [7:0]  b_addr = 0;
    reg  [31:0] b_wdata = 0;
    wire        u_rst, u_we;
    wire [1:0]  u_sel;
    wire [7:0]  u_addr;
    wire [31:0] u_wdata;
    wire        done;
    wire [31:0] cycles, ub_rdata;
    wire [127:0] acc_rdata;
    wire [15:0] dbg;
    uart_host #(.CLKS_PER_BIT(CLKS_PER_BIT)) u_host (.clk(clk), .uart_rx(RsRx), .uart_tx(RsTx),
        .host_we(u_we), .host_sel(u_sel), .host_addr(u_addr), .host_wdata(u_wdata),
        .ub_rdata(ub_rdata), .acc_rdata(acc_rdata), .tpu_rst(u_rst), .done(done), .cycles(cycles));
    tpu_top #(.N(4)) u_tpu (.clk(tclk), .rst(uart_mode ? u_rst : b_rst), .done(done), .cycles(cycles),
        .host_we(uart_mode ? u_we : b_we), .host_sel(uart_mode ? u_sel : b_sel),
        .host_addr(uart_mode ? u_addr : b_addr), .host_wdata(uart_mode ? u_wdata : b_wdata),
        .host_ub_rdata(ub_rdata), .host_acc_rdata(acc_rdata), .dbg(dbg));

    // ------------------------------------------------------------ load -> run -> check sequencer
    localparam S_IDLE = 0, S_LOAD = 1, S_RST = 2, S_RUN = 3, S_CHECK = 4, S_DONE = 5;
    reg [2:0]  st = S_IDLE;
    reg [10:0] k = 0;                          // load: 3 x 256 rows, check: 256 rows (+1 for ROM latency)
    reg [1:0]  demo = 0;
    reg [8:0]  errors = 0;
    reg [24:0] slow = 0;
    reg [31:0] ub_d = 0;
    wire [10:0] km2 = k - 11'd2;               // the row being written (two cycles behind the ROM address)
    wire       pass = (errors == 0);
    always @(posedge clk) begin
        b_we <= 0;
        // TPU clock enable: always on except while a program runs in slow or step mode
        if (st == S_RUN && !uart_mode && (sw[15] || sw[14])) begin
            slow <= (slow == SLOW - 1) ? 0 : slow + 1;
            ce   <= sw[15] ? pU : (slow == SLOW - 1);
        end else ce <= 1;
        if (pD) st <= S_IDLE;
        else case (st)
            S_IDLE, S_DONE: begin
                b_addr <= sw[7:0];                       // lets the display read any result row
                if (pC && !uart_mode) begin demo <= sw[1:0]; k <= 0; b_rst <= 1; st <= S_LOAD; end
            end
            S_LOAD: begin                                // ROM row k is read; row k-2 is written (2-cycle ROM latency)
                rom_addr <= {demo, k[7:0]};
                if (k >= 2) begin
                    b_we <= 1; b_addr <= km2[7:0]; b_sel <= km2[9:8];
                    b_wdata <= (km2[9:8] == 2'd0) ? q_i : (km2[9:8] == 2'd1) ? q_w : q_u;
                end
                k <= k + 1;
                if (k == 11'd769) begin k <= 0; st <= S_RST; end
            end
            S_RST: begin k <= k + 1;
                if (k == 3) begin b_rst <= 0; st <= S_RUN;
                    if (!uart_mode && (sw[15] || sw[14])) ce <= 0;   // step/slow: don't let a free tick slip in
                end
            end
            S_RUN: if (done) begin k <= 0; errors <= 0; st <= S_CHECK; end
            S_CHECK: begin                               // compare every Unified Buffer row with the answer key
                rom_addr <= {demo, k[7:0]}; b_addr <= k[7:0]; ub_d <= ub_rdata;
                if (k >= 2 && ub_d != q_e) errors <= errors + 1;
                k <= k + 1;
                if (k == 11'd257) st <= S_DONE;
            end
        endcase
    end

    // ------------------------------------------------------------ display
    reg [1:0] view = 0;
    always @(posedge clk) begin
        if (pR) view <= view + 1;
        if (pL) view <= view - 1;
        if (pC) view <= 0;
    end
    // value to show in decimal: cycles (view 1) or the selected result lane (view 3)
    wire signed [7:0] lane = ub_rdata[sw[9:8] * 8 +: 8];
    wire        neg  = (view == 2'd3) && lane[7];
    wire [13:0] mag  = (view == 2'd3) ? (lane[7] ? -lane : lane) : (cycles > 9999 ? 14'd9999 : cycles[13:0]);
    wire [15:0] bcd;
    bin2bcd u_bcd (.bin(mag), .bcd(bcd));
    // characters: 0-9 digits, then A b C d E F H I L n o P r S U - (blank) u
    localparam A = 10, Bb = 11, Cc = 12, Dd = 13, E = 14, F = 15, H = 16, I = 17, L = 18, Nn = 19, O = 20, P = 21, R = 22, S = 23, U = 24, MI = 25, BL = 26, UU = 27;
    reg [4:0] ch [0:3];                          // ch[3] is the leftmost digit
    wire [7:0] pcv = dbg[7:0];
    always @(*) begin
        case (view)
            2'd0: case (uart_mode ? 3'd7 : st)
                    S_IDLE:  begin ch[3] = I;  ch[2] = Dd; ch[1] = L;  ch[0] = E;  end
                    S_LOAD, S_RST: begin ch[3] = L; ch[2] = O; ch[1] = A; ch[0] = Dd; end
                    S_RUN, S_CHECK: begin ch[3] = R; ch[2] = UU; ch[1] = Nn; ch[0] = BL; end
                    S_DONE:  if (pass) begin ch[3] = P; ch[2] = A; ch[1] = S; ch[0] = S; end
                             else      begin ch[3] = F; ch[2] = A; ch[1] = I; ch[0] = L; end
                    default: begin ch[3] = U; ch[2] = A; ch[1] = R; ch[0] = 5'd0 + 26; end   // "UAr " = UART mode
                  endcase
            2'd1: begin ch[3] = bcd[15:12]; ch[2] = bcd[11:8]; ch[1] = bcd[7:4]; ch[0] = bcd[3:0]; end
            2'd2: begin                                // e.g. "Ld 3" while loading weights for pc 3
                    if (dbg[8])       begin ch[3] = L;  ch[2] = Dd; end
                    else if (dbg[9])  begin ch[3] = Nn; ch[2] = Nn; end   // "nn" = MMUL streaming
                    else if (dbg[11]) begin ch[3] = A;  ch[2] = Cc; end
                    else              begin ch[3] = MI; ch[2] = MI; end
                    ch[1] = (pcv / 10) % 10; ch[0] = pcv % 10;
                  end
            default: begin ch[3] = neg ? MI : BL; ch[2] = bcd[11:8]; ch[1] = bcd[7:4]; ch[0] = bcd[3:0]; end
        endcase
    end
    reg [REFRESH_BITS-1:0] scan = 0;
    always @(posedge clk) scan <= scan + 1;
    wire [1:0] digit = scan[REFRESH_BITS-1 -: 2];
    sevenseg u_7 (.ch(ch[digit]), .seg(seg));
    assign an = ~(4'b0001 << digit);
    assign dp = ~(digit == view);                // the lit decimal point shows which view you are in

    // ------------------------------------------------------------ LEDs
    always @(posedge clk)
        led <= {pass && st == S_DONE, !pass && st == S_DONE, done, !b_rst || (uart_mode && !u_rst), dbg[6:0], dbg[12], dbg[11], dbg[10], dbg[9], dbg[8]};
endmodule

// ---------------------------------------------------------------- helpers
module debounce #(parameter N = 1_000_000) (input wire clk, input wire in, output reg press = 0);
    reg s0 = 0, s1 = 0, stable = 0;
    reg [$clog2(N + 1):0] cnt = 0;
    always @(posedge clk) begin
        s0 <= in; s1 <= s0; press <= 0;
        if (s1 == stable) cnt <= 0;
        else if (cnt == N) begin stable <= s1; cnt <= 0; if (s1) press <= 1; end
        else cnt <= cnt + 1;
    end
endmodule

module bin2bcd (input wire [13:0] bin, output reg [15:0] bcd);   // double dabble, 0..9999
    integer i;
    always @(*) begin
        bcd = 0;
        for (i = 13; i >= 0; i = i - 1) begin
            if (bcd[3:0] > 4)   bcd[3:0]   = bcd[3:0] + 3;
            if (bcd[7:4] > 4)   bcd[7:4]   = bcd[7:4] + 3;
            if (bcd[11:8] > 4)  bcd[11:8]  = bcd[11:8] + 3;
            if (bcd[15:12] > 4) bcd[15:12] = bcd[15:12] + 3;
            bcd = {bcd[14:0], bin[i]};
        end
    end
endmodule

module sevenseg (input wire [4:0] ch, output reg [6:0] seg);      // seg[0] = a ... seg[6] = g, active low
    reg [6:0] on;
    always @(*) begin
        case (ch)
            0: on = 7'h3F; 1: on = 7'h06; 2: on = 7'h5B; 3: on = 7'h4F; 4: on = 7'h66;
            5: on = 7'h6D; 6: on = 7'h7D; 7: on = 7'h07; 8: on = 7'h7F; 9: on = 7'h6F;
            10: on = 7'h77; 11: on = 7'h7C; 12: on = 7'h39; 13: on = 7'h5E; 14: on = 7'h79;
            15: on = 7'h71; 16: on = 7'h76; 17: on = 7'h30; 18: on = 7'h38; 19: on = 7'h54;
            20: on = 7'h5C; 21: on = 7'h73; 22: on = 7'h50; 23: on = 7'h6D; 24: on = 7'h3E;
            25: on = 7'h40; 27: on = 7'h1C; default: on = 7'h00;
        endcase
        seg = ~on;
    end
endmodule
