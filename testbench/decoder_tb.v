`timescale 1ns/1ps
`include "cpu_defs.vh"

module decoder_fsm_tb;

    // Clock & Reset
    reg clk = 0;
    reg rst_n = 0;

    // DUT inputs
    reg [`INSTR_W-1:0] instr;   // 11-bit instruction
    reg [3:0] ram_dataout;      // external feed from RAM
    reg [3:0] alu_out;          // external feed from ALU

    // DUT outputs
    wire [3:0] ram_addr;
    wire [3:0] ram_datain;
    wire       ram_csn;
    wire       ram_rwn;

    wire [2:0] alu_sel;
    wire       alu_cin;
    wire [3:0] alu_a;
    wire [3:0] alu_b;

    // Instantiate DUT
    decoder_fsm dut (
        .clk(clk),
        .rst_n(rst_n),
        .instr(instr),

        .ram_addr(ram_addr),
        .ram_datain(ram_datain),
        .ram_dataout(ram_dataout),
        .ram_csn(ram_csn),
        .ram_rwn(ram_rwn),

        .alu_a(alu_a),
        .alu_b(alu_b),
        .alu_cin(alu_cin),
        .alu_sel(alu_sel),
        .alu_out(alu_out),
        .alu_cout() // not probed here
    );

    // Clock generation (10ns period)
    always #5 clk = ~clk;

    // ------------------------------------------------------------
    // Monitor task: print FSM state & signals
    // ------------------------------------------------------------
    task show_signals;
        input [39:0] phase;
    begin
        $display("%s | ST=%b | RAM[addr=%h din=%h csn=%b rwn=%b dout=%h] | ALU[sel=%b cin=%b A=%h B=%h out=%h]",
            phase,
            dut.state,
            ram_addr, ram_datain, ram_csn, ram_rwn, ram_dataout,
            alu_sel, alu_cin, alu_a, alu_b, alu_out
        );
    end
    endtask

    // ------------------------------------------------------------
    // Apply instruction (runs through FSM cycle)
    // ------------------------------------------------------------
    task run_instr;
        input [2:0] opcode;
        input [3:0] op1;
        input [3:0] op2;
        input [3:0] dest_val;
        input [3:0] alu_result;
    begin
        instr = {opcode, op1, op2};

        $display("\n======================================");
        $display(" INSTR OPC=%b  OP1=%h  OP2=%h", opcode, op1, op2);
        $display("======================================");

        // FETCH
        ram_dataout = dest_val;
        @(posedge clk); #1; show_signals("FETCH");

        // EXEC
        alu_out = alu_result;
        @(posedge clk); #1; show_signals("EXEC ");

        // STORE
        @(posedge clk); #1; show_signals("STORE");
    end
    endtask

    // ------------------------------------------------------------
    // MAIN SIM
    // ------------------------------------------------------------
    initial begin
        $dumpfile("waveform/decoder_fsm_tb.vcd");
        $dumpvars(0, decoder_fsm_tb);

        // Reset sequence
        repeat (2) @(posedge clk);
        rst_n = 1;

        // Run sample instructions
        run_instr(`OPC_STO, 4'h3, 4'h9, 4'h0, 4'h9);  // STO mem[3]=9
        run_instr(`OPC_ADD, 4'h4, 4'h2, 4'hA, 4'hC);  // ADD
        run_instr(`OPC_SUB, 4'h5, 4'h1, 4'h9, 4'h8);  // SUB
        run_instr(`OPC_AND, 4'h6, 4'h7, 4'hF, 4'h7);  // AND
        run_instr(`OPC_OR , 4'h8, 4'h9, 4'h2, 4'hB);  // OR
        run_instr(`OPC_XOR, 4'hA, 4'hB, 4'h9, 4'h2);  // XOR
        run_instr(`OPC_NOT, 4'hC, 4'h0, 4'h3, 4'hC);  // NOT

        $display("\n======= FSM TEST COMPLETE =======\n");
        $finish;
    end

endmodule
