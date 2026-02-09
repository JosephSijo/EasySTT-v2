# VERSION: 2.0.0 - Enhanced UI with Onboarding Integration
import tkinter as tk
from tkinter import messagebox, ttk, filedialog

class SettingsWindow:
    """
    Independent Settings UI for EasySTT. 
    Detached from Main Window for modularity.
    """
    def __init__(self, config):
        self.config = config
        self.win = tk.Toplevel()
        self.win.title("EasySTT - Global Settings")
        self.win.geometry("450x650")
        self.win.configure(bg="#1c1c1c")
        
        # Center the window
        self.win.update_idletasks()
        width = 450
        height = 650
        x = (self.win.winfo_screenwidth() // 2) - (width // 2)
        y = (self.win.winfo_screenheight() // 2) - (height // 2)
        self.win.geometry('{}x{}+{}+{}'.format(width, height, x, y))

        # Build UI
        tk.Label(self.win, text="⚙ SETTINGS", font=("Segoe UI", 16, "bold"), fg="white", bg="#1c1c1c").pack(pady=20)
        
        # --- Provider & Keys ---
        tk.Label(self.win, text="AI PROVIDER", font=("Segoe UI", 8, "bold"), fg="#777777", bg="#1c1c1c").pack(pady=(10,0))
        self.provider_var = tk.StringVar(value=self.config.get("provider", "Gemini"))
        providers = list(self.config.get("keys", {}).keys())
        if not providers: providers = ["Gemini", "OpenAI", "Anthropic", "DeepSeek", "Mistral", "Groq"]
        self.provider_combo = ttk.Combobox(self.win, textvariable=self.provider_var, values=providers, state="readonly")
        self.provider_combo.pack(pady=5)
        self.provider_combo.bind("<<ComboboxSelected>>", self.on_provider_change)
        
        tk.Label(self.win, text="API KEY", font=("Segoe UI", 8, "bold"), fg="#777777", bg="#1c1c1c").pack(pady=(15,0))
        self.key_entry = tk.Entry(self.win, width=35, show="*", bg="#2d2d2d", fg="white", borderwidth=0, font=("Consolas", 10))
        # Load the key for the current provider
        keys = self.config.get("keys", {})
        self.key_entry.insert(0, keys.get(self.provider_var.get(), ""))
        self.key_entry.pack(pady=5, ipady=5)
        
        # --- Engine Settings ---
        tk.Label(self.win, text="LANGUAGE", font=("Segoe UI", 8, "bold"), fg="#777777", bg="#1c1c1c").pack(pady=(15,0))
        self.lang_var = tk.StringVar(value=self.config.get("language", "en"))
        self.lang_combo = ttk.Combobox(self.win, textvariable=self.lang_var, values=["en", "hi", "fr", "es", "de", "it", "jp", "auto"], state="readonly")
        self.lang_combo.pack(pady=5)

        tk.Label(self.win, text="GLOBAL HOTKEY", font=("Segoe UI", 8, "bold"), fg="#777777", bg="#1c1c1c").pack(pady=(15,0))
        self.shortcut_var = tk.StringVar(value=self.config.get("shortcut", "ctrl+alt+r"))
        tk.Entry(self.win, textvariable=self.shortcut_var, width=35, bg="#2d2d2d", fg="white", borderwidth=0).pack(pady=5, ipady=3)
        tk.Label(self.win, text="(Restart app to apply hotkey changes)", font=("Segoe UI", 7), fg="#666666", bg="#1c1c1c").pack()

        # --- Storage & Cleanup ---
        tk.Label(self.win, text="STORAGE & CLEANUP", font=("Segoe UI", 8, "bold"), fg="#777777", bg="#1c1c1c").pack(pady=(15,0))
        
        path_frame = tk.Frame(self.win, bg="#1c1c1c")
        path_frame.pack(fill="x", padx=40)
        
        self.storage_var = tk.StringVar(value=self.config.get("storage_path", ""))
        tk.Entry(path_frame, textvariable=self.storage_var, bg="#2d2d2d", fg="#aaaaaa", borderwidth=0, font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True, ipady=3)
        tk.Button(path_frame, text="📁", command=self.browse_storage, bg="#333333", fg="white", borderwidth=0).pack(side="right", padx=(5,0))

        cleanup_frame = tk.Frame(self.win, bg="#1c1c1c")
        cleanup_frame.pack(pady=10)
        tk.Label(cleanup_frame, text="Clear data after ", font=("Segoe UI", 9), fg="white", bg="#1c1c1c").pack(side="left")
        self.clear_days_var = tk.StringVar(value=str(self.config.get("auto_clear_days", 30)))
        tk.Entry(cleanup_frame, textvariable=self.clear_days_var, width=4, bg="#2d2d2d", fg="white", borderwidth=0, justify="center").pack(side="left", padx=5)
        tk.Label(cleanup_frame, text=" days", font=("Segoe UI", 9), fg="white", bg="#1c1c1c").pack(side="left")

        # --- Toggles ---
        toggle_frame = tk.Frame(self.win, bg="#1c1c1c")
        toggle_frame.pack(pady=20)

        self.auto_submit_var = tk.BooleanVar(value=self.config.get("auto_submit", True))
        tk.Checkbutton(toggle_frame, text="Auto-Submit to AI", variable=self.auto_submit_var, 
                      bg="#1c1c1c", fg="white", selectcolor="#2d2d2d", activebackground="#1c1c1c", 
                      activeforeground="white", font=("Segoe UI", 10)).pack(anchor="w")
        
        self.refinement_var = tk.BooleanVar(value=self.config.get("use_ai_refinement", True))
        tk.Checkbutton(toggle_frame, text="Enable AI Refinement", variable=self.refinement_var, 
                      bg="#1c1c1c", fg="white", selectcolor="#2d2d2d", activebackground="#1c1c1c", 
                      activeforeground="white", font=("Segoe UI", 10)).pack(anchor="w")

        # --- Personalization Section ---
        tk.Label(self.win, text="PERSONALIZATION", font=("Segoe UI", 8, "bold"), fg="#777777", bg="#1c1c1c").pack(pady=(15,0))
        
        p_frame = tk.Frame(self.win, bg="#1c1c1c")
        p_frame.pack(pady=10)
        
        tk.Button(p_frame, text="🔊 RETRAIN VOICE", command=self.retrain_voice,
                  bg="#333333", fg="#4caf50", borderwidth=0, padx=15, pady=5, font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)
        
        tk.Button(p_frame, text="📖 MANAGE WORDS", command=self.manage_vocabulary,
                  bg="#333333", fg="#00BCD4", borderwidth=0, padx=15, pady=5, font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)

        # Footer
        btn_frame = tk.Frame(self.win, bg="#1c1c1c")
        btn_frame.pack(side="bottom", pady=30)
        
        tk.Button(btn_frame, text="CANCEL", command=self.win.destroy, 
                  bg="#333333", fg="white", borderwidth=0, padx=20, pady=8, font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)
        
        tk.Button(btn_frame, text="SAVE CHANGES", command=self.save, 
                  bg="#007acc", fg="white", borderwidth=0, padx=20, pady=8, font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)

    def on_provider_change(self, event):
        """Update key entry when provider changes."""
        provider = self.provider_var.get()
        keys = self.config.get("keys", {})
        self.key_entry.delete(0, tk.END)
        self.key_entry.insert(0, keys.get(provider, ""))

    def save(self):
        # Update config fields
        provider = self.provider_var.get()
        self.config.set("provider", provider)
        
        # Save key to the nested dictionary
        keys = self.config.get("keys", {})
        keys[provider] = self.key_entry.get()
        self.config.set("keys", keys)
        
        self.config.set("language", self.lang_var.get())
        self.config.set("shortcut", self.shortcut_var.get())
        self.config.set("auto_submit", self.auto_submit_var.get())
        self.config.set("use_ai_refinement", self.refinement_var.get())
        self.config.set("storage_path", self.storage_var.get())
        
        try:
            self.config.set("auto_clear_days", int(self.clear_days_var.get()))
        except ValueError:
            pass
        
        # Force a persistence check
        self.config.save_config(self.config.config)
        
        messagebox.showinfo("EasySTT", "Settings updated successfully!\nPlease restart app to apply new hotkey.")
        self.win.destroy()

    def browse_storage(self):
        """Browser for storage path."""
        path = filedialog.askdirectory(initialdir=self.storage_var.get())
        if path:
            self.storage_var.set(path)

    def retrain_voice(self):
        """Opens the onboarding window for voice training."""
        # Signal parent to open onboarding (will be handled by MainWindow)
        if hasattr(self, 'on_retrain_callback') and self.on_retrain_callback:
            self.win.destroy()
            self.on_retrain_callback()
        else:
            messagebox.showinfo("EasySTT", "Please use the onboarding option from the main application.")

    def manage_vocabulary(self):
        """Opens vocabulary management window."""
        from core.personalization import PersonalizationManager
        import os
        
        pm = PersonalizationManager()
        all_terms = pm.get_all_terms()
        
        # Create vocabulary viewer window
        vocab_win = tk.Toplevel(self.win)
        vocab_win.title("Vocabulary Management")
        vocab_win.geometry("400x500")
        vocab_win.configure(bg="#1c1c1c")
        
        tk.Label(vocab_win, text="📖 Learned Vocabulary", font=("Segoe UI", 14, "bold"), fg="white", bg="#1c1c1c").pack(pady=15)
        
        for category, terms in all_terms.items():
            if not terms:
                continue
            
            frame = tk.Frame(vocab_win, bg="#2d2d2d", padx=10, pady=10)
            frame.pack(fill="x", padx=20, pady=5)
            
            tk.Label(frame, text=category.upper(), font=("Segoe UI", 10, "bold"), fg="#00bcd4", bg="#2d2d2d").pack(anchor="w")
            
            terms_text = ", ".join(terms) if terms else "(empty)"
            tk.Label(frame, text=terms_text, font=("Segoe UI", 9), fg="#aaaaaa", bg="#2d2d2d", wraplength=350).pack(anchor="w", pady=(5, 0))
        
        # Clear button
        def clear_all():
            if messagebox.askyesno("Confirm", "Clear all learned vocabulary?"):
                for cat in ["names", "jargon", "phrases"]:
                    pm.clear_category(cat)
                vocab_win.destroy()
                messagebox.showinfo("EasySTT", "Vocabulary cleared!")
        
        tk.Button(vocab_win, text="🗑 CLEAR ALL", command=clear_all, bg="#ff5252", fg="white", borderwidth=0, padx=15, pady=8).pack(pady=20)
    
    def set_retrain_callback(self, callback):
        """Set callback for retrain button."""
        self.on_retrain_callback = callback
