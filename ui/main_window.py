# VERSION: 2.0.0 - Onboarding & HUD Integration
import tkinter as tk
import queue
from tkinter import ttk, messagebox
import threading
from .settings_window import SettingsWindow
from .hud_window import HUD
from .marketplace_modal import MarketplaceModal


class MainWindow(tk.Tk):
    """
    Primary Control Center for EasySTT v2.0.
    Features:
    - Integrated onboarding system
    - Enhanced HUD with live preview
    - Timer for recording feedback
    """
    def __init__(self, config, engine):
        super().__init__()
        self.config = config
        self.engine = engine
        self.msg_queue = queue.Queue()
        self._timer_seconds = 0
        self._timer_job = None
        self.last_raw_text = ""
        
        # 1. System Config (Frameless)
        self.overrideredirect(True) # Remove borders
        self.geometry("480x520")
        self.configure(bg="#0a0a0a") # Deep Obsidian
        
        # 2. Window Dragging State
        self._drag_data = {"x": 0, "y": 0}
        
        # 2. Child Components
        self.hud = HUD(self, config, engine)
        self.hud.root.withdraw() 
        self.hud.is_visible = False
        
        # 3. UI Construction
        self._build_ui()
        
        # 4. Start Queue Monitor
        self.after(100, self._process_queue)
        
        # 5. Connection status callback
        self.engine.callback_fn = self._engine_callback
        
        
        print("[MainWindow] Control Center Initialized.")

    def _build_ui(self):
        """Build the main interface with a custom title bar."""
        # 0. Custom Title Bar
        self.title_bar = tk.Frame(self, bg="#0a0a0a", height=35)
        self.title_bar.pack(fill="x", side="top")
        self.title_bar.bind("<Button-1>", self._start_drag)
        self.title_bar.bind("<B1-Motion>", self._do_drag)

        # App Icon/Title in Title Bar
        tk.Label(self.title_bar, text=" ✦ EasySTT", font=("Segoe UI", 9, "bold"),
                 bg="#0a0a0a", fg="#ffffff").pack(side="left", padx=10)

        # Window Controls
        tk.Button(self.title_bar, text="✕", font=("Segoe UI", 8),
                  bg="#0a0a0a", fg="#666666", borderwidth=0, cursor="hand2",
                  activebackground="#ff5252", activeforeground="white",
                  command=self.destroy, padx=10).pack(side="right")
        
        tk.Button(self.title_bar, text="─", font=("Segoe UI", 8),
                  bg="#0a0a0a", fg="#666666", borderwidth=0, cursor="hand2",
                  activebackground="#333333", activeforeground="white",
                  command=self._minimize_window, padx=10).pack(side="right")

        # 1. Tabbed Interface (Obsidian Style)
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TNotebook", background="#0a0a0a", borderwidth=0)
        style.configure("TNotebook.Tab", background="#1a1a1a", foreground="#888888", 
                        padding=[15, 5], font=("Segoe UI", 8, "bold"), borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", "#0a0a0a")], 
                  foreground=[("selected", "#ffffff")])

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=2, pady=(0, 2))
        
        # --- TAB 1: TRANSCRIPTION ---
        self.transcription_frame = tk.Frame(self.notebook, bg="#0a0a0a")
        self.notebook.add(self.transcription_frame, text="   TRANSCRIBE   ")
        
        # --- TAB 2: PLUGINS & LEARNING ---
        self.control_frame = tk.Frame(self.notebook, bg="#0a0a0a")
        self.notebook.add(self.control_frame, text="   ECOSYSTEM   ")
        
        # --- TAB 3: PRIVACY & AUDIT ---
        self.privacy_frame = tk.Frame(self.notebook, bg="#0a0a0a")
        self.notebook.add(self.privacy_frame, text="   PRIVACY   ")
        
        self._build_transcription_tab()
        self._build_control_tab()
        self._build_privacy_tab()
        self._build_footer()

    def _build_transcription_tab(self):
        parent = self.transcription_frame
        # ... (Previous transcription UI logic moved here)
        main_container = tk.Frame(parent, bg="#1e1e1e")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header
        header = tk.Frame(main_container, bg="#1e1e1e")
        header.pack(fill="x", pady=(0, 10))
        
        tk.Label(header, text="EasySTT", font=("Segoe UI", 16, "bold"), 
                 bg="#1e1e1e", fg="#ffffff").pack(side="left")
        
        # Status
        self.status_label = tk.Label(header, text="Ready", font=("Segoe UI", 9), 
                                    bg="#0a0a0a", fg="#444444")
        self.status_label.pack(side="right", pady=5)
        
        self.timer_label = tk.Label(header, text="", font=("Segoe UI", 9, "bold"),
                                   bg="#0a0a0a", fg="#ff5252")
        self.timer_label.pack(side="right", padx=10)
        
        # Interim Result Label (Live Preview)
        self.interim_label = tk.Label(main_container, text="", font=("Segoe UI", 10, "italic"),
                                     bg="#1e1e1e", fg="#00bcd4")
        self.interim_label.pack(fill="x", pady=(0, 5))

        # Result Area
        result_frame = tk.Frame(main_container, bg="#2d2d2d", bd=1)
        result_frame.pack(fill="both", expand=True)
        
        # Styled Text Container with Tags for Confidence
        self.result_text = tk.Text(
            result_frame, wrap="word", bg="#2d2d2d", fg="white",
            font=("Segoe UI", 11), borderwidth=0, padx=10, pady=10,
            undo=True, height=8
        )
        self.result_text.pack(fill="both", expand=True)
        
        # Confidence Tags
        self.result_text.tag_configure("high_conf", foreground="#ffffff")
        self.result_text.tag_configure("med_conf", foreground="#e0e0e0")
        self.result_text.tag_configure("low_conf", foreground="#ffb74d") # Soft orange
        self.result_text.tag_configure("ghost", foreground="#666666", font=("Segoe UI", 11, "italic"))
        
        # Correction Actions
        self.learn_frame = tk.Frame(result_frame, bg="#2d2d2d")
        self.learn_frame.pack(fill="x", pady=(5, 5), padx=10)
        
        self.token_label = tk.Label(self.learn_frame, text="", font=("Segoe UI", 8),
                                   bg="#2d2d2d", fg="#666666")
        self.token_label.pack(side="left")

        self.learn_btn = tk.Button(
            self.learn_frame, text="✨ TEACH AI", command=self._learn_correction,
            bg="#4caf50", fg="white", font=("Segoe UI", 8, "bold"), borderwidth=0, padx=8
        )
        self.learn_btn.pack(side="right")
        
        action_frame = tk.Frame(main_container, bg="#1e1e1e")
        action_frame.pack(side="bottom", pady=15)
        
        # Main Button
        self.mic_btn = tk.Button(
            action_frame, text="🎙 RECORD", command=self.toggle_mic,
            bg="#007acc", fg="white", font=("Segoe UI", 12, "bold"),
            borderwidth=0, cursor="hand2", padx=20, pady=10
        )
        self.mic_btn.pack()
        
        # Navigation Links
        nav_frame = tk.Frame(action_frame, bg="#1e1e1e", pady=10)
        nav_frame.pack()
        
        
        tk.Button(
            nav_frame, text="🏙 Settings", command=self.open_settings,
            bg="#0a0a0a", fg="#666666", font=("Segoe UI", 9), borderwidth=0, padx=10, pady=5, cursor="hand2"
        ).pack(side="left")

        tk.Button(
            nav_frame, text="📖 Vocabulary", command=self._open_vocabulary,
            bg="#0a0a0a", fg="#666666", font=("Segoe UI", 9), borderwidth=0, padx=10, pady=5, cursor="hand2"
        ).pack(side="left")

    def _build_footer(self):
        """Build the app footer with HUD toggle and status."""
        footer = tk.Frame(self, bg="#2d2d2d", height=40)
        footer.pack(side="bottom", fill="x")
        
        # HUD Toggle
        self.floater_btn = tk.Button(
            footer, text="🔘 HUD", font=("Segoe UI", 8, "bold"),
            bg="#2d2d2d", fg="#666666", borderwidth=0, cursor="hand2",
            command=self.toggle_floater
        )
        self.floater_btn.pack(side="right", padx=10, pady=5)
        
        # Version
        tk.Label(footer, text="EasySTT v2.0 • Pro Active", font=("Segoe UI", 8),
                 bg="#2d2d2d", fg="#555555").pack(side="left", padx=10)

    def _build_control_tab(self):
        """Build the Plugins & Learning management tab."""
        parent = self.control_frame
        container = tk.Frame(parent, bg="#1e1e1e", padx=20, pady=20)
        container.pack(fill="both", expand=True)
        
        # 1. Plugin Section
        tk.Label(container, text="🧩 Active Plugins", 
                 font=("Segoe UI", 12, "bold"), bg="#1e1e1e", fg="white").pack(anchor="w")
        
        self.plugin_list_frame = tk.Frame(container, bg="#1e1e1e", pady=10)
        self.plugin_list_frame.pack(fill="x")
        
        # Marketplace Button
        self.market_btn = tk.Button(
            container, text=" 🛍️ BROWSE MARKETPLACE ",
            font=("Segoe UI", 10, "bold"),
            bg="#2c3e50", fg="white",
            activebackground="#34495e", activeforeground="white",
            borderwidth=0, cursor="hand2", padx=10, pady=8,
            command=self._open_marketplace
        )
        self.market_btn.pack(pady=20)
        
        # 2. Learning Stats Section
        tk.Label(container, text="🧠 AI Learning Stats", 
                 font=("Segoe UI", 12, "bold"), bg="#1e1e1e", fg="white").pack(anchor="w", pady=(10, 5))
        
        self.stats_label = tk.Label(container, text="Loading stats...", 
                                   font=("Segoe UI", 10), bg="#1e1e1e", fg="#aaaaaa", justify="left")
        self.stats_label.pack(anchor="w")

        # 3. Agent A2A Bridge Section
        a2a_frame = tk.Frame(container, bg="#1a1a1a", pady=10, padx=15)
        a2a_frame.pack(fill="x", pady=20)
        
        tk.Label(a2a_frame, text="🤖 Agent Ecosystem (A2A Bridge)", 
                 font=("Segoe UI", 9, "bold"), bg="#1a1a1a", fg="#00ccff").pack(anchor="w")
        
        a2a_url = f"http://localhost:{self.engine.a2a.port}"
        tk.Label(a2a_frame, text=f"Local API: {a2a_url}", 
                 font=("Consolas", 8), bg="#1a1a1a", fg="#888888").pack(anchor="w")
        
        state_text = "🟢 ACTIVE" if self.engine.a2a.enabled else "⚪ DISABLED"
        tk.Label(a2a_frame, text=state_text, font=("Segoe UI", 8, "bold"), 
                 bg="#1a1a1a", fg="#4caf50").pack(anchor="w", pady=(5, 0))

        # Refresh
        self._update_ecosystem_view()

    def _update_ecosystem_view(self):
        """Update plugin list and learning stats from the engine."""
        try:
            # Clear existing plugin labels
            for widget in self.plugin_list_frame.winfo_children():
                widget.destroy()
            
            # Get plugins
            plugins = self.engine.plugins.discover_plugins()
            if not plugins:
                tk.Label(self.plugin_list_frame, text="No plugins active.", 
                         bg="#1e1e1e", fg="#666666").pack(anchor="w")
            else:
                for p in plugins:
                    tk.Label(self.plugin_list_frame, text=f"✅ {p.name} (v{p.version})", 
                             bg="#1e1e1e", fg="#4caf50", font=("Segoe UI", 10)).pack(anchor="w")
            
            # Stats
            stats = self.engine.vocab.get_stats()
            stats_text = (
                f"• Total Learned Words: {stats['total_words']}\n"
                f"• Corrections Processed: {stats['total_corrections']}\n"
                f"• Knowledge Base: {os.path.basename(stats['db_path'])}"
            )
            self.stats_label.config(text=stats_text)
            
        except Exception as e:
            print(f"Error updating ecosystem view: {e}")

    def _open_marketplace(self):
        """Open the Marketplace discovery modal."""
        MarketplaceModal(self, self.engine)

    def _build_privacy_tab(self):
        """Build the Privacy & Audit management tab."""
        parent = self.privacy_frame
        container = tk.Frame(parent, bg="#1e1e1e", padx=20, pady=20)
        container.pack(fill="both", expand=True)
        
        tk.Label(container, text="🛡️ Transcription Audit Log", 
                 font=("Segoe UI", 12, "bold"), bg="#1e1e1e", fg="white").pack(anchor="w")
        
        tk.Label(container, text="Review how your voice data was processed.", 
                 font=("Segoe UI", 9), bg="#1e1e1e", fg="#666666").pack(anchor="w", pady=(0, 10))

        # Audit List (Scrollable)
        list_container = tk.Frame(container, bg="#1a1a1a")
        list_container.pack(fill="both", expand=True)
        
        self.audit_scroll = tk.Scrollbar(list_container)
        self.audit_scroll.pack(side="right", fill="y")
        
        self.audit_list = tk.Listbox(
            list_container, bg="#1a1a1a", fg="#aaaaaa", borderwidth=0,
            font=("Consolas", 9), yscrollcommand=self.audit_scroll.set,
            highlightthickness=0, selectbackground="#333333"
        )
        self.audit_list.pack(fill="both", expand=True)
        self.audit_scroll.config(command=self.audit_list.yview)
        
        # Refresh Button
        tk.Button(
            container, text=" 🔄 REFRESH LOG ",
            font=("Segoe UI", 8, "bold"),
            bg="#2c3e50", fg="white", borderwidth=0, cursor="hand2",
            command=self._update_privacy_view
        ).pack(pady=10)
        
        self._update_privacy_view()

    def _update_privacy_view(self):
        """Fetch and display recent audit logs."""
        try:
            self.audit_list.delete(0, tk.END)
            logs = self.engine.privacy.get_audit_summary(limit=20)
            
            for log in logs:
                ts = log['timestamp'].split()[1] # Just time
                mode = log['mode'].upper()
                conf = f"{int(log['confidence']*100)}%"
                dur = f"{log['duration_seconds']:.1f}s"
                
                indicator = "🟢" if log['mode'] == 'local' else "🔵"
                entry = f"{indicator} [{ts}] {mode} | Conf: {conf} | Dur: {dur}"
                self.audit_list.insert(tk.END, entry)
                
        except Exception as e:
            self.audit_list.insert(tk.END, f"Error loading logs: {e}")

    def toggle_mic(self):
        """Toggle recording state."""
        if not self.engine.is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        """Start recording audio."""
        self.mic_btn.config(text="🛑 STOP", bg="#d32f2f")
        self.status_label.config(text="🔴 Recording...", fg="#ff5252")
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", "Listening...")
        self.result_text.config(state="disabled")
        
        # Start timer
        self._timer_seconds = 0
        self._update_timer()
        
        # Update HUD
        if self.hud.is_visible:
            self.hud.start_recording_mode()
        
        self.engine.start_recording(self._engine_callback)

    def _stop_recording(self):
        """Stop recording and process."""
        self.mic_btn.config(text="⏳", bg="#ff9800", state="disabled")
        self.status_label.config(text="⏳ Processing...", fg="#ff9800")
        
        # Stop timer
        if self._timer_job:
            self.after_cancel(self._timer_job)
            self._timer_job = None
        self.timer_label.config(text="")
        
        # Update HUD
        if self.hud.is_visible:
            self.hud.stop_recording_mode()
        
        self.engine.stop_recording()

    def _update_timer(self):
        """Update recording timer."""
        mins = self._timer_seconds // 60
        secs = self._timer_seconds % 60
        self.timer_label.config(text=f"⏱ {mins}:{secs:02d}")
        
        # Also update HUD timer
        if self.hud.is_visible:
            self.hud.update_timer(self._timer_seconds)
        
        self._timer_seconds += 1
        self._timer_job = self.after(1000, self._update_timer)

    def _engine_callback(self, data):
        """Called from background engine threads."""
        self.msg_queue.put(data)

    def _process_queue(self):
        """Process messages from the engine."""
        try:
            while True:
                data = self.msg_queue.get_nowait()
                
                if data.get("type") == "connection":
                    # Connection status update
                    online = data.get("online", False)
                    if self.hud.is_visible:
                        self.hud.update_connection(online)
                
                elif data.get("type") == "interim":
                    text = data.get("text", "")
                    self.interim_label.config(text=text[-100:] if len(text) > 100 else text)
                    if self.hud.is_visible:
                        self.hud.update_interim(text)
                
                elif data.get("type") == "final":
                    text = data.get("text", "")
                    warning = data.get("warning")
                    error = data.get("error")
                    self.interim_label.config(text="")
                    
                    if text:
                        self.result_text.config(state="normal")
                        self.result_text.delete("1.0", tk.END)
                        
                        # 1. Confidence-based Insertion
                        conf = data.get("confidence", 1.0)
                        tag = "high_conf"
                        if conf < 0.6: tag = "low_conf"
                        elif conf < 0.85: tag = "med_conf"
                        
                        self.result_text.insert("1.0", text, tag)
                        self.last_raw_text = text
                        
                        # 2. Update Smart Status
                        is_spec = data.get("is_specialized", False)
                        self.hud.update_smart_status(is_spec)
                        
                        # 3. Update Labels & Control Center
                        # 3. Update Metrics (Conditional)
                        conf_percent = int(conf*100)
                        tokens = data.get("tokens", 0)
                        
                        # Only show confidence if enabled or if we have an API key (meaning we might be using cloud)
                        show_conf = self.config.get("show_confidence", False) or bool(self.config.get("keys", {}).get("Gemini") or self.config.get("keys", {}).get("OpenAI"))
                        
                        status_text = f"Tokens: {tokens}"
                        if show_conf:
                            status_text = f"Confidence: {conf_percent}% | {status_text}"
                        
                        self.status_label.config(text=status_text, fg="#4caf50")
                        self.token_label.config(text=f"Est. Tokens: {tokens}")
                        self._update_ecosystem_view() 

                        # 4. Clipboard & Feedback
                        if self.config.get("auto_clipboard", True):
                            import pyperclip
                            pyperclip.copy(text)
                        
                        if warning:
                            self.status_label.config(text=f"⚠ {warning}", fg="#ff9800")
                        else:
                            self.status_label.config(text="✅ Copied to clipboard!", fg="#4caf50")
                        
                        if self.hud.is_visible:
                            self.hud.show_final(text, success=True)
                    else:
                        error_text = error if error else "No speech detected"
                        self.status_label.config(text=f"❌ {error_text}", fg="#f44336")
                        if self.hud.is_visible:
                            self.hud.show_final("", success=False)
                    
                    self.mic_btn.config(text="🎙 RECORD", bg="#007acc", state="normal")
                    self.timer_label.config(text="")

        except queue.Empty:
            pass
        self.after(100, self._process_queue)

    def open_settings(self):
        """Open settings window."""
        SettingsWindow(self.config)

    def _open_vocabulary(self):
        """Open vocabulary viewer via settings."""
        settings = SettingsWindow(self.config)
        settings.manage_vocabulary()

    def _learn_correction(self):
        """Trigger learning from the current text in the result box."""
        current_text = self.result_text.get("1.0", tk.END).strip()
        if current_text and current_text != self.last_raw_text:
            self.engine.learn_correction(self.last_raw_text, current_text)
            self.status_label.config(text="✨ AI Learned from correction!", fg="#4caf50")
            self.last_raw_text = current_text
            # Visual feedback
            self.learn_btn.config(state="disabled", text="LEARNED ✓")
            self.after(2000, lambda: self.learn_btn.config(state="normal", text="✨ TEACH AI"))
        else:
            messagebox.showinfo("EasySTT", "No changes detected to learn from.")

    def toggle_floater(self):
        """Toggle the floating HUD visibility."""
        if self.hud.is_visible:
            self.hud.root.withdraw()
            self.hud.is_visible = False
            self.floater_btn.config(fg="#666666")
        else:
            self.hud.root.deiconify()
            self.hud.is_visible = True
            self.floater_btn.config(fg="#007acc")
            
            # Sync HUD state
            if self.engine.is_recording:
                self.hud.start_recording_mode()
            elif self.engine.is_processing:
                self.hud.stop_recording_mode()
            else:
                self.hud.update_status("READY")
            
            self.hud.update_connection(self.engine.api_status)

    def _start_drag(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _do_drag(self, event):
        x = self.winfo_x() - self._drag_data["x"] + event.x
        y = self.winfo_y() - self._drag_data["y"] + event.y
        self.geometry(f"+{x}+{y}")

    def _minimize_window(self):
        self.withdraw()
        self.overrideredirect(False)
        self.iconify()
        self.after(0, lambda: self.overrideredirect(True))
