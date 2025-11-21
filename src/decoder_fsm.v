`timescale 1ns/1ps

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

    input [3:0] opcode,       //instruction opcode
    input [3:0] op1,          //destination value
    input [3:0] op2,          //source value

    input [3:0] ram_data_out, //ram data_out read by decoder_fsm
    input [3:0] alu_addr,     //collect alu_out signal as addr value 

    input clk, rst            //clock and reset signal for all modules
);

endmodule