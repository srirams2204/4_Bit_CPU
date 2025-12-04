import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import os
import subprocess
from assembler import assemble_text, write_memhex, OPC

#GUI Window Title
root = tk.Tk()
title = root.title('4-Bit-CPU')

#Default GUI Window Dimension
window_width = 1200
window_height = 850

#GUI window size limits
root.minsize(window_width, window_height)
#root.maxsize(1000, 700)

#Startup GUI Window Position
window_size = root.geometry(f'{window_width}x{window_height}+257+33')
window_resize = root.resizable(True, True) #Can Resize GUI window in the X and Y axis

#GUI Transparency
root.attributes('-alpha', 0.94)

#GUI Icon File Path
icon_path = os.path.abspath("ic_chip.png") 

if os.path.exists(icon_path):
    try:
        # For .png files, use PhotoImage + iconphoto
        icon_img = tk.PhotoImage(file=icon_path)
        root.iconphoto(False, icon_img)
    except Exception as e:
        print(f"Icon error: {e}")
        # Fallback for .ico if you happen to use one later
        try:
             root.iconbitmap(icon_path)
        except:
             pass
else:
    print(f"Icon file not found at: {icon_path}")

def handle_ctrl_s(event):
    save_asm_file()
    return "break"   # prevents 's' being inserted

root.bind_class("Text", "<Control-s>", handle_ctrl_s)
root.bind_class("Text", "<Control-S>", handle_ctrl_s)
# Enable keyboard shortcuts
#root.bind('<Control-Key-s>', lambda event: save_asm_file())
#root.bind('<Command-Key-s>', lambda event: save_asm_file()) # Mac support

toolbar = tk.Frame(root, bg="#1E1E1E")
toolbar.pack(fill="x", side="top")

# -------------------------------------
# FILE STATE
# -------------------------------------
current_file = None

# -------------------------------------
# SIMULATION STATE
# -------------------------------------
execution_trace = []  # List of steps parsed from log
current_step = 0      # Index of the next step to execute
ram_injections = []    # Stores {address: value} for manual writes

# ============================================================
# SIMULATION ENGINE
# ============================================================

def run_verilog_process():
    """
    Directly runs iverilog/vvp using hardcoded paths.
    """
    sim_exe = "cpu_sim"
    log_file = "simulation.log"
    
    # 1. Define source files with correct relative paths from 'tools/'
    sources = [
        "../testbench/bridge_tb.v",                # Local testbench
        "../src/cpu_top.v",
        "../src/decoder_fsm.v",
        "../src/ram16x4.v",
        "../src/reg_alu4.v",
        "../src/full_adder4.v",
        "../src/full_adder1.v",
        "../src/xor_gate.v"
    ]

    try:
        # A. COMPILE
        cmd_compile = ["iverilog", "-o", sim_exe, "-I", "../src"] + sources
        subprocess.run(cmd_compile, check=True, capture_output=True)

        # B. RUN & LOG
        with open(log_file, "w") as outfile:
            subprocess.run(["vvp", sim_exe], stdout=outfile, check=True)
            
        return True

    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.decode() if e.stderr else str(e)
        messagebox.showerror("Simulation Error", f"Verilog failed:\n{err_msg}")
        console_write(f"[SIM ERROR] {err_msg}")
        return False
    except FileNotFoundError:
        messagebox.showerror("Config Error", "Icarus Verilog (iverilog) not found in PATH.")
        return False

