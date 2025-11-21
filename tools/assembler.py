# ============================================================
# 4-bit CPU Assembler
# ------------------------------------------------------------
# Converts custom assembly syntax into 11-bit machine code.
# Works in both CLI (python3 assembler.py program.asm)
# and GUI mode (import assemble_text / assemble_file).
#
# Instruction Format: [10:8]=opcode, [7:4]=op1, [3:0]=op2
# ------------------------------------------------------------
# Example Assembly:
#   STO 0x4 0x5
#   ADD 0x4 0x6
#   STO 0x1 0xF
#   SUB 0x1 0x7
#   NOT 0xF
# ============================================================

import re
import sys
import os

# ------------------------------------------------------------
# OPCODE MAP (instruction set)
# ------------------------------------------------------------
OPC = {
    "STO": 0b000,
    "ADD": 0b001,
    "SUB": 0b010,
    "AND": 0b011,
    "OR" : 0b100,
    "XOR": 0b101,
    "NOT": 0b110,
}

# ------------------------------------------------------------
# Helper: Parse immediate or operand value (STRICT 4-bit)
# ------------------------------------------------------------
def parse_imm(tok: str) -> int:
    tok = tok.strip().lower()

    # Detect number format
    if tok.startswith("0x"):
        val = int(tok, 16)
    elif tok.startswith("0b"):
        val = int(tok, 2)
    else:
        val = int(tok, 10)

    # Enforce strict 4-bit range (0–15)
    if val < 0 or val > 0xF:
        raise ValueError(f"Immediate value out of 4-bit range (0–F): {tok}")

    return val

# ------------------------------------------------------------
# Assemble a single line into a 11-bit binary word
# ------------------------------------------------------------
def assemble_line(line: str):
    # Remove comments (";" or "//")
    line = re.split(r";|//", line, 1)[0].strip()
    if not line:
        return None  # skip blank/comment-only lines

    parts = re.split(r"[,\s]+", line.strip())
    mnem = parts[0].upper()

    if mnem not in OPC:
        raise ValueError(f"Unknown instruction: '{mnem}'")

    # Instruction format validation
    if mnem == "NOT":
        if len(parts) != 2:
            raise ValueError(f"Invalid syntax for NOT — expected: NOT <op1>")
        op1 = parse_imm(parts[1])
        op2 = 0
    else:
        if len(parts) != 3:
            raise ValueError(f"Invalid syntax for {mnem} — expected: {mnem} <op1> <op2>")
        op1 = parse_imm(parts[1])
        op2 = parse_imm(parts[2])

    opc = OPC[mnem] & 0x7
    word = (opc << 8) | (op1 << 4) | op2   # pack 11-bit instruction
    return word

# ------------------------------------------------------------
# Assemble multi-line assembly text (used in GUI)
# ------------------------------------------------------------
def assemble_text(text: str):
    words, hex_lines = [], []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        try:
            w = assemble_line(raw)
        except Exception as e:
            raise ValueError(f"Line {lineno}: {e}")
        if w is None:
            continue
        words.append(w)
        hex_lines.append(f"{w:03x}")  # 11 bits → up to 0x7FF (3 hex chars)
    return words, hex_lines

# ------------------------------------------------------------
# Assemble directly from a file (for CLI or GUI)
# ------------------------------------------------------------
def assemble_file(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Assembly file not found: {path}")
    with open(path, "r") as f:
        text = f.read()
    return assemble_text(text)

# ------------------------------------------------------------
# Write .hex file (for $readmemh in Verilog)
# ------------------------------------------------------------
def write_memhex(hex_lines, path="program.hex"):
    with open(path, "w") as f:
        for h in hex_lines:
            f.write(h + "\n")

# ------------------------------------------------------------
# CLI Main entry
# ------------------------------------------------------------
def main():
    if len(sys.argv) > 1:
        asm_path = sys.argv[1]
        try:
            words, hex_lines = assemble_file(asm_path)
        except Exception as e:
            print(f"\n❌ Assembly failed: {e}")
            sys.exit(1)

        out_path = os.path.splitext(asm_path)[0] + ".hex"
        write_memhex(hex_lines, out_path)

        print(f"\n✅ Assembled '{asm_path}' → '{out_path}'")
        print("----------------------------------------------------")
        print("ADDR |   HEX   |   BINARY (11-bit)")
        print("----------------------------------------------------")
        for i, (w, h) in enumerate(zip(words, hex_lines)):
            print(f" {i:02d}   |   {h.upper():>3}   |   {w:011b}")
        print("----------------------------------------------------")
        print("✅ Assembly complete!\n")
        sys.exit(0)

    # Demo mode (no args)
    print("Demo Mode: assembling built-in sample...\n")
    demo = """
    STO 0x4 0x5
    ADD 0x4 0x6
    STO 0x1 0xF
    SUB 0x1 0x7
    NOT 0xF
    """
    words, hex_lines = assemble_text(demo)
    write_memhex(hex_lines, "program.hex")
    for w, h in zip(words, hex_lines):
        print(f"{h.upper():>3}   ({w:011b})")
    print("\n✅ 'program.hex' written.\n")

# ------------------------------------------------------------
# Exported symbols for GUI
# ------------------------------------------------------------
__all__ = [
    "assemble_text",
    "assemble_file",
    "write_memhex",
    "OPC",
]

# ------------------------------------------------------------
# Entry point
# ------------------------------------------------------------
if __name__ == "__main__":
    main()
