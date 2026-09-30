// =====================================================================
//  tb_tpu_top.v  -  runs any program on TinyTPU (v1 or v2) and checks
//                   ALL 256 Unified Buffer words and ALL 256 accumulators
// ---------------------------------------------------------------------
//  1. load the images made by tools/golden_model.py
//  2. release reset, wait for 'done'
//  3. compare against the instruction-level answer key
//  4. write build/tpu.vcd for GTKWave and the waveform renderer
// =====================================================================
`timescale 1ns/1ps
module tb_tpu_top;
    localparam N = 4;
    reg clk = 0, rst = 1;
    wire done;
    wire [31:0] cycles;

    tpu_top #(.N(N)) dut (.clk(clk), .rst(rst), .done(done), .cycles(cycles),
                  .host_we(1'b0), .host_sel(2'd0), .host_addr(8'd0), .host_wdata(), .host_ub_rdata(), .host_acc_rdata());
    always #5 clk = ~clk;

    reg [N*8-1:0]  expect_ub  [0:255];
    reg [N*32-1:0] expect_acc [0:255];
    integer i, errors;

    initial begin
        if (!$test$plusargs("novcd")) begin
            $dumpfile("build/tpu.vcd");
            $dumpvars(0, tb_tpu_top);
        end
        #1;
        $readmemh("build/imem.hex",       dut.imem);
        $readmemh("build/wmem.hex",       dut.wmem);
        $readmemh("build/ub.hex",         dut.ub);
        $readmemh("build/expect_ub.hex",  expect_ub);
        $readmemh("build/expect_acc.hex", expect_acc);

        repeat (3) @(posedge clk);
        rst = 0;
        fork
            begin wait (done); end
            begin #200000; $display("TIMEOUT: TPU never raised done"); $finish; end
        join_any
        disable fork;
        @(posedge clk);

        errors = 0;
        for (i = 0; i < 256; i = i + 1) begin
            if (dut.ub[i] !== expect_ub[i]) begin
                if (errors < 8) $display("  MISMATCH ub[%0d]  got %h  expected %h", i, dut.ub[i], expect_ub[i]);
                errors = errors + 1;
            end
            if (dut.u_acc.mem[i] !== expect_acc[i]) begin
                if (errors < 8) $display("  MISMATCH acc[%0d] got %h  expected %h", i, dut.u_acc.mem[i], expect_acc[i]);
                errors = errors + 1;
            end
        end
        // dump the chip's own final memories so pictures can be drawn from them
        $writememh("build/final_ub.hex",  dut.ub);
        $writememh("build/final_acc.hex", dut.u_acc.mem);
        $display("-------------------------------------------------");
        $display("  TinyTPU finished in %0d clock cycles", cycles);
        if (errors == 0) $display("  PASS  - all 512 memory words match the answer key");
        else             $display("  FAIL  - %0d mismatches", errors);
        $display("-------------------------------------------------");
        $finish;
    end
endmodule
