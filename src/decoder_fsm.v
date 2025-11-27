`timescale 1ns/1ps
`include "cpu_defs.vh"

module decoder_fsm (
    // RAM Port 
    output reg [3:0] ram_data_in, // ram data input (to be written)
    output reg [3:0] ram_addr,    // ram addr port
    output reg csn,               // ram chip select enable = 0, disable = 1
    output reg rwn,               // ram read = 1, write = 0

    // ALU Port
    output reg [2:0] alu_sel,     // 3-bit alu select
    output reg       cin,         // alu carry-in
    output reg [3:0] a,           // alu a input (driven from a_reg)
    output reg [3:0] b,           // alu b input (driven from b_reg)

    // Data returned from RAM and ALU
    input  [3:0] ram_data_out,    // single-port RAM output
    input  [3:0] alu_out,         // registered ALU output (assumed valid when needed)

    input              clk,
    input              rst_n,    // active low async reset
    input  [`INSTR_W-1:0] instr
    // add RAM + ALU ports here as needed
);

// FSM state register
reg [1:0] state, next_state;

// Extract fields from instruction
wire [2:0] opcode = `GET_OPCODE(instr);
wire [3:0] op1    = `GET_OP1(instr);
wire [3:0] op2    = `GET_OP2(instr);

reg csn = 1'b1;

// -------------------------------
// State register update
// -------------------------------
always @(posedge clk or negedge rst_n) begin
    if (!rst_n)
        state <= `ST_INIT;
    else
        state <= next_state;
end

// -------------------------------
// Next-state sequencing
// -------------------------------
always @(*) begin
    case (state)
        `ST_INIT:  next_state = `ST_FETCH;
        `ST_FETCH: next_state = `ST_EXEC;
        `ST_EXEC:  next_state = `ST_STORE;
        `ST_STORE: next_state = `ST_FETCH; // loop back from exec back to fetch state
        default:   next_state = `ST_INIT;
    endcase
end

// -------------------------------
// Output/control placeholder
// -------------------------------
always @(*) begin
    case (state)

        // INIT: reset state
        // → Clear outputs, prepare for first instruction
        `ST_INIT: begin
            // TODO: drive RAM idle, ALU idle
            rst_n = 1'b0;

        end

        // FETCH: read operand from memory
        // → Use op1 as address, fetch data into ALU A
        `ST_FETCH: begin
            // TODO: set RAM to READ at addr=op1
            // TODO: latch fetched data into ALU input
        end

        // EXEC: perform operation
        // → Depending on opcode, configure ALU (ADD, SUB, AND, OR, XOR, NOT)
        // → For STO, bypass ALU and prepare op2 constant for writeback
        `ST_EXEC: begin
            // TODO: decode opcode
            // TODO: set ALU select, inputs, cin
            // TODO: for STO, prepare ram_datain = op2
        end

        // STORE: write result back to memory
        // → Use op1 as address, write ALU result (or op2 constant for STO)
        `ST_STORE: begin
            // TODO: set RAM to WRITE at addr=op1
            // TODO: ram_datain = alu_out (or op2 if STO)
        end

    endcase
end

endmodule
