import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import os
import subprocess
from assembler import assemble_text, write_memhex, OPC

#GUI Window Title
root = tk.Tk()
title = root.title('4-Bit CPU Simulator')

#Default GUI Window Dimension
window_width = 1400
window_height = 900

#GUI window size limits
root.minsize(window_width, window_height)
#root.maxsize(1000, 700)

#Startup GUI Window Position
window_size = root.geometry(f'{window_width}x{window_height}+257+33')
window_resize = root.resizable(True, True) #Can Resize GUI window in the X and Y axis

#GUI Transparency
root.attributes('-alpha', 1.0)

# Color scheme (Modern Dark - GitHub inspired)
COLOR_BG_PRIMARY = "#0D1117"      # Very dark background
COLOR_BG_SECONDARY = "#161B22"    # Slightly lighter
COLOR_BG_ACCENT = "#21262D"       # Accent background
COLOR_TEXT_PRIMARY = "#E6EDF3"    # Light text
COLOR_TEXT_SECONDARY = "#8B949E"  # Dimmed text
COLOR_ACCENT_PRIMARY = "#1F6FEB"  # Bright blue
COLOR_ACCENT_SUCCESS = "#238636"  # Green
COLOR_ACCENT_WARNING = "#D29922"  # Orange
COLOR_ACCENT_DANGER = "#DA3633"   # Red
COLOR_BORDER = "#30363D"          # Border color

root.configure(bg=COLOR_BG_PRIMARY)

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

toolbar = tk.Frame(root, bg=COLOR_BG_SECONDARY, relief="flat", bd=0)
toolbar.pack(fill="x", side="top", padx=0, pady=0)

# Toolbar separator
toolbar_sep = tk.Frame(root, bg=COLOR_BORDER, height=2)
toolbar_sep.pack(fill="x", side="top")

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
            lines = [l.rstrip('\n') for l in f]

        # Echo raw log for debugging
        console_write("=== RAW SIM LOG START ===")
        for l in lines:
            console_write(l)
        console_write("=== RAW SIM LOG END ===")

        for line in lines:
            line = line.strip()

            if not line:
                continue

            # PARSE [EXEC] EVENTS
            if line.startswith("[EXEC]"):
                parts = line.split("|")
                try:
                    step = {
                        "type": "EXEC",
                        "pc":   parts[0].split(":")[1].strip(),
                        "op":   parts[1].split(":")[1].strip(),
                        "dest": parts[2].split(":")[1].strip(),
                        "src":  parts[3].split(":")[1].strip()
                    }
                    execution_trace.append(step)
                except Exception as ex:
                    console_write(f"[PARSE ERROR] EXEC line: {ex}")

            # PARSE [RAM] EVENTS
            elif line.startswith("[RAM]"):
                parts = line.split()
                try:
                    step = {
                        "type": "RAM",
                        "addr": int(parts[1].split(":")[1], 16),
                        "val":  int(parts[2].split(":")[1], 16)
                    }
                    execution_trace.append(step)
                except Exception as ex:
                    console_write(f"[PARSE ERROR] RAM line: {ex}")

            elif line.startswith("[DONE]"):
                execution_trace.append({"type": "DONE"})

        console_write(f"[INFO] Simulation trace loaded: {len(execution_trace)} steps.")

    except Exception as e:
        console_write(f"[LOG ERROR] Could not read log: {e}")


def read_cpu_state():
    """Read `cpu_state.hex` and return a dict with pc, acc, carry, ram[16].
    If the file doesn't exist, return default zeros and create it.
    """
    state = {"pc":0, "acc":0, "carry":0, "ram":[0]*16}
    if not os.path.exists("cpu_state.hex"):
        write_cpu_state(state)
        return state

    try:
        with open("cpu_state.hex","r") as f:
            # PC <decimal>\n
            line = f.readline()
            if line and line.startswith("PC"):
                parts = line.split()
                state["pc"] = int(parts[1])

            line = f.readline()
            if line and line.startswith("ACC"):
                state["acc"] = int(line.split()[1], 16)

            line = f.readline()
            if line and line.startswith("CARRY"):
                state["carry"] = int(line.split()[1])

            # RAM line (16 hex values)
            line = f.readline()
            if line:
                vals = line.strip().split()
                for i, v in enumerate(vals[:16]):
                    state["ram"][i] = int(v, 16)

    except Exception as e:
        console_write(f"[ERROR] Reading cpu_state.hex: {e}")

    return state


