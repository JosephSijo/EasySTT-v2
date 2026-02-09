# EasySTT v2.0 - Voice Onboarding Window
# Step-by-step wizard for vocabulary training

import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Callable, Optional


class OnboardingWindow(tk.Toplevel):
    """
    Voice Onboarding Wizard for first-time setup.
    Features:
    - 3-step guided flow (Name, Jargon, Phrases)
    - Animated mic button with visual feedback
    - Progress bar
    - Skip/Back/Next navigation
    - Correction input for fixing transcripts
    """
    
    COLORS = {
        "bg": "#1e1e1e",
        "surface": "#2d2d2d",
        "border": "#444444",
        "text_primary": "#ffffff",
        "text_secondary": "#aaaaaa",
        "blue": "#007acc",
        "red": "#ff5252",
        "green": "#4caf50",
        "amber": "#ff9800",
        "cyan": "#00bcd4"
    }
    
    def __init__(self, parent, engine, onboarding_manager, on_complete: Optional[Callable] = None):
        super().__init__(parent)
        self.engine = engine
        self.manager = onboarding_manager
        self.on_complete = on_complete
        
        # State
        self.is_recording = False
        self.current_transcript = ""
        self._timer_seconds = 0
        self._timer_job = None
        
        # Window Setup
        self.title("EasySTT Voice Onboarding")
        self.geometry("500x450")
        self.configure(bg=self.COLORS["bg"])
        self.resizable(False, False)
        
        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 500) // 2
        y = (self.winfo_screenheight() - 450) // 2
        self.geometry(f"+{x}+{y}")
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Build UI
        self._build_ui()
        self._update_step_ui()
        
    def _build_ui(self):
        """Build the wizard UI."""
        # Header
        header = tk.Frame(self, bg=self.COLORS["bg"])
        header.pack(fill="x", padx=30, pady=(30, 20))
        
        tk.Label(
            header, text="🎯 Voice Onboarding",
            font=("Segoe UI", 20, "bold"),
            fg=self.COLORS["text_primary"],
            bg=self.COLORS["bg"]
        ).pack(anchor="w")
        
        tk.Label(
            header, text="Train the AI to recognize your vocabulary",
            font=("Segoe UI", 10),
            fg=self.COLORS["text_secondary"],
            bg=self.COLORS["bg"]
        ).pack(anchor="w", pady=(5, 0))
        
        # Progress bar
        self.progress_frame = tk.Frame(self, bg=self.COLORS["bg"])
        self.progress_frame.pack(fill="x", padx=30, pady=(0, 20))
        
        self.step_label = tk.Label(
            self.progress_frame, text="Step 1/3",
            font=("Segoe UI", 9),
            fg=self.COLORS["text_secondary"],
            bg=self.COLORS["bg"]
        )
        self.step_label.pack(anchor="w")
        
        self.progress = ttk.Progressbar(self.progress_frame, length=440, mode='determinate')
        self.progress.pack(fill="x", pady=(5, 0))
        
        # Content area
        self.content_frame = tk.Frame(self, bg=self.COLORS["surface"], padx=20, pady=20)
        self.content_frame.pack(fill="both", expand=True, padx=30)
        
        # Step title
        self.title_label = tk.Label(
            self.content_frame, text="",
            font=("Segoe UI", 14, "bold"),
            fg=self.COLORS["text_primary"],
            bg=self.COLORS["surface"]
        )
        self.title_label.pack(anchor="w", pady=(0, 10))
        
        # Prompt
        self.prompt_label = tk.Label(
            self.content_frame, text="",
            font=("Segoe UI", 11),
            fg=self.COLORS["cyan"],
            bg=self.COLORS["surface"],
            wraplength=400
        )
        self.prompt_label.pack(anchor="w", pady=(0, 20))
        
        # Mic button
        self.mic_frame = tk.Frame(self.content_frame, bg=self.COLORS["surface"])
        self.mic_frame.pack(pady=10)
        
        self.mic_btn = tk.Button(
            self.mic_frame, text="🎙 Press to Record",
            font=("Segoe UI", 12, "bold"),
            bg=self.COLORS["blue"],
            fg="white",
            width=20,
            height=2,
            borderwidth=0,
            command=self._toggle_recording
        )
        self.mic_btn.pack()
        
        self.timer_label = tk.Label(
            self.mic_frame, text="",
            font=("Segoe UI", 9),
            fg=self.COLORS["text_secondary"],
            bg=self.COLORS["surface"]
        )
        self.timer_label.pack(pady=(5, 0))
        
        # Transcript display
        self.transcript_frame = tk.Frame(self.content_frame, bg=self.COLORS["bg"], padx=10, pady=10)
        self.transcript_frame.pack(fill="x", pady=(15, 10))
        
        tk.Label(
            self.transcript_frame, text="Transcript:",
            font=("Segoe UI", 9),
            fg=self.COLORS["text_secondary"],
            bg=self.COLORS["bg"]
        ).pack(anchor="w")
        
        self.transcript_label = tk.Label(
            self.transcript_frame, text="(will appear here)",
            font=("Segoe UI", 10, "italic"),
            fg=self.COLORS["text_primary"],
            bg=self.COLORS["bg"],
            wraplength=380
        )
        self.transcript_label.pack(anchor="w", pady=(5, 0))
        
        # Correction input
        correction_frame = tk.Frame(self.content_frame, bg=self.COLORS["surface"])
        correction_frame.pack(fill="x", pady=(10, 0))
        
        tk.Label(
            correction_frame, text="Correction (optional):",
            font=("Segoe UI", 9),
            fg=self.COLORS["text_secondary"],
            bg=self.COLORS["surface"]
        ).pack(anchor="w")
        
        self.correction_entry = tk.Entry(
            correction_frame,
            font=("Segoe UI", 10),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text_primary"],
            insertbackground="white",
            borderwidth=1,
            relief="solid"
        )
        self.correction_entry.pack(fill="x", pady=(5, 0))
        
        # Navigation buttons
        nav_frame = tk.Frame(self, bg=self.COLORS["bg"])
        nav_frame.pack(fill="x", padx=30, pady=20)
        
        self.skip_btn = tk.Button(
            nav_frame, text="Skip Onboarding",
            font=("Segoe UI", 9),
            fg=self.COLORS["text_secondary"],
            bg=self.COLORS["bg"],
            borderwidth=0,
            command=self._skip
        )
        self.skip_btn.pack(side="left")
        
        self.next_btn = tk.Button(
            nav_frame, text="Next →",
            font=("Segoe UI", 11, "bold"),
            bg=self.COLORS["green"],
            fg="white",
            width=10,
            borderwidth=0,
            command=self._next_step
        )
        self.next_btn.pack(side="right")
        
        self.back_btn = tk.Button(
            nav_frame, text="← Back",
            font=("Segoe UI", 10),
            bg=self.COLORS["surface"],
            fg=self.COLORS["text_primary"],
            width=8,
            borderwidth=0,
            command=self._prev_step
        )
        self.back_btn.pack(side="right", padx=(0, 10))
        
        self.retry_btn = tk.Button(
            nav_frame, text="🔄 Try Again",
            font=("Segoe UI", 9),
            bg=self.COLORS["amber"],
            fg="white",
            borderwidth=0,
            command=self._retry
        )
        self.retry_btn.pack(side="right", padx=(0, 10))
        self.retry_btn.pack_forget()  # Hidden initially
        
    def _update_step_ui(self):
        """Update UI for current step."""
        step = self.manager.current_step
        if not step:
            self._complete()
            return
            
        # Update progress
        progress_pct = (self.manager.current_step_index / self.manager.total_steps) * 100
        self.progress['value'] = progress_pct
        self.step_label.config(text=f"Step {self.manager.current_step_index + 1}/{self.manager.total_steps}")
        
        # Update content
        self.title_label.config(text=step.title)
        self.prompt_label.config(text=step.prompt)
        
        # Reset transcript and correction
        self.current_transcript = ""
        self.transcript_label.config(text="(will appear here)", fg=self.COLORS["text_primary"])
        self.correction_entry.delete(0, tk.END)
        
        # Update navigation visibility
        if self.manager.current_step_index == 0:
            self.back_btn.pack_forget()
        else:
            self.back_btn.pack(side="right", padx=(0, 10))
            
        self.retry_btn.pack_forget()
        
    def _toggle_recording(self):
        """Toggle recording state."""
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()
            
    def _start_recording(self):
        """Start recording audio."""
        self.is_recording = True
        self.mic_btn.config(text="🔴 Recording... (Click to Stop)", bg=self.COLORS["red"])
        self._timer_seconds = 0
        self._update_timer()
        
        # Start engine recording
        self.engine.start_recording(self._engine_callback)
        
    def _stop_recording(self):
        """Stop recording and process."""
        self.is_recording = False
        self.mic_btn.config(text="⏳ Processing...", bg=self.COLORS["amber"], state="disabled")
        
        if self._timer_job:
            self.after_cancel(self._timer_job)
            self._timer_job = None
            
        # Stop engine
        self.engine.stop_recording()
        
    def _update_timer(self):
        """Update recording timer."""
        if self.is_recording:
            mins = self._timer_seconds // 60
            secs = self._timer_seconds % 60
            self.timer_label.config(text=f"{mins}:{secs:02d}")
            self._timer_seconds += 1
            self._timer_job = self.after(1000, self._update_timer)
            
    def _engine_callback(self, data: dict):
        """Handle callbacks from STT engine."""
        self.after(0, lambda: self._handle_engine_data(data))
        
    def _handle_engine_data(self, data: dict):
        """Process engine data on main thread."""
        if data.get("type") == "interim":
            text = data.get("text", "")
            self.transcript_label.config(text=text, fg=self.COLORS["cyan"])
            
        elif data.get("type") == "final":
            text = data.get("text", "")
            self.current_transcript = text
            self.transcript_label.config(text=text if text else "(No speech detected)", fg=self.COLORS["text_primary"])
            self.mic_btn.config(text="🎙 Press to Record", bg=self.COLORS["blue"], state="normal")
            self.timer_label.config(text="")
            
            # Show retry button if we got something
            if text:
                self.retry_btn.pack(side="right", padx=(0, 10))
                
    def _next_step(self):
        """Save current step and move to next."""
        # Save correction if provided, otherwise use transcript
        correction = self.correction_entry.get().strip()
        if correction:
            self.manager.save_correction(correction)
        elif self.current_transcript:
            self.manager.save_transcript(self.current_transcript)
            
        # Advance
        if self.manager.advance():
            self._update_step_ui()
        else:
            self._complete()
            
    def _prev_step(self):
        """Go back to previous step."""
        self.manager.go_back()
        self._update_step_ui()
        
    def _retry(self):
        """Clear and retry current step."""
        self.current_transcript = ""
        self.transcript_label.config(text="(will appear here)", fg=self.COLORS["text_primary"])
        self.correction_entry.delete(0, tk.END)
        self.retry_btn.pack_forget()
        
    def _skip(self):
        """Skip onboarding entirely."""
        self.destroy()
        if self.on_complete:
            self.on_complete(skipped=True)
            
    def _complete(self):
        """Onboarding complete."""
        self.destroy()
        if self.on_complete:
            self.on_complete(skipped=False)
