`timescale 1ns/1ps

module ram16x4 (
    output reg  [3:0] data_out,
    input  wire [3:0] data_in,
    input  wire [3:0] addr,
    input  wire       csn,      // Chip Select (Active Low)
    input  wire       rwn,      // Read(1) / Write(0)
    input  wire       clk,
    input  wire       rst_n
);
    reg [3:0] mem [15:0];
    integer i;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i=0; i<16; i=i+1) mem[i] <= 4'b0000;
            data_out <= 4'b0000;
        end 
        else if (!csn) begin // Chip Selected
            if (!rwn) begin
                // WRITE: Update memory, force output to 0
                mem[addr] <= data_in;
                data_out  <= 4'b0000; 
            end else begin
                // READ: Output memory content
                data_out <= mem[addr];
            end
        end 
        else begin
            // Chip Deselected
            data_out <= 4'b0000;
        end
    end
endmodule