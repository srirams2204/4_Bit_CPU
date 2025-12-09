`timescale 1ns/1ps
`include "cpu_defs.vh"

module cpu_tb_step;

    // Signals
    wire [3:0]  debug_alu_res;
    wire [3:0]  debug_ram_out;
    wire        debug_cout;
    reg         clk;
    reg         reset_n;
    reg  [10:0] instruction;

    // Instruction Memory (256 slots)
    reg [10:0] prog_mem [0:255];
    integer pc;
    integer sf, r; // file handles
    integer i;
    reg [3:0] acc_val;
    reg carry_val;
    reg [3:0] tmp_ram;
    reg [1023:0] ram_line;

    // For logging
    reg [23:0] op_str;

    // DUT
    cpu_top u_cpu (
        .debug_alu_res (debug_alu_res),
        .debug_ram_out (debug_ram_out),
        .debug_cout    (debug_cout),
        .clk           (clk),
        .reset_n       (reset_n),
        .instruction   (instruction)
    );

    // Clock
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    // Waveform
    initial begin
        $dumpfile("simulation.vcd");
        $dumpvars(0, cpu_tb_step);
    end

    // MAIN: single-step execution using external state file
    initial begin

        // Load program
        $readmemh("program.hex", prog_mem);

        // Default state
        pc = 0;
        acc_val = 4'b0000;
        carry_val = 0;
        for (i = 0; i < 16; i = i + 1) u_cpu.u_ram.mem[i] = 4'b0000;

        // Reset pulse first (clear internals)
        reset_n = 0;
        @(posedge clk); @(posedge clk);
        reset_n = 1;
        @(negedge clk);

        // After reset, load the saved cpu_state (so reset doesn't overwrite it)
        sf = $fopen("cpu_state.hex", "r");
        if (sf) begin
            // Expected format:
            // PC <decimal>\n
            r = $fscanf(sf, "PC %d\n", pc);
            r = $fscanf(sf, "ACC %h\n", acc_val);
            r = $fscanf(sf, "CARRY %d\n", carry_val);

            // Read RAM line: 16 hex values
            for (i = 0; i < 16; i = i + 1) begin
                r = $fscanf(sf, "%h ", tmp_ram);
                u_cpu.u_ram.mem[i] = tmp_ram;
            end
            $fclose(sf);
        end

        // Restore accumulator and carry (reg_alu internals)
        u_cpu.u_alu.f = acc_val;
        u_cpu.u_alu.cout = carry_val;

        // Fetch instruction at PC
        instruction = prog_mem[pc];

        // If instruction undefined, nothing to do
        if (instruction === 11'bx) begin
            $display("[DONE]");
            $finish;
        end

        // Decode opcode string for logging
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

        $display("[EXEC] PC:%0d | Op:%s | Dest:%h | Src:%h", pc, op_str, `GET_OP1(instruction), `GET_OP2(instruction));

        // Run one instruction cycle
        run_cycle();

        // After execution, capture updated RAM and ALU
        acc_val = u_cpu.u_alu.f;
        carry_val = u_cpu.u_alu.cout;

        // Increment PC (simple linear flow)
        pc = pc + 1;

        // Dump RAM values and write cpu_state.hex back
        // Also print RAM update for GUI (single dest read already printed by run_cycle)
        sf = $fopen("cpu_state.hex", "w");
        if (sf) begin
            $fdisplay(sf, "PC %0d", pc);
            $fdisplay(sf, "ACC %h", acc_val);
            $fdisplay(sf, "CARRY %0d", carry_val);
            // Write RAM as 16 hex values on one line
            for (i = 0; i < 16; i = i + 1) begin
                $fwrite(sf, "%h ", u_cpu.u_ram.mem[i]);
            end
            $fdisplay(sf, "");
            $fclose(sf);
        end

        $display("[DONE]");
        $finish;
    end

    // Run cycle task reused from bridge_tb
    task run_cycle;
        reg [3:0] dest;
        reg [3:0] ram_val;
        begin
            dest = `GET_OP1(instruction);
            // Wait 2 cycles to get to Store state
            repeat(2) @(posedge clk);
            #1;
            @(posedge clk);
            #1;

            // Peek at RAM to see the result
            ram_val = u_cpu.u_ram.mem[dest];
            $display("[RAM] Addr:%h Val:%h", dest, ram_val);
            @(negedge clk);
        end
    endtask

endmodule
