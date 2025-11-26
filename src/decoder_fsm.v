`timescale 1ns/1ps
`include "cpu_defs.vh"

module decoder_fsm (
    // RAM Port 
    output reg [3:0] ram_data_in, // ram data input (to be written)
    output reg [3:0] ram_addr,    // ram addr port
    output reg [1:0] ram_crtl,    // {csn, rwn}

    // ALU Port
    output reg [2:0] alu_sel,     // 3-bit alu select
    output reg       cin,         // alu carry-in
    output reg [3:0] a,           // alu a input (driven from a_reg)
    output reg [3:0] b,           // alu b input (driven from b_reg)

    // Instruction fields (sampled from instruction ROM / TB)
    input  [2:0] opcode,          // 3-bit opcode (use cpu_defs OPC_ macros)
    input  [3:0] op1,             // destination (address)
    input  [3:0] op2,             // source (address) or immediate (for STO)

    // Data returned from RAM and ALU
    input  [3:0] ram_data_out,    // single-port RAM output
    input  [3:0] alu_out,         // registered ALU output (assumed valid when needed)

    input  clk,
    input  rst
);

// FSM states (2-bit)
reg [1:0] state, next_state;

// Internal registers to hold operands / result
reg [3:0] a_reg;       // dest value (from mem[op1])
reg [3:0] b_reg;       // source value (from mem[op2])
reg [3:0] result_reg;  // ALU result or immediate for STO

// Keep sampled instruction across cycles
reg [2:0] opcode_reg;
reg [3:0] op1_reg;
reg [3:0] op2_reg;

// internal exec step (0 = start read source, 1 = compute)
reg exec_step;

