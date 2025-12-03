`timescale 1ns/1ps
`include "cpu_defs.vh"

module cpu_tb_file;

    // ===============================================================
    // 1. SIGNALS
    // ===============================================================
    wire [3:0]  debug_alu_res;
    wire [3:0]  debug_ram_out;
    wire        debug_cout;
    
    reg         clk;
    reg         reset_n;
    reg  [10:0] instruction;

    // Instruction Memory (Simulated)
    // capable of holding up to 256 instructions
    reg [10:0] prog_mem [0:255]; 
    integer pc; // Program Counter (Index)

    // Helper strings for printing
    reg [8*3:1] op_str; 

    // ===============================================================
    // 2. DUT INSTANTIATION
    // ===============================================================
    cpu_top u_cpu (
        .debug_alu_res (debug_alu_res),
        .debug_ram_out (debug_ram_out),
        .debug_cout    (debug_cout),
        .clk           (clk),
        .reset_n       (reset_n),
        .instruction   (instruction)
    );

    // ===============================================================
    // 3. CLOCK GENERATION
    // ===============================================================
    initial begin
        clk = 0;
        forever #5 clk = ~clk; 
    end

    // ===============================================================
    // 4. TEST SEQUENCE
    // ===============================================================
    initial begin
        // 1. Load the Hex File
        // Ensure you have a file named "program.hex" in the same folder
        $readmemh("/home/sriram/Projects/4_Bit_CPU/program.hex", prog_mem);

        // 2. Initialize
        reset_n = 0;
        instruction = 0;

        // 3. Print Header
        $display("\n========================================================================================================");
        $display("                                   GENERIC HEX PROGRAM LOADER                                           ");
        $display("========================================================================================================");
        $display("| PC  | Op  | Dest | Src/Val | Act ALU | RAM State | Cout | Description                                |");
        $display("|-----|-----|------|---------|---------|-----------|------|--------------------------------------------|");

        // 4. Reset Sequence
        repeat(2) @(posedge clk);
        reset_n = 1;
        @(negedge clk); // Align to negative edge for driving inputs

        // 5. Execution Loop
        for (pc = 0; pc < 256; pc = pc + 1) begin
            
            // Fetch instruction from our simulated memory array
            instruction = prog_mem[pc];

            // STOP Condition: If instruction is undefined (x) or 0 (assuming empty ROM is 0), stop.
            // Note: 000 is actually STO 0 0, so be careful. We check for 'x' which readmemh leaves for empty lines.
            if (instruction === 11'bx) begin
                $display("========================================================================================================");
                $display("[INFO] End of Program reached at PC=%0d.", pc);
                $finish;
            end

            // Helper: Decode Opcode to String for display
            case (`GET_OPCODE(instruction))
                `OPC_STO: op_str = "STO";
                `OPC_ADD: op_str = "ADD";
                `OPC_SUB: op_str = "SUB";
                `OPC_AND: op_str = "AND";
                `OPC_OR:  op_str = "OR ";
                `OPC_XOR: op_str = "XOR";
                `OPC_NOT: op_str = "NOT";
                default:  op_str = "???";
            endcase

            // Run the Cycle
            run_cycle();

        end
    end

    // ===============================================================
    // TASK: Run One Instruction Cycle
    // ===============================================================
    task run_cycle;
        reg [3:0] dest;
        reg [3:0] src;
        reg [3:0] ram_val;
        begin
            dest = `GET_OP1(instruction);
            src  = `GET_OP2(instruction);

            // 1. Execute (Fetch -> Exec -> Store)
            // Wait 2 cycles to get to Store state
            repeat(2) @(posedge clk);
            #1; // Wait for logic

            // Capture ALU result before write ends
            // (We could check against an expected value here if we had one)

            // Finish Write
            @(posedge clk);
            #1;

            // Peek at RAM
            ram_val = u_cpu.u_ram.mem[dest];

            // Print Row
            $display("| %3d | %s |  %1h   |    %1h    |    %1h    |    %1h      |   %b  | Executed Instruction                       |", 
                     pc, op_str, dest, src, debug_alu_res, ram_val, debug_cout);
            
            // Re-align
            @(negedge clk);
        end
    endtask

endmodule