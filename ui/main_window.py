# VERSION: 2.0.0 - Onboarding & HUD Integration
import tkinter as tk
import queue
from tkinter import ttk, messagebox
import threading
import os
from .settings_window import SettingsWindow
from .hud_window import HUD
from .marketplace_modal import MarketplaceModal
from core.win32_utils import apply_window_masking, enable_acrylic_effect, set_window_shadow


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
        
        # 1. System Config (Premium Dimensions)
        self.overrideredirect(True) # Remove borders
        self.geometry("940x650")
        self.configure(bg="#101a22") # Deep Space
        
        # 2. Window Dragging State
        self._drag_data = {"x": 0, "y": 0}
        
        # 2. Child Components
        self.hud = HUD(self, config, engine)
        self.hud.root.withdraw() 
        self.hud.is_visible = False
        
        # 3. UI Construction
        self._build_ui()
        
        # 4. Advanced Windows Customization (Antigravity Framework)
        self.after(100, self._apply_antigravity_features)
        
        # 5. Start Queue Monitor
        self.after(100, self._process_queue)
        
        # 6. Connection status callback
        self.engine.callback_fn = self._engine_callback
        
        print("[MainWindow] Control Center Initialized.")

    def _apply_antigravity_features(self):
        """Apply Win32 masking, acrylic, and shadow effects."""
        hwnd = self.winfo_id()
        apply_window_masking(hwnd, radius=30)
        enable_acrylic_effect(hwnd, theme="dark")
        set_window_shadow(hwnd, enabled=True)

    def _build_ui(self):
        """Build the main interface with a sidebar-based layout."""
        # 0. Custom Title Bar
        self.title_bar = tk.Frame(self, bg="#111518", height=32)
        self.title_bar.pack(fill="x", side="top")
        self.title_bar.bind("<Button-1>", self._start_drag)
        self.title_bar.bind("<B1-Motion>", self._do_drag)

        # App Icon in Title Bar
        tk.Label(self.title_bar, text="✦ EasySTT v2.0", font=("Segoe UI Semibold", 9),
                 bg="#111518", fg="#888888").pack(side="left", padx=15)

        # Window Controls
        tk.Button(self.title_bar, text="✕", font=("Segoe UI", 9),
                  bg="#111518", fg="#666666", borderwidth=0, cursor="hand2",
                  activebackground="#e81123", activeforeground="white",
                  command=self.destroy, padx=12).pack(side="right")
        
        tk.Button(self.title_bar, text="─", font=("Segoe UI", 9),
                  bg="#111518", fg="#666666", borderwidth=0, cursor="hand2",
                  activebackground="#333333", activeforeground="white",
                  command=self._minimize_window, padx=12).pack(side="right")

        # Layout Main Containers
        self.main_container = tk.Frame(self, bg="#101a22")
        self.main_container.pack(fill="both", expand=True)

        # 1. Sidebar (Obsidian)
        self.sidebar = tk.Frame(self.main_container, bg="#111518", width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Sidebar Header
        logo_frame = tk.Frame(self.sidebar, bg="#111518", pady=30)
        logo_frame.pack(fill="x")
        tk.Label(logo_frame, text="EasySTT", font=("Segoe UI", 18, "bold"),
                 bg="#111518", fg="#ffffff").pack()
        tk.Label(logo_frame, text="PROFESSIONAL", font=("Segoe UI", 7, "bold"),
                 bg="#111518", fg="#1392ec").pack()

        # Navigation Buttons
        self.nav_buttons = {}
        nav_items = [
            ("🏠 HOME", "home"),
            ("🧩 ECOSYSTEM", "ecosystem"),
            ("🛡️ PRIVACY", "privacy"),
            ("🐒 ABOUT", "about")
        ]
        
        for text, key in nav_items:
            btn = tk.Button(
                self.sidebar, text=f"  {text}", font=("Segoe UI Semibold", 10),
                bg="#111518", fg="#888888", borderwidth=0, anchor="w",
                padx=25, pady=12, cursor="hand2", activebackground="#1a1f24",
                activeforeground="#ffffff", command=lambda k=key: self._switch_tab(k)
            )
            btn.pack(fill="x")
            self.nav_buttons[key] = btn

        # Sidebar Footer
        self.sidebar_footer = tk.Frame(self.sidebar, bg="#111518", pady=20)
        self.sidebar_footer.pack(side="bottom", fill="x")
        
        tk.Button(
            self.sidebar_footer, text="⚙️ SETTINGS", font=("Segoe UI", 9, "bold"),
            bg="#111518", fg="#666666", borderwidth=0, cursor="hand2",
            padx=25, command=self.open_settings
        ).pack(side="left")

        # 2. Content Area
        self.content_area = tk.Frame(self.main_container, bg="#101a22")
        self.content_area.pack(side="right", fill="both", expand=True)

        # Initialize Frames
        self.frames = {}
        self.frames["home"] = tk.Frame(self.content_area, bg="#101a22")
        self.frames["ecosystem"] = tk.Frame(self.content_area, bg="#101a22")
        self.frames["privacy"] = tk.Frame(self.content_area, bg="#101a22")
        self.frames["about"] = tk.Frame(self.content_area, bg="#101a22")

        for frame in self.frames.values():
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Build Sub-Views
        self._build_home_view()
        self._build_ecosystem_view()
        self._build_privacy_view()
        self._build_about_view()

        # Set default view
        self._switch_tab("home")

    def _switch_tab(self, key):
        """Switch between sidebar tabs."""
        # Update buttons
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.config(bg="#1a1f24", fg="#ffffff")
            else:
                btn.config(bg="#111518", fg="#888888")
        
        # Lift frame
        self.frames[key].tkraise()

    def _build_home_view(self):
        """Build the redesigned Home Dashboard."""
        parent = self.frames["home"]
        container = tk.Frame(parent, bg="#101a22", padx=40, pady=40)
        container.pack(fill="both", expand=True)

        # Hero Section
        hero_frame = tk.Frame(container, bg="#101a22")
        hero_frame.pack(pady=(40, 60))

        tk.Label(hero_frame, text="Ready to capture your thoughts?", 
                 font=("Segoe UI Variable Display", 24, "bold"),
                 bg="#101a22", fg="#ffffff").pack()
        
        tk.Label(hero_frame, text="Press the button below or use Ctrl+Alt+R to start.", 
                 font=("Segoe UI", 11), bg="#101a22", fg="#666666").pack(pady=5)

        # Large Record Button
        self.record_circle = tk.Canvas(container, width=120, height=120, 
                                      bg="#101a22", highlightthickness=0)
        self.record_circle.pack()
        
        self._btn_circle = self.record_circle.create_oval(10, 10, 110, 110, 
                                                        fill="#1392ec", outline="")
        self.record_circle.create_text(60, 60, text="🎙️", font=("Segoe UI", 32), fill="white")
        
        self.record_circle.bind("<Button-1>", lambda e: self.toggle_mic())
        self.record_circle.config(cursor="hand2")

        # Stats / Health Row
        stats_frame = tk.Frame(container, bg="#101a22")
        stats_frame.pack(side="bottom", fill="x", pady=20)

        for label, val in [("LOCAL ENGINE", "V2.0-ULTRA"), ("UPTIME", "4.2h"), ("ACCURACY", "98.4%")]:
            card = tk.Frame(stats_frame, bg="#111518", padx=15, pady=10)
            card.pack(side="left", expand=True, padx=5)
            tk.Label(card, text=label, font=("Segoe UI", 7, "bold"), 
                     bg="#111518", fg="#1392ec").pack(anchor="w")
            tk.Label(card, text=val, font=("Segoe UI Semibold", 10), 
                     bg="#111518", fg="#ffffff").pack(anchor="w")

        # 4. Transcription Area (Now integrated)
        result_container = tk.Frame(container, bg="#101a22")
        result_container.pack(fill="both", expand=True, pady=20)
        
        # Status & Timer Header (Subtle)
        status_header = tk.Frame(result_container, bg="#101a22")
        status_header.pack(fill="x")
        
        self.status_label = tk.Label(status_header, text="READY", font=("Segoe UI", 8, "bold"),
                                    bg="#101a22", fg="#444444")
        self.status_label.pack(side="left")
        
        self.timer_label = tk.Label(status_header, text="", font=("Segoe UI", 8, "bold"),
                                   bg="#101a22", fg="#ff5252")
        self.timer_label.pack(side="right")

        # Result Text Box (The main transcription target)
        self.result_text = tk.Text(
            result_container, wrap="word", bg="#111518", fg="white",
            font=("Segoe UI", 11), borderwidth=0, padx=20, pady=20,
            undo=True, height=8, insertbackground="white"
        )
        self.result_text.pack(fill="both", expand=True, pady=10)
        
        # Interim Result (Live Preview)
        self.interim_label = tk.Label(result_container, text="", font=("Segoe UI", 10, "italic"),
                                     bg="#101a22", fg="#1392ec")
        self.interim_label.pack(fill="x")

        # Confidence Tags (Required for engine callbacks)
        self.result_text.tag_configure("high_conf", foreground="#ffffff")
        self.result_text.tag_configure("med_conf", foreground="#e0e0e0")
        self.result_text.tag_configure("low_conf", foreground="#ffb74d")
        
        # Interaction Buttons
        actions_frame = tk.Frame(result_container, bg="#101a22")
        actions_frame.pack(fill="x", pady=10)
        
        self.learn_btn = tk.Button(
            actions_frame, text="✨ TEACH AI", font=("Segoe UI", 8, "bold"),
            bg="#1a1f24", fg="#888888", borderwidth=0, cursor="hand2",
            padx=15, pady=8, command=self._learn_correction
        )
        self.learn_btn.pack(side="right")
        # Token Stats (subtle)
        self.token_label = tk.Label(actions_frame, text="", font=("Segoe UI", 8),
                                   bg="#101a22", fg="#444444")
        self.token_label.pack(side="left")


    def _build_ecosystem_view(self):
        """Build the Plugins & Learning management view."""
        parent = self.frames["ecosystem"]
        container = tk.Frame(parent, bg="#101a22", padx=40, pady=40)
        container.pack(fill="both", expand=True)
        
        tk.Label(container, text="Ecosystem Control", 
                 font=("Segoe UI", 18, "bold"), bg="#101a22", fg="#ffffff").pack(anchor="w")
        
        tk.Label(container, text="Manage your specialized vocabularies and AI plugins.", 
                 font=("Segoe UI", 10), bg="#101a22", fg="#666666").pack(anchor="w", pady=(5, 20))

        # 1. Plugin Section
        section_p = tk.Frame(container, bg="#111518", padx=20, pady=20)
        section_p.pack(fill="x", pady=10)
        
        tk.Label(section_p, text="🧩 ACTIVE PLUGINS", 
                 font=("Segoe UI", 8, "bold"), bg="#111518", fg="#1392ec").pack(anchor="w")
        
        self.plugin_list_frame = tk.Frame(section_p, bg="#111518", pady=10)
        self.plugin_list_frame.pack(fill="x")
        
        tk.Button(
            section_p, text="BROWSE MARKETPLACE",
            font=("Segoe UI", 9, "bold"), bg="#1392ec", fg="white",
            borderwidth=0, cursor="hand2", padx=15, pady=8,
            command=self._open_marketplace
        ).pack(side="right")
        
        # 2. Stats Section
        section_s = tk.Frame(container, bg="#111518", padx=20, pady=20)
        section_s.pack(fill="x", pady=10)
        
        tk.Label(section_s, text="🧠 AI LEARNING STATS", 
                 font=("Segoe UI", 8, "bold"), bg="#111518", fg="#1392ec").pack(anchor="w")
        
        self.stats_label = tk.Label(section_s, text="Loading stats...", 
                                   font=("Segoe UI", 10), bg="#111518", fg="#ffffff", justify="left")
        self.stats_label.pack(anchor="w", pady=10)

        # 3. Agent Bridge
        section_a = tk.Frame(container, bg="#111518", padx=20, pady=20)
        section_a.pack(fill="x", pady=10)
        
        tk.Label(section_a, text="🤖 AGENT A2A BRIDGE", 
                 font=("Segoe UI", 8, "bold"), bg="#111518", fg="#1392ec").pack(anchor="w")
        
        a2a_url = f"http://localhost:{self.engine.a2a.port}"
        tk.Label(section_a, text=f"Local API: {a2a_url}", 
                 font=("Consolas", 9), bg="#111518", fg="#888888").pack(anchor="w", pady=5)
        
        self._update_ecosystem_view()

    def _update_ecosystem_view(self):
        """Update plugin list and learning stats from the engine."""
        try:
            for widget in self.plugin_list_frame.winfo_children():
                widget.destroy()
            
            plugins = self.engine.plugins.discover_plugins()
            if not plugins:
                tk.Label(self.plugin_list_frame, text="No plugins active.", 
                         bg="#111518", fg="#666666").pack(anchor="w")
            else:
                for p in plugins:
                    tk.Label(self.plugin_list_frame, text=f"✅ {p.name} (v{p.version})", 
                             bg="#111518", fg="#4caf50", font=("Segoe UI", 10)).pack(anchor="w")
            
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

    def _build_privacy_view(self):
        """Build the Privacy & Audit management view."""
        parent = self.frames["privacy"]
        container = tk.Frame(parent, bg="#101a22", padx=40, pady=40)
        container.pack(fill="both", expand=True)
        
        tk.Label(container, text="Privacy & Audit", 
                 font=("Segoe UI", 18, "bold"), bg="#101a22", fg="#ffffff").pack(anchor="w")
        
        tk.Label(container, text="Local-first data processing. Review your audit logs below.", 
                 font=("Segoe UI", 10), bg="#101a22", fg="#666666").pack(anchor="w", pady=(5, 20))

        table_frame = tk.Frame(container, bg="#111518", padx=2, pady=2)
        table_frame.pack(fill="both", expand=True)
        
        list_container = tk.Frame(table_frame, bg="#111518")
        list_container.pack(fill="both", expand=True)
        
        self.audit_scroll = tk.Scrollbar(list_container, width=10)
        self.audit_scroll.pack(side="right", fill="y")
        
        self.audit_list = tk.Listbox(
            list_container, bg="#111518", fg="#aaaaaa", borderwidth=0,
            font=("Consolas", 10), yscrollcommand=self.audit_scroll.set,
            highlightthickness=0, selectbackground="#1a1f24"
        )
        self.audit_list.pack(fill="both", expand=True, padx=15, pady=15)
        self.audit_scroll.config(command=self.audit_list.yview)
        
        tk.Button(
            container, text="REFRESH LOG", font=("Segoe UI", 8, "bold"),
            bg="#1a1f24", fg="#888888", borderwidth=0, cursor="hand2",
            padx=15, pady=8, command=self._update_privacy_view
        ).pack(pady=20, side="right")
        
        self._update_privacy_view()

    def _update_privacy_view(self):
        """Fetch and display recent audit logs."""
        try:
            self.audit_list.delete(0, tk.END)
            logs = self.engine.privacy.get_audit_summary(limit=20)
            for log in logs:
                ts = log['timestamp'].split()[1]
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
        """Start recording audio and update UI."""
        self.record_circle.itemconfig(self._btn_circle, fill="#d32f2f") # Red
        self.status_label.config(text="🔴 RECORDING", fg="#ff5252")
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", "Listening...")
        self.result_text.config(state="disabled")
        
        self._timer_seconds = 0
        self._update_timer()
        
        if self.hud.is_visible:
            self.hud.start_recording_mode()
        
        self.engine.start_recording(self._engine_callback)

    def _stop_recording(self):
        """Stop recording and update UI."""
        self.record_circle.itemconfig(self._btn_circle, fill="#ff9800") # Amber
        self.status_label.config(text="⏳ PROCESSING", fg="#ff9800")
        
        if self._timer_job:
            self.after_cancel(self._timer_job)
            self._timer_job = None
        self.timer_label.config(text="")
        
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
                        
                        conf = data.get("confidence", 1.0)
                        tag = "high_conf"
                        if conf < 0.6: tag = "low_conf"
                        elif conf < 0.85: tag = "med_conf"
                        
                        self.result_text.insert("1.0", text, tag)
                        self.last_raw_text = text
                        
                        is_spec = data.get("is_specialized", False)
                        self.hud.update_smart_status(is_spec)
                        
                        conf_percent = int(conf*100)
                        tokens = data.get("tokens", 0)
                        
                        show_conf = self.config.get("show_confidence", False) or bool(self.config.get("keys", {}).get("Gemini") or self.config.get("keys", {}).get("OpenAI"))
                        
                        status_text = f"Tokens: {tokens}"
                        if show_conf:
                            status_text = f"Confidence: {conf_percent}% | {status_text}"
                        
                        self.status_label.config(text=status_text, fg="#4caf50")
                        self.token_label.config(text=f"Est. Tokens: {tokens}")
                        self._update_ecosystem_view() 

                        if self.config.get("auto_clipboard", True):
                            import pyperclip
                            pyperclip.copy(text)
                        
                        if warning:
                            self.status_label.config(text=f"⚠ {warning}", fg="#ff9800")
                        else:
                            self.status_label.config(text="✅ COPIED!", fg="#4caf50")
                        
                        if self.hud.is_visible:
                            self.hud.show_final(text, success=True)
                        
                        self.record_circle.itemconfig(self._btn_circle, fill="#1392ec") # Reset Blue
                    else:
                        error_text = error if error else "No speech detected"
                        self.status_label.config(text=f"❌ {error_text}", fg="#f44336")
                        if self.hud.is_visible:
                            self.hud.show_final("", success=False)
                        self.record_circle.itemconfig(self._btn_circle, fill="#1392ec") # Reset Blue
                    
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
        # Only allow dragging if the click was in the title bar or sidebar (DragZones)
        if event.widget in [self.title_bar, self.sidebar] or isinstance(event.widget, tk.Label):
            self._drag_data["x"] = event.x
            self._drag_data["y"] = event.y

    def _do_drag(self, event):
        if self._drag_data.get("x") is not None:
            x = self.winfo_x() - self._drag_data["x"] + event.x
            y = self.winfo_y() - self._drag_data["y"] + event.y
            self.geometry(f"+{x}+{y}")

    def _minimize_window(self):
        self.withdraw()
        self.overrideredirect(False)
        self.iconify()
        self.after(0, lambda: self.overrideredirect(True))

    def _build_about_view(self):
        """Build the highly stylized About page."""
        parent = self.frames["about"]
        
        canvas = tk.Canvas(parent, bg="#101a22", highlightthickness=0)
        scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview, width=0)
        scroll_content = tk.Frame(canvas, bg="#101a22")
        
        scroll_content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_content, anchor="nw", width=700)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        header = tk.Frame(scroll_content, bg="#111518", padx=40, pady=50)
        header.pack(fill="x", pady=20, padx=40)
        
        tk.Label(header, text="🎙️", font=("Segoe UI", 48), bg="#111518").pack()
        tk.Label(header, text="EasySTT", font=("Segoe UI", 36, "bold"), 
                 bg="#111518", fg="#ffffff").pack()
        tk.Label(header, text="The I'm Too Lazy to Type Edition", 
                 font=("Segoe UI", 12, "bold"), bg="#111518", fg="#1392ec").pack()

        specs_container = tk.Frame(scroll_content, bg="#101a22", padx=40)
        specs_container.pack(fill="x")
        
        tk.Label(specs_container, text="BUILD INFORMATION", font=("Segoe UI", 8, "bold"), 
                 bg="#101a22", fg="#1392ec").pack(anchor="w", pady=(20, 10))
        
        for label, val in [("Architect", "Sijo Joseph"), ("Version", "2.0.0-pro"), ("Core", "Faster Whisper Turbo")]:
            row = tk.Frame(specs_container, bg="#111518", padx=20, pady=15)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, font=("Segoe UI", 10), bg="#111518", fg="#666666").pack(side="left")
            tk.Label(row, text=val, font=("Segoe UI Semibold", 10), bg="#111518", fg="#ffffff").pack(side="right")

        warning_frame = tk.Frame(scroll_content, bg="#1a1401", padx=25, pady=20, 
                                highlightbackground="#3d2a01", highlightthickness=1)
        warning_frame.pack(fill="x", padx=40, pady=40)
        
        tk.Label(warning_frame, text="⚠️ WARNING: Excessive use of this software might lead to complete loss of typing skills and a sudden urge to talk to inanimate objects.", 
                 font=("Segoe UI", 9, "bold"), bg="#1a1401", fg="#ff9800", wraplength=600, justify="center").pack()
        
        tk.Label(scroll_content, text="© 2026 Monkey Lab. All rights reserved.", 
                 font=("Segoe UI", 8), bg="#101a22", fg="#444444").pack(pady=20)
