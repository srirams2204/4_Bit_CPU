`timescale 1ns/1ps
`include "cpu_defs.vh"

module cpu_top (
    output wire [3:0]  debug_alu_res,
    output wire [3:0]  debug_ram_out,
    output wire        debug_cout,
    input  wire        clk,
    input  wire        reset_n,
    input  wire [10:0] instruction
);

    wire       ram_csn;
    wire       ram_rwn;
    wire [3:0] ram_addr;
    wire [3:0] ram_wdata;
    wire [3:0] ram_rdata;

    wire       alu_en;   // <--- Internal Wire
    wire [3:0] alu_sel;
    wire [3:0] alu_a;
    wire [3:0] alu_b;
    wire [3:0] alu_f;
    wire       alu_cout;

    instruction_decoder u_decoder (
        .ram_csn      (ram_csn),
        .ram_rwn      (ram_rwn),
        .ram_addr     (ram_addr),
        .ram_data_in  (ram_wdata),
        .alu_en       (alu_en),       // <--- Connected
        .alu_sel      (alu_sel),
        .alu_a        (alu_a),
        .alu_b        (alu_b),
        .clk          (clk),
        .reset_n      (reset_n),
        .instruction  (instruction),
        .ram_data_out (ram_rdata),
        .alu_result   (alu_f)
    );

    reg_alu u_alu (
        .f       (alu_f),
        .cout    (alu_cout),
        .clk     (clk),
        .reset_n (reset_n),
        .alu_en  (alu_en),            // <--- Connected
        .alu_sel (alu_sel),
        .a       (alu_a),
        .b       (alu_b)
    );

    ram16x4 u_ram (
        .data_out (ram_rdata),
        .data_in  (ram_wdata),
        .addr     (ram_addr),
        .csn      (ram_csn),
        .rwn      (ram_rwn),
        .clk      (clk),
        .rst_n    (reset_n)
    );

    assign debug_alu_res = alu_f;
    assign debug_ram_out = ram_rdata;
    assign debug_cout    = alu_cout;

endmodule