def process_simulation_log():
    """Parses simulation.log into a structured trace for stepping"""
    global execution_trace, current_step
    
    log_file = "simulation.log"
    execution_trace = [] # Clear previous trace
    current_step = 0     # Reset step counter
    
    if not os.path.exists(log_file):
        return

    console_write("=== PARSING LOG ===")
    
    try:
        with open(log_file, "r") as f:
            for line in f:
                line = line.strip()
                
                # PARSE [EXEC] EVENTS
                # Format: [EXEC] PC:0 | Op:STO | Dest:7 | Src:2
                if line.startswith("[EXEC]"):
                    parts = line.split("|")
                    step = {
                        "type": "EXEC",
                        "pc":   parts[0].split(":")[1].strip(),
                        "op":   parts[1].split(":")[1].strip(),
                        "dest": parts[2].split(":")[1].strip(),
                        "src":  parts[3].split(":")[1].strip()
                    }
                    execution_trace.append(step)

                # PARSE [RAM] EVENTS
                # Format: [RAM] Addr:7 Val:2
                elif line.startswith("[RAM]"):
                    parts = line.split() 
                    step = {
                        "type": "RAM",
                        "addr": int(parts[1].split(":")[1], 16),
                        "val":  int(parts[2].split(":")[1], 16)
                    }
                    execution_trace.append(step)

                elif line.startswith("[DONE]"):
                    execution_trace.append({"type": "DONE"})
                    console_write(f"[INFO] Simulation trace loaded: {len(execution_trace)} steps.")

    except Exception as e:
        console_write(f"[LOG ERROR] Could not read log: {e}")

def save_injections_file():
    """Writes user RAM edits to injections.txt for the testbench to read"""
    try:
        with open("injections.txt", "w") as f:
            for step, addr, val in ram_injections:
                # Format: STEP_INDEX ADDRESS VALUE (in hex)
                f.write(f"{step} {addr:x} {val:x}\n")
    except Exception as e:
        console_write(f"[ERROR] Saving injections: {e}")

#-------------------------------------
# GUI Button Functions
#-------------------------------------

#Display Current File Name
def update_title():
    if current_file:
        filename = os.path.basename(current_file)
        root.title(f"4-Bit-CPU — {filename}")
    else:
        root.title("4-Bit-CPU — Untitled")

#New File Function
def new_file():
    global current_file
    current_file = None
    editor.delete("1.0", "end")
    console_write("[NEW] Blank file created.")
    update_title()

#Console Output Helper
def console_write(msg):
    console.config(state="normal")
    console.insert("end", msg + "\n")
    console.see("end")
    console.config(state="disabled")

#Open File Function
def open_asm_file():
    global current_file

    path = filedialog.askopenfilename(
        title="Open Assembly File",
        filetypes=[("Assembly Files", "*.asm"), ("All Files", "*.*")]
    )

    if not path:
        return

    try:
        with open(path, "r") as f:
            content = f.read()

        editor.delete("1.0", "end")
        editor.insert("1.0", content)

        apply_highlighting()

        current_file = path
        update_title()

        console_write(f"[OPEN] Loaded: {path}")

    except Exception as e:
        messagebox.showerror("File Error", f"Could not open file:\n{e}")

#Save File Function
def save_asm_file():
    global current_file

    if current_file is None:
        return save_asm_file_as()

    try:
        with open(current_file, "w") as f:
            f.write(editor.get("1.0", "end-1c"))

        messagebox.showinfo("Saved", f"File saved:\n{current_file}")
        console_write(f"[SAVE] Updated: {current_file}")

    except Exception as e:
        messagebox.showerror("Save Error", f"Could not save file:\n{e}")

#Save As File Function
def save_asm_file_as():
    global current_file

    path = filedialog.asksaveasfilename(
        defaultextension=".asm",
        filetypes=[("Assembly Files", "*.asm"), ("All Files", "*.*")]
    )

    if not path:
        return

    current_file = path
    save_asm_file()
    update_title()

def cmd_open_gtkwave():
    """Opens the simulation waveform in GTKWave"""
    vcd_file = "simulation.vcd"
    if not os.path.exists(vcd_file):
        messagebox.showerror("Error", "No waveform found. Run the simulation first.")
        return
    
    try:
        # Opens GTKWave as a separate process
        subprocess.Popen(["gtkwave", vcd_file])
        console_write("[TOOL] GTKWave opened.")
    except FileNotFoundError:
        messagebox.showerror("Error", "GTKWave not found in PATH.\nPlease install gtkwave.")

#Clear RAM Table Button Function
def cmd_clear_ram():
    global ram_overrides
    ram_overrides = {} # Clear overrides
    for lbl in ram_cells:
        lbl.config(text="0", fg="#FFFFFF") 
    console_write("[CMD] RAM Table cleared.")

