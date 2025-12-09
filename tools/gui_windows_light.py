import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
import os
import subprocess
from assembler import assemble_text, write_memhex, OPC

# ============================================================
# WINDOW & COLOR SCHEME (Windows Light Theme)
# ============================================================
root = tk.Tk()
root.title('4-Bit CPU Simulator')
root.geometry('1600x950+100+50')
root.minsize(1400, 800)
root.attributes('-alpha', 1.0)

# Windows Light Theme Colors
COLOR_BG_PRIMARY = "#FFFFFF"           # White (Primary panels/windows)
COLOR_BG_SECONDARY = "#F0F0F0"         # Light Grey (Toolbar/Borders)
COLOR_TEXT_PRIMARY = "#000000"         # Black (Main text)
COLOR_SECTION_HEADER = "#E1E1E1"       # Light Grey (Section headers)
COLOR_SELECTED = "#CCE8FF"             # Pale Blue (Selected item highlight)
COLOR_ACCENT_BORDER = "#0078D7"        # Standard Blue (Active tab border)
COLOR_SUCCESS = "#107C10"              # Green (Success buttons)
COLOR_WARNING = "#FFB900"              # Orange (Warning buttons)
COLOR_DANGER = "#E81123"               # Red (Error buttons)

root.configure(bg=COLOR_BG_PRIMARY)

# Icon
icon_path = os.path.abspath("ic_chip.png")
if os.path.exists(icon_path):
    try:
        icon_img = tk.PhotoImage(file=icon_path)
        root.iconphoto(False, icon_img)
    except:
        pass

# ============================================================
# GLOBAL STATE
# ============================================================
current_file = None
execution_trace = []
current_step = 0
ram_injections = []
ram_cells = []

# ============================================================
# KEYBOARD SHORTCUTS
# ============================================================
def handle_ctrl_s(event):
    save_asm_file()
    return "break"

root.bind_class("Text", "<Control-s>", handle_ctrl_s)
root.bind_class("Text", "<Control-S>", handle_ctrl_s)

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def console_write(msg):
    console.config(state="normal")
    console.insert("end", msg + "\n")
    console.see("end")
    console.config(state="disabled")

def update_title():
    if current_file:
        filename = os.path.basename(current_file)
        root.title(f"4-Bit CPU Simulator — {filename}")
    else:
        root.title("4-Bit CPU Simulator")

def read_cpu_state():
    state = {"pc":0, "acc":0, "carry":0, "ram":[0]*16}
    if not os.path.exists("cpu_state.hex"):
        write_cpu_state(state)
        return state
    try:
        with open("cpu_state.hex","r") as f:
            line = f.readline()
            if line and line.startswith("PC"):
                state["pc"] = int(line.split()[1])
            line = f.readline()
            if line and line.startswith("ACC"):
                state["acc"] = int(line.split()[1], 16)
            line = f.readline()
            if line and line.startswith("CARRY"):
                state["carry"] = int(line.split()[1])
            line = f.readline()
            if line:
                vals = line.strip().split()
                for i, v in enumerate(vals[:16]):
                    state["ram"][i] = int(v, 16)
    except Exception as e:
        console_write(f"[ERROR] Reading cpu_state.hex: {e}")
    return state

def write_cpu_state(state):
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
        messagebox.showerror("Config Error", "Icarus Verilog not found in PATH.")
        return False

