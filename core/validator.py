import os
import sys
import pathlib
import platform
import subprocess
from colorama import Fore

class SetupValidator:
    """
    Performs integrity and health checks on app startup.
    Ported from v1 to ensure production readiness.
    """
    
    CRITICAL_FILES = [
        "core/engine.py",
        "core/controller.py",
        "core/vocabulary_engine.py",
        "core/plugin_manager.py",
        "core/hotkey_manager.py",
        "ui/qt_main_window.py",
        "ui/qt_widgets.py",
        "main.py",
        "config.json"
    ]
    
    @staticmethod
    def validate():
        print(f"{Fore.CYAN}[Validator] Checking system integrity...")
        base_dir = pathlib.Path(__file__).parent.parent
        
        # 1. File Integrity
        missing = []
        for f in SetupValidator.CRITICAL_FILES:
            if not (base_dir / f).exists():
                # Don't fail if config doesn't exist yet, it will be created
                if f == "config.json": continue
                missing.append(f)
        
        if missing:
            print(f"{Fore.RED}[Validator] FAILED: Missing critical files: {', '.join(missing)}")
            return False
        
        # 2. Dependency Check (Brief)
        try:
            import faster_whisper
            import sounddevice as sd
            import numpy as np
            import PySide6
        except ImportError as e:
            print(f"{Fore.RED}[Validator] FAILED: Missing libraries. Run 'pip install -r requirements.txt'")
            print(f"Details: {e}")
            return False

        # 3. Hardware Check
        device = "CPU"
        try:
            import torch

            if torch.cuda.is_available():
                device = f"GPU (CUDA: {torch.cuda.get_device_name(0)})"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device = "Apple Silicon (MPS)"
        except ImportError:
            pass
            
        print(f"{Fore.GREEN}[Validator] Platform: {platform.system()} {platform.release()}")
        print(f"{Fore.GREEN}[Validator] Hardware: {device}")
        print(f"{Fore.GREEN}[Validator] Integrity: All core modules verified.")
        return True
