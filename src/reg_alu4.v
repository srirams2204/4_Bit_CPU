`timescale 1ns/1ps
`include "cpu_defs.vh"

module reg_alu (
    output reg  [3:0] f,
    output reg        cout,
    input  wire       clk,
    input  wire       reset_n,
    input  wire       alu_en,   // Clock Enable
    input  wire [3:0] alu_sel,
    input  wire [3:0] a,
    input  wire [3:0] b
);
    // 1. Decode & Arith Setup
    wire s2=alu_sel[3], s1=alu_sel[2], s0=alu_sel[1], cin_in=alu_sel[0];
    reg [3:0] adder_b;

    always @(*) begin
        case ({s1, s0})
            2'b00: adder_b = 4'b0000;
            2'b01: adder_b = b;
            2'b10: adder_b = ~b;
            2'b11: adder_b = 4'b1111;
        endcase
    end

    // 2. Calculation Units
    wire [3:0] sum_out;
    wire       cout_arith;
    full_adder4 u_adder (.sum(sum_out), .cout(cout_arith), .a(a), .b(adder_b), .cin(cin_in));

    reg [3:0] logic_res;
    wire [3:0] xor_res;
    xor_gate u_xor0 (.c(xor_res[0]), .a(a[0]), .b(b[0]));
    xor_gate u_xor1 (.c(xor_res[1]), .a(a[1]), .b(b[1]));
    xor_gate u_xor2 (.c(xor_res[2]), .a(a[2]), .b(b[2]));
    xor_gate u_xor3 (.c(xor_res[3]), .a(a[3]), .b(b[3]));

    always @(*) begin
        casez (alu_sel)
            `ALU_OR_MASK:  logic_res = a | b;
            `ALU_AND_MASK: logic_res = a & b;
            `ALU_XOR_MASK: logic_res = xor_res;
            `ALU_NOT_MASK: logic_res = ~a;
            default:       logic_res = 4'b0000;
        endcase
    end

    // 3. Output Logic
    wire [3:0] next_f    = (s2 == 1'b0) ? sum_out : logic_res;
    wire       next_cout = (s2 == 1'b0) ? cout_arith : 1'b0;

    // 4. Sequential Update with Enable
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            f    <= 4'b0000;
            cout <= 1'b0;
        end else if (alu_en) begin
            f    <= next_f;
            cout <= next_cout;
        end
    end
endmodule