def run_verilog_process():
    sim_exe = "cpu_sim"
    log_file = "simulation.log"
    sources = [
        "../testbench/bridge_tb.v",
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
        messagebox.showerror("Config Error", "Icarus Verilog not found.")
        return False

def process_simulation_log():
    global execution_trace, current_step
    log_file = "simulation.log"
    execution_trace = []
    current_step = 0
    
    if not os.path.exists(log_file):
        return

    console_write("=== PARSING LOG ===")
    try:
        with open(log_file, "r") as f:
            lines = [l.rstrip('\n') for l in f]

        console_write("=== RAW SIM LOG START ===")
        for l in lines:
            console_write(l)
        console_write("=== RAW SIM LOG END ===")

        for line in lines:
            line = line.strip()
            if not line:
                continue
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

def execute_step(step):
    if step["type"] == "EXEC":
        msg = f"[PC {step['pc']}] {step['op']} {step['dest']}, {step['src']}"
        console_write(msg)
        try:
            pc_int = int(step['pc'])
            highlight_execution_line(pc_int)
        except:
            pass
    elif step["type"] == "RAM":
        addr = step["addr"]
        val  = step["val"]
        ram_cells[addr].config(text=f"{val:X}", fg=COLOR_ACCENT_BORDER)
        console_write(f"    └── RAM[{addr:X}] = {val:X}")
    elif step["type"] == "DONE":
        console_write("[STOP] Program Halted.")

def highlight_execution_line(pc_val):
    content = editor.get("1.0", "end").splitlines()
    valid_ins_count = 0
    target_line_idx = -1

    for idx, line in enumerate(content):
        clean_line = line.split(";")[0].split("//")[0].strip()
        if clean_line:
            if valid_ins_count == pc_val:
                target_line_idx = idx + 1
                break
            valid_ins_count += 1

    editor.tag_remove("exec_line", "1.0", "end")
    if target_line_idx != -1:
        start = f"{target_line_idx}.0"
        end   = f"{target_line_idx+1}.0"
        editor.tag_add("exec_line", start, end)
        editor.see(start)

# ============================================================
# FILE OPERATIONS
# ============================================================
def new_file():
    global current_file
    current_file = None
    editor.delete("1.0", "end")
    console_write("[NEW] Blank file created.")
    update_title()

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

# ============================================================
# SIMULATION OPERATIONS
# ============================================================
def compile_program():
    code = editor.get("1.0", "end-1c")
    try:
        words, hex_lines, errors = assemble_text(code)
        if errors:
            console_write("=== COMPILE ERRORS ===")
            for e in errors:
                console_write(f"[ERROR] {e}")
            messagebox.showerror("Compile Failed", f"Found {len(errors)} errors.")
            return
        write_memhex(hex_lines, "program.hex")
        messagebox.showinfo("Success", "Assembly compiled successfully!")
        console_write("=== COMPILE OUTPUT ===")
        for i, h in enumerate(hex_lines):
            console_write(f"{i:02d}: {h}")
    except Exception as e:
        messagebox.showerror("Compile Error", str(e))
        console_write("[ERROR] " + str(e))

def cmd_run():
    global current_step, ram_injections
    ram_injections = []
    if os.path.exists("injections.txt"):
        os.remove("injections.txt")
    
    code = editor.get("1.0", "end-1c")
    try:
        words, hex_lines, errors = assemble_text(code)
        if errors:
            console_write("[ABORT] Fix assembly errors first.")
            for e in errors: console_write(f"[ASM ERROR] {e}")
            messagebox.showerror("Error", "Fix assembly errors first.")
            return
        write_memhex(hex_lines, "program.hex")
        console_write("[1/3] Assembly Compiled.")
        if run_verilog_process():
            console_write("[2/3] Verilog Simulation Finished.")
            process_simulation_log()
            console_write("=== EXECUTING ===")
            for step in execution_trace:
                execute_step(step)
            current_step = len(execution_trace)
            console_write("[3/3] Execution Complete.")
    except Exception as e:
        console_write(f"[CRITICAL] {e}")
        messagebox.showerror("Runtime Error", str(e))

def cmd_step():
    global current_step, execution_trace
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

    try:
        program_len = 0
        if os.path.exists('program.hex'):
            with open('program.hex','r') as pf:
                program_len = sum(1 for l in pf if l.strip())
        state = read_cpu_state()
        if program_len == 0:
            messagebox.showerror('Error', 'program.hex is empty.')
            return
        if state.get('pc',0) >= program_len:
            state['pc'] = 0
            write_cpu_state(state)
    except Exception as e:
        console_write(f"[WARN] {e}")

    if not run_verilog_step():
        return
    process_simulation_log()
    for st in execution_trace:
        execute_step(st)
    try:
        state = read_cpu_state()
        for i, v in enumerate(state['ram']):
            ram_cells[i].config(text=f"{v:X}", fg=COLOR_TEXT_PRIMARY)
        highlight_execution_line(int(state['pc']))
    except:
        pass
    execution_trace = []
    current_step = 0

def cmd_clear_ram():
    for lbl in ram_cells:
        lbl.config(text="0", fg=COLOR_TEXT_PRIMARY)
    console_write("[CMD] RAM Table cleared.")

def cmd_refresh():
    global execution_trace, current_step, ram_injections
    execution_trace = []
    current_step = 0
    ram_injections = []
    console.config(state="normal")
    console.delete("1.0", "end")
    console.config(state="disabled")
    try:
        editor.tag_remove("exec_line", "1.0", "end")
    except:
        pass
    for lbl in ram_cells:
        lbl.config(text="0", fg=COLOR_TEXT_PRIMARY)
    for fname in ("simulation.log", "injections.txt"):
        try:
            if os.path.exists(fname):
                os.remove(fname)
        except:
            pass
    try:
        empty_state = {"pc": 0, "acc": 0, "carry": 0, "ram": [0]*16}
        write_cpu_state(empty_state)
    except Exception as e:
        console_write(f"[ERROR] {e}")
    console_write("[REFRESH] GUI reset to initial state.")

def cmd_open_gtkwave():
    vcd_file = "simulation.vcd"
    if not os.path.exists(vcd_file):
        messagebox.showerror("Error", "No waveform found. Run first.")
        return
    try:
        subprocess.Popen(["gtkwave", vcd_file])
        console_write("[TOOL] GTKWave opened.")
    except FileNotFoundError:
        messagebox.showerror("Error", "GTKWave not found.")

def validate_hex_entry(entry_widget, max_value=0xF):
    text = entry_widget.get().strip()
    try:
        value = int(text, 16)
    except ValueError:
        entry_widget.config(bg="#FFCCCC")
        return False
    if value < 0 or value > max_value:
        entry_widget.config(bg="#FFCCCC")
        return False
    entry_widget.config(bg=COLOR_BG_PRIMARY)
    return True

def write_to_ram():
    if not validate_hex_entry(addr_entry, 0xF):
        messagebox.showerror("Invalid Address", "Address must be 0–F.")
        return
    if not validate_hex_entry(data_entry, 0xF):
        messagebox.showerror("Invalid Data", "Data must be 0–F.")
        return
    addr = int(addr_entry.get(), 16)
    data = int(data_entry.get(), 16)
    try:
        state = read_cpu_state()
        state['ram'][addr] = data
        write_cpu_state(state)
        ram_cells[addr].config(text=f"{data:X}", fg=COLOR_ACCENT_BORDER)
        console_write(f"[MANUAL] RAM[{addr:X}]={data:X}")
        new_state = read_cpu_state()
        console_write(f"[VERIFY] RAM[{addr:X}]={new_state['ram'][addr]:X}")
    except Exception as e:
        console_write(f"[ERROR] {e}")

# ============================================================
# SYNTAX HIGHLIGHTING
# ============================================================
def setup_highlight_tags():
    editor.tag_configure("opcode", foreground=COLOR_ACCENT_BORDER, font=("Consolas", 12, "bold"))
    editor.tag_configure("number", foreground=COLOR_SUCCESS)
    editor.tag_configure("comment", foreground="#696969", font=("Consolas", 12, "italic"))
    editor.tag_configure("exec_line", background=COLOR_SELECTED)

def apply_highlighting(event=None):
    if 'editor' not in globals():
        return
    for tag in ["opcode", "number", "comment"]:
        editor.tag_remove(tag, "1.0", "end")
    for opcode in OPC.keys():
        start_idx = "1.0"
        pattern = r"\m" + opcode + r"\M"
        while True:
            start_idx = editor.search(pattern, start_idx, stopindex="end", count=tk.IntVar(), regexp=True, nocase=True)
            if not start_idx:
                break
            line, char = start_idx.split(".")
            end_idx = f"{line}.{int(char) + len(opcode)}"
            editor.tag_add("opcode", start_idx, end_idx)
            start_idx = end_idx
    start_idx = "1.0"
    while True:
        count_var = tk.IntVar()
        start_idx = editor.search(r"(0x[0-9A-Fa-f]+|0b[01]+|\d+)", start_idx, stopindex="end", count=count_var, regexp=True)
        if not start_idx:
            break
        length = count_var.get()
        if length == 0:
            break
        end_idx = f"{start_idx}+{length}c"
        editor.tag_add("number", start_idx, end_idx)
        start_idx = end_idx
    start_idx = "1.0"
    while True:
        count_var = tk.IntVar()
        start_idx = editor.search(r"(;|//).*", start_idx, stopindex="end", count=count_var, regexp=True)
        if not start_idx:
            break
        length = count_var.get()
        if length == 0:
            break
        end_idx = f"{start_idx}+{length}c"
        editor.tag_add("comment", start_idx, end_idx)
        start_idx = end_idx

# ============================================================
# TOOLBAR
# ============================================================
toolbar = tk.Frame(root, bg=COLOR_BG_SECONDARY, relief="solid", bd=1, height=50)
toolbar.pack(fill="x", side="top", padx=0, pady=0)
toolbar.pack_propagate(False)

tk.Button(toolbar, text="📄 New", bg=COLOR_BG_SECONDARY, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 10, "bold"), relief="flat", padx=12, pady=6, command=new_file).pack(side="left", padx=4, pady=5)
tk.Button(toolbar, text="📂 Open", bg=COLOR_BG_SECONDARY, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 10, "bold"), relief="flat", padx=12, pady=6, command=open_asm_file).pack(side="left", padx=4, pady=5)
tk.Button(toolbar, text="💾 Save", bg=COLOR_BG_SECONDARY, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 10, "bold"), relief="flat", padx=12, pady=6, command=save_asm_file).pack(side="left", padx=4, pady=5)
tk.Button(toolbar, text="💾 Save As", bg=COLOR_BG_SECONDARY, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 10, "bold"), relief="flat", padx=12, pady=6, command=save_asm_file_as).pack(side="left", padx=4, pady=5)

ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8, pady=5)

