`timescale 1ns/1ps
`include "cpu_defs.vh"

module reg_alu4 (
    output reg [3:0] alu_out,
    output reg       cout,

    input  [3:0] a,
    input  [3:0] b,
    input        cin,
    input  [2:0] alu_sel,

    input        clk,
    input        rst
);

    // --------------------------------------
    // Wires to the ripple-carry full adder
    // --------------------------------------
    reg  [3:0] fa_a, fa_b;
    reg        fa_cin;

    wire [3:0] fa_sum;
    wire       fa_cout;

    // Instantiate 4-bit ripple adder (combinational)
    full_adder4 u_fa4 (
        .a(fa_a),
        .b(fa_b),
        .cin(fa_cin),
        .sum(fa_sum),
        .cout(fa_cout)
    );

    // --------------------------------------
    // Combinational (next) signals
    // --------------------------------------
    reg [3:0] alu_out_next;
    reg       cout_next;

    // Combinational logic computes next values
    always @(*) begin
        // defaults
        fa_a        = a;
        fa_b        = b;
        fa_cin      = cin;

        alu_out_next = 4'b0000;
        cout_next    = 1'b0;

        // combine alu_sel (3 bits) + cin (1 bit) into 4 bits for pattern matching
        // use casez so '?' in masks match don't-care
        casez ({alu_sel, cin})
            // Arithmetic / transfer (cin meaningful)
            `ALU_TRANSFER: begin
                fa_a   = a;         fa_b   = 4'b0000; fa_cin = 1'b0;
                alu_out_next = fa_sum;
                cout_next    = fa_cout;
            end

            `ALU_INC: begin
                fa_a   = a;         fa_b   = 4'b0000; fa_cin = 1'b1;
                alu_out_next = fa_sum;
                cout_next    = fa_cout;
            end

            `ALU_ADD_AB: begin
                fa_a   = a;         fa_b   = b;       fa_cin = 1'b0;
                alu_out_next = fa_sum;
                cout_next    = fa_cout;
            end

            `ALU_ADD_ABCIN: begin
                fa_a   = a;         fa_b   = b;       fa_cin = 1'b1;
                alu_out_next = fa_sum;
                cout_next    = fa_cout;
            end

            `ALU_SUB_A_B: begin
                fa_a   = a;         fa_b   = ~b;      fa_cin = 1'b0; // a + (~b)
                alu_out_next = fa_sum;
                cout_next    = fa_cout;
            end

            `ALU_SUB_A_B_1: begin
                fa_a   = a;         fa_b   = ~b;      fa_cin = 1'b1; // a + (~b) + 1
                alu_out_next = fa_sum;
                cout_next    = fa_cout;
            end

            `ALU_DEC: begin
                fa_a   = a;         fa_b   = 4'b1111; fa_cin = 1'b1; // a + 1111 + 1 -> a - 1
                alu_out_next = fa_sum;
                cout_next    = fa_cout;
            end

            `ALU_PASS_A: begin
                // transfer a (via a + 1111 + 1 trick)
                fa_a   = a;         fa_b   = 4'b1111; fa_cin = 1'b1;
                alu_out_next = fa_sum;
                cout_next    = fa_cout;
            end

            // Logical ops (cin ignored — use casez mask '?')
            `ALU_OR_MASK: begin
                alu_out_next = a | b;
                cout_next    = 1'b0;
            end

            `ALU_XOR_MASK: begin
                alu_out_next = a ^ b;
                cout_next    = 1'b0;
            end

            `ALU_AND_MASK: begin
                alu_out_next = a & b;
                cout_next    = 1'b0;
            end

            `ALU_NOT_MASK: begin
                alu_out_next = ~a;
                cout_next    = 1'b0;
            end

            default: begin
                alu_out_next = 4'b0000;
                cout_next    = 1'b0;
            end
        endcase
    end

    // ------------------------------------------------
    // Synchronous register update & Asynchronous Reset
    // ------------------------------------------------
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            alu_out <= 4'b0000;
            cout    <= 1'b0;
        end else begin
            alu_out <= alu_out_next;
            cout    <= cout_next;
        end
    end

endmodule
