// ---------- FSM State Transition Logic ----------
// INIT    → FETCH (on reset release)
// FETCH   → EXEC
// EXEC    → STORE
// STORE   → FETCH (loop continues)

`timescale 1ns/1ps
`include "cpu_defs.vh"

module decoder_fsm (
    //RAM Port 
    output [3:0] ram_data_in, //ram data input port
    output [3:0] ram_addr,    //ram addr port
    output [1:0] ram_crtl,    // ram chip select and read/write control signal

    //ALU Port
    output [3:0] alu_sel,     //alu control signal
    output [3:0] a,           //alu a input
    output [3:0] b,           //alu b input
    output cin,               //alu carry-in signal

    //11-bit Intruction from Testbench
    input [3:0] opcode,       //instruction opcode
    input [3:0] op1,          //destination value
    input [3:0] op2,          //source value

    input [3:0] ram_data_out, //ram data_out read by decoder_fsm
    input [3:0] alu_addr,     //collect alu_out signal as addr value 

    input clk, rst            //clock and reset signal for all modules
);

reg [1:0] state, next_state;

always @(posedge clk or posedge rst) begin
    if (rst)
        state <= `ST_INIT;
    else
        state <= next_state;
end

always @(*) begin
    case (state)
        `ST_INIT:   next_state = `ST_FETCH;
        `ST_FETCH:  next_state = `ST_EXEC;
        `ST_EXEC:   next_state = `ST_STORE;
        `ST_STORE:  next_state = `ST_FETCH;
        default:    next_state = `ST_INIT; // fallback
    endcase
end

always @(*) begin
    case (state)
        `ST_INIT: begin
            // Initialization logic here
            rst = 0;
        end

        `ST_FETCH: begin
            // Fetch instruction from RAM
            
        end

        `ST_EXEC: begin
            // Decode and execute instruction
        end

        `ST_STORE: begin
            // Write result back to RAM
        end
    endcase
end

endmodule