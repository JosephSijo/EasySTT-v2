import os
import webview
from ui.web_bridge import WebBridge

class WebWindow:
    """
    Main application controller managing pywebview windows.
    """
    def __init__(self, config, engine):
        self.config = config
        self.engine = engine
        self.bridge = WebBridge(engine, config)

        # Base directory for HTML files
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.web_dir = os.path.join(self.base_dir, "web_ui")

        self.main_window = None
        self.hud_window = None

        self._init_windows()

    def _init_windows(self):
        # 1. Main Workspace Window
        index_path = os.path.join(self.web_dir, "index.html")
        self.main_window = webview.create_window(
            "EzSTT Workspace",
            url=f"file://{index_path}",
            width=1280, height=800,
            min_size=(800, 600),
            js_api=self.bridge,
            resizable=True,
            frameless=False
        )
        self.bridge.attach_window(self.main_window, "main")

        # 2. HUD Window (Floating, Transparent)
        hud_path = os.path.join(self.web_dir, "hud.html")
        self.hud_window = webview.create_window(
            "EzSTT HUD",
            url=f"file://{hud_path}",
            width=400, height=120,
            js_api=self.bridge,
            frameless=True,
            transparent=True,
            on_top=True,
            x=50, y=50 # Position it somewhere visible
        )
        self.bridge.attach_window(self.hud_window, "hud")

    def run(self):
        """Start the webview GUI loop."""
        # debug=True enables the Inspector (F12)
        webview.start(debug=True)
