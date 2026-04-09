# EasySTT v2.0 - Integrated Desktop Application
# Entry point with GUI Onboarding and Enhanced HUD

import sys
import colorama
from colorama import Fore

from core.config_manager import ConfigManager
from core.engine import STTEngine
from core.hotkey_manager import HotkeyManager
from core.personalization import PersonalizationManager
from core.startup_coordinator import StartupCoordinator
from ui.qt_main_window import QtMainWindow
from core.controller import AppController
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread, QTimer

# Initialize Colorama for Terminal Logging
colorama.init(autoreset=True)

def main():
    print(f"{Fore.CYAN}===============================================")
    print(f"{Fore.WHITE}       EasySTT v2.0 - Desktop Application        ")
    print(f"{Fore.CYAN}==============================================={Fore.RESET}")

    # 1. Initialize Configuration
    config = ConfigManager()
    print(f"{Fore.GREEN}✓ Configuration loaded")

    # 2. Initialize Engine
    engine = STTEngine(config)
    print(f"{Fore.GREEN}✓ STT Engine initialized")

    hotkey_manager = HotkeyManager()

    # 3. Launch Main Window & Controller
    qt_app = QApplication(sys.argv)
    window = QtMainWindow(config, engine, hotkey_manager)
    controller = AppController(window, engine, config)
    controller.set_ready(False)

    def toggle_recording():
        QTimer.singleShot(
            0,
            lambda: controller.stop_recording() if controller.is_recording else controller.start_recording(),
        )

    hotkey_manager.set_primary_handler(toggle_recording)

    startup_thread = QThread()
    startup_worker = StartupCoordinator(engine, config, hotkey_manager)
    startup_worker.moveToThread(startup_thread)
    startup_thread.started.connect(startup_worker.run)
    startup_worker.progressChanged.connect(window.update_startup_progress)
    startup_worker.completed.connect(controller.handle_startup_complete)
    startup_worker.failed.connect(controller.handle_startup_failed)
    startup_worker.completed.connect(startup_thread.quit)
    startup_worker.failed.connect(startup_thread.quit)
    startup_thread.finished.connect(startup_worker.deleteLater)
    startup_thread.finished.connect(startup_thread.deleteLater)
    window.startup_thread = startup_thread
    window.startup_worker = startup_worker
    startup_thread.start()

    # 4. Run Application
    print(f"{Fore.CYAN}===============================================")
    print(f"{Fore.WHITE}[Startup] Running readiness checks...")
    print(f"{Fore.CYAN}==============================================={Fore.RESET}")
    
    try:
        sys.exit(qt_app.exec())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Shutting down...")
    finally:
        if startup_thread.isRunning():
            startup_thread.quit()
            startup_thread.wait(3000)
        hotkey_manager.shutdown()
        print(f"{Fore.GREEN}EasySTT closed. Goodbye!")


if __name__ == "__main__":
    main()
