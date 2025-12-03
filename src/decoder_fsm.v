`timescale 1ns/1ps
`include "cpu_defs.vh"

module instruction_decoder (
    output reg        ram_csn, ram_rwn,
    output reg  [3:0] ram_addr, ram_data_in,
    output reg        alu_en,
    output reg  [3:0] alu_sel, alu_a, alu_b,
    input  wire       clk, reset_n,
    input  wire [10:0] instruction,
    input  wire [3:0] ram_data_out, alu_result
);

    wire [2:0] opcode = `GET_OPCODE(instruction);
    wire [3:0] op1    = `GET_OP1(instruction);
    wire [3:0] op2    = `GET_OP2(instruction);

    reg [1:0] current_state, next_state;

    always @(posedge clk or negedge reset_n)
        if (!reset_n) current_state <= `ST_INIT;
        else current_state <= next_state;

    always @(*) begin
        case (current_state)
            `ST_INIT:  next_state = `ST_FETCH;
            `ST_FETCH: next_state = `ST_EXEC;
            `ST_EXEC:  next_state = `ST_STORE;
            `ST_STORE: next_state = `ST_FETCH;
            default:   next_state = `ST_INIT;
        endcase
    end

    always @(*) begin
        // Defaults
        ram_csn = `RAM_IDLE; ram_rwn = `RAM_READ; ram_addr = 0; ram_data_in = 0;
        alu_en = 0; alu_sel = `ALU_TRANSFER; alu_a = 0; alu_b = 0;

        case (current_state)
            `ST_FETCH: begin
                ram_csn = `RAM_ACTIVE; ram_rwn = `RAM_READ; ram_addr = op1;
            end
            `ST_EXEC: begin
                ram_csn = `RAM_ACTIVE; ram_rwn = `RAM_READ; ram_addr = op1;
                alu_en = 1; // Enable ALU
                alu_b = op2;
                if (opcode == `OPC_STO) alu_a = 0; else alu_a = ram_data_out;
                
                case (opcode)
                    `OPC_STO: alu_sel = `ALU_ADD_AB;
                    `OPC_ADD: alu_sel = `ALU_ADD_AB;
                    `OPC_SUB: alu_sel = `ALU_SUB_A_B_1;
                    `OPC_AND: alu_sel = `ALU_AND_MASK;
                    `OPC_OR:  alu_sel = `ALU_OR_MASK;
                    `OPC_XOR: alu_sel = `ALU_XOR_MASK;
                    `OPC_NOT: alu_sel = `ALU_NOT_MASK;
                    default:  alu_sel = `ALU_TRANSFER;
                endcase
            end
            `ST_STORE: begin
                ram_csn = `RAM_ACTIVE; ram_rwn = `RAM_WRITE; ram_addr = op1; ram_data_in = alu_result;
                alu_en = 0; // Hold ALU
            end
        endcase
    end
endmodule