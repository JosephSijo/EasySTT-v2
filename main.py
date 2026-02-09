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
from ui.main_window import MainWindow

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
    
    # 4. Launch Main Window
    app = MainWindow(config, engine)
    
    # 6. Register Global Hotkey
    shortcut = config.get("shortcut", "ctrl+alt+r")
    try:
        keyboard.add_hotkey(shortcut, lambda: app.after(0, app.toggle_mic))
        print(f"{Fore.GREEN}✓ Global hotkey registered: {shortcut.upper()}")
    except Exception as e:
        print(f"{Fore.RED}✗ Could not bind hotkey '{shortcut}': {e}")
        print(f"{Fore.YELLOW}  Tip: Try running as Administrator or change hotkey in Settings")
    
    # 7. Run Application
    print(f"{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"{Fore.GREEN}🚀 Application Ready! Use {shortcut.upper()} to toggle recording.")
    print(f"{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Fore.RESET}")
    
    try:
        app.mainloop()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Shutting down...")
    finally:
        keyboard.unhook_all()
        print(f"{Fore.GREEN}EasySTT closed. Goodbye!")


if __name__ == "__main__":
    main()
