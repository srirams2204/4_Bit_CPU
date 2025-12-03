`timescale 1ns/1ps
`include "cpu_defs.vh"

module cpu_tb;
    wire [3:0] debug_alu_res, debug_ram_out;
    wire       debug_cout;
    reg        clk, reset_n;
    reg [10:0] instruction;
    integer    errors;

    cpu_top u_cpu (
        .debug_alu_res(debug_alu_res), .debug_ram_out(debug_ram_out), .debug_cout(debug_cout),
        .clk(clk), .reset_n(reset_n), .instruction(instruction)
    );

    // Clock Gen
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    initial begin
        reset_n = 0; instruction = 0; errors = 0;

        $display("\n========================================================================================================================");
        $display("| Time | Op  | Dest | Src/Val | Exp Val | Act ALU | RAM Check | Cout |   STATUS   | Description                         |");
        $display("|------|-----|------|---------|---------|---------|-----------|------|------------|-------------------------------------|");

        // --- RESET SEQUENCE ---
        repeat(2) @(posedge clk);
        reset_n = 1;
        
        // Align to Negative Edge so we change inputs safely
        @(negedge clk);

        // 1. STO 4, 5
        instruction = {`OPC_STO, 4'h4, 4'h5}; 
        run_and_check("STO", 4'h4, 4'h5, 4'h5, 0, "Store Constant 5 to Addr 4");

        // 2. ADD 4, 6
        instruction = {`OPC_ADD, 4'h4, 4'h6};
        run_and_check("ADD", 4'h4, 4'h6, 4'hB, 0, "Add 6 to RAM[4] (5+6=11)");

        // 3. STO 1, 15
        instruction = {`OPC_STO, 4'h1, 4'hF};
        run_and_check("STO", 4'h1, 4'hF, 4'hF, 0, "Store Constant 15 to Addr 1");

        // 4. SUB 1, 7
        instruction = {`OPC_SUB, 4'h1, 4'h7};
        run_and_check("SUB", 4'h1, 4'h7, 4'h8, 1, "Sub 7 from RAM[1] (15-7=8)");

        // 5. NOT 15
        instruction = {`OPC_NOT, 4'hF, 4'h0};
        run_and_check("NOT", 4'hF, 4'h0, 4'hF, 0, "Invert RAM[15] (~0=15)");

        if (errors == 0) $display("\n[SUCCESS] ALL TESTS PASSED.\n");
        else $display("\n[FAILURE] %0d ERRORS FOUND.\n", errors);
        $finish;
    end

    task run_and_check;
        input [8*3:1] op_name;
        input [3:0] dest_addr, src_val, exp_val;
        input exp_cout;
        input [8*35:1] desc;
        reg [3:0] actual_ram_val;
        begin
            // We drive input at negedge. 
            // Wait 2 full cycles (FETCH->EXEC->STORE)
            // We check ALU during STORE (Cycle 3)
            repeat(2) @(posedge clk); 
            #1; 

            if (debug_alu_res !== exp_val) begin
                 $display("| %4t | %s |  %1h   |    %1h    |    %1h    |    %1h    |    -      |   %b  | *** FAIL *** | ALU HOLD FAIL (Got %h)      |", 
                    $time, op_name, dest_addr, src_val, exp_val, debug_alu_res, debug_cout, debug_alu_res);
                 errors = errors + 1;
            end

            // Advance to finish Write
            @(posedge clk);
            #1;

            actual_ram_val = u_cpu.u_ram.mem[dest_addr];
            if (actual_ram_val !== exp_val) begin
                $display("| %4t | %s |  %1h   |    %1h    |    %1h    |    %1h    |    %1h      |   %b  | *** FAIL *** | RAM WRITE FAIL                  |", 
                    $time, op_name, dest_addr, src_val, exp_val, debug_alu_res, actual_ram_val, debug_cout);
                errors = errors + 1;
            end else begin
                if (debug_alu_res === exp_val)
                    $display("| %4t | %s |  %1h   |    %1h    |    %1h    |    %1h    |    %1h      |   %b  |     PASS     | %-35s |", 
                        $time, op_name, dest_addr, src_val, exp_val, debug_alu_res, actual_ram_val, debug_cout, desc);
            end

            // Re-align to Negedge for next instruction update
            @(negedge clk);
        end
    endtask
endmodule