def write_cpu_state(state):
    """Write the cpu state dict to `cpu_state.hex` in the canonical format.
    Format:
      PC <decimal>\n
      ACC <hex>\n
      CARRY <0|1>\n
      <16 hex RAM values separated by spaces>\n
    """
    try:
        with open("cpu_state.hex","w") as f:
            f.write(f"PC {state['pc']}\n")
            f.write(f"ACC {state['acc']:X}\n")
            f.write(f"CARRY {state['carry']}\n")
            ram_line = " ".join(f"{v:X}" for v in state["ram"]) + "\n"
            f.write(ram_line)
    except Exception as e:
        console_write(f"[ERROR] Writing cpu_state.hex: {e}")


def run_verilog_step():
    """Compile and run the single-step testbench `bridge_tb_step.v`.
    Logs go to `simulation.log` just like the full-run flow.
    """
    sim_exe = "cpu_sim_step"
    log_file = "simulation.log"

    sources = [
        "../testbench/bridge_tb_step.v",
        "../src/cpu_top.v",
        "../src/decoder_fsm.v",
        "../src/ram16x4.v",
        "../src/reg_alu4.v",
        "../src/full_adder4.v",
        "../src/full_adder1.v",
        "../src/xor_gate.v"
    ]

    try:
        cmd_compile = ["iverilog", "-o", sim_exe, "-I", "../src"] + sources
        subprocess.run(cmd_compile, check=True, capture_output=True)

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
    # New snapshot single-step flow:
    # 1) Ensure program.hex is up-to-date, 2) run single-step testbench, 3) parse and display its small trace
    code = editor.get("1.0", "end-1c")
    try:
        words, hex_lines, errors = assemble_text(code)
        if errors:
            console_write("[ABORT] Fix errors first.")
            for e in errors: console_write(f"[ASM ERROR] {e}")
            return
        write_memhex(hex_lines, "program.hex")
    except Exception as e:
        console_write(f"[ERROR] {e}")
        return

    # Run the single-step testbench which reads/writes cpu_state.hex
    # Before running: ensure PC in cpu_state.hex points to an existing instruction
    try:
        # Count non-empty lines in program.hex
        program_len = 0
        if os.path.exists('program.hex'):
            with open('program.hex','r') as pf:
                for l in pf:
                    if l.strip():
                        program_len += 1

        state = read_cpu_state()
        if program_len == 0:
            console_write('[ERROR] program.hex is empty — compile your program first.')
            messagebox.showerror('Error', 'program.hex is empty — compile your program first.')
            return

        if state.get('pc',0) >= program_len:
            console_write(f"[WARN] cpu_state.hex PC ({state.get('pc')}) is beyond program length ({program_len}). Resetting PC to 0.")
            state['pc'] = 0
            write_cpu_state(state)

    except Exception as e:
        console_write(f"[WARN] Could not validate PC vs program.hex: {e}")

    if not run_verilog_step():
        return

    # Parse the small log and update GUI
    process_simulation_log()

    # Execute any events produced (typically one EXEC + one RAM)
    exec_count = 0
    for st in execution_trace:
        execute_step(st)
        if st.get('type') == 'EXEC':
            exec_count += 1

    # If no EXEC lines were present, show cpu_state.hex and warn user (helpful debug)
    if exec_count == 0:
        console_write("[WARN] No EXEC events in trace. Inspecting cpu_state.hex and program.hex:")
        try:
            if os.path.exists('cpu_state.hex'):
                console_write('--- cpu_state.hex ---')
                with open('cpu_state.hex','r') as sf:
                    for l in sf:
                        console_write(l.strip())
                console_write('--- program.hex (first 32 lines) ---')
                if os.path.exists('program.hex'):
                    with open('program.hex','r') as pf:
                        for i, l in enumerate(pf):
                            if i >= 32: break
                            console_write(f"{i:02d}: {l.strip()}")
        except Exception as e:
            console_write(f"[ERROR] Inspecting state files: {e}")

    # Refresh entire RAM view from cpu_state.hex (authoritative)
    try:
        state = read_cpu_state()
        for i, v in enumerate(state['ram']):
            ram_cells[i].config(text=f"{v:X}", fg="#FFFFFF")

        # Highlight next PC line (if applicable)
        try:
            highlight_execution_line(int(state['pc']))
        except Exception:
            pass

    except Exception as e:
        console_write(f"[ERROR] after step: {e}")

    # Reset execution_trace so next step remains snapshot-driven
    execution_trace = []
    current_step = 0

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