// ------------------------------------------------------------------
// State register (synchronous)
// ------------------------------------------------------------------
always @(posedge clk or posedge rst) begin
    if (rst) begin
        state <= `ST_INIT;
    end else begin
        state <= next_state;
    end
end

// ------------------------------------------------------------------
// Next-state logic (pure combinational)
// ------------------------------------------------------------------
always @(*) begin
    case (state)
        `ST_INIT:  next_state = `ST_FETCH;
        `ST_FETCH: next_state = `ST_EXEC;
        `ST_EXEC:  begin
            // if exec requires two sub-steps, stay in EXEC until exec_step says done
            if (exec_step == 1'b0)
                next_state = `ST_EXEC; // stay to perform second exec cycle
            else
                next_state = `ST_STORE;
        end
        `ST_STORE: next_state = `ST_FETCH;
        default:   next_state = `ST_INIT;
    endcase
end

// ------------------------------------------------------------------
// Synchronous sampling of instruction and simple counters
// - sample instruction at start of FETCH so it remains stable
// - sample RAM data when expected (after read)
// ------------------------------------------------------------------
always @(posedge clk or posedge rst) begin
    if (rst) begin
        // init internal regs
        opcode_reg <= 3'b000;
        op1_reg    <= 4'b0000;
        op2_reg    <= 4'b0000;
        a_reg      <= 4'b0000;
        b_reg      <= 4'b0000;
        result_reg <= 4'b0000;
        exec_step  <= 1'b0;
    end else begin
        case (state)
            `ST_INIT: begin
                // clear regs (already handled above)
                exec_step <= 1'b0;
            end

            `ST_FETCH: begin
                // Sample instruction fields (stable before FETCH edge)
                opcode_reg <= opcode;
                op1_reg    <= op1;
                op2_reg    <= op2;

                // We requested a read of mem[op1] in combinational outputs
                // The RAM is synchronous so ram_data_out becomes valid now (in this same cycle
                // after posedge depending on your RAM timing). Sample it into a_reg.
                a_reg <= ram_data_out;

                // Prepare for EXEC: first exec sub-step is 0 (read source)
                exec_step <= 1'b0;
            end

            `ST_EXEC: begin
                if (exec_step == 1'b0) begin
                    // We previously requested read of mem[op2] (driven in comb outputs).
                    // Now sample ram_data_out into b_reg.
                    b_reg <= ram_data_out;

                    // move to next exec step so we compute result in next cycle
                    exec_step <= 1'b1;
                end else begin
                    // exec_step == 1: compute result using ALU output or immediate
                    // For STO we don't need ALU; store immediate op2.
                    if (opcode_reg == `OPC_STO) begin
                        result_reg <= op2_reg; // immediate store
                    end else begin
                        // For other operations ALU should have been driven to compute result
                        // and registered; we sample registered ALU output (alu_out).
                        result_reg <= alu_out;
                    end
                    // exec_step remains 1 until next fetch/store transition
                end
            end

            `ST_STORE: begin
                // After asserting write, sampling of the RAM (if needed) not required.
                // increment PC or let external ROM update instruction lines.
                // clear exec_step so next instruction begins fresh
                exec_step <= 1'b0;
            end

            default: begin
                // nothing
            end
        endcase
    end
end

// ------------------------------------------------------------------
// Combinational outputs: ram controls, ram_addr, ram_data_in, ALU inputs
// This block decides what to drive to RAM and ALU depending on state
// ------------------------------------------------------------------
always @(*) begin
    // Default outputs (RAM idle, ALU neutral)
    ram_addr     = 4'b0000;
    ram_data_in  = 4'b0000;
    ram_crtl     = {1'b1, 1'b1}; // csn=1 (idle), rwn=1 (read) by default (RAM idle)
    alu_sel      = 3'b000;
    cin          = 1'b0;
    a            = 4'b0000;
    b            = 4'b0000;

    case (state)
        `ST_INIT: begin
            // Hold RAM idle and ALU neutral
            ram_crtl = {1'b1, 1'b1};
        end

        `ST_FETCH: begin
            // Read destination (mem[op1]) so that a_reg gets the destination value next clock
            ram_addr    = op1;           // address to read
            ram_crtl    = {1'b0, 1'b1};  // csn=0 active, rwn=1 -> READ
            // ALU idle in fetch
            alu_sel     = 3'b000;
            cin         = 1'b0;
        end

        `ST_EXEC: begin
            // EXEC has two sub-steps controlled by exec_step (sampled/updated in sequential always)
            if (exec_step == 1'b0) begin
                // First EXEC cycle: request read of source mem[op2]
                ram_addr    = op2_reg;
                ram_crtl    = {1'b0, 1'b1};  // READ mem[op2]
                // drive ALU with current a_reg & placeholder b (will be valid next cycle)
                alu_sel     = 3'b000; // idle
                cin         = 1'b0;
                a           = a_reg;
                b           = 4'b0000;
                ram_data_in = 4'b0000;
            end else begin
                // Second EXEC cycle: b_reg is available (sampled), now set ALU control
                ram_crtl    = {1'b1, 1'b1};  // RAM idle
                a           = a_reg;
                b           = b_reg;

                // Select ALU function based on opcode_reg
                case (opcode_reg)
                    `OPC_ADD: begin
                        alu_sel = 3'b001; // ADD (ALU_ADD_AB)
                        cin     = 1'b0;
                    end
                    `OPC_SUB: begin
                        alu_sel = 3'b010; // SUB (ALU_SUB_A_B)
                        cin     = 1'b0;
                    end
                    `OPC_AND: begin
                        alu_sel = 3'b011;
                        cin     = 1'b0;
                    end
                    `OPC_OR: begin
                        alu_sel = 3'b100;
                        cin     = 1'b0;
                    end
                    `OPC_XOR: begin
                        alu_sel = 3'b101;
                        cin     = 1'b0;
                    end
                    `OPC_NOT: begin
                        alu_sel = 3'b111;
                        cin     = 1'b0;
                    end
                    `OPC_STO: begin
                        // For STO, ALU not needed; result_reg will be immediate op2 (sampled earlier)
                        alu_sel = 3'b000;
                        cin     = 1'b0;
                    end
                    default: begin
                        alu_sel = 3'b000;
                        cin     = 1'b0;
                    end
                endcase
            end
        end

        `ST_STORE: begin
            // Write result_reg back into mem[op1]
            ram_addr    = op1_reg;
            ram_data_in = result_reg;
            ram_crtl    = {1'b0, 1'b0}; // csn=0 active, rwn=0 -> WRITE
            // ALU idle
            alu_sel = 3'b000;
            cin     = 1'b0;
            a       = a_reg;
            b       = b_reg;
        end

        default: begin
            // defaults already set
        end
    endcase
end

endmodule
