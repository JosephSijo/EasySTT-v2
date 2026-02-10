# EasySTT v2.0 - Integrated Desktop Application
# Entry point with GUI Onboarding and Enhanced HUD

import sys
import colorama
import keyboard
from colorama import Fore

from core.config_manager import ConfigManager
from core.engine import STTEngine
from core.personalization import PersonalizationManager
from core.validator import SetupValidator
from core.dependency_manager import DependencyManager
from ui.qt_main_window import QtMainWindow
from core.controller import AppController
from PySide6.QtWidgets import QApplication

# Initialize Colorama for Terminal Logging
colorama.init(autoreset=True)

def main():
    print(f"{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"{Fore.WHITE}       EasySTT v2.0 - Desktop Application        ")
    print(f"{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Fore.RESET}")
    
    # 1. Setup Validation & Dependency Check
    if not SetupValidator.validate():
        print(f"{Fore.RED}✗ System validation failed. Exiting.")
        sys.exit(1)
        
    DependencyManager.setup_ffmpeg()
    
    # 2. Initialize Configuration
    config = ConfigManager()
    print(f"{Fore.GREEN}✓ Configuration loaded")
    
    # 2. Initialize Engine
    engine = STTEngine(config)
    print(f"{Fore.GREEN}✓ STT Engine initialized")
    
    # 3. Preload Whisper Model (background thread)
    import threading
    threading.Thread(target=engine.preload_model, daemon=True).start()
    
    # 4. Launch Main Window & Controller
    qt_app = QApplication(sys.argv)
    window = QtMainWindow(config, engine)
    controller = AppController(window, engine, config)
    
    # 6. Register Global Hotkey
    shortcut = config.get("shortcut", "ctrl+alt+r")
    try:
        # Connect hotkey to controller start/stop toggle
        keyboard.add_hotkey(shortcut, lambda: controller.start_recording() if not controller.is_recording else controller.stop_recording())
        print(f"{Fore.GREEN}✓ Global hotkey registered: {shortcut.upper()}")
    except Exception as e:
        print(f"{Fore.RED}✗ Could not bind hotkey '{shortcut}': {e}")
    
    # 7. Run Application
    print(f"{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"{Fore.GREEN}🚀 Application Ready! Use {shortcut.upper()} to toggle recording.")
    print(f"{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Fore.RESET}")
    
    try:
        sys.exit(qt_app.exec())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Shutting down...")
    finally:
        keyboard.unhook_all()
        print(f"{Fore.GREEN}EasySTT closed. Goodbye!")


if __name__ == "__main__":
    main()
