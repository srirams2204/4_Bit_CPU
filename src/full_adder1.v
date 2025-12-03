`timescale 1ns/1ps

module full_adder1 (
    output wire sum,
    output wire cout,
    input  wire a,
    input  wire b,
    input  wire cin
);
    wire s_ab;      // a ^ b
    wire c1, c2;    // carry terms

    xor_gate u_xor_ab  (.c(s_ab), .a(a),    .b(b));
    xor_gate u_xor_sum (.c(sum),  .a(s_ab), .b(cin));

    assign c1  = a & b;
    assign c2  = cin & s_ab;
    assign cout = c1 | c2;
endmodule