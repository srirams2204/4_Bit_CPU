`timescale 1ns/1ps

module ram16x4(
    output reg [3:0] data_out,
    input [3:0] data_in,
    input [3:0] addr,
    input csn,
    input rwn,
    input clk, rst
); 

reg [3:0] mem [15:0];

integer i;
always @(posedge clk) begin
    //Synchronous Reset of RAM Memory
    if (rst) begin
        for (i=0; i<16; i=i+1) begin
            mem[i] <= 4'b0000;
            data_out <= 4'b0000;
        end
    end

    else if (!csn) begin 
        if (!rwn) begin
            // WRITE operation
            mem[addr] <= data_in;
            data_out  <= data_in;   // write-through
        end

        else begin
            // READ operation
            data_out <= mem[addr];
        end
    end

end

endmodule