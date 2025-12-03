import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import os
from assembler import assemble_text, write_memhex

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
#icon_path = r'C:\Users\srira\Desktop\CPU_4bit\tools\ic_chip_2.ico'
icon_path = "./tools/ic_chip.png"

#GUI Icon Change and Taskbar Icon
if os.path.exists(icon_path):
    try:
        root.iconbitmap(icon_path)
    except Exception as e:
        print("Icon error:", e)
else:
    print("Icon file not found:", icon_path)

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

#Assembly Code Compile Function
def compile_program():
    code = editor.get("1.0", "end-1c")

    try:
        words, hex_lines = assemble_text(code)
        write_memhex(hex_lines, "program.hex")

        messagebox.showinfo("Compile Success", "Assembly compiled successfully!")
        console_write("=== COMPILE OUTPUT ===")

        for i, h in enumerate(hex_lines):
            console_write(f"{i:02d}: {h}")

    except Exception as e:
        messagebox.showerror("Compile Error", str(e))
        console_write("[ERROR] " + str(e))

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
                     command=lambda: console_write("[STEP] Not yet connected"))
btn_step.pack(side="right", padx=6, pady=8)

btn_run = tk.Button(toolbar, text="▶ Run", width=9, height=1,
                    bg="#2ecc71", fg="black",
                    activebackground="#27ae60", activeforeground="white",
                    font=("Consolas", 12, "bold"),
                    relief="flat", bd=0,
                    command=lambda: console_write("[RUN] Not yet connected"))
btn_run.pack(side="right", padx=6, pady=8)

btn_clear_ram = tk.Button(toolbar, text="Clear RAM", width=9, height=1,
                          bg="#3c3c3c", fg="white",
                          activebackground="#555", activeforeground="white",
                          font=("Consolas", 12, "bold"),
                          relief="flat", bd=0,
                          command=lambda: console_write("[RAM] Clear not implemented"))
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
        self.text_widget.bind("<KeyRelease>", self.update)

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
    # Validate address
    if not validate_hex_entry(addr_entry, 0xF):
        messagebox.showerror("Invalid Address", "Address must be 0–F (4-bit).")
        return

    # Validate data
    if not validate_hex_entry(data_entry, 0xF):
        messagebox.showerror("Invalid Data", "Data must be 0–F (4-bit).")
        return

    addr = int(addr_entry.get(), 16)
    data = int(data_entry.get(), 16)

    # Update RAM table visually
    ram_cells[addr].config(text=f"{data:X}")

    print(f"[RAM] Updated RAM[{addr:01X}] = {data:01X}")


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
