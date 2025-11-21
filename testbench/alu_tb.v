`timescale 1ns/1ps
`include "cpu_defs.vh"

module alu_tb;

    reg clk;
    reg rst;

    reg  [3:0] a;
    reg  [3:0] b;
    reg        cin;
    reg  [2:0] sel;

    wire [3:0] out;
    wire       cout;

    // DUT
    reg_alu4 uut (
        .alu_out(out),
        .cout(cout),
        .a(a),
        .b(b),
        .cin(cin),
        .alu_sel(sel),
        .clk(clk),
        .rst(rst)
    );

    // Clock
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    // Helpers
    task apply_and_check(
        input [2:0] sel_in,
        input       cin_in,
        input [3:0] a_in,
        input [3:0] b_in,
        input [3:0] expected_out,
        input       expected_cout,
        input [8*80:1] case_name
    );
    begin
        sel = sel_in;
        cin = cin_in;
        a   = a_in;
        b   = b_in;

        @(posedge clk); // inputs sampled by combinational logic
        @(posedge clk); // outputs registered on next clock edge

        $display("TEST %-20s | sel=%b cin=%b a=%04b b=%04b | out=%04b cout=%b | exp=%04b %b",
                 case_name, sel, cin, a, b, out, cout, expected_out, expected_cout);

        if (out !== expected_out || cout !== expected_cout) begin
            $display("  >>> MISMATCH for %s (got %h/%b expected %h/%b)", case_name, out, cout, expected_out, expected_cout);
        end
    end
    endtask

    initial begin
        $dumpfile("waveform/alu.vcd");
        $dumpvars(0, alu_tb);

        $display("========================================================");
        $display("        4-bit REGISTERED ALU TESTBENCH START");
        $display("========================================================");

        // Reset
        rst = 1; a = 0; b = 0; cin = 0; sel = 0;
        #12;
        rst = 0;
        #10;

        // ---------- TEST VECTORS ----------
        // We'll test with specific vectors chosen to show behavior

        // 1) TRANSFER a (ALU_TRANSFER) -> a + 0
        apply_and_check(3'b000, 1'b0, 4'b1010, 4'b0000, (4'b1010), 1'b0, "TRANSFER A");

        // 2) INCREMENT a (ALU_INC)
        apply_and_check(3'b000, 1'b1, 4'b0101, 4'b0000, 4'b0110, 1'b0, "INCREMENT A");

        // 3) ADD a + b (no cin)
        apply_and_check(3'b001, 1'b0, 4'b0011, 4'b0100, 4'b0111, 1'b0, "ADD A+B");

        // 4) ADD a + b + cin
        apply_and_check(3'b001, 1'b1, 4'b0011, 4'b0100, 4'b1000, 1'b0, "ADD A+B+Cin");

        // 5) SUB: a + (~b)  (borrow mode)
        // compute expected: (a + ~b) & 0xF, cout from fa_cout (we calculate using integer math)
        apply_and_check(3'b010, 1'b0, 4'b1010, 4'b0011, ( (4'b1010 + (~4'b0011 & 4'hF) ) & 4'hF ), 1'b1, "SUB a+(~b)");

        // 6) SUB with +1: a + (~b) + 1  -> expecting a - b
        apply_and_check(3'b010, 1'b1, 4'b1010, 4'b0011, ( (4'b1010 + (~4'b0011 & 4'hF) + 1) & 4'hF ), 1'b1, "SUB a+(~b)+1");

        // 7) DECREMENT (a-1)
        apply_and_check(3'b011, 1'b1, 4'b0111, 4'b0000, ( (4'b0111 + 4'b1111 + 1) & 4'hF ), 1'b1, "DECREMENT A");

        // 8) PASS A (using PASS_A pattern)
        apply_and_check(3'b011, 1'b1, 4'b1011, 4'b0000, ( (4'b1011 + 4'b1111 + 1) & 4'hF ), 1'b1, "PASS A");

        // 9) OR (logical)
        apply_and_check(3'b100, 1'b0, 4'b1010, 4'b0101, 4'b1111, 1'b0, "OR");

        // 10) XOR
        apply_and_check(3'b101, 1'b0, 4'b1010, 4'b0101, 4'b1111, 1'b0, "XOR");

        // 11) AND
        apply_and_check(3'b110, 1'b0, 4'b1010, 4'b0101, 4'b0000, 1'b0, "AND");

        // 12) NOT (logical)
        apply_and_check(3'b111, 1'b0, 4'b1010, 4'b0000, (~4'b1010 & 4'hF), 1'b0, "NOT");

        $display("\n=== TEST COMPLETE ===");
        #20;
        $finish;
    end

endmodule
