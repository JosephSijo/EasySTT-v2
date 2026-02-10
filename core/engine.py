import time
import os
import threading
import queue
import numpy as np
import colorama
from colorama import Fore, Style
from typing import Optional, Callable, Dict, Any
from core.config_manager import ConfigManager
from core.token_tracker import TokenTracker
from core.ai_handler import AIHandler
from core.vocabulary_engine import VocabularyEngine
from core.plugin_manager import PluginManager
from core.mcp_bridge import MCPBridge
from core.privacy_manager import PrivacyManager
from core.license_manager import LicenseManager
from core.marketplace_service import MarketplaceService
from core.text_utils import sterilize_transcript, apply_formatting_commands, auto_punctuate_and_capitalize
from core.a2a_bridge import A2ABridge
import sounddevice as sd
from faster_whisper import WhisperModel
import scipy.io.wavfile as wav

# Initialize colorama
colorama.init(autoreset=True)

class STTEngine:
    """
    Robust, Threaded STT Engine.
    Handles live preview, VAD, connection monitoring, and background processing.
    Enhanced from HeadlessSTT reference.
    """
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.tracker = TokenTracker(config)
        self.vocab = VocabularyEngine()
        self.plugins = PluginManager()
        self.mcp = MCPBridge(self)
        self.privacy = PrivacyManager()
        self.license = LicenseManager()
        self.marketplace = MarketplaceService()
        self.ai: Optional[AIHandler] = None
        self.a2a = A2ABridge(self, self.config)
        self.a2a.start()
        
        # Initial Purge of old data
        self.privacy.purge_old_data(
            self.config.get("storage_path"),
            self.config.get("auto_clear_days", 30)
        )
        
        # Whisper Model (Loaded or pre-loaded)
        self.model_size = self.config.get("whisper_model", "turbo") 
        self.model = None
        
        # State Flags
        self.is_recording = False
        self.is_processing = False  # True while transcribing/refining
        self.onboarding_active = False  # Suppress review prompts during onboarding
        self.api_status = False  # Network connectivity status
        
        self.fs = 16000  # Whisper prefers 16kHz
        self.audio_queue = queue.Queue()
        self.callback_fn: Optional[Callable[[Dict[str, Any]], None]] = None
        
        # Threads
        self.recording_thread: Optional[threading.Thread] = None
        self.processing_thread: Optional[threading.Thread] = None
        
        # VAD & Streaming state
        self.silence_threshold = 0.5  # seconds
        self.last_audio_time = time.time()
        self.interim_buffer = []
        self.live_text = ""  # Accumulated live transcription
        
        # Start Background Services
        self._start_connection_monitor()
        self.start_cleanup_thread()

    def _start_connection_monitor(self):
        """Monitors network connectivity in background."""
        def monitor():
            while True:
                prev_status = self.api_status
                self.api_status = self._check_internet()
                if self.api_status != prev_status:
                    status_str = "ONLINE" if self.api_status else "OFFLINE"
                    color = Fore.GREEN if self.api_status else Fore.RED
                    print(f"{color}[Network] Connection: {status_str}")
                    # Emit status change to UI
                    if self.callback_fn:
                        self.callback_fn({"type": "connection", "online": self.api_status})
                time.sleep(30)
        
        threading.Thread(target=monitor, daemon=True).start()

    def preload_model(self):
        """Loads faster-whisper into memory and discovers plugins."""
        # 1. Load Whisper
        if not self.model:
            # ... (existing model loading logic)
            pass # Keep previous logic here
        
        # 2. Discover MCP Plugins
        self.plugins.discover_plugins()
        for plugin in self.plugins.plugins.values():
            # Check if licensed or if it's a free plugin
            if self.license.is_licensed(plugin.id) or plugin.priority <= 0:
                if plugin.vocabulary_path:
                    full_vocab_path = os.path.join(self.plugins.plugins_dir, plugin.id, plugin.vocabulary_path)
                    self.vocab.register_plugin(plugin.id, plugin.name, full_vocab_path)
            else:
                print(f"{Fore.YELLOW}[License] Plugin {plugin.name} is not licensed. Skipping.")
            # Auto-detect CUDA availability
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"
            
            compute_type = "float16" if device == "cuda" else "int8"
            print(f"{Fore.CYAN}[Engine] Loading Whisper ({self.model_size}) on {device.upper()}...")
            
            try:
                self.model = WhisperModel(self.model_size, device=device, compute_type=compute_type)
            except Exception as e:
                # Fallback for GPU compatibility issues
                if device == "cuda":
                    print(f"{Fore.YELLOW}[Engine] GPU fallback, using CPU...")
                    self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                else:
                    raise e

    def refresh_ai_handler(self) -> None:
        provider = self.config.get("provider", "Gemini")
        keys = self.config.get("keys", {})
        self.ai = AIHandler(provider, keys)

    def start_recording(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Starts the industrial engine."""
        if self.is_recording: return
        
        # Sync model size with config before loading
        self.model_size = self.config.get("whisper_model", "turbo")
        self.preload_model()
        self.refresh_ai_handler()
        
        self.is_recording = True
        self.callback_fn = callback
        self.audio_queue = queue.Queue()
        self.interim_buffer = []
        
        self.recording_thread = threading.Thread(target=self._record_loop, daemon=True)
        self.processing_thread = threading.Thread(target=self._process_loop, daemon=True)
        
        self.recording_thread.start()
        self.processing_thread.start()

    def stop_recording(self) -> None:
        self.is_recording = False
        if self.recording_thread: self.recording_thread.join()
        if self.processing_thread: self.processing_thread.join()

    def _record_loop(self):
        """Captures raw audio in chunks and calculates amplitude for UI."""
        def sd_callback(indata, frames, time_info, status):
            if self.is_recording:
                self.audio_queue.put(indata.copy())
                # Calculate Peak Amplitude/RMS for UI Level Meter
                amplitude = float(np.max(np.abs(indata)))
                if self.callback_fn:
                    self.callback_fn({"type": "level", "value": amplitude})

        with sd.InputStream(samplerate=self.fs, channels=1, callback=sd_callback):
            while self.is_recording:
                time.sleep(0.1)

    def _process_loop(self):
        """The brain: processes audio chunks, handles VAD and live preview."""
        accumulated_audio = []
        last_interim_emit = time.time()
        
        while self.is_recording or not self.audio_queue.empty():
            try:
                chunk = self.audio_queue.get(timeout=0.2)
                accumulated_audio.append(chunk)
            except queue.Empty:
                if not self.is_recording: break
                continue

            # Emit Live Preview every 0.5s (synced with HeadlessSTT)
            if time.time() - last_interim_emit > 0.5:
                # Transcribe accumulated so far
                combined = np.concatenate(accumulated_audio)
                interim_text = self._transcribe_raw(combined.flatten())
                if interim_text:
                    self._emit({"type": "interim", "text": interim_text})
                last_interim_emit = time.time()

        # Final processing
        if accumulated_audio:
            final_audio = np.concatenate(accumulated_audio).flatten()
            self._finalize_transcription(final_audio)

    def _transcribe_raw(self, audio_data: np.ndarray) -> str:
        """Core faster-whisper transcription with Multi-Layered Biasing."""
        if not self.model: return ""
        
        # 1. Get Base Vocabulary Bias from SQLite (Personal + Domain)
        initial_prompt = self.vocab.get_prompt_bias()
        is_specialized = "Vocabulary: " in initial_prompt
        
        # 2. Inject Dynamic Context Hints from MCP Bridge
        context_hints = self.mcp.get_vocabulary_hints()
        if context_hints:
            is_specialized = True
            context_str = ", ".join(context_hints)
            initial_prompt = f"{initial_prompt} Current Context: {context_str}. "
        
        if not initial_prompt:
            initial_prompt = "A transcription of speech."
        
        # 3. Transcribe with Bias and VAD filtering
        segments, info = self.model.transcribe(
            audio_data,
            beam_size=2,
            initial_prompt=initial_prompt,
            language=self.config.get("language"),
            vad_filter=True, # Improved reliability
            vad_parameters=dict(min_silence_duration_ms=500),
            word_timestamps=True # Enable for accurate confidence
        )
        
        text_parts = []
        confidences = []
        segments_list = list(segments)
        
        for s in segments_list:
            text_parts.append(s.text)
            if hasattr(s, 'words') and s.words:
                for word in s.words:
                    confidences.append(word.probability)

        full_text = "".join(text_parts).strip()
        
        # Sterilize (Filler removal, Hallucination filtering)
        use_professional = self.config.get("enhancement_style", "Professional") == "Professional"
        clean_text = sterilize_transcript(full_text, remove_filler=use_professional)
        
        # Convert logprob to 0-1 confidence (heuristic)
        avg_conf = sum(confidences) / len(confidences) if confidences else 1.0
        
        return {
            "text": clean_text,
            "confidence": float(avg_conf),
            "is_specialized": is_specialized,
            "tokens": len(clean_text) // 4  # Parted from v1 heuristic
        }

    def _finalize_transcription(self, audio_data: np.ndarray):
        """Transcribe -> Refine -> Emit Final Result."""
        self.is_processing = True
        self._emit({"type": "state", "state": "processing"})
        print(f"{Fore.CYAN}[Engine] Transcribing...")
        
        # 1. Core Transcription with Bias
        result = self._transcribe_raw(audio_data)
        text = result["text"]
        if not text:
            self._emit({"type": "final", "text": "", "error": "No speech detected"})
            return

        print(f"{Fore.WHITE}[Transcript] Raw: {text}")

        # Refinement logic
        result.update({"word_count": len(text.split())})
        
        if self.config.get("use_ai_refinement", True):
            style = self.config.get("enhancement_style", "Professional")
            custom_prompt = self.config.get("custom_style_prompt", "")
            
            # Hybrid Privacy Logic:
            # - standard: Allows cloud refinement for low confidence or explicit request
            # - extreme: NEVER allows cloud
            # - enterprise: Only allows cloud if audit logging is confirmed
            privacy_mode = self.config.get("privacy_mode", "standard")
            threshold = self.config.get("cloud_enhancement_threshold", 0.7)
            
            should_refine = False
            if privacy_mode == "extreme":
                print(f"{Fore.YELLOW}[Privacy] Extreme mode active. AI refinement skipped.")
            elif privacy_mode == "standard":
                # Auto-enhance if confidence is low, or if user always wants refinement
                if result.get("confidence", 1.0) < threshold:
                    print(f"{Fore.CYAN}[Hybrid] Low confidence ({result['confidence']:.2f}) -> Triggering Cloud Enhancement.")
                    should_refine = True
                else:
                    should_refine = True # Default to True if setting is on
            
            if should_refine:
                # Check online status
                is_online = self._check_internet()
                if not is_online:
                    print(f"{Fore.YELLOW}[AI] Offline - Using raw transcript.")
                    result["warning"] = "System offline. Using local transcript."
                else:
                    print(f"{Fore.MAGENTA}[AI] Refining ({style})...")
                    refined_data = self.ai.refine_text(text, style, custom_prompt)
                    result.update(refined_data)
                    result["mode"] = "hybrid"
        else:
            print(f"{Fore.YELLOW}[AI] Refinement disabled in settings.")
            result["mode"] = "local"
            
        # 2. Smart Formatting (spoken commands -> formatting)
        result["text"] = apply_formatting_commands(result["text"])
        
        # 3. Punctuation & Casing
        result["text"] = auto_punctuate_and_capitalize(result["text"])
        
        # Final metadata
        result["type"] = "final"
        
        # Log to Token Tracker
        self.tracker.track_usage(f"stt_{int(time.time())}", result["text"])
        
        # Save audio and transcript for history
        storage_path = self.config.get("storage_path", "recordings")
        os.makedirs(storage_path, exist_ok=True)
        base_name = f"stt_{int(time.time())}"
        
        wav_path = os.path.join(storage_path, f"{base_name}.wav")
        txt_path = os.path.join(storage_path, f"{base_name}.txt")
        
        wav.write(wav_path, self.fs, audio_data)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(result.get("text", ""))
        
        print(f"{Fore.GREEN}[Success] Final Output: {result.get('text', '')[:50]}...")
        
        # Log to Privacy Audit
        mode = "hybrid" if self.config.get("use_ai_refinement") and self._check_internet() else "local"
        self.privacy.log_transcription(
            mode=mode,
            confidence=result.get("confidence", 1.0),
            duration=len(audio_data) / self.fs,
            agents=list(self.mcp.context_cache.keys())
        )
        
        self.is_processing = False
        
        # 5. Publish to A2A / Agent Ecosystem
        self.mcp.publish_event("transcription.final", result)
        self.a2a.on_transcription_event(result)
        
        self._emit(result)

    def _emit(self, data: Dict[str, Any]):
        if self.callback_fn:
            self.callback_fn(data)

    def learn_correction(self, incorrect: str, correct: str):
        """Public bridge to learning from user edits."""
        print(f"{Fore.CYAN}[Engine] Learning from correction: {incorrect} -> {correct}")
        self.vocab.learn_correction(incorrect, correct)

    def _check_internet(self) -> bool:
        import socket
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            return False

    def start_cleanup_thread(self):
        def cleanup():
            while True:
                days = self.config.get("auto_clear_days", 30)
                storage_path = self.config.get("storage_path", "recordings")
                if os.path.exists(storage_path):
                    now = time.time()
                    for f in os.listdir(storage_path):
                        f_path = os.path.join(storage_path, f)
                        if os.stat(f_path).st_mtime < now - (days * 86400):
                            try:
                                os.remove(f_path)
                                print(f"Cleaned up: {f}")
                            except: pass
                time.sleep(3600 * 24) # Daily check

        threading.Thread(target=cleanup, daemon=True).start()