#Run button function
def cmd_run():
    """Run Button Logic: Compile -> Run -> Parse -> Replay All"""
    global current_step, ram_injections  # <--- NEW: Access global step counter

    ram_injections = [] 
    if os.path.exists("injections.txt"):
        os.remove("injections.txt")
    
    code = editor.get("1.0", "end-1c")
    try:
        # 1. Compile Assembly
        words, hex_lines, errors = assemble_text(code)
        if errors:
            console_write("[ABORT] Fix assembly errors first.")
            for e in errors: console_write(f"[ASM ERROR] {e}")
            messagebox.showerror("Error", "Fix assembly errors first.")
            return
        
        write_memhex(hex_lines, "program.hex")
        console_write("[1/3] Assembly Compiled.")

        # 2. Run Simulation
        if run_verilog_process():
            console_write("[2/3] Verilog Simulation Finished.")
            
            # 3. Parse Log (Fills execution_trace list)
            process_simulation_log()
            
            # 4. NEW: Replay ALL steps to update GUI to final state
            console_write("=== EXECUTING ===")
            for step in execution_trace:
                execute_step(step)
                
            # 5. NEW: Set stepper to the end
            current_step = len(execution_trace)
            console_write("[3/3] Execution Complete.")
            
    except Exception as e:
        console_write(f"[CRITICAL] {e}")
        messagebox.showerror("Runtime Error", str(e))

def highlight_execution_line(pc_val):
    """Maps the PC value to the text editor line and highlights it"""
    # 1. Get all text from editor
    content = editor.get("1.0", "end").splitlines()
    
    valid_ins_count = 0
    target_line_idx = -1

    # 2. Scan lines to find the Nth instruction (matching PC)
    for idx, line in enumerate(content):
        # Strip comments and whitespace (same logic as assembler)
        # We assume import re exists at top
        clean_line = line.split(";")[0].split("//")[0].strip()
        
        if clean_line:
            # If this line has code, it counts towards the PC
            if valid_ins_count == pc_val:
                target_line_idx = idx + 1 # Tkinter lines are 1-based
                break
            valid_ins_count += 1

    # 3. Apply Visual Highlight
    editor.tag_remove("exec_line", "1.0", "end") # Clear old
    
    if target_line_idx != -1:
        start = f"{target_line_idx}.0"
        end   = f"{target_line_idx+1}.0"
        editor.tag_add("exec_line", start, end)
        editor.see(start) # Auto-scroll to keep line in view

def execute_step(step):
    """Updates GUI based on a single step event"""
    if step["type"] == "EXEC":
        # Log the executed instruction
        msg = f"[PC {step['pc']}] {step['op']} {step['dest']}, {step['src']}"
        console_write(msg)
        
        # --- NEW: Highlight the line in editor ---
        try:
            pc_int = int(step['pc'])
            highlight_execution_line(pc_int)
        except:
            pass
        
    elif step["type"] == "RAM":
        # Update RAM Table Visuals
        addr = step["addr"]
        val  = step["val"]
        ram_cells[addr].config(text=f"{val:X}", fg="#00FF00") 
        console_write(f"    └── RAM[{addr:X}] updated to {val:X}")
        
    elif step["type"] == "DONE":
        console_write("[STOP] Program Halted.")
        # Optional: Remove highlight on finish
        # editor.tag_remove("exec_line", "1.0", "end")
        
    elif step["type"] == "DONE":
        console_write("[STOP] Program Halted.")

