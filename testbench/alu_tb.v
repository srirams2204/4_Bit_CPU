`timescale 1ns/1ps
`include "cpu_defs.vh"

module reg_alu_tb;

    // ===============================================================
    // 1. SIGNALS & CONSTANTS
    // ===============================================================
    reg        clk;
    reg        reset_n;
    reg  [3:0] alu_sel;
    reg  [3:0] a;
    reg  [3:0] b;
    
    wire [3:0] f;
    wire       cout;

    // For self-checking
    reg [3:0] expected_f;
    reg       expected_cout;
    integer   errors;

    // ===============================================================
    // 2. DUT INSTANTIATION (Outputs First)
    // ===============================================================
    reg_alu u_dut (
        .f       (f),
        .cout    (cout),
        .clk     (clk),
        .reset_n (reset_n),
        .alu_sel (alu_sel),
        .a       (a),
        .b       (b)
    );

    // ===============================================================
    // 3. CLOCK GENERATION
    // ===============================================================
    initial begin
        clk = 0;
        forever #5 clk = ~clk; // 10ns Period
    end

    // ===============================================================
    // 4. TEST SCENARIOS
    // ===============================================================
    initial begin
        $dumpfile("waveform/alu_tb.vcd");
        $dumpvars(0, reg_alu_tb);
        // Initialize
        reset_n = 0;
        alu_sel = 0;
        a       = 0;
        b       = 0;
        errors  = 0;

        // Header for the table
        $display("\n=========================================================================================");
        $display("                                REGISTERED ALU TESTBENCH                                 ");
        $display("=========================================================================================");
        $display("| Time  | Operation          | Sel  | A    | B    | Exp F | Exp C | Act F | Act C | Pass |");
        $display("|-------|--------------------|------|------|------|-------|-------|-------|-------|------|");

        // Release Reset
        @(negedge clk);
        reset_n = 1;

        // --- ARITHMETIC TESTS ---
        
        // 1. Transfer A (Add 0)
        check_op("TRANSFER A", `ALU_TRANSFER, 4'h5, 4'h3, 4'h5, 0); 
        
        // 2. Increment A (A + 1)
        check_op("INCREMENT A", `ALU_INC, 4'h5, 4'h3, 4'h6, 0);
        
        // 3. Add A + B
        check_op("ADD A + B", `ALU_ADD_AB, 4'h5, 4'h3, 4'h8, 0);
        
        // 4. Add with Carry (Overflow case: 10 + 7 = 17 -> 1, Cout=1)
        check_op("ADD A+B (Ovf)", `ALU_ADD_AB, 4'hA, 4'h7, 4'h1, 1);

        // 5. Add A + B + Cin
        check_op("ADD A+B+Cin", `ALU_ADD_ABCIN, 4'h2, 4'h2, 4'h5, 0);

        // 6. Sub with Borrow (A + ~B) -> 5 - 3 - 1 = 1
        check_op("SUB (Borrow)", `ALU_SUB_A_B, 4'h5, 4'h3, 4'h1, 1); 

        // 7. Subtract (A - B) -> 5 - 3 = 2
        // Note: A - B is A + ~B + 1. 
        // 5 (0101) + ~3(1100) + 1 = 0101 + 1101 = 10010 (Res=2, Cout=1)
        // Cout=1 in subtraction usually means "No Borrow" / Positive result
        check_op("SUBTRACT", `ALU_SUB_A_B_1, 4'h5, 4'h3, 4'h2, 1);

        // 8. Decrement A (A - 1) -> 5 - 1 = 4
        check_op("DECREMENT A", `ALU_DEC, 4'h5, 4'h3, 4'h4, 1);

        // --- LOGIC TESTS (Cout is 0) ---

        // 9. OR
        check_op("OR", `ALU_OR_MASK, 4'hA, 4'h5, 4'hF, 0); // 1010 | 0101 = 1111

        // 10. XOR
        check_op("XOR", `ALU_XOR_MASK, 4'hA, 4'h5, 4'hF, 0); // 1010 ^ 0101 = 1111

        // 11. AND
        check_op("AND", `ALU_AND_MASK, 4'hA, 4'hC, 4'h8, 0); // 1010 & 1100 = 1000

        // 12. NOT
        check_op("NOT A", `ALU_NOT_MASK, 4'hA, 4'h0, 4'h5, 0); // ~1010 = 0101

        // --- SUMMARY ---
        $display("=========================================================================================");
        if (errors == 0)
            $display("TEST PASSED: All operations verified correctly.");
        else
            $display("TEST FAILED: %0d errors found.", errors);
        $display("=========================================================================================\n");
        
        $finish;
    end

    // ===============================================================
    // 5. CHECKER TASK
    // ===============================================================
    task check_op;
        input [19*8:1] name; // String for op name
        input [3:0]    sel;
        input [3:0]    in_a;
        input [3:0]    in_b;
        input [3:0]    exp_f;
        input          exp_cout;
        begin
            // 1. Setup Inputs
            alu_sel = sel;
            a       = in_a;
            b       = in_b;

            // 2. Wait for Clock Edge (ALU is registered!)
            @(posedge clk);
            #1; // Hold time buffer to read outputs

            // 3. Verify
            if (f !== exp_f || cout !== exp_cout) begin
                $display("| %4t | %-18s | %b |  %h   |  %h   |   %h   |   %b   |   %h   |   %b   | FAIL |", 
                    $time, name, sel, in_a, in_b, exp_f, exp_cout, f, cout);
                errors = errors + 1;
            end else begin
                $display("| %4t | %-18s | %b |  %h   |  %h   |   %h   |   %b   |   %h   |   %b   | PASS |", 
                    $time, name, sel, in_a, in_b, exp_f, exp_cout, f, cout);
            end
        end
    endtask

endmodule