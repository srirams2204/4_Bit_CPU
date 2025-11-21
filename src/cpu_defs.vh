`ifndef CPU_DEFS_VH
`define CPU_DEFS_VH

// ===========================================================
// CPU GLOBAL CONSTANTS / OPCODES / ALU CODES / STATES
// ===========================================================

// ---------- Instruction Format ----------
`define INSTR_W   11
`define ADDR_W    4
`define DATA_W    4

// Extract fields
`define GET_OPCODE(x)   (x[10:8])
`define GET_OP1(x)      (x[7:4])
`define GET_OP2(x)      (x[3:0])

// ---------- OPCODES ----------
`define OPC_STO   3'b000
`define OPC_ADD   3'b001
`define OPC_SUB   3'b010
`define OPC_AND   3'b011
`define OPC_OR    3'b100
`define OPC_XOR   3'b101
`define OPC_NOT   3'b110
// (3'b111 reserved)

// ---------- FSM States ----------
`define ST_INIT    2'b00
`define ST_FETCH   2'b01
`define ST_EXEC    2'b10
`define ST_STORE   2'b11

// ---------- ALU Select Codes ----------
// We'll use 4-bit ALU select tokens = {alu_sel[2:0], cin}
// Use `casez` in logic so '-'/'?' positions act as don't cares.

// Arithmetic / Transfer (cin is meaningful)
`define ALU_TRANSFER     4'b0000
`define ALU_INC          4'b0001

`define ALU_ADD_AB       4'b0010
`define ALU_ADD_ABCIN    4'b0011

`define ALU_SUB_A_B      4'b0100
`define ALU_SUB_A_B_1    4'b0101

`define ALU_DEC          4'b0110
`define ALU_PASS_A       4'b0111

// Logical Ops (cin ignored -> use '?' in pattern macros with casez)
`define ALU_OR_MASK      4'b100?   // casez pattern: matches 1000 or 1001
`define ALU_XOR_MASK     4'b101?   // matches 1010 or 1011
`define ALU_AND_MASK     4'b110?   // matches 1100 or 1101
`define ALU_NOT_MASK     4'b111?   // matches 1110 or 1111

// ---------- RAM Control ----------
`define RAM_ACTIVE  1'b0
`define RAM_IDLE    1'b1
`define RAM_READ    1'b1
`define RAM_WRITE   1'b0

`endif