tk.Button(toolbar, text="⚙️  Compile", bg=COLOR_ACCENT_BORDER, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=12, pady=6, command=compile_program).pack(side="right", padx=4, pady=5)
tk.Button(toolbar, text="▶ Run", bg=COLOR_SUCCESS, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=12, pady=6, command=cmd_run).pack(side="right", padx=4, pady=5)
tk.Button(toolbar, text="⏭ Step", bg=COLOR_WARNING, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=12, pady=6, command=cmd_step).pack(side="right", padx=4, pady=5)
tk.Button(toolbar, text="🔄 Refresh", bg=COLOR_BG_SECONDARY, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 10, "bold"), relief="flat", padx=12, pady=6, command=cmd_refresh).pack(side="right", padx=4, pady=5)
tk.Button(toolbar, text="🗑  Clear RAM", bg=COLOR_BG_SECONDARY, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 10, "bold"), relief="flat", padx=12, pady=6, command=cmd_clear_ram).pack(side="right", padx=4, pady=5)
tk.Button(toolbar, text="📊 Wave", bg=COLOR_BG_SECONDARY, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 10, "bold"), relief="flat", padx=12, pady=6, command=cmd_open_gtkwave).pack(side="right", padx=4, pady=5)

# ============================================================
# MAIN CONTENT - RESIZABLE PANELS
# ============================================================
main_paned = tk.PanedWindow(root, orient=tk.HORIZONTAL, bg=COLOR_BG_PRIMARY, sashwidth=4, relief="flat")
main_paned.pack(fill="both", expand=True, padx=0, pady=0)

