import os
import sys
import time
import json
import threading
import queue
import datetime
import shutil
import socket
import urllib.request
import zipfile
import argparse
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
import keyboard
import pyperclip
import colorama
from colorama import Fore, Style
from faster_whisper import WhisperModel
from core.personalization import PersonalizationManager

# Initialize Colorama for Terminal UI
colorama.init(autoreset=True)

# --- CONFIGURATION MANAGER ---
class Config:
    FILE = "config.json"
    DEFAULTS = {
        "storage_path": "recordings",
        "transcribes_path": "transcriptions",
        "auto_clear_days": 7,
        "language": "auto",  # 'en', 'hi', 'fr', etc.
        "provider": "Gemini", # Gemini or OpenAI
        "keys": {"Gemini": "", "OpenAI": ""},
        "model_size": "base",   # base, small, medium, turbo
        "engine_tier": "Basic", # Basic (Fast/Live) or Advanced (Full Pass)
        "shortcut": "ctrl+alt+s",
        "auto_clipboard": True,
        "use_ai_refinement": True,
        "manual_review": False, # If True, pauses for your edits after each recording
        "enhancement_style": "Professional" # Professional, Poetic, Verbatim
    }

    @staticmethod
    def load():
        abs_path = os.path.abspath(Config.FILE)
        print(f"{Fore.CYAN}[Config] Loading settings from: {abs_path}")
        
        if not os.path.exists(Config.FILE):
            return Config.DEFAULTS.copy()
            
        with open(Config.FILE, 'r') as f:
            data = json.load(f)
            
            # --- MIGRATION LOGIC ---
            needs_save = False
            # 1. Ensure keys dict exists
            if "keys" not in data:
                data["keys"] = Config.DEFAULTS["keys"].copy()
                needs_save = True
                
            # 2. Migrate legacy api_key if Gemini slot is empty
            if data["keys"].get("Gemini") == "" and "api_key" in data:
                data["keys"]["Gemini"] = data["api_key"]
                print(f"{Fore.GREEN}[Config] Migrated legacy API key to new format.")
                needs_save = True

            # Merge defaults to handle missing keys in old configs
            for k, v in Config.DEFAULTS.items():
                if k not in data:
                    data[k] = v
                    needs_save = True
            
            if needs_save:
                Config.save(data)
                
            return data

    @staticmethod
    def save(data):
        with open(Config.FILE, 'w') as f:
            json.dump(data, f, indent=4)

# --- UTILS: TOKEN & CLEANUP ---
class Utils:
    @staticmethod
    def count_tokens(text):
        # Simple heuristic: 1 token ~= 4 chars (Good enough for estimation)
        return len(text) // 4

    @staticmethod
    def word_count(text):
        return len(text.split())

    @staticmethod
    def auto_cleanup(folder, days):
        if not os.path.exists(folder): return
        print(f"{Fore.CYAN}[System] Running Auto-Cleanup (older than {days} days)...")
        now = time.time()
        deleted = 0
        cutoff = now - (days * 86400)
        for root, dirs, files in os.walk(folder):
            for f in files:
                fpath = os.path.join(root, f)
                if os.stat(fpath).st_mtime < cutoff:
                    try:
                        os.remove(fpath)
                        deleted += 1
                    except: pass
        if deleted > 0:
            print(f"{Fore.GREEN}[System] Cleaned up {deleted} old recording files.")

    @staticmethod
    def check_connection(provider="google.com"):
        try:
            socket.create_connection((provider, 80), timeout=2)
            return True
        except:
            return False

