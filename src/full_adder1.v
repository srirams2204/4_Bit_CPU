`timescale 1ns/1ps

module full_adder1 (
    input  wire a,
    input  wire b,
    input  wire cin,
    output wire sum,
    output wire cout
);
    wire s_ab;      // a ^ b
    wire c1, c2;    // carry terms

    //user xor gate instatiated    
    xor_gate u_xor_ab (.a(a),   .b(b),   .c(s_ab));
    xor_gate u_xor_sum(.a(s_ab),.b(cin), .c(sum));

    assign c1  = a & b;
    assign c2  = cin & s_ab;
    assign cout = c1 | c2;
endmodule
