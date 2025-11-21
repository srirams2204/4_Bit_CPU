# ============================================================
# Cross-Platform Makefile (Linux + Windows)
# ============================================================

# Directories
SRC_DIR := src
TB_DIR := testbench
SIM_DIR := sim
WAVE_DIR := waveform

# Detect OS
ifeq ($(OS),Windows_NT)
    # Windows commands
    RM := del /Q
    RMDIR := rmdir /S /Q
    SEP := \\
    EXE := .exe
    SHELL := cmd
else
    # Linux/Mac commands
    RM := rm -f
    RMDIR := rm -rf
    SEP := /
    EXE :=
endif

# Tools
IVERILOG := iverilog$(EXE) -I src
VVP := vvp$(EXE)
GTKWAVE := gtkwave$(EXE)

# Pass filenames (without .v) from terminal
# Example: make run SRC=adder TB=tb_adder
SRC ?= my_design
TB ?= tb_my_design

# File paths
SRC_FILE := $(SRC_DIR)$(SEP)$(SRC).v
TB_FILE := $(TB_DIR)$(SEP)$(TB).v
VVP_FILE := $(SIM_DIR)$(SEP)$(SRC).vvp
VCD_FILE := $(WAVE_DIR)$(SEP)$(SRC).vcd

# Default target
all: run

# ============================================================
# UPDATED: Compile all Verilog files in src/
# ============================================================
$(VVP_FILE): $(TB_FILE)
	$(IVERILOG) -o $(VVP_FILE) $(wildcard $(SRC_DIR)/*.v) $(TB_FILE)

# Run simulation
run: $(VVP_FILE)
	$(VVP) $(VVP_FILE)

# Open waveform in GTKWave (if available)
wave: $(VCD_FILE)
	$(GTKWAVE) $(VCD_FILE)

# Clean generated files
clean:
ifeq ($(OS),Windows_NT)
	-$(RM) "$(SIM_DIR)\\*.vvp"
	-$(RM) "$(WAVE_DIR)\\*.vcd"
else
	-$(RM) $(SIM_DIR)/*.vvp
	-$(RM) $(WAVE_DIR)/*.vcd
endif

.PHONY: all run wave clean