btn_new = tk.Button(toolbar, text="📄 New", width=8, height=1, bg=COLOR_BG_ACCENT, fg=COLOR_TEXT_PRIMARY,
                    activebackground=COLOR_ACCENT_PRIMARY, activeforeground=COLOR_TEXT_PRIMARY,
                    font=("Segoe UI", 11, "bold"), relief="flat", bd=0,
                    command=new_file)
btn_new.pack(side="left", padx=BTN_PADX, pady=BTN_PADY)

btn_open = tk.Button(toolbar, text="📂 Open", width=8, height=1, bg=COLOR_BG_ACCENT, fg=COLOR_TEXT_PRIMARY,
                     activebackground=COLOR_ACCENT_PRIMARY, activeforeground=COLOR_TEXT_PRIMARY,
                     font=("Segoe UI", 11, "bold"), relief="flat", bd=0,
                     command=open_asm_file)
btn_open.pack(side="left", padx=BTN_PADX, pady=BTN_PADY)

btn_save = tk.Button(toolbar, text="💾 Save", width=8, height=1, bg=COLOR_BG_ACCENT, fg=COLOR_TEXT_PRIMARY,
                     activebackground=COLOR_ACCENT_PRIMARY, activeforeground=COLOR_TEXT_PRIMARY,
                     font=("Segoe UI", 11, "bold"), relief="flat", bd=0,
                     command=save_asm_file)
btn_save.pack(side="left", padx=BTN_PADX, pady=BTN_PADY)

btn_save_as = tk.Button(toolbar, text="💾 Save As", width=8, height=1, bg=COLOR_BG_ACCENT, fg=COLOR_TEXT_PRIMARY,
                        activebackground=COLOR_ACCENT_PRIMARY, activeforeground=COLOR_TEXT_PRIMARY,
                        font=("Segoe UI", 11, "bold"), relief="flat", bd=0,
                        command=save_asm_file_as)
btn_save_as.pack(side="left", padx=BTN_PADX, pady=BTN_PADY)

# Separator between file and simulation buttons
sep_file = tk.Frame(toolbar, bg=COLOR_BORDER, width=2)
sep_file.pack(side="left", fill="y", padx=10, pady=5)

#-------------------------------------
# Refresh button function
#-------------------------------------
def cmd_refresh():
    """Clear console, execution trace, ram table, logs and reset `cpu_state.hex` to zeros."""
    global execution_trace, current_step, ram_injections
    # Clear internal state
    execution_trace = []
    current_step = 0
    ram_injections = []

    # Clear console
    console.config(state="normal")
    console.delete("1.0", "end")
    console.config(state="disabled")

    # Clear editor execution highlight
    try:
        editor.tag_remove("exec_line", "1.0", "end")
    except:
        pass

    # Reset RAM table visuals
    for lbl in ram_cells:
        lbl.config(text="0", fg=COLOR_TEXT_PRIMARY)

    # Remove simulator artifacts if present
    for fname in ("simulation.log", "injections.txt"):
        try:
            if os.path.exists(fname):
                os.remove(fname)
        except Exception:
            pass

    # Reset cpu_state.hex to default zero state
    try:
        empty_state = {"pc": 0, "acc": 0, "carry": 0, "ram": [0]*16}
        write_cpu_state(empty_state)
    except Exception as e:
        console_write(f"[REFRESH ERROR] Could not reset cpu_state.hex: {e}")

    console_write("[REFRESH] GUI cleared; cpu_state.hex reset to initial state.")
    messagebox.showinfo("Refreshed", "GUI state, logs and cpu_state reset to initial state.")