#Step instruction button function
def cmd_step():
    """Executes the trace grouping EXEC+RAM into a single click"""
    global current_step, execution_trace
    
    # 1. AUTO-INITIALIZATION (Silent)
    # If trace is empty, we compile and run sim, but DO NOT replay all steps yet.
    if not execution_trace:
        console_write("[INFO] Initializing simulation trace...")
        
        # A. Compile Assembly
        code = editor.get("1.0", "end-1c")
        try:
            words, hex_lines, errors = assemble_text(code)
            if errors:
                console_write("[ABORT] Fix errors first.")
                return
            write_memhex(hex_lines, "program.hex")
        except Exception as e:
            console_write(f"[ERROR] {e}")
            return

        # B. Run Hardware Simulation
        if not run_verilog_process(): 
            return
        
        # C. Parse Log
        process_simulation_log() 
        current_step = 0
        # Note: We do NOT return here. We proceed immediately to execute the first step.

    # 2. RESTART LOGIC
    # If we reached the end previously, loop back to start
    if current_step >= len(execution_trace):
        console_write("[INFO] Restarting simulation trace...")
        current_step = 0
        for lbl in ram_cells: lbl.config(fg="#FFFFFF") # Reset colors

    # 3. SMART STEP EXECUTION
    # Execute the current event (EXEC), and then auto-play any immediate RAM updates
    if current_step < len(execution_trace):
        
        # Execute the main instruction event
        execute_step(execution_trace[current_step])
        current_step += 1
        
        # Look ahead: If the next events are RAM updates (associated with this op), do them now.
        while current_step < len(execution_trace):
            next_type = execution_trace[current_step]["type"]
            
            # Stop if we hit the next Instruction Start
            if next_type == "EXEC":
                break
            
            # Execute RAM updates or DONE messages immediately
            execute_step(execution_trace[current_step])
            current_step += 1

#Assembly Code Compile Function
def compile_program():
    code = editor.get("1.0", "end-1c")

    try:
        # FIX: Unpack 3 values (words, hex, errors) instead of 2
        words, hex_lines, errors = assemble_text(code)

        # 1. Check for Assembly Errors
        if errors:
            console_write("=== COMPILE ERRORS ===")
            for e in errors:
                console_write(f"[ERROR] {e}")
            messagebox.showerror("Compile Failed", f"Found {len(errors)} errors.\nCheck console details.")
            return # Stop here to prevent writing bad hex files

        # 2. Success Path
        write_memhex(hex_lines, "program.hex")
        messagebox.showinfo("Compile Success", "Assembly compiled successfully!")
        console_write("=== COMPILE OUTPUT ===")

        for i, h in enumerate(hex_lines):
            console_write(f"{i:02d}: {h}")

    except Exception as e:
        messagebox.showerror("Compile Error", str(e))
        console_write("[CRITICAL ERROR] " + str(e))

# -------------------------------------
# SYNTAX HIGHLIGHTING ENGINE
# -------------------------------------
def setup_highlight_tags():
    """Define colors for syntax highlighting"""
    # Define tags only if editor exists
    try:
        # Keywords/Opcodes (Blue)
        editor.tag_configure("opcode", foreground="#569CD6", font=("Consolas", 12, "bold"))
        # Numbers (Light Green)
        editor.tag_configure("number", foreground="#B5CEA8")
        # Comments (Dark Green)
        editor.tag_configure("comment", foreground="#6A9955", font=("Consolas", 12, "italic"))
        # Dark Blue background for the active line
        editor.tag_configure("exec_line", background="#264f78")
    except:
        pass

def apply_highlighting(event=None):
    """Scan text and apply tags based on regex patterns"""
    if 'editor' not in globals():
        return

    # 1. Clear existing tags
    for tag in ["opcode", "number", "comment"]:
        editor.tag_remove(tag, "1.0", "end")

    # 2. Highlight Opcodes (Keywords)
    # Using \m (start of word) and \M (end of word) for Tcl regex boundaries
    for opcode in OPC.keys():
        start_idx = "1.0"
        pattern = r"\m" + opcode + r"\M"
        
        while True:
            # Search for pattern
            start_idx = editor.search(pattern, start_idx, stopindex="end", count=tk.IntVar(), regexp=True, nocase=True)
            if not start_idx:
                break
            
            # Calculate end index based on opcode length
            line, char = start_idx.split(".")
            end_idx = f"{line}.{int(char) + len(opcode)}"
            
            editor.tag_add("opcode", start_idx, end_idx)
            start_idx = end_idx

    # 3. Highlight Numbers (Hex 0x..., Bin 0b..., Decimal)
    start_idx = "1.0"
    while True:
        count_var = tk.IntVar()
        # Regex: 0x... OR 0b... OR digits
        start_idx = editor.search(r"(0x[0-9A-Fa-f]+|0b[01]+|\d+)", start_idx, stopindex="end", count=count_var, regexp=True)
        if not start_idx:
            break
        
        length = count_var.get()
        if length == 0: break
        
        end_idx = f"{start_idx}+{length}c"
        editor.tag_add("number", start_idx, end_idx)
        start_idx = end_idx

    # 4. Highlight Comments (Starting with ; or //)
    start_idx = "1.0"
    while True:
        count_var = tk.IntVar()
        start_idx = editor.search(r"(;|//).*", start_idx, stopindex="end", count=count_var, regexp=True)
        if not start_idx:
            break
            
        length = count_var.get()
        if length == 0: break

        end_idx = f"{start_idx}+{length}c"
        editor.tag_add("comment", start_idx, end_idx)
        start_idx = end_idx

