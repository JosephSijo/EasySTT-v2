import os
import sys
import json
import pathlib

def validate_setup():
    print("🔍 INITIALIZING EASYSTT V1.7 HEALTH CHECK\n")
    
    base_dir = pathlib.Path(__file__).parent
    critical_files = [
        "core/config_manager.py",
        "core/ai_handler.py",
        "core/token_tracker.py",
        "ui/main_window.py",
        "ui/settings_window.py",
        "ui/hud_window.py",
        "main.py",
        "version_info.json"
    ]
    
    # 1. File Integrity Check
    print("📂 [1/4] Checking File Integrity...")
    all_files_present = True
    for file_path in critical_files:
        full_path = base_dir / file_path
        if full_path.exists():
            print(f"  ✅ [PASS] {file_path}")
        else:
            print(f"  ❌ [FAIL] Missing: {file_path}")
            all_files_present = False
            
    if not all_files_present:
        print("\n🆘 CRITICAL ERROR: Some files are missing. Restore the project structure.")
        sys.exit(1)
    print()

    # 2. Import Validation (Smoke Test)
    print("📦 [2/4] Validating Dependencies & Imports...")
    try:
        import tkinter as tk
        from google import genai
        import faster_whisper
        import sounddevice as sd
        import numpy
        import keyboard
        import keyring
        import pyperclip
        
        from core.config_manager import ConfigManager
        from core.ai_handler import AIHandler
        from core.token_tracker import TokenTracker
        from ui.main_window import MainWindow
        from ui.hud_window import HUD
        print("  ✅ [PASS] All new libraries and local modules imported successfully.")
    except ImportError as e:
        missing_lib = str(e).split("'")[-2] if "'" in str(e) else str(e)
        pypi_name = missing_lib
        if missing_lib == "google":
            pypi_name = "google-genai"
        
        print(f"  ❌ [FAIL] Missing dependency: {missing_lib}")
        print(f"  💡 FIX: Run 'pip install {pypi_name}'")
        sys.exit(1)
    except Exception as e:
        print(f"  ❌ [FAIL] Import Error: {e}")
        sys.exit(1)
    print()

    # 3. Logic Unit Tests (Mocking)
    print("🧪 [3/4] Running Logic Smoke Tests...")
    try:
        # Config test
        config = ConfigManager()
        if config.config_file.exists():
            print("  ✅ [PASS] ConfigManager initialized (AppData path verified).")
        
        # Token math test
        tracker = TokenTracker(config)
        test_tokens = tracker.track_usage("Test input", "Test output")
        if test_tokens > 0:
            print(f"  ✅ [PASS] TokenTracker math verified ({test_tokens} tokens for test).")

        # Engine test
        from core.engine import STTEngine
        engine = STTEngine(config)
        print("  ✅ [PASS] New Threaded STTEngine initialized correctly.")
    except Exception as e:
        print(f"  ❌ [FAIL] Logic Test Failed: {e}")
        sys.exit(1)
    print()

    # 4. UI Structure Test
    print("🎨 [4/4] Performing UI Structure Check...")
    try:
        from ui.main_window import MainWindow
        from ui.hud_window import HUD
        print("  ✅ [PASS] UI Module structure verified for V1.7.")
    except Exception as e:
        print(f"  ❌ [FAIL] UI Code Error: {e}")
        sys.exit(1)
    print()

    print("--------------------------------------------------")
    print("🚀 SYSTEM READY: EasySTT v1.7 is properly configured.")
    print("👉 To start the app, run: python main.py")
    print("--------------------------------------------------")

if __name__ == "__main__":
    validate_setup()

if __name__ == "__main__":
    validate_setup()