btn_compile = tk.Button(toolbar, text="⚙️ Compile", width=10, height=1,
                        bg=COLOR_ACCENT_PRIMARY, fg=COLOR_TEXT_PRIMARY,
                        activebackground="#1A63D8", activeforeground=COLOR_TEXT_PRIMARY,
                        font=("Segoe UI", 11, "bold"),
                        relief="flat", bd=0,
                        command=compile_program)
btn_compile.pack(side="right", padx=8, pady=8)

btn_run = tk.Button(toolbar, text="▶ Run", width=10, height=1,
                    bg=COLOR_ACCENT_SUCCESS, fg=COLOR_TEXT_PRIMARY,
                    activebackground="#1f6e3f", activeforeground=COLOR_TEXT_PRIMARY,
                    font=("Segoe UI", 11, "bold"),
                    relief="flat", bd=0,
                    command=cmd_run)
btn_run.pack(side="right", padx=8, pady=8)

btn_step = tk.Button(toolbar, text="⏭ Step", width=10, height=1,
                     bg=COLOR_ACCENT_WARNING, fg=COLOR_TEXT_PRIMARY,
                     activebackground="#b8860b", activeforeground=COLOR_TEXT_PRIMARY,
                     font=("Segoe UI", 11, "bold"),
                     relief="flat", bd=0,
                     command=cmd_step)
btn_step.pack(side="right", padx=8, pady=8)

btn_refresh = tk.Button(toolbar, text="🔄 Refresh", width=10, height=1,
                        bg=COLOR_BG_ACCENT, fg=COLOR_TEXT_PRIMARY,
                        activebackground=COLOR_ACCENT_PRIMARY, activeforeground=COLOR_TEXT_PRIMARY,
                        font=("Segoe UI", 11, "bold"),
                        relief="flat", bd=0,
                        command=cmd_refresh)
btn_refresh.pack(side="right", padx=8, pady=8)

btn_clear_ram = tk.Button(toolbar, text="🗑 Clear RAM", width=10, height=1,
                          bg=COLOR_BG_ACCENT, fg=COLOR_TEXT_PRIMARY,
                          activebackground=COLOR_ACCENT_DANGER, activeforeground=COLOR_TEXT_PRIMARY,
                          font=("Segoe UI", 11, "bold"),
                          relief="flat", bd=0,
                          command=cmd_clear_ram)
btn_clear_ram.pack(side="right", padx=8, pady=8)

btn_wave = tk.Button(toolbar, text="🌊 Wave", width=10, height=1,
                     bg=COLOR_BG_ACCENT, fg=COLOR_TEXT_PRIMARY,
                     activebackground=COLOR_ACCENT_PRIMARY, activeforeground=COLOR_TEXT_PRIMARY,
                     font=("Segoe UI", 11, "bold"),
                     relief="flat", bd=0,
                     command=cmd_open_gtkwave)
btn_wave.pack(side="right", padx=8, pady=8)

#-------------------------------------
# Editor + Console split area
#-------------------------------------

content_frame = tk.Frame(root, bg=COLOR_BG_PRIMARY)
content_frame.pack(fill="both", expand=True, padx=0, pady=0)

# LEFT SIDE: Editor + Console (stacked vertically)
left_side = tk.Frame(content_frame, bg=COLOR_BG_PRIMARY)
left_side.pack(side="left", fill="both", expand=True)