# LEFT PANED (Editor & Console)
left_paned = tk.PanedWindow(main_paned, orient=tk.VERTICAL, bg=COLOR_BG_PRIMARY, sashwidth=3, relief="flat")
main_paned.add(left_paned, width=900)

# EDITOR PANEL
editor_frame = tk.Frame(left_paned, bg=COLOR_BG_PRIMARY, relief="solid", bd=1)
left_paned.add(editor_frame, height=500)

editor_header = tk.Frame(editor_frame, bg=COLOR_SECTION_HEADER, relief="flat", bd=0)
editor_header.pack(fill="x", padx=0, pady=0)
tk.Label(editor_header, text="ASSEMBLY CODE EDITOR", bg=COLOR_SECTION_HEADER, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9, "bold")).pack(fill="x", padx=8, pady=6)

editor_inner = tk.Frame(editor_frame, bg=COLOR_BG_PRIMARY)
editor_inner.pack(fill="both", expand=True, padx=0, pady=0)

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
            self.create_text(5, y, anchor="nw", text=line_no, fill="#999", font=("Consolas", 10))
            i = self.text_widget.index(f"{i}+1line")

line_bar = LineNumbers(editor_inner, width=35, bg=COLOR_SECTION_HEADER, highlightthickness=0, bd=0, relief="flat")
line_bar.pack(side="left", fill="y")