#-------------------------------------
# GUI Buttons in the Toolbar
#-------------------------------------

BTN_PADX = 3
BTN_PADY = 5

btn_new = tk.Button(toolbar, text="New", width=7, height=1, bg="#3c3c3c", fg="white",
                    activebackground="#555", activeforeground="white",
                    font=("Consolas", 12, "bold"), relief="flat", bd=0,
                    command=new_file)
btn_new.pack(side="left", padx=BTN_PADX, pady=BTN_PADY)

btn_open = tk.Button(toolbar, text="Open", width=7, height=1, bg="#3c3c3c", fg="white",
                     activebackground="#555", activeforeground="white",
                     font=("Consolas", 12, "bold"), relief="flat", bd=0,
                     command=open_asm_file)
btn_open.pack(side="left", padx=BTN_PADX, pady=BTN_PADY)

btn_save = tk.Button(toolbar, text="Save", width=7, height=1, bg="#3c3c3c", fg="white",
                     activebackground="#555", activeforeground="white",
                     font=("Consolas", 12, "bold"), relief="flat", bd=0,
                     command=save_asm_file)
btn_save.pack(side="left", padx=BTN_PADX, pady=BTN_PADY)

btn_save_as = tk.Button(toolbar, text="Save As", width=7, height=1, bg="#3c3c3c", fg="white",
                        activebackground="#555", activeforeground="white",
                        font=("Consolas", 12, "bold"), relief="flat", bd=0,
                        command=save_asm_file_as)
btn_save_as.pack(side="left", padx=BTN_PADX, pady=BTN_PADY)

btn_wave = tk.Button(toolbar, text="🌊 Wave", width=9, height=1,
                     bg="#3498db", fg="black",
                     activebackground="#2980b9", activeforeground="white",
                     font=("Consolas", 12, "bold"),
                     relief="flat", bd=0,
                     command=cmd_open_gtkwave)
btn_wave.pack(side="right", padx=6, pady=8)

# RUN / STEP / COMPILE / CLEAR RAM buttons unchanged

btn_compile = tk.Button(toolbar, text="Compile", width=9, height=1,
                        bg="#3c3c3c", fg="white",
                        activebackground="#555", activeforeground="white",
                        font=("Consolas", 12, "bold"),
                        relief="flat", bd=0,
                        command=compile_program)
btn_compile.pack(side="right", padx=6, pady=8)

btn_step = tk.Button(toolbar, text="⏭ Step", width=9, height=1,
                     bg="#e67e22", fg="black",
                     activebackground="#d35400", activeforeground="white",
                     font=("Consolas", 12, "bold"),
                     relief="flat", bd=0,
                     command=cmd_step)
btn_step.pack(side="right", padx=6, pady=8)

btn_run = tk.Button(toolbar, text="▶ Run", width=9, height=1,
                    bg="#2ecc71", fg="black",
                    activebackground="#27ae60", activeforeground="white",
                    font=("Consolas", 12, "bold"),
                    relief="flat", bd=0,
                    command=cmd_run)
btn_run.pack(side="right", padx=6, pady=8)

btn_clear_ram = tk.Button(toolbar, text="Clear RAM", width=9, height=1,
                          bg="#3c3c3c", fg="white",
                          activebackground="#555", activeforeground="white",
                          font=("Consolas", 12, "bold"),
                          relief="flat", bd=0,
                          command=cmd_clear_ram)
btn_clear_ram.pack(side="right", padx=6, pady=8)

#-------------------------------------
# Editor + Console split area
#-------------------------------------

content_frame = tk.Frame(root, bg="#1E1E1E")
content_frame.pack(fill="both", expand=True)

