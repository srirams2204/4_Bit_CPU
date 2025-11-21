`timescale 1ns/1ps

module ram16x4_tb;

    reg  [3:0] data_in;
    reg  [3:0] addr;
    reg        csn;
    reg        rwn;
    reg        clk;
    reg        rst;
    wire [3:0] data_out;

    // DUT
    ram16x4 uut (
        .data_out(data_out),
        .data_in(data_in),
        .addr(addr),
        .csn(csn),
        .rwn(rwn),
        .clk(clk),
        .rst(rst)
    );

    // Clock
    always #5 clk = ~clk;

    // -----------------------------
    // WRITE TASK
    // -----------------------------
    task DO_WRITE(input [3:0] a, input [3:0] d);
    begin
        @(posedge clk);
        addr    = a;
        data_in = d;
        csn     = 0;
        rwn     = 0;
        @(posedge clk);
        $display("[WRITE] mem[%0d] <= %h | data_out=%h", a, d, data_out);
    end
    endtask

    // -----------------------------
    // READ TASK
    // -----------------------------
    task DO_READ(input [3:0] a);
    begin
        @(posedge clk);
        addr = a;
        csn  = 0;
        rwn  = 1;
        @(posedge clk);
        $display("[READ] mem[%0d] => %h", a, data_out);
    end
    endtask

    // -----------------------------
    // MAIN TEST
    // -----------------------------
    integer i;
    reg [3:0] rand_addr, rand_data;

    initial begin
        $dumpfile("waveform/ram_tb.vcd");
        $dumpvars(0, ram16x4_tb);

        clk = 0;
        rst = 1;
        csn = 1;
        rwn = 1;
        addr = 0;
        data_in = 0;

        // RESET
        $display("\n=== APPLY RESET ===");
        @(posedge clk);
        rst = 1;
        @(posedge clk);
        rst = 0;

        // BASIC WRITES
        $display("\n=== BASIC WRITE TESTS ===");
        DO_WRITE(4'd3,  4'hA);
        DO_WRITE(4'd7,  4'h5);
        DO_WRITE(4'd15, 4'hF);

        // BASIC READS
        $display("\n=== BASIC READ TESTS ===");
        DO_READ(4'd3);
        DO_READ(4'd7);
        DO_READ(4'd15);

        // FULL ADDRESS SWEEP WRITE
        $display("\n=== FULL WRITE (0–15) ===");
        for (i = 0; i < 16; i = i + 1)
            DO_WRITE(i[3:0], i[3:0]);

        // FULL ADDRESS SWEEP READ
        $display("\n=== FULL READ (0–15) ===");
        for (i = 0; i < 16; i = i + 1)
            DO_READ(i[3:0]);

        // RANDOMIZED TEST
        $display("\n=== RANDOMIZED READ/WRITE TEST ===");
        for (i = 0; i < 10; i = i + 1) begin
            rand_addr = $random % 16;
            rand_data = $random % 16;
            DO_WRITE(rand_addr, rand_data);
            DO_READ(rand_addr);
        end

        // CSN DISABLE TEST
        $display("\n=== CSN DISABLE TEST ===");
        @(posedge clk);
        addr = 4'd3;
        data_in = 4'h0;
        rwn = 0;
        csn = 1;  // disabled RAM
        @(posedge clk);

        DO_READ(4'd3); // should remain unchanged

        // BACK-TO-BACK WRITE STRESS
        $display("\n=== BACK-TO-BACK WRITE STRESS ===");
        csn = 0;
        rwn = 0;
        for (i = 0; i < 16; i = i + 1) begin
            @(posedge clk);
            addr    = i;
            data_in = ~i;
        end

        // verify
        $display("\n=== VERIFY AFTER STRESS ===");
        rwn = 1;
        for (i = 0; i < 16; i = i + 1)
            DO_READ(i);

        $display("\n=== TEST COMPLETE ===");
        #20 $finish;
    end

endmodule