editor_scroll = tk.Scrollbar(editor_inner, bg=COLOR_BG_SECONDARY)
editor_scroll.pack(side="right", fill="y")

editor = tk.Text(editor_inner, wrap="none", undo=True, font=("Consolas", 11), bg=COLOR_BG_PRIMARY, fg=COLOR_TEXT_PRIMARY, insertbackground=COLOR_ACCENT_BORDER, selectbackground=COLOR_SELECTED, relief="flat", bd=0, yscrollcommand=editor_scroll.set)
editor.pack(side="left", fill="both", expand=True)

editor_scroll.config(command=editor.yview)
line_bar.attach(editor)
line_bar.update()

setup_highlight_tags()
editor.bind("<KeyRelease>", apply_highlighting, add="+")
apply_highlighting()

# CONSOLE PANEL
console_frame = tk.Frame(left_paned, bg=COLOR_BG_PRIMARY, relief="solid", bd=1)
left_paned.add(console_frame, height=300)

console_header = tk.Frame(console_frame, bg=COLOR_SECTION_HEADER, relief="flat", bd=0)
console_header.pack(fill="x", padx=0, pady=0)
tk.Label(console_header, text="SIMULATION LOG", bg=COLOR_SECTION_HEADER, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9, "bold")).pack(fill="x", padx=8, pady=6)

console_inner = tk.Frame(console_frame, bg=COLOR_BG_PRIMARY)
console_inner.pack(fill="both", expand=True, padx=0, pady=0)

console_scroll = tk.Scrollbar(console_inner, bg=COLOR_BG_SECONDARY)
console_scroll.pack(side="right", fill="y")

console = tk.Text(console_inner, height=15, bg=COLOR_BG_PRIMARY, fg=COLOR_TEXT_PRIMARY, font=("Consolas", 9), insertbackground=COLOR_ACCENT_BORDER, selectbackground=COLOR_SELECTED, relief="flat", bd=0, yscrollcommand=console_scroll.set)
console.pack(side="left", fill="both", expand=True)

console_scroll.config(command=console.yview)
console.config(state="disabled")

# RIGHT PANEL - RAM & CONTROL (SCROLLABLE)
right_outer = tk.Frame(main_paned, bg=COLOR_BG_PRIMARY, relief="solid", bd=1)
main_paned.add(right_outer, width=380)