# LEFT SIDE: Editor + Console (stacked vertically)
left_side = tk.Frame(content_frame, bg="#1E1E1E")
left_side.pack(side="left", fill="both", expand=True)

# -------------- EDITOR AREA (top 65%) --------------
editor_area = tk.Frame(left_side, bg="#252526")
editor_area.pack(side="top", fill="both", expand=True)

class LineNumbers(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.text_widget = None

    def attach(self, text_widget):
        self.text_widget = text_widget
        self.text_widget.bind("<<Modified>>", self.update)
        self.text_widget.bind("<Configure>", self.update)
        self.text_widget.bind("<KeyRelease>", self.update, add="+")

    def update(self, event=None):
        if self.text_widget is None:
            return
        self.text_widget.edit_modified(False)
        self.delete("all")
        i = self.text_widget.index("@0,0")
        while True:
            d = self.text_widget.dlineinfo(i)
            if d is None:
                break
            y = d[1]
            line_no = str(i).split(".")[0]
            self.create_text(5, y, anchor="nw",
                             text=line_no, fill="#888",
                             font=("Consolas", 11))
            i = self.text_widget.index(f"{i}+1line")

line_bar = LineNumbers(
    editor_area,
    width=40,
    bg="#1e1e1e",
    highlightthickness=0,   # remove highlight border
    bd=0,                   # remove border
    relief="flat"           # completely flat, no edges
)
line_bar.pack(side="left", fill="y")

editor_scroll = tk.Scrollbar(editor_area)
editor_scroll.pack(side="right", fill="y")

editor = tk.Text(editor_area,
                 wrap="none",
                 undo=True,
                 font=("Consolas", 12),
                 bg="#1e1e1e",
                 fg="#ffffff",
                 insertbackground="white",
                 selectbackground="#555555",
                 yscrollcommand=editor_scroll.set)
editor.pack(side="left", fill="both", expand=True)

setup_highlight_tags()
editor.bind("<KeyRelease>", apply_highlighting, add="+")
apply_highlighting()

editor_scroll.config(command=editor.yview)
line_bar.attach(editor)
line_bar.update()

# -------------- CONSOLE AREA (bottom 35%) --------------
console_frame = tk.Frame(left_side, bg="#000000")
console_frame.pack(side="bottom", fill="x")

console_scroll = tk.Scrollbar(console_frame)
console_scroll.pack(side="right", fill="y")

console = tk.Text(console_frame,
                  height=12,
                  bg="#111111",
                  fg="#00FF00",
                  font=("Consolas", 11),
                  insertbackground="white",
                  selectbackground="#333333",
                  yscrollcommand=console_scroll.set)
console.pack(fill="x")

console_scroll.config(command=console.yview)

console.config(state="disabled")

# -------------------------------------
# RAM TABLE AREA (unchanged)
# -------------------------------------
ram_frame = tk.Frame(content_frame, bg="#1E1E1E")
ram_frame.pack(side="right", fill="y", padx=20, pady=20)

ram_label = tk.Label(
    ram_frame,
    text="RAM (16 x 4)",
    fg="white",
    bg="#1E1E1E",
    font=("Consolas", 14, "bold")
)
ram_label.pack(pady=10)

table_container = tk.Frame(ram_frame, bg="#1E1E1E")
table_container.pack(expand=True)

ram_cells = []
for i in range(16):
    row = tk.Frame(table_container, bg="#1E1E1E")
    row.pack(fill="x", pady=1)

    addr_lbl = tk.Label(row, text=f"{i:02X}", width=6,
                        fg="#00FFAA", bg="#2A2A2A",
                        font=("Consolas", 13, "bold"),
                        bd=1, relief="solid")
    addr_lbl.pack(side="left", padx=3)

    data_lbl = tk.Label(row, text="0", width=6,
                        fg="#FFFFFF", bg="#3A3A3A",
                        font=("Consolas", 13),
                        bd=1, relief="solid")
    data_lbl.pack(side="left", padx=3)

    ram_cells.append(data_lbl)

write_panel = tk.Frame(ram_frame, bg="#1E1E1E")
write_panel.pack(fill="x", pady=20)

tk.Label(write_panel, text="Write to RAM", fg="white",
         bg="#1E1E1E", font=("Consolas", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 10))

tk.Label(write_panel, text="Addr (0-F):", fg="#AAAAAA",
         bg="#1E1E1E", font=("Consolas", 11)).grid(row=1, column=0, sticky="e", padx=5, pady=3)

addr_entry = tk.Entry(write_panel, width=6,
                      font=("Consolas", 12),
                      bg="#2A2A2A", fg="white",
                      insertbackground="white",
                      relief="solid", bd=1)
addr_entry.grid(row=1, column=1, sticky="w", padx=5, pady=3)

tk.Label(write_panel, text="Data (0-F):", fg="#AAAAAA",
         bg="#1E1E1E", font=("Consolas", 11)).grid(row=2, column=0, sticky="e", padx=5, pady=3)

data_entry = tk.Entry(write_panel, width=6,
                      font=("Consolas", 12),
                      bg="#2A2A2A", fg="white",
                      insertbackground="white",
                      relief="solid", bd=1)
data_entry.grid(row=2, column=1, sticky="w", padx=5, pady=3)

# RAM User Write input value limit check
def validate_hex_entry(entry_widget, max_value=0xF):
    """Validate hex input (0–F). Highlight red if invalid."""
    text = entry_widget.get().strip()

    try:
        value = int(text, 16)
    except ValueError:
        entry_widget.config(bg="#662222")  # red highlight
        return False

    if value < 0 or value > max_value:
        entry_widget.config(bg="#662222")
        return False

    # Valid → restore normal color
    entry_widget.config(bg="#2A2A2A")
    return True


def write_to_ram():
    """
    Injects a manual RAM value and re-simulates WITHOUT losing position.
    """
    global execution_trace, current_step, ram_injections
    
    # 1. Validation
    if not validate_hex_entry(addr_entry, 0xF):
        messagebox.showerror("Invalid Address", "Address must be 0–F.")
        return
    if not validate_hex_entry(data_entry, 0xF):
        messagebox.showerror("Invalid Data", "Data must be 0–F.")
        return

    addr = int(addr_entry.get(), 16)
    data = int(data_entry.get(), 16)

    # 2. Calculate Injection Target (Map Step -> PC)
    # We must attach this injection to the CURRENT PC so the Verilog knows WHEN to inject.
    target_pc = 0
    if execution_trace and current_step < len(execution_trace):
        # Try to find the PC of the current step
        item = execution_trace[current_step]
        if item["type"] == "EXEC":
            target_pc = int(item["pc"])
        else:
            # If currently on a RAM step, look back or assume same PC
            # Defaulting to index logic if parsing fails
            target_pc = int(execution_trace[current_step-1]["pc"]) if current_step > 0 else 0
    else:
        # If at start or end, inject at 0 or max
        target_pc = 0

    # 3. Save Injection
    ram_injections.append((target_pc, addr, data))
    console_write(f"[MANUAL] Injecting RAM[{addr:X}]={data:X} at PC={target_pc}")

    # 4. SAVE POSITION (The Fix!)
    old_step_index = current_step

    # 5. Re-Run Simulation
    save_injections_file()
    if run_verilog_process():
        process_simulation_log() # This resets current_step to 0
        
        # 6. RESTORE POSITION (Fast Forward)
        console_write(f"=== RESTORING STATE TO STEP {old_step_index} ===")
        
        # Re-play everything up to where we were
        # We assume the trace structure hasn't fundamentally changed
        current_step = 0
        while current_step < old_step_index and current_step < len(execution_trace):
            execute_step(execution_trace[current_step])
            current_step += 1
            
        console_write("=== RESTORE COMPLETE ===")

# Live validation while typing
addr_entry.bind("<KeyRelease>", lambda e: validate_hex_entry(addr_entry))
data_entry.bind("<KeyRelease>", lambda e: validate_hex_entry(data_entry))


# Write Button
tk.Button(
    write_panel,
    text="Write",
    width=6,
    bg="#2ecc71",
    fg="black",
    font=("Consolas", 11, "bold"),
    relief="flat",
    bd=0,
    activebackground="#27ae60",
    activeforeground="white",
    command=write_to_ram
).grid(row=3, column=0, columnspan=2, pady=10)

root.mainloop()