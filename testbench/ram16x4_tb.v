`timescale 1ns/1ps

module ram16x4_tb;

// ===============================================================
// 1. SIGNALS
// ===============================================================
reg        clk;
reg        rst_n;
reg        csn;      // Chip Select (Active Low)
reg        rwn;      // Read(1) / Write(0)
reg  [3:0] addr;
reg  [3:0] data_in;

wire [3:0] data_out;

// Loop variable
integer i;
integer errors;

// Temporary variable to hold the expected 4-bit result
reg [3:0] expected_val;

// ===============================================================
// 2. DUT INSTANTIATION (Outputs First)
// ===============================================================
ram16x4 u_dut (
    .data_out (data_out),
    .data_in  (data_in),
    .addr     (addr),
    .csn      (csn),
    .rwn      (rwn),
    .clk      (clk),
    .rst_n    (rst_n)
);

// ===============================================================
// 3. CLOCK GENERATION
// ===============================================================
initial begin
    clk = 0;
    forever #5 clk = ~clk; // 10ns Period
end

// ===============================================================
// 4. TEST SEQUENCE
// ===============================================================
initial begin
    $dumpfile("waveform/ram_tb.vcd");
    $dumpvars(0, ram16x4_tb);
    // Initialize
    rst_n   = 0;
    csn     = 1; // Deselected
    rwn     = 1; // Read
    addr    = 0;
    data_in = 0;
    errors  = 0;

    // Print Header
    $display("\n=========================================================================================");
    $display("                                   RAM 16x4 TESTBENCH                                    ");
    $display("=========================================================================================");
    $display("| Time | Operation | CS | RW | Addr | Data In | Data Out | Exp Out | Status |");
    $display("|------|-----------|----|----|------|---------|----------|---------|--------|");

    // Apply Reset
    repeat (2) @(posedge clk);
    rst_n = 1;

    // =================================================
    // PHASE 1: WRITE SWEEP
    // Write pattern (Addr + 1) to every location
    // =================================================
    $display("| ---- | WRITE ALL | -- | -- | ---- | ------- | -------- | ------- | ------ |");
    
    for (i = 0; i < 16; i = i + 1) begin
        // Setup Inputs
        @(posedge clk);
        csn     = 0;          // Select RAM
        rwn     = 0;          // Write Mode
        addr    = i[3:0];
        data_in = i[3:0] + 1; // 4-bit roll-over happens naturally here
        
        // Wait for write to happen
        #1; 
        
        $display("| %4t | Write Mem |  0 |  0 |  %1h   |    %1h    |    %1h     |    -    |   -    |", 
                    $time, addr, data_in, data_out);
    end

    // Idle cycle
    @(posedge clk);
    csn = 1;
    rwn = 1;

    // =================================================
    // PHASE 2: READ SWEEP & VERIFY
    // Read back and check if Data == Addr + 1
    // =================================================
    $display("| ---- | READ ALL  | -- | -- | ---- | ------- | -------- | ------- | ------ |");

    for (i = 0; i < 16; i = i + 1) begin
        // Setup Inputs
        @(posedge clk);
        csn     = 0;       // Select RAM
        rwn     = 1;       // Read Mode
        addr    = i[3:0];
        data_in = 4'h0;    
        
        // Calculate Expected Value (Masked to 4 bits to handle overflow!)
        // 15 + 1 = 16 (0x10) -> Masked with 0xF = 0x0
        expected_val = (i[3:0] + 1) & 4'hF;

        // Wait for read access time
        #1; 
        
        // Check Result
        if (data_out !== expected_val) begin
            $display("| %4t | Read Mem  |  0 |  1 |  %1h   |    -    |    %1h     |    %1h    |  FAIL  |", 
                        $time, addr, data_out, expected_val);
            errors = errors + 1;
        end else begin
            $display("| %4t | Read Mem  |  0 |  1 |  %1h   |    -    |    %1h     |    %1h    |  PASS  |", 
                        $time, addr, data_out, expected_val);
        end
    end

    // =================================================
    // PHASE 3: CHIP SELECT TEST
    // =================================================
    @(posedge clk);
    csn  = 1; // Deselect
    rwn  = 1; // Read
    addr = 4'h5; 
    #1;
    
    if (data_out !== 4'b0000) begin
            $display("| %4t | CS High   |  1 |  1 |  %1h   |    -    |    %1h     |    0    |  FAIL  |", 
                    $time, addr, data_out);
            errors = errors + 1;
    end else begin
            $display("| %4t | CS High   |  1 |  1 |  %1h   |    -    |    %1h     |    0    |  PASS  |", 
                    $time, addr, data_out);
    end


    // =================================================
    // SUMMARY
    // =================================================
    $display("=========================================================================================");
    if (errors == 0)
        $display("TEST PASSED: All 16 addresses verified.");
    else
        $display("TEST FAILED: %0d errors found.", errors);
    $display("=========================================================================================\n");
    
    $finish;
end

endmodule