# Add scrollbar to right panel
right_canvas = tk.Canvas(right_outer, bg=COLOR_BG_PRIMARY, highlightthickness=0)
scrollbar = tk.Scrollbar(right_outer, orient="vertical", command=right_canvas.yview)
right_frame = tk.Frame(right_canvas, bg=COLOR_BG_PRIMARY)

right_canvas.create_window((0, 0), window=right_frame, anchor="nw")
right_canvas.configure(yscrollcommand=scrollbar.set)

right_canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

def _on_mousewheel(event):
    right_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
right_canvas.bind_all("<MouseWheel>", _on_mousewheel)

# RAM HEADER
ram_header = tk.Frame(right_frame, bg=COLOR_SECTION_HEADER, relief="flat", bd=0)
ram_header.pack(fill="x", padx=0, pady=0)
tk.Label(ram_header, text="MEMORY (RAM)", bg=COLOR_SECTION_HEADER, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9, "bold")).pack(fill="x", padx=8, pady=6)

# RAM TABLE
ram_table_frame = tk.Frame(right_frame, bg=COLOR_BG_PRIMARY)
ram_table_frame.pack(fill="x", padx=8, pady=(8, 12))

ram_cells = []
for i in range(16):
    row = tk.Frame(ram_table_frame, bg=COLOR_BG_PRIMARY)
    row.pack(fill="x", pady=4)
    
    addr = tk.Label(row, text=f"{i:02X}", width=3, bg=COLOR_ACCENT_BORDER, fg="white", font=("Consolas", 12, "bold"), relief="solid", bd=1, padx=6, pady=5)
    addr.pack(side="left", padx=4)
    
    val = tk.Label(row, text="0", width=6, bg=COLOR_BG_SECONDARY, fg=COLOR_TEXT_PRIMARY, font=("Consolas", 12), relief="solid", bd=1, padx=6, pady=5)
    val.pack(side="left", padx=4, fill="x", expand=True)
    
    ram_cells.append(val)

# WRITE TO RAM SECTION
write_header = tk.Frame(right_frame, bg=COLOR_SECTION_HEADER, relief="flat", bd=0)
write_header.pack(fill="x", padx=0, pady=(12, 0))
tk.Label(write_header, text="WRITE TO RAM", bg=COLOR_SECTION_HEADER, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9, "bold")).pack(fill="x", padx=8, pady=6)

write_frame = tk.Frame(right_frame, bg=COLOR_BG_PRIMARY)
write_frame.pack(fill="x", padx=8, pady=12)

tk.Label(write_frame, text="Address (0–F):", bg=COLOR_BG_PRIMARY, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 4))
addr_entry = tk.Entry(write_frame, width=12, font=("Consolas", 11), bg=COLOR_BG_PRIMARY, fg=COLOR_TEXT_PRIMARY, relief="solid", bd=1, insertbackground=COLOR_ACCENT_BORDER)
addr_entry.pack(fill="x", pady=(0, 10))

tk.Label(write_frame, text="Value (0–F):", bg=COLOR_BG_PRIMARY, fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 4))
data_entry = tk.Entry(write_frame, width=12, font=("Consolas", 11), bg=COLOR_BG_PRIMARY, fg=COLOR_TEXT_PRIMARY, relief="solid", bd=1, insertbackground=COLOR_ACCENT_BORDER)
data_entry.pack(fill="x", pady=(0, 12))

addr_entry.bind("<KeyRelease>", lambda e: validate_hex_entry(addr_entry))
data_entry.bind("<KeyRelease>", lambda e: validate_hex_entry(data_entry))

tk.Button(write_frame, text="✓ Write to RAM", bg=COLOR_SUCCESS, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=10, pady=6, command=write_to_ram).pack(fill="x")

right_canvas.configure(scrollregion=right_canvas.bbox("all"))

root.mainloop()
