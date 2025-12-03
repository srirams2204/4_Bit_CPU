`timescale 1ns/1ps

module xor_gate (
    output wire c,
    input  wire a,
    input  wire b
);
    assign c = (a & ~b) | (~a & b);
endmodule