# -------------- EDITOR AREA (top 65%) --------------
editor_area = tk.Frame(left_side, bg=COLOR_BG_SECONDARY)
editor_area.pack(side="top", fill="both", expand=True)

# Editor label
editor_label = tk.Label(editor_area, text="Assembly Code Editor", bg=COLOR_BG_SECONDARY, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 10, "bold"))
editor_label.pack(side="top", fill="x", padx=10, pady=(10, 5))

editor_container = tk.Frame(editor_area, bg=COLOR_BG_PRIMARY)
editor_container.pack(side="top", fill="both", expand=True, padx=10, pady=(0, 10))

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
    editor_container,
    width=40,
    bg=COLOR_BG_SECONDARY,
    highlightthickness=0,   # remove highlight border
    bd=0,                   # remove border
    relief="flat"           # completely flat, no edges
)
line_bar.pack(side="left", fill="y")

editor_scroll = tk.Scrollbar(editor_container)
editor_scroll.pack(side="right", fill="y")

editor = tk.Text(editor_container,
                 wrap="none",
                 undo=True,
                 font=("Consolas", 12),
                 bg=COLOR_BG_SECONDARY,
                 fg=COLOR_TEXT_PRIMARY,
                 insertbackground=COLOR_ACCENT_PRIMARY,
                 selectbackground=COLOR_BG_ACCENT,
                 relief="flat",
                 bd=0)
editor.pack(side="left", fill="both", expand=True)

setup_highlight_tags()
editor.bind("<KeyRelease>", apply_highlighting, add="+")
apply_highlighting()

editor_scroll.config(command=editor.yview)
line_bar.attach(editor)
line_bar.update()

# -------------- CONSOLE AREA (bottom 35%) --------------
console_frame = tk.Frame(left_side, bg=COLOR_BG_PRIMARY)
console_frame.pack(side="bottom", fill="both", expand=False, padx=10, pady=10)

console_label = tk.Label(console_frame, text="Simulation Log", bg=COLOR_BG_PRIMARY, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 10, "bold"))
console_label.pack(side="top", fill="x", pady=(0, 5))

console_container = tk.Frame(console_frame, bg=COLOR_BG_SECONDARY, relief="flat", bd=0)
console_container.pack(side="top", fill="both", expand=True)

console_scroll = tk.Scrollbar(console_container)
console_scroll.pack(side="right", fill="y")

console = tk.Text(console_container,
                  height=10,
                  bg=COLOR_BG_SECONDARY,
                  fg=COLOR_TEXT_PRIMARY,
                  font=("Consolas", 10),
                  insertbackground=COLOR_ACCENT_PRIMARY,
                  selectbackground=COLOR_BG_ACCENT,
                  relief="flat",
                  bd=0)
console.pack(side="left", fill="both", expand=True)

console_scroll.config(command=console.yview)

console.config(state="disabled")

# -------------------------------------
# RAM TABLE AREA (unchanged)
# -------------------------------------
ram_frame = tk.Frame(content_frame, bg=COLOR_BG_PRIMARY)
ram_frame.pack(side="right", fill="y", padx=15, pady=15)

ram_label = tk.Label(
    ram_frame,
    text="RAM (16 × 4-bit)",
    fg=COLOR_TEXT_PRIMARY,
    bg=COLOR_BG_PRIMARY,
    font=("Segoe UI", 12, "bold")
)
ram_label.pack(pady=(0, 12))

# RAM Table Container with border
ram_table_container = tk.Frame(ram_frame, bg=COLOR_BG_SECONDARY, relief="flat", bd=0)
ram_table_container.pack(expand=True, fill="y")

table_container = tk.Frame(ram_table_container, bg=COLOR_BG_SECONDARY)
table_container.pack(expand=True, fill="y", padx=1, pady=1)