# --- DEPENDENCY MANAGER (FFMPEG AUTO-FIX) ---
class DependencyManager:
    @staticmethod
    def setup_ffmpeg():
        """Ensures ffmpeg.exe is available for Whisper subprocess."""
        # 1. Check Global PATH
        if shutil.which("ffmpeg"):
            return True
        
        # 2. Check Local Folders
        current_dir = os.path.dirname(os.path.abspath(__file__))
        local_bin = os.path.join(current_dir, "bin")
        
        for p in [current_dir, local_bin]:
            if not os.path.exists(p): continue
            ffmpeg_path = os.path.join(p, "ffmpeg.exe")
            if os.path.exists(ffmpeg_path):
                print(f"{Fore.GREEN}[System] FFmpeg found locally in {p}. Patching PATH.")
                os.environ["PATH"] += os.pathsep + p
                return True
        
        # 3. Auto-Download if absolutely missing
        print(f"{Fore.YELLOW}[System] FFmpeg missing. Downloading from GitHub (Required for Whisper)...")
        url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        zip_path = os.path.join(current_dir, "ffmpeg.zip")
        
        try:
            # Simple download
            urllib.request.urlretrieve(url, zip_path)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Find and extract ONLY ffmpeg.exe
                for file_info in zip_ref.infolist():
                    if file_info.filename.endswith("ffmpeg.exe"):
                        # We want to extract it to the current root for easy access
                        # Change name to omit the long zip prefix
                        file_info.filename = os.path.basename(file_info.filename)
                        zip_ref.extract(file_info, current_dir)
                        break
            
            # Cleanup Zip
            if os.path.exists(zip_path):
                os.remove(zip_path)
                
            # Add to PATH for this process session
            os.environ["PATH"] += os.pathsep + current_dir
            print(f"{Fore.GREEN}[System] FFmpeg installed successfully.")
            return True
        except Exception as e:
            print(f"{Fore.RED}[Error] FFmpeg auto-install failed: {e}")
            return False

