import sys
import os
from PySide6.QtCore import QObject, Signal, Slot, QThread, QTimer
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
            self.stateChanged.emit("idle")
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
        
        # 1. Setup Worker
        self.worker = EngineWorker(self.engine)
        
        # 2. Connect UI to Controller Actions
        self._setup_connections()
        
        # 3. Initial State
        self.is_recording = False

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
        if self.is_recording: return
        self.is_recording = True
        
        # Switch View to Recording
        self.window.content_stack.setCurrentWidget(self.window.recording)
        self.window.recording.waveform.setActive(True)
        self.window.recording.main_text.setText("Listening...")
        self.window.recording.interim_text.setText("")
        
        # Start Engine
        self.engine.start_recording(self.worker.signal_callback)

    @Slot()
    def stop_recording(self):
        if not self.is_recording: return
        self.is_recording = False
        
        # Stop Engine (Engine will call callback with 'final' result)
        self.engine.stop_recording()
        self.window.recording.waveform.setActive(False)

    @Slot(dict)
    def _handle_transcription(self, data):
        text = data.get("text", "")
        if data.get("type") == "interim":
            self.window.recording.interim_text.setText(f"...{text}")
        elif data.get("type") == "final":
            self.window.recording.main_text.setText(text)
            self.window.recording.interim_text.setText("")

    @Slot(float)
    def _handle_audio_level(self, value):
        # Push amplitude level to the waveform widget
        # Normalize/Scale if necessary. STT Engine sends raw peak (0.0 to 1.0)
        if hasattr(self.window.recording.waveform, 'set_level'):
            self.window.recording.waveform.set_level(value)

    @Slot(str)
    def _handle_state_change(self, state):
        if state == "processing":
            self.window.recording.main_text.setText("Refining transcript with AI...")
        elif state == "idle":
            # Potentially stay on recording view for review or auto-switch back to home
            pass

    @Slot(bool)
    def _handle_connection(self, is_online):
        # Update status badge in settings if visible
        # For now, print or update a global status
        pass

    def get_resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller"""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)
