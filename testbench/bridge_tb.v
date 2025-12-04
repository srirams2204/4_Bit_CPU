`timescale 1ns/1ps
`include "cpu_defs.vh"

module cpu_tb_gui;

    // ===============================================================
    // 1. SIGNALS
    // ===============================================================
    wire [3:0]  debug_alu_res;
    wire [3:0]  debug_ram_out;
    wire        debug_cout;
    
    reg         clk;
    reg         reset_n;
    reg  [10:0] instruction;

    // Instruction Memory (256 slots)
    reg [10:0] prog_mem [0:255]; 
    integer pc;

    // Helper for printing opcode strings
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
    // WAVEFORM DUMPING (For GTKWave)
    // ===============================================================
    initial begin
        $dumpfile("simulation.vcd");
        $dumpvars(0, cpu_tb_gui);
    end
    
    // ===============================================================
    // 4. MAIN EXECUTION LOOP
    // ===============================================================
    initial begin
        // 1. Load the Hex File created by the GUI
        // The GUI MUST save "program.hex" before running this simulation
        $readmemh("program.hex", prog_mem);

        // 2. Initialize
        reset_n = 0;
        instruction = 0;

        // 3. Reset Sequence
        repeat(2) @(posedge clk);
        reset_n = 1;
        @(negedge clk); 

        // 4. Run Loop
        // We scan until we hit an undefined instruction (x) or limit
        for (pc = 0; pc < 256; pc = pc + 1) begin
            
            instruction = prog_mem[pc];

            // STOP Condition: Undefined instruction implies end of program
            if (instruction === 11'bx) begin
                $display("[DONE]"); // Signal to GUI that we finished
                $finish;
            end

            // Decode Opcode for logging
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

            // Log the start of execution (Python reads this to highlight current line)
            $display("[EXEC] PC:%0d | Op:%s | Dest:%h | Src:%h", 
                     pc, op_str, `GET_OP1(instruction), `GET_OP2(instruction));

            // Run the hardware cycle
            run_cycle();
        end
        
        $display("[DONE]");
        $finish;
    end

    // ===============================================================
    // TASK: Run One Instruction & Log Updates
    // ===============================================================
    task run_cycle;
        reg [3:0] dest;
        reg [3:0] ram_val;
        
        // MOVED DECLARATIONS TO TOP (Fixes Syntax Error)
        integer file, r, inj_step, inj_addr, inj_val;

        begin
            dest = `GET_OP1(instruction);

            // 1. Execute (FETCH -> EXEC -> STORE)
            // Wait 2 cycles to get to Store state
            repeat(2) @(posedge clk);
            #1; 

            // (Optional: Log ALU intermediate result if needed)

            // Finish Write
            @(posedge clk);
            #1;

            // --- INJECTION LOGIC ---
            file = $fopen("injections.txt", "r");
            if (file) begin
                while (!$feof(file)) begin
                    r = $fscanf(file, "%d %h %h\n", inj_step, inj_addr, inj_val);
                    // If the injection is for the CURRENT step (pc counter), apply it
                    if (inj_step == pc) begin
                        // FORCE WRITE to RAM
                        u_cpu.u_ram.mem[inj_addr] = inj_val;
                        $display("[INJECT] Step:%0d RAM[%h]=%h", inj_step, inj_addr, inj_val);
                        // Also update our local view if we injected into the dest addr
                        if (inj_addr == dest) begin
                             // Wait small delay for write to settle? Not needed for blocking assignment
                        end
                    end
                end
                $fclose(file);
            end
            // -----------------------

            // 2. Peek at RAM to see the result
            ram_val = u_cpu.u_ram.mem[dest];

            // 3. Log the RAM Update (Python reads this to update the table)
            // Format: [RAM] Addr:<HexAddr> Val:<HexData>
            $display("[RAM] Addr:%h Val:%h", dest, ram_val);
            
            // Re-align
            @(negedge clk);
        end
    endtask

endmodule