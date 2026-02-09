import os
import sys
import shutil
import urllib.request
import zipfile
import pathlib
import threading
from colorama import Fore

class DependencyManager:
    """
    Handles external dependencies like FFmpeg for the STT engine.
    Ensures the app is portable by auto-downloading FFmpeg if missing.
    """
    
    @staticmethod
    def setup_ffmpeg():
        """Ensures ffmpeg.exe is available and in PATH."""
        # 1. Check if already in PATH
        if shutil.which("ffmpeg"):
            return True
            
        # 2. Check current directory and user app data
        app_data = pathlib.Path(os.getenv("APPDATA", ".")) / "EasySTT" / "bin"
        local_dir = pathlib.Path(__file__).parent.parent
        
        search_paths = [local_dir, app_data]
        for p in search_paths:
            if not p.exists(): continue
            ffmpeg_path = p / "ffmpeg.exe"
            if ffmpeg_path.exists():
                print(f"{Fore.GREEN}[DependencyManager] FFmpeg found in {p}. Patching PATH.")
                os.environ["PATH"] += os.pathsep + str(p)
                return True

        # 3. Auto-Download (Windows only for now)
        if sys.platform != "win32":
            print(f"{Fore.YELLOW}[DependencyManager] FFmpeg manual install required for {sys.platform}.")
            return False

        print(f"{Fore.YELLOW}[DependencyManager] FFmpeg missing. Downloading portable version...")
        app_data.mkdir(parents=True, exist_ok=True)
        
        # Using a reliable direct link to a portable ffmpeg build
        url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        zip_path = app_data / "ffmpeg.zip"
        
        try:
            # Download with progress hint
            print(f"{Fore.CYAN}Downloading FFmpeg (~100MB)...")
            urllib.request.urlretrieve(url, zip_path)
            
            print(f"{Fore.CYAN}Extracting FFmpeg...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    if file_info.filename.endswith("ffmpeg.exe"):
                        # Extract only ffmpeg.exe to the bin folder
                        file_info.filename = "ffmpeg.exe"
                        zip_ref.extract(file_info, app_data)
                        break
            
            # Cleanup
            if zip_path.exists():
                os.remove(zip_path)
                
            os.environ["PATH"] += os.pathsep + str(app_data)
            print(f"{Fore.GREEN}[DependencyManager] FFmpeg installed successfully to {app_data}.")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}[DependencyManager] FFmpeg auto-install failed: {e}")
            return False

    @staticmethod
    def async_setup():
        """Run setup in background if needed (non-blocking)."""
        thread = threading.Thread(target=DependencyManager.setup_ffmpeg, daemon=True)
        thread.start()
        return thread
