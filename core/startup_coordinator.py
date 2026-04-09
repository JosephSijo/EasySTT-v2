from PySide6.QtCore import QObject, Signal, Slot

from core.dependency_manager import DependencyManager
from core.validator import SetupValidator


class StartupCoordinator(QObject):
    """Runs blocking startup checks off the UI thread and reports readiness."""

    progressChanged = Signal(int, str, str)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, engine, config, hotkey_manager):
        super().__init__()
        self.engine = engine
        self.config = config
        self.hotkey_manager = hotkey_manager

    @Slot()
    def run(self):
        try:
            hotkey_warning = ""
            self.progressChanged.emit(10, "Checking system integrity", "Verifying core files, Python packages, and hardware support.")
            if not SetupValidator.validate():
                raise RuntimeError("System validation failed. Check the console for the missing dependency or file.")

            self.progressChanged.emit(30, "Preparing dependencies", "Ensuring FFmpeg and bundled runtime tools are available.")
            if not DependencyManager.setup_ffmpeg():
                raise RuntimeError("FFmpeg setup did not complete, so the app cannot finish startup safely.")

            self.progressChanged.emit(55, "Initializing AI services", "Refreshing provider settings and background engine state.")
            self.engine.refresh_ai_handler()

            self.progressChanged.emit(80, "Loading speech engine", "Preloading the active transcription model for fast first use.")
            self.engine.preload_model()

            shortcut = self.config.get("shortcut", "ctrl+alt+r")
            self.progressChanged.emit(95, "Binding global hotkey", f"Registering {shortcut.upper()} for recording control.")
            success, message = self.hotkey_manager.register(shortcut)
            if not success:
                hotkey_warning = (
                    f" Hotkey binding failed for {shortcut.upper()}; "
                    "use the on-screen record button or rebind it in Test Lab."
                )

            self.progressChanged.emit(100, "Everything is ready", f"{shortcut.upper()} is active and the transcription engine is loaded.")
            self.completed.emit(
                f"The transcription engine is ready.{hotkey_warning}".strip()
            )
        except Exception as exc:
            self.failed.emit(str(exc))
