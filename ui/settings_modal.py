# VERSION: 1.5.0 - Tkinter Original Recovery
import tkinter as tk
from tkinter import messagebox, ttk

class SettingsView:
    """
    Settings UI for EasySTT.
    Uses Tkinter for 100% stability.
    """
    def __init__(self, parent, config):
        self.config = config
        self.win = tk.Toplevel(parent)
        self.win.title("EasySTT - Settings")
        self.win.geometry("400x550")
        self.win.configure(bg="#1e1e1e")
        self.win.grab_set() # Modal
        
        # Build UI
        tk.Label(self.win, text="Settings", font=("Segoe UI", 14, "bold"), fg="white", bg="#1e1e1e").pack(pady=10)
        
        # Provider
        tk.Label(self.win, text="AI Provider:", fg="#aaaaaa", bg="#1e1e1e").pack(pady=(10,0))
        self.provider_var = tk.StringVar(value=self.config.get("provider", "Gemini"))
        self.provider_combo = ttk.Combobox(self.win, textvariable=self.provider_var, values=["Gemini", "OpenAI", "Whisper"], state="readonly")
        self.provider_combo.pack(pady=5)
        
        # API Key
        tk.Label(self.win, text="API Key:", fg="#aaaaaa", bg="#1e1e1e").pack(pady=(10,0))
        self.key_entry = tk.Entry(self.win, width=30, show="*", bg="#2d2d2d", fg="white", borderwidth=0)
        self.key_entry.insert(0, self.config.get("api_key", ""))
        self.key_entry.pack(pady=5)
        
        # Storage
        tk.Label(self.win, text="Storage Path:", fg="#aaaaaa", bg="#1e1e1e").pack(pady=(10,0))
        self.path_var = tk.StringVar(value=self.config.get("storage_path", ""))
        tk.Entry(self.win, textvariable=self.path_var, width=30, bg="#2d2d2d", fg="white", borderwidth=0).pack(pady=5)
        
        # Auto-submit
        self.auto_submit_var = tk.BooleanVar(value=self.config.get("auto_submit", True))
        tk.Checkbutton(self.win, text="Auto-submit for processing", variable=self.auto_submit_var, 
                      bg="#1e1e1e", fg="white", selectcolor="#2d2d2d", activebackground="#1e1e1e").pack(pady=15)
        
        # Buttons
        btn_frame = tk.Frame(self.win, bg="#1e1e1e")
        btn_frame.pack(side="bottom", pady=20)
        
        tk.Button(btn_frame, text="Cancel", command=self.win.destroy, bg="#444444", fg="white", borderwidth=0, padx=15).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Save Settings", command=self.save, bg="#007acc", fg="white", borderwidth=0, padx=15).pack(side="left", padx=5)

    def save(self):
        self.config.set("provider", self.provider_var.get())
        self.config.set("api_key", self.key_entry.get())
        self.config.set("storage_path", self.path_var.get())
        self.config.set("auto_submit", self.auto_submit_var.get())
        
        messagebox.showinfo("Success", "Settings saved successfully!")
        self.win.destroy()
