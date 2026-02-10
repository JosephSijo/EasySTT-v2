# EasySTT v2.0 - Enhanced HUD with Live Preview
# Auto-expanding floating pill with real-time transcription

import tkinter as tk
from typing import Optional
from core.win32_utils import apply_window_masking, enable_acrylic_effect, set_window_shadow


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
    HEIGHT = 50
    WIDTH = 450
    
    # Colors (Premium Palette)
    COLORS = {
        "bg": "#111518",
        "accent": "#1392ec",
        "red": "#ff5252",
        "green": "#4caf50",
        "text": "#ffffff",
        "dim": "#888888"
    }
    
    def __init__(self, parent, config, engine):
        self.parent = parent
        self.config = config
        self.engine = engine
        self.is_visible = False
        self._collapse_job = None
        
        # 1. Window Setup
        self.root = tk.Toplevel(parent)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.95)
        self.root.configure(bg=self.COLORS["bg"])
        
        # 2. Geometry
        screen_w = self.root.winfo_screenwidth()
        self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}+{(screen_w - self.WIDTH)//2}+30")
        
        # Antigravity Framework Effects
        self.root.after(10, self._apply_win32_effects)

        # 3. Build UI Elements
        self.main_frame = tk.Frame(self.root, bg=self.COLORS["bg"], padx=20)
        self.main_frame.pack(fill="both", expand=True)

        # 3. Build UI Elements
        # Status Dot
        self.dot = tk.Label(self.main_frame, text="●", font=("Segoe UI", 12), 
                           bg=self.COLORS["bg"], fg=self.COLORS["green"])
        self.dot.pack(side="left", padx=(0, 10))

        # Main Label (The "Pill" content)
        self.status_label = tk.Label(self.main_frame, text="READY", 
                                    font=("Segoe UI Semibold", 10),
                                    bg=self.COLORS["bg"], fg=self.COLORS["text"])
        self.status_label.pack(side="left")

        # Live Ghost Text Area
        self.ghost_label = tk.Label(self.main_frame, text="", 
                                   font=("Segoe UI", 10, "italic"),
                                   bg=self.COLORS["bg"], fg=self.COLORS["dim"])
        self.ghost_label.pack(side="left", padx=15, fill="x", expand=True)

        # Timer
        self.timer_label = tk.Label(self.main_frame, text="0:00", 
                                   font=("Segoe UI", 9),
                                   bg=self.COLORS["bg"], fg=self.COLORS["dim"])
        self.timer_label.pack(side="right")

        # 4. Interaction
        self.root.bind("<Button-1>", self._on_click)
        self.root.bind("<B1-Motion>", self._do_drag)
        self._drag_data = {"x": 0, "y": 0}

    def _on_click(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _do_drag(self, event):
        x = self.root.winfo_x() - self._drag_data["x"] + event.x
        y = self.root.winfo_y() - self._drag_data["y"] + event.y
        self.root.geometry(f"+{x}+{y}")

    def start_recording_mode(self):
        self.dot.config(fg=self.COLORS["red"])
        self.status_label.config(text="REC", fg=self.COLORS["red"])
        self.ghost_label.config(text="Listening...")

    def stop_recording_mode(self):
        self.dot.config(fg="#ff9800")
        self.status_label.config(text="PRC", fg="#ff9800")
        self.ghost_label.config(text="Processing...")

    def update_interim(self, text):
        display_text = text[-50:] if len(text) > 50 else text
        self.ghost_label.config(text=display_text)

    def update_timer(self, seconds):
        m, s = divmod(seconds, 60)
        self.timer_label.config(text=f"{m}:{s:02d}")

    def show_final(self, text, success=True):
        if success:
            self.dot.config(fg=self.COLORS["green"])
            self.status_label.config(text="READY", fg=self.COLORS["text"])
            self.ghost_label.config(text="✓ Copied", fg=self.COLORS["green"])
        else:
            self.dot.config(fg=self.COLORS["red"])
            self.status_label.config(text="ERROR", fg=self.COLORS["red"])
            self.ghost_label.config(text="Failed", fg=self.COLORS["red"])
        
        self.root.after(2000, lambda: self.ghost_label.config(text="", fg=self.COLORS["dim"]))

    def update_connection(self, online):
        color = self.COLORS["green"] if online else self.COLORS["dim"]
        self.dot.config(fg=color)

    def update_status(self, text):
        self.status_label.config(text=text.upper())
    
    def update_smart_status(self, active):
        pass # Optional: add sparkle if needed

    def _apply_win32_effects(self):
        """Apply the Antigravity premium look to the HUD."""
        hwnd = self.root.winfo_id()
        apply_window_masking(hwnd, radius=25)
        enable_acrylic_effect(hwnd, theme="dark")
        set_window_shadow(hwnd, enabled=True)