# --- CORE ENGINE ---
class HeadlessEngine:
    def __init__(self):
        # 1. Dependency Check (Critical Fix)
        if not DependencyManager.setup_ffmpeg():
            print(f"{Fore.RED}[Critical] FFmpeg is missing and could not be installed. Whisper will fail.")
            sys.exit(1)

        # 2. Silence UserWarnings (Note: faster-whisper handles this natively)
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning)

        self.personalization = PersonalizationManager()
        self.cfg = Config.load()
        self.is_recording = False
        self.is_processing = False # True while transcribing
        self.onboarding_active = False # Suppress manual_review prompt during onboarding
        self.audio_data = []
        self.live_text = ""  # Accumulated live transcription
        self.samplerate = 16000
        self.model = None 
        self.api_status = False
        
        # Ensure storage exists
        os.makedirs(self.cfg["storage_path"], exist_ok=True)
        os.makedirs(self.cfg["transcribes_path"], exist_ok=True)
        
        # Start Background Threads
        threading.Thread(target=self._connection_monitor, daemon=True).start()
        threading.Thread(target=lambda: Utils.auto_cleanup(self.cfg["storage_path"], self.cfg["auto_clear_days"]), daemon=True).start()
        threading.Thread(target=lambda: Utils.auto_cleanup(self.cfg["transcribes_path"], self.cfg["auto_clear_days"]), daemon=True).start()
        
        # 3. Hardware & Resource Optimization
        try:
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            self.device = "cpu"
            
        cpu_cores = os.cpu_count() or 4
        self.threads = max(1, int(cpu_cores * 0.8))
        self.compute_type = "float16" if self.device == "cuda" else "int8"
        
        m_size = self.cfg.get("model_size", "base")
        print(f"{Fore.YELLOW}[Init] Device: {self.device.upper()} | Threads: {self.threads} | Model: {m_size}")
        
        try:
            self.model = WhisperModel(
                m_size, 
                device=self.device, 
                compute_type=self.compute_type,
                cpu_threads=self.threads,
                num_workers=1
            )
            print(f"{Fore.GREEN}[Init] Ready! Press {self.cfg['shortcut']} to record.")
        except Exception as e:
            print(f"{Fore.RED}[Error] Failed to load model '{m_size}': {e}")
            # Fallback for faster-whisper if float16 fails on some GPUs
            if self.device == "cuda" and self.compute_type == "float16":
                print(f"{Fore.YELLOW}[Init] Retrying with int8_float16...")
                try:
                    self.model = WhisperModel(m_size, device=self.device, compute_type="int8_float16")
                    print(f"{Fore.GREEN}[Init] Model loaded with fallback.")
                    return
                except: pass
            sys.exit(1)

    def _connection_monitor(self):
        while True:
            prev_status = self.api_status
            self.api_status = Utils.check_connection()
            if self.api_status != prev_status:
                status_str = "ONLINE" if self.api_status else "OFFLINE"
                color = Fore.GREEN if self.api_status else Fore.RED
                print(f"\n{color}[Network] Connection Status: {status_str}")
                # Reprint prompt
                if not self.is_recording:
                    sys.stdout.write(f"{Fore.WHITE}> Waiting for hotkey... \r")
            time.sleep(30)

    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        self.is_recording = True
        self.audio_data = []
        self.live_text = "" # Reset for new session
        print(f"\n{Fore.RED}🔴 RECORDING... (Press {self.cfg['shortcut']} to stop)")
        
        # Start Input Stream
        self.stream = sd.InputStream(callback=self._audio_callback, channels=1, samplerate=self.samplerate)
        self.stream.start()

        # Start Live Preview Thread (0.5s interval)
        threading.Thread(target=self._live_preview_loop, daemon=True).start()

    def _live_preview_loop(self):
        """Background loop to show what's being said in real-time."""
        while self.is_recording:
            time.sleep(0.5) # Fast 0.5s updates
            if not self.is_recording: break
            
            if len(self.audio_data) > 3:
                try:
                    # 1. Get FULL buffer for accumulation
                    full_audio = np.concatenate(self.audio_data, axis=0).flatten()
                    
                    # 2. Faster-Whisper Transcription on FULL buffer to ensure no data loss
                    # but with beam_size=1 for speed
                    segments, _ = self.model.transcribe(
                        full_audio, 
                        beam_size=1, 
                        vad_filter=True,
                        vad_parameters=dict(min_silence_duration_ms=500),
                        language=None if self.cfg['language'] == 'auto' else self.cfg['language']
                    )
                    
                    text_parts = [s.text for s in segments]
                    text = " ".join(text_parts).strip()
                    if text:
                        self.live_text = text # FULL accumulated transcript
                        # Display only the last 70 chars to keep terminal clean
                        display_text = text[-70:]
                        sys.stdout.write(f"\r{Fore.YELLOW}[Preview] {display_text} ")
                        sys.stdout.flush()
                except Exception:
                    pass

    def stop_recording(self):
        self.is_recording = False
        self.is_processing = True # Start processing
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
            
        if not self.audio_data:
            print(f"\r{Fore.RED}❌ No audio detected.{' ' * 80}")
            self.is_processing = False
            return

        # 1. Prepare Audio Data
        recording = np.concatenate(self.audio_data, axis=0).flatten()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 2. Save WAV for permanent history (Always do this)
        filename = f"{self.cfg['storage_path']}/rec_{timestamp}.wav"
        wav_data = (recording * 32767).astype(np.int16)
        write(filename, self.samplerate, wav_data)
        
        # 3. Choose Transcription Tier
        if self.cfg.get("engine_tier") == "Basic" and self.live_text:
            print(f"\r{Fore.GREEN}🟢 Using Fast-Path (Instant Full Output)...{' ' * 50}")
            # Final check to see if there's any pending text in the very end
            self.finalize_transcript(self.live_text, timestamp)
        else:
            print(f"\r{Fore.YELLOW}🟡 Processing High-Accuracy Pass (Full Stream)...{' ' * 50}") 
            self.process_audio(recording, timestamp)

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        self.audio_data.append(indata.copy())

    def process_audio(self, audio_data, timestamp):
        # 1. Local Faster-Whisper Transcription
        print(f"{Fore.CYAN}[Whisper] Transcribing with High-Accuracy Engine...")
        
        try:
            # Inject Personalization Bias
            prompt_bias = self.personalization.get_prompt_bias()
            full_prompt = prompt_bias + "A transcription of speech."
            
            # Optimized for Accuracy and Noise Rejection
            segments, info = self.model.transcribe(
                audio_data, 
                beam_size=2,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=700),
                initial_prompt=full_prompt, 
                language=None if self.cfg['language'] == 'auto' else self.cfg['language']
            )
            
            text_chunks = []
            for s in segments:
                # Basic cleanup
                chunk = s.text.strip()
                if chunk: text_chunks.append(chunk)
                
            raw_text = " ".join(text_chunks).strip()
        except Exception as e:
            print(f"{Fore.RED}[Error] Transcription failed: {e}")
            return
            
        if not raw_text:
            print(f"{Fore.YELLOW}[Whisper] No speech detected.")
            return

        self.finalize_transcript(raw_text, timestamp)

    def finalize_transcript(self, raw_text, timestamp):
        print(f"{Fore.WHITE}📝 Raw Transcript: {raw_text}")
        
        final_text = raw_text
        tokens_used = 0

        # 2. AI Refinement (If Online & Enabled)
        if self.cfg["use_ai_refinement"] and self.api_status:
            final_text, tokens_used = self.refine_with_ai(raw_text)
        elif self.cfg["use_ai_refinement"] and not self.api_status:
            print(f"{Fore.RED}[AI] Offline - Skipping refinement.")

        # 3. Final Output
        wc = Utils.word_count(final_text)
        print(f"\n{Fore.GREEN}✅ FINAL OUTPUT ({wc} words):")
        print(f"{Style.BRIGHT}{final_text}")
        
        if tokens_used > 0:
            print(f"{Fore.MAGENTA}💰 Est. Tokens Used: {tokens_used}")

        # 4. Save to Text File (Organized into folder)
        text_filename = f"{self.cfg['transcribes_path']}/STT_{timestamp}.txt"
        try:
            with open(text_filename, 'w', encoding='utf-8') as f:
                f.write(final_text)
            print(f"{Fore.GREEN}[System] Saved transcript to: {text_filename}")
        except Exception as e:
            print(f"{Fore.RED}[Error] Failed to save text file: {e}")

        # 5. Clipboard
        if self.cfg["auto_clipboard"]:
            pyperclip.copy(final_text)
            print(f"{Fore.BLUE}[System] Copied to clipboard.")

        # 6. Interactive Review & Auto-Learning
        if self.cfg.get("manual_review") and not self.onboarding_active:
            print(f"\n{Fore.CYAN}{'='*20} REVIEW MODE {'='*20}")
            print(f"{Fore.WHITE}Verify the text. Type corrections to teach the AI, or press Enter to accept.")
            correction = input(f"{Fore.MAGENTA}Edit: ").strip()
            
            if correction and correction != final_text:
                # Basic Auto-Learning: Identify new words
                orig_words = set(final_text.lower().split())
                corr_words = correction.split()
                new_terms = [w for w in corr_words if w.lower() not in orig_words and len(w) > 2]
                
                if new_terms:
                    for term in new_terms:
                        clean_term = "".join(c for c in term if c.isalnum())
                        if clean_term:
                            self.personalization.add_term("jargon", clean_term)
                            print(f"{Fore.GREEN}[Learned] New term: {clean_term}")
                
                final_text = correction
                # Re-copy to clipboard if edited
                if self.cfg["auto_clipboard"]:
                    pyperclip.copy(final_text)
                    print(f"{Fore.BLUE}[System] Updated clipboard with your edits.")

        self.is_processing = False
        print(f"{Fore.WHITE}\n> Waiting for hotkey... ")

    def refine_with_ai(self, text):
        provider = self.cfg["provider"]
        key = self.cfg["keys"].get(provider)
        style = self.cfg["enhancement_style"]
        
        if not key:
            print(f"{Fore.RED}[AI] No API Key for {provider}. Skipping.")
            return text, 0

        print(f"{Fore.MAGENTA}[AI] Refining ({provider} | {style})...")
        
        prompt = f"Rewrite the following text to be {style}. Remove fillers. Maintain meaning.\nInput: {text}"
        
        try:
            if provider == "Gemini":
                import google.generativeai as genai
                genai.configure(api_key=key)
                model = genai.GenerativeModel('gemini-2.0-flash')
                response = model.generate_content(prompt)
                return response.text.strip(), Utils.count_tokens(prompt + response.text)
            
            elif provider == "OpenAI":
                from openai import OpenAI
                client = OpenAI(api_key=key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content.strip(), response.usage.total_tokens
                
        except Exception as e:
            print(f"{Fore.RED}[AI Error] {e}")
            return text, 0

# --- VOICE ONBOARDING ---
class VoiceOnboarding:
    @staticmethod
    def run(engine):
        engine.onboarding_active = True
        print(f"\n{Fore.CYAN}{'='*50}")
        print(f"{Fore.WHITE}{Style.BRIGHT}   WELCOME TO VOICE ONBOARDING")
        print(f"{Fore.CYAN}{'='*50}\n")
        print(f"{Fore.WHITE}I will help you 'train' the AI to recognize your specific vocabulary.")
        print(f"You can use the hotkey ({engine.cfg['shortcut']}) OR follow the prompts below.\n")

        prompts = [
            ("NAME", "1. Please say: 'My name is [Your Name]'"),
            ("JARGON", "2. Please say some technical words or slang you use daily."),
            ("PHRASE", "3. Please say a frequent phrase you use when dictated.")
        ]

        for cat, msg in prompts:
            print(f"\n{Fore.YELLOW}{msg}")
            print(f"{Fore.GREEN}[Option A] Press {engine.cfg['shortcut']} and speak.")
            print(f"{Fore.CYAN}[Option B] Press ENTER to start/stop recording here.")
            
            # Wait for start (Hotkey or Enter)
            trigger = input(f"{Fore.WHITE}Press ENTER to start (or just use hotkey)...")
            if not engine.is_recording:
                engine.start_recording()
            
            # Wait for stop (Hotkey or Enter)
            input(f"{Fore.RED}🔴 Recording... Press ENTER to stop.")
            if engine.is_recording:
                engine.stop_recording()
            
            # CRITICAL: Wait for transcription to FINISH
            print(f"{Fore.YELLOW}⌛ Transcribing...")
            while engine.is_processing:
                time.sleep(0.1)
            
            # User will see the transcript on screen via engine.finalize_transcript
            print(f"\n{Fore.WHITE}Check the transcription above. If I got it wrong, type the CORRECT word/phrase below.")
            fix = input(f"{Fore.MAGENTA}Correction (or Enter to keep): ").strip()
            
            if fix:
                cat_map = {"NAME": "names", "JARGON": "jargon", "PHRASE": "phrases"}
                engine.personalization.add_term(cat_map[cat], fix)
                print(f"{Fore.GREEN}Learned: {fix}")
            else:
                print(f"{Fore.GREEN}Got it!")

        engine.onboarding_active = False
        print(f"\n{Fore.CYAN}Onboarding complete! Your personalized vocabulary is ready.{Style.RESET_ALL}\n")

# --- MAIN LOOP ---
if __name__ == "__main__":
    from colorama import init
    init(autoreset=True)
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--onboard", action="store_true", help="Run voice onboarding")
    args = parser.parse_args()

    # 1. Initialize Engine
    print(f"{Fore.CYAN}=== EasySTT Headless Engine v2.0 ===")
    
    # Check if vocabulary exists to suggest onboarding
    if not os.path.exists("vocabulary.json") and not args.onboard:
        print(f"{Fore.YELLOW}[Tip] No vocabulary found. Run with --onboard for Siri-style training!")

    engine = HeadlessEngine()
    
    # 2. Register Hotkey (Shared) - MUST happen before mode check
    shortcut = engine.cfg['shortcut']
    try:
        keyboard.add_hotkey(shortcut, engine.toggle_recording)
        print(f"{Fore.GREEN}[Hotkey] Registered '{shortcut}'")
    except Exception as e:
        print(f"{Fore.RED}[Error] Could not bind hotkey '{shortcut}': {e}")
        print(f"{Fore.YELLOW}Tip: Try running as Administrator if hotkey fails.")
        sys.exit(1)

    # 3. Handle Mode
    if args.onboard:
        VoiceOnboarding.run(engine)
    else:
        print(f"{Fore.GREEN}Headless STT Active. Listening...")
        try:
            keyboard.wait()
        except KeyboardInterrupt:
            pass
        print(f"\n{Fore.YELLOW}Exiting...")