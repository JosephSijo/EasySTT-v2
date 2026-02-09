import json
import os
import sys
import threading
import time

class WebBridge:
    """
    Bridge between Python backend and the Web UI.
    Exposes methods to JavaScript and handles event dispatching.
    """
    def __init__(self, engine, config):
        self.engine = engine
        self.config = config
        self.window = None
        self.hud_window = None

    def attach_window(self, window, window_type="main"):
        """Attach a pywebview window instance."""
        if window_type == "main":
            self.window = window
        elif window_type == "hud":
            self.hud_window = window

    # --- Methods called from JavaScript ---

    def start_recording(self):
        """Start the STT engine recording."""
        print("[Bridge] Start Recording requested")
        if not self.engine.is_recording:
            # Pass our internal callback that dispatches to JS
            self.engine.start_recording(self._engine_callback)
            # Update UI state immediately
            self.dispatch_event({"type": "status", "state": "recording"})
            return {"success": True}
        return {"success": False, "message": "Already recording"}

    def stop_recording(self):
        """Stop the STT engine recording."""
        print("[Bridge] Stop Recording requested")
        if self.engine.is_recording:
            self.engine.stop_recording()
            self.dispatch_event({"type": "status", "state": "processing"})
            return {"success": True}
        return {"success": False, "message": "Not recording"}

    def toggle_recording(self):
        if self.engine.is_recording:
            return self.stop_recording()
        else:
            return self.start_recording()

    def get_status(self):
        """Return current engine status."""
        return {
            "is_recording": self.engine.is_recording,
            "is_processing": self.engine.is_processing
        }

    def navigate(self, page_name):
        """Navigate the main window to a different HTML file."""
        if self.window:
            # Assuming files are in ui/web_ui/
            base_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(base_dir, "web_ui", page_name)
            if os.path.exists(file_path):
                self.window.load_url(f"file://{file_path}")
                print(f"[Bridge] Navigating to {page_name}")
            else:
                print(f"[Bridge] Error: File not found {file_path}")

    def quit_app(self):
        """Close the application."""
        print("[Bridge] Quitting application")
        if self.window:
            self.window.destroy()
        if self.hud_window:
            self.hud_window.destroy()
        sys.exit(0)

    def log(self, message):
        """Log message from JS."""
        print(f"[JS Log] {message}")

    # --- Internal Event Handling ---

    def _engine_callback(self, data):
        """Callback received from STTEngine (runs in background thread)."""
        # Dispatch to UI immediately
        self.dispatch_event(data)

    def dispatch_event(self, data):
        """Send event data to JavaScript via handleEngineEvent()."""
        try:
            json_data = json.dumps(data)
            js_code = f"if(window.handleEngineEvent) window.handleEngineEvent({json_data})"

            # Send to Main Window
            if self.window:
                self.window.evaluate_js(js_code)

            # Send to HUD
            if self.hud_window:
                self.hud_window.evaluate_js(js_code)

        except Exception as e:
            print(f"[Bridge] Error dispatching event: {e}")
