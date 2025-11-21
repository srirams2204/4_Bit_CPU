`timescale 1ns/1ps

module xor_gate (
    input  wire a,
    input  wire b,
    output wire c
);
    assign c = (a & ~b) | (~a & b);
endmodule
