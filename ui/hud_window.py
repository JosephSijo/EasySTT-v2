# EasySTT v2.0 - Enhanced HUD with Live Preview
# Auto-expanding floating pill with real-time transcription

import tkinter as tk
from typing import Optional


class HUD:
    """
    Enhanced Floating HUD (The Pill) for EasySTT.
    Features:
    - Auto-expand on recording (45px -> 120px)
    - Auto-collapse 2s after processing complete
    - Connection status indicator
    - Live transcription display with word-by-word updates
    - Click to toggle recording
    - Right-click context menu
    """
    
    # Appearance constants
    COMPACT_HEIGHT = 45
    EXPANDED_HEIGHT = 130
    WIDTH = 350
    
    # Colors (matching UI/UX spec)
    COLORS = {
        "bg": "#0a0a0a",
        "surface": "#121212",
        "border": "#333333",
        "text_primary": "#ffffff",
        "text_secondary": "#666666",
        "blue": "#007acc",
        "red": "#ff5252",
        "green": "#4caf50",
        "amber": "#ff9800",
        "cyan": "#00bcd4"
    }
    
    def __init__(self, parent, config, engine):
        self.parent = parent
        self.config = config
        self.engine = engine
        self.is_visible = False
        self.is_expanded = False
        self._collapse_job = None
        
        # 1. Window Setup
        self.root = tk.Toplevel(parent)
        self.root.overrideredirect(True)  # Frameless
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.98) # Slightly more opaque for obsidian
        self.root.configure(bg=self.COLORS["bg"])
        
        # 2. Dimensions & Positioning
        screen_width = self.root.winfo_screenwidth()
        self.root.geometry(f"{self.WIDTH}x{self.COMPACT_HEIGHT}+{(screen_width - self.WIDTH)//2}+20")
        
        # 3. Build UI
        self._build_compact_ui()
        self._build_expanded_ui()
        
        # Start in compact mode
        self._show_compact()
        
        # 4. Bindings
        self.root.bind("<Button-1>", self._on_click)
        self.root.bind("<Button-3>", self._show_context_menu)
        self.root.bind("<B1-Motion>", self._do_move)
        
        # Track drag start
        self._drag_start_x = 0
        self._drag_start_y = 0
        
    def _build_compact_ui(self):
        """Build the compact (collapsed) view."""
        self.compact_frame = tk.Frame(self.root, bg=self.COLORS["surface"], height=self.COMPACT_HEIGHT)
        
        # Connection indicator dot
        self.status_dot = tk.Label(
            self.compact_frame, text="●", 
            font=("Segoe UI", 10), 
            fg=self.COLORS["green"], 
            bg=self.COLORS["surface"]
        )
        self.status_dot.pack(side="left", padx=(15, 5))
        
        # Status text
        self.compact_label = tk.Label(
            self.compact_frame, text="READY",
            font=("Segoe UI", 11, "bold"),
            fg=self.COLORS["text_primary"],
            bg=self.COLORS["surface"]
        )
        self.compact_label.pack(side="left", padx=5, expand=True)
        
        # Smart Indicator (Sparkle)
        self.smart_indicator = tk.Label(
            self.compact_frame, text=" ✨ ",
            font=("Segoe UI", 10),
            fg=self.COLORS["border"], # Default dim
            bg=self.COLORS["surface"]
        )
        self.smart_indicator.pack(side="left", padx=5)
        
        # Hotkey hint
        shortcut = self.config.get("shortcut", "ctrl+alt+r")
        self.hotkey_label = tk.Label(
            self.compact_frame, text=shortcut.upper(),
            font=("Segoe UI", 8),
            fg=self.COLORS["text_secondary"],
            bg=self.COLORS["surface"]
        )
        self.hotkey_label.pack(side="right", padx=15)
        
    def _build_expanded_ui(self):
        """Build the expanded view with live preview."""
        self.expanded_frame = tk.Frame(self.root, bg=self.COLORS["surface"])
        
        # Header row
        header = tk.Frame(self.expanded_frame, bg=self.COLORS["surface"])
        header.pack(fill="x", padx=10, pady=(10, 5))
        
        # Recording indicator
        self.expanded_status = tk.Label(
            header, text="🔴 RECORDING",
            font=("Segoe UI", 11, "bold"),
            fg=self.COLORS["red"],
            bg=self.COLORS["surface"]
        )
        self.expanded_status.pack(side="left")
        
        # Timer
        self.timer_label = tk.Label(
            header, text="0:00",
            font=("Segoe UI", 9),
            fg=self.COLORS["text_secondary"],
            bg=self.COLORS["surface"]
        )
        self.timer_label.pack(side="right")
        
        # Separator
        sep = tk.Frame(self.expanded_frame, height=1, bg=self.COLORS["border"])
        sep.pack(fill="x", padx=10, pady=5)
        
        # Live transcript area
        self.transcript_label = tk.Label(
            self.expanded_frame,
            text="Listening...",
            font=("Segoe UI", 10),
            fg=self.COLORS["cyan"],
            bg=self.COLORS["surface"],
            wraplength=self.WIDTH - 30,
            justify="left",
            anchor="nw",
            height=3
        )
        self.transcript_label.pack(fill="both", expand=True, padx=15, pady=(0, 5))
        
        # Footer row
        footer = tk.Frame(self.expanded_frame, bg=self.COLORS["surface"])
        footer.pack(fill="x", padx=10, pady=(0, 10))
        
        # Connection status
        self.footer_status = tk.Label(
            footer, text="🟢 Online",
            font=("Segoe UI", 8),
            fg=self.COLORS["text_secondary"],
            bg=self.COLORS["surface"]
        )
        self.footer_status.pack(side="left")
        
        # Engine tier
        engine_tier = self.config.get("engine_tier", "Basic")
        model = self.config.get("whisper_model", "turbo")
        self.engine_label = tk.Label(
            footer, text=f"Engine: {model}",
            font=("Segoe UI", 8),
            fg=self.COLORS["text_secondary"],
            bg=self.COLORS["surface"]
        )
        self.engine_label.pack(side="right")
        
        # Expanded Smart Label
        self.expanded_smart = tk.Label(
            footer, text="Specialized Vocab Active",
            font=("Segoe UI", 8, "italic"),
            fg=self.COLORS["border"],
            bg=self.COLORS["surface"]
        )
        self.expanded_smart.pack(side="right", padx=10)
        
    def _show_compact(self):
        """Switch to compact mode."""
        self.is_expanded = False
        self.expanded_frame.pack_forget()
        self.compact_frame.pack(fill="both", expand=True)
        self.root.geometry(f"{self.WIDTH}x{self.COMPACT_HEIGHT}")
        
    def _show_expanded(self):
        """Switch to expanded mode."""
        self.is_expanded = True
        self.compact_frame.pack_forget()
        self.expanded_frame.pack(fill="both", expand=True)
        self.root.geometry(f"{self.WIDTH}x{self.EXPANDED_HEIGHT}")
        
    def _on_click(self, event):
        """Handle click - start drag or toggle recording."""
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        
    def _do_move(self, event):
        """Drag the window."""
        deltax = event.x - self._drag_start_x
        deltay = event.y - self._drag_start_y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")
        
    def _show_context_menu(self, event):
        """Show right-click context menu."""
        menu = tk.Menu(self.root, tearoff=0, bg=self.COLORS["surface"], fg="white")
        menu.add_command(label="⚙ Settings", command=self._open_settings)
        menu.add_command(label="🎯 Onboarding", command=self._open_onboarding)
        menu.add_separator()
        menu.add_command(label="❌ Exit", command=self._exit_app)
        menu.tk_popup(event.x_root, event.y_root)
        
    def _open_settings(self):
        """Open settings window via parent."""
        if hasattr(self.parent, 'open_settings'):
            self.parent.open_settings()
            
    def _open_onboarding(self):
        """Open onboarding window via parent."""
        if hasattr(self.parent, 'open_onboarding'):
            self.parent.open_onboarding()
            
    def _exit_app(self):
        """Exit the application."""
        self.parent.quit()

    # --- Public API ---
    
    def update_status(self, text: str, color: str = None):
        """Update status text (compact mode)."""
        color = color or self.COLORS["text_primary"]
        self.compact_label.config(text=text.upper(), fg=color)
        
        # Also update expanded header if visible
        if text.upper() == "RECORDING":
            self.expanded_status.config(text="🔴 RECORDING", fg=self.COLORS["red"])
        elif text.upper() == "PROCESSING":
            self.expanded_status.config(text="⏳ PROCESSING", fg=self.COLORS["amber"])
        elif text.upper() == "COPIED!":
            self.expanded_status.config(text="✅ COPIED!", fg=self.COLORS["green"])
        elif text.upper() == "ERROR":
            self.expanded_status.config(text="❌ ERROR", fg=self.COLORS["red"])
        else:
            self.expanded_status.config(text=f"● {text.upper()}", fg=color)
    
    def update_interim(self, text: str):
        """Update live preview text (triggers expand)."""
        if not self.is_expanded:
            self._show_expanded()
            
        # Cancel any pending collapse
        if self._collapse_job:
            self.root.after_cancel(self._collapse_job)
            self._collapse_job = None
            
        # Show last portion if text is too long
        max_chars = 150
        display_text = text[-max_chars:] if len(text) > max_chars else text
        if len(text) > max_chars:
            display_text = "..." + display_text
            
        self.transcript_label.config(text=display_text, fg=self.COLORS["cyan"])
        
    def update_connection(self, online: bool):
        # ... (Existing update_connection logic)
        pass # Keep logic

    def update_smart_status(self, active: bool):
        """Update the sparkle indicator when specialized vocab is active."""
        color = self.COLORS["amber"] if active else self.COLORS["border"]
        self.smart_indicator.config(fg=color)
        self.expanded_smart.config(fg=color if active else self.COLORS["surface"])
    def update_timer(self, seconds: int):
        """Update recording timer display."""
        mins = seconds // 60
        secs = seconds % 60
        self.timer_label.config(text=f"{mins}:{secs:02d}")
    
    def show_final(self, text: str, success: bool = True):
        """Show final result and schedule collapse."""
        if success:
            self.update_status("COPIED!", self.COLORS["green"])
            self.transcript_label.config(text=text[:150], fg=self.COLORS["green"])
        else:
            self.update_status("ERROR", self.COLORS["red"])
            
        # Schedule collapse after 2 seconds
        self._collapse_job = self.root.after(2000, self._auto_collapse)
        
    def _auto_collapse(self):
        """Auto-collapse after showing result."""
        self._show_compact()
        self.update_status("READY", self.COLORS["text_primary"])
        self.transcript_label.config(text="Listening...", fg=self.COLORS["cyan"])
        self._collapse_job = None

    def start_recording_mode(self):
        """Switch to recording mode UI."""
        self._show_expanded()
        self.update_status("RECORDING", self.COLORS["red"])
        self.transcript_label.config(text="Listening...", fg=self.COLORS["cyan"])
        
    def stop_recording_mode(self):
        """Switch to processing mode UI."""
        self.update_status("PROCESSING", self.COLORS["amber"])
        self.transcript_label.config(text="Processing...", fg=self.COLORS["amber"])