ram_cells = []
for i in range(16):
    row = tk.Frame(table_container, bg=COLOR_BG_SECONDARY)
    row.pack(fill="x", pady=2)

    addr_lbl = tk.Label(row, text=f"{i:02X}", width=6,
                        fg=COLOR_ACCENT_PRIMARY, bg=COLOR_BG_ACCENT,
                        font=("Consolas", 12, "bold"),
                        bd=0, relief="flat")
    addr_lbl.pack(side="left", padx=3)

    data_lbl = tk.Label(row, text="0", width=6,
                        fg=COLOR_TEXT_PRIMARY, bg=COLOR_BG_ACCENT,
                        font=("Consolas", 12),
                        bd=0, relief="flat")
    data_lbl.pack(side="left", padx=3)

    ram_cells.append(data_lbl)

# Write to RAM section
write_panel = tk.Frame(ram_frame, bg=COLOR_BG_PRIMARY)
write_panel.pack(fill="x", pady=20)

write_label = tk.Label(write_panel, text="Write to RAM", fg=COLOR_TEXT_PRIMARY,
         bg=COLOR_BG_PRIMARY, font=("Segoe UI", 11, "bold"))
write_label.grid(row=0, column=0, columnspan=2, pady=(0, 12))

tk.Label(write_panel, text="Addr (0-F):", fg=COLOR_TEXT_SECONDARY,
         bg=COLOR_BG_PRIMARY, font=("Segoe UI", 10)).grid(row=1, column=0, sticky="e", padx=5, pady=5)

addr_entry = tk.Entry(write_panel, width=6,
                      font=("Consolas", 11),
                      bg=COLOR_BG_ACCENT, fg=COLOR_TEXT_PRIMARY,
                      insertbackground=COLOR_ACCENT_PRIMARY,
                      relief="flat", bd=1, borderwidth=1)
addr_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

tk.Label(write_panel, text="Data (0-F):", fg=COLOR_TEXT_SECONDARY,
         bg=COLOR_BG_PRIMARY, font=("Segoe UI", 10)).grid(row=2, column=0, sticky="e", padx=5, pady=5)

data_entry = tk.Entry(write_panel, width=6,
                      font=("Consolas", 11),
                      bg=COLOR_BG_ACCENT, fg=COLOR_TEXT_PRIMARY,
                      insertbackground=COLOR_ACCENT_PRIMARY,
                      relief="flat", bd=1, borderwidth=1)
data_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)

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
    entry_widget.config(bg=COLOR_BG_ACCENT)
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

    # Snapshot approach: directly update cpu_state.hex so next Step will use it
    try:
        state = read_cpu_state()
        state['ram'][addr] = data
        write_cpu_state(state)

        # Update GUI table immediately to reflect user's edit
        ram_cells[addr].config(text=f"{data:X}", fg="#00FF00")
        console_write(f"[MANUAL] Updated cpu_state.hex RAM[{addr:X}]={data:X} (PC={state['pc']})")

        # Verify write by reading back and logging
        new_state = read_cpu_state()
        console_write(f"[VERIFY] cpu_state.hex RAM[{addr:X}]={new_state['ram'][addr]:X}")

        # Do NOT run the simulator now — the single-step testbench will load the updated file
    except Exception as e:
        console_write(f"[ERROR] write_to_ram: {e}")

# Live validation while typing
addr_entry.bind("<KeyRelease>", lambda e: validate_hex_entry(addr_entry))
data_entry.bind("<KeyRelease>", lambda e: validate_hex_entry(data_entry))


# Write Button
tk.Button(
    write_panel,
    text="✓ Write",
    width=8,
    bg=COLOR_ACCENT_SUCCESS,
    fg=COLOR_TEXT_PRIMARY,
    font=("Segoe UI", 10, "bold"),
    relief="flat",
    bd=0,
    activebackground="#1f6e3f",
    activeforeground=COLOR_TEXT_PRIMARY,
    command=write_to_ram
).grid(row=3, column=0, columnspan=2, pady=12)

root.mainloop()