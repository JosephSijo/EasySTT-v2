import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Mock dependencies
sys.modules['sounddevice'] = MagicMock()
sys.modules['webview'] = MagicMock()
sys.modules['core.engine'] = MagicMock()

# We need to be able to import ui.web_bridge, but we mocked core.engine.
# ui.web_bridge imports nothing from core, so it should be fine.

from ui.web_bridge import WebBridge
from ui.web_window import WebWindow

class TestWebBridge(unittest.TestCase):
    def setUp(self):
        self.mock_engine = MagicMock()
        self.mock_config = MagicMock()
        self.bridge = WebBridge(self.mock_engine, self.mock_config)
        self.bridge.window = MagicMock()
        self.bridge.hud_window = MagicMock()

    def test_start_recording(self):
        self.mock_engine.is_recording = False
        result = self.bridge.start_recording()
        self.assertTrue(result['success'])
        self.mock_engine.start_recording.assert_called_once()
        # It calls dispatch_event -> evaluate_js
        self.bridge.window.evaluate_js.assert_called()

    def test_stop_recording(self):
        self.mock_engine.is_recording = True
        result = self.bridge.stop_recording()
        self.assertTrue(result['success'])
        self.mock_engine.stop_recording.assert_called_once()

    def test_dispatch_event(self):
        data = {"type": "test"}
        self.bridge.dispatch_event(data)
        # Should be called for both windows
        self.assertTrue(self.bridge.window.evaluate_js.called)
        self.assertTrue(self.bridge.hud_window.evaluate_js.called)

class TestWebWindow(unittest.TestCase):
    @patch('ui.web_window.webview')
    def test_init(self, mock_webview):
        mock_engine = MagicMock()
        mock_config = MagicMock()

        # We need to mock os.path.abspath because web_window uses it
        with patch('os.path.abspath', return_value='/app/ui'):
            window = WebWindow(mock_config, mock_engine)

            # Verify bridge created
            self.assertIsInstance(window.bridge, WebBridge)

            # Verify windows created (Main + HUD)
            # create_window is called twice
            self.assertEqual(mock_webview.create_window.call_count, 2)

            # Verify start is calling webview.start
            window.run()
            mock_webview.start.assert_called()

if __name__ == '__main__':
    unittest.main()
