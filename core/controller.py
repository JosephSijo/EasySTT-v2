import sys
import os
from PySide6.QtCore import QObject, Signal, Slot, QThread, QTimer
from PySide6.QtWidgets import QApplication
from typing import Dict, Any

class EngineWorker(QObject):
    """
    Worker to interface with the STTEngine.
    Emits signals that the UI can safely connect to.
    """
    transcriptionReceived = Signal(dict)
    levelUpdated = Signal(float)
    stateChanged = Signal(str)
    connectionChanged = Signal(bool)

    def __init__(self, engine):
        super().__init__()
        self.engine = engine

    def signal_callback(self, data: Dict[str, Any]):
        """
        Callback passed to the engine. Converts engine dict events to Qt Signals.
        """
        msg_type = data.get("type")
        if msg_type == "interim":
            self.transcriptionReceived.emit(data)
        elif msg_type == "final":
            self.transcriptionReceived.emit(data)
        elif msg_type == "refined":
            self.transcriptionReceived.emit(data)
        elif msg_type == "level":
            self.levelUpdated.emit(data.get("value", 0.0))
        elif msg_type == "state":
            self.stateChanged.emit(data.get("state"))
        elif msg_type == "connection":
            self.connectionChanged.emit(data.get("online", False))

class AppController(QObject):
    """
    The main orchestrator for EasySTT.
    Bridges the UI (Views) with the Backend (Engine).
    """
    def __init__(self, main_window, engine, config):
        super().__init__()
        self.window = main_window
        self.engine = engine
        self.config = config
        self.is_ready = False
        self.pending_finalize = False
        self._return_home_timer = QTimer(self)
        self._return_home_timer.setSingleShot(True)
        self._return_home_timer.timeout.connect(self._return_to_dashboard)
        
        # 1. Setup Worker
        self.worker = EngineWorker(self.engine)
        
        # 2. Connect UI to Controller Actions
        self._setup_connections()
        
        # 3. Initial State
        self.is_recording = False

    def set_ready(self, ready: bool):
        self.is_ready = ready

    @Slot(str)
    def handle_startup_complete(self, message: str):
        self.set_ready(True)
        self.window.finish_startup(message)

    @Slot(str)
    def handle_startup_failed(self, message: str):
        self.set_ready(False)
        self.window.fail_startup(message)

    def _setup_connections(self):
        # UI -> Controller
        self.window.dashboard.recordingRequested.connect(self.start_recording)
        self.window.recording.stopRequested.connect(self.stop_recording)
        
        # Controller/Worker -> UI updates
        self.worker.transcriptionReceived.connect(self._handle_transcription)
        self.worker.levelUpdated.connect(self._handle_audio_level)
        self.worker.stateChanged.connect(self._handle_state_change)
        self.worker.connectionChanged.connect(self._handle_connection)

    @Slot()
    def start_recording(self):
        if not self.is_ready or self.is_recording or self.engine.is_processing or self.pending_finalize:
            return
        self.is_recording = True
        self._return_home_timer.stop()
        
        # Switch View to Recording
        self.window.content_stack.setCurrentWidget(self.window.recording)
        self.window.recording.waveform.setActive(True)
        self.window.recording.det_label.setText("VOICE-FOCUSED CAPTURE")
        self.window.recording.main_text.setPlainText("Listening for a complete phrase...")
        self.window.recording.interim_text.setText("")
        self.window.recording.status_line.setText("Listening for speech...")
        
        # Start Engine
        self.engine.start_recording(self.worker.signal_callback)

    @Slot()
    def stop_recording(self):
        if not self.is_recording:
            return
        self.is_recording = False
        self.pending_finalize = True
        
        # Stop Engine (Engine will call callback with 'final' result)
        self.engine.stop_recording()
        self.window.recording.waveform.setActive(False)
        self.window.recording.status_line.setText("Processing final transcript...")

    @Slot(dict)
    def _handle_transcription(self, data):
        text = data.get("text", "")
        if data.get("type") == "interim":
            if text:
                self.window.recording.main_text.setPlainText(text)
                self.window.recording.interim_text.setText("Live preview")
                self.window.recording.status_line.setText("Capturing live preview...")
        elif data.get("type") == "final":
            self.is_recording = False
            self.pending_finalize = False
            self.window.recording.waveform.setActive(False)
            self.window.recording.main_text.setPlainText(text or "No speech detected. Try again with a clearer phrase.")
            self.window.recording.interim_text.setText("")
            self._copy_to_clipboard_if_enabled(text)
            self.window.refresh_transcript_history()
            if data.get("pending_refinement"):
                self.window.recording.status_line.setText("Local transcript ready. Optional AI cleanup is running in the background.")
                self._return_home_timer.start(4000)
            else:
                self.window.recording.status_line.setText("Final transcript ready.")
                self._return_home_timer.start(1200)
        elif data.get("type") == "refined":
            self.window.recording.main_text.setPlainText(text or self.window.recording.main_text.toPlainText())
            self.window.recording.interim_text.setText("")
            self.window.recording.status_line.setText("Background AI cleanup applied.")
            self._copy_to_clipboard_if_enabled(text)
            self.window.refresh_transcript_history()
            self._return_home_timer.start(1200)

    @Slot(float)
    def _handle_audio_level(self, value):
        # Push amplitude level to the waveform widget
        # Normalize/Scale if necessary. STT Engine sends raw peak (0.0 to 1.0)
        if hasattr(self.window.recording.waveform, 'set_level'):
            self.window.recording.waveform.set_level(value)

    @Slot(str)
    def _handle_state_change(self, state):
        if state == "processing":
            self.window.recording.status_line.setText("Transcribing locally...")
        elif state == "refining":
            self.window.recording.status_line.setText("Optional AI cleanup running in the background...")
        elif state == "idle" and self.is_recording:
            self.window.recording.status_line.setText("Ready for the next phrase.")

    def _copy_to_clipboard_if_enabled(self, text: str):
        if not text or not self.config.get("auto_clipboard", True):
            return
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)

    @Slot(bool)
    def _handle_connection(self, is_online):
        # Update status badge in settings if visible
        # For now, print or update a global status
        pass

    def _return_to_dashboard(self):
        if self.window.app_ready:
            self.window.content_stack.setCurrentWidget(self.window.dashboard)

    def get_resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller"""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)
