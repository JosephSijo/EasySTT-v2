import time
import os
import threading
import queue
import numpy as np
import colorama
from colorama import Fore, Style
from typing import Optional, Callable, Dict, Any
from scipy.signal import butter, sosfilt

try:
    import torch
except ImportError:  # pragma: no cover - optional runtime path
    torch = None

try:
    from silero_vad import VADIterator, load_silero_vad
except ImportError:  # pragma: no cover - optional runtime path
    VADIterator = None
    load_silero_vad = None

try:
    from pyrnnoise import RNNoise
except ImportError:  # pragma: no cover - optional runtime path
    RNNoise = None

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
        self.loaded_model_target: Optional[str] = None
        self.active_backend = "faster-whisper"
        
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
        self.chunk_duration_sec = 0.05
        self.preview_interval_sec = max(0.2, self.config.get("preview_interval_ms", 300) / 1000)
        self.preview_window_sec = max(2.0, self.config.get("preview_window_ms", 3500) / 1000)
        self.max_silence_sec = max(0.4, self.config.get("silence_duration_ms", 850) / 1000)
        self.min_speech_sec = max(0.15, self.config.get("min_speech_ms", 250) / 1000)
        self.vad_rms_threshold = float(self.config.get("vad_rms_threshold", 0.012))
        self.vad_noise_ratio = float(self.config.get("vad_noise_ratio", 2.0))
        self.auto_stop_on_silence = bool(self.config.get("auto_stop_on_silence", True))
        self.use_silero_vad = bool(self.config.get("use_silero_vad", True))
        self.noise_suppression_enabled = bool(self.config.get("noise_suppression_enabled", True))
        self.noise_suppression_engine = self.config.get("noise_suppression_engine", "rnnoise")
        self.rnnoise_speech_threshold = float(self.config.get("rnnoise_speech_threshold", 0.35))
        self.voice_focus_sos = None
        try:
            self.voice_focus_sos = butter(4, [120, 7800], btype="bandpass", fs=self.fs, output="sos")
        except Exception:
            self.voice_focus_sos = None
        self.silero_model = None
        self.silero_iterator = None
        self.silero_window_samples = 512
        self.silero_in_speech = False
        self.silero_last_error = ""
        self.rnnoise_stream = None
        self.rnnoise_last_error = ""
        
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
        preferred_engine = self.config.get("preferred_engine_profile", "faster-whisper")
        if preferred_engine != "faster-whisper":
            print(f"{Fore.YELLOW}[Engine] Preferred engine '{preferred_engine}' is cataloged but not yet integrated. Using faster-whisper.")

        model_target = self.config.get("whisper_model", "turbo")

        # 1. Discover plugin vocabularies
        self.plugins.discover_plugins()
        for plugin in self.plugins.plugins.values():
            # Check if licensed or if it's a free plugin
            if self.license.is_licensed(plugin.id) or plugin.priority <= 0:
                if plugin.vocabulary_path:
                    full_vocab_path = os.path.join(self.plugins.plugins_dir, plugin.id, plugin.vocabulary_path)
                    self.vocab.register_plugin(plugin.id, plugin.name, full_vocab_path)
            else:
                print(f"{Fore.YELLOW}[License] Plugin {plugin.name} is not licensed. Skipping.")

        # 2. Load model once for the currently selected target
        if self.model and self.loaded_model_target == model_target:
            self._ensure_vad_backend()
            self._ensure_noise_backend()
            return

        try:
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

        compute_type = "float16" if device == "cuda" else "int8"
        print(f"{Fore.CYAN}[Engine] Loading Whisper ({model_target}) on {device.upper()}...")

        try:
            self.model = WhisperModel(model_target, device=device, compute_type=compute_type)
        except Exception as e:
            if device == "cuda":
                print(f"{Fore.YELLOW}[Engine] GPU fallback, using CPU...")
                self.model = WhisperModel(model_target, device="cpu", compute_type="int8")
            else:
                raise e

        self.loaded_model_target = model_target
        self._ensure_vad_backend()
        self._ensure_noise_backend()

    def refresh_ai_handler(self) -> None:
        provider = self.config.get("provider", "Gemini")
        keys = self.config.get("keys", {})
        api_models = self.config.get("api_models", {})
        custom_api_profiles = self.config.get("custom_api_profiles", [])
        self.ai = AIHandler(provider, keys, api_models, custom_api_profiles)

    def start_recording(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Starts the industrial engine."""
        if self.is_recording or self.is_processing:
            return
        
        # Sync model size with config before loading
        self.model_size = self.config.get("whisper_model", "turbo")
        self.preview_interval_sec = max(0.2, self.config.get("preview_interval_ms", 300) / 1000)
        self.preview_window_sec = max(2.0, self.config.get("preview_window_ms", 3500) / 1000)
        self.max_silence_sec = max(0.4, self.config.get("silence_duration_ms", 850) / 1000)
        self.min_speech_sec = max(0.15, self.config.get("min_speech_ms", 250) / 1000)
        self.vad_rms_threshold = float(self.config.get("vad_rms_threshold", 0.012))
        self.vad_noise_ratio = float(self.config.get("vad_noise_ratio", 2.0))
        self.auto_stop_on_silence = bool(self.config.get("auto_stop_on_silence", True))
        self.use_silero_vad = bool(self.config.get("use_silero_vad", True))
        self.noise_suppression_enabled = bool(self.config.get("noise_suppression_enabled", True))
        self.noise_suppression_engine = self.config.get("noise_suppression_engine", "rnnoise")
        self.rnnoise_speech_threshold = float(self.config.get("rnnoise_speech_threshold", 0.35))
        self.preload_model()
        self.refresh_ai_handler()
        if self.silero_iterator is not None:
            try:
                self.silero_iterator.reset_states()
            except Exception:
                pass
        self.silero_in_speech = False
        if self.rnnoise_stream is not None:
            try:
                self.rnnoise_stream.reset()
            except Exception:
                pass
        
        self.is_recording = True
        self.is_processing = False
        self.callback_fn = callback
        self.audio_queue = queue.Queue()
        self.interim_buffer = []
        self.live_text = ""
        
        self.recording_thread = threading.Thread(target=self._record_loop, daemon=True)
        self.processing_thread = threading.Thread(target=self._process_loop, daemon=True)
        
        self.recording_thread.start()
        self.processing_thread.start()

    def stop_recording(self) -> None:
        self.is_recording = False

    def _record_loop(self):
        """Captures raw audio in chunks and calculates amplitude for UI."""
        def sd_callback(indata, frames, time_info, status):
            if self.is_recording:
                self.audio_queue.put(indata.copy())
                # Calculate Peak Amplitude/RMS for UI Level Meter
                amplitude = float(np.max(np.abs(indata)))
                if self.callback_fn:
                    self.callback_fn({"type": "level", "value": amplitude})

        device_id = self.config.get("selected_input_device")
        with sd.InputStream(
            samplerate=self.fs,
            channels=1,
            blocksize=self.silero_window_samples if self.silero_iterator is not None else int(self.fs * self.chunk_duration_sec),
            device=device_id,
            callback=sd_callback,
        ):
            while self.is_recording:
                time.sleep(0.1)

    def _process_loop(self):
        """Low-latency utterance loop with silence endpointing and rolling previews."""
        accumulated_audio = []
        last_interim_emit = time.time()
        speech_started = False
        speech_duration = 0.0
        silence_duration = 0.0
        noise_floor = self.vad_rms_threshold * 0.5
        
        while self.is_recording or not self.audio_queue.empty():
            try:
                chunk = self.audio_queue.get(timeout=0.2)
            except queue.Empty:
                if speech_started and silence_duration >= self.max_silence_sec:
                    break
                if not self.is_recording:
                    break
                continue

            flattened = chunk.flatten().astype(np.float32)
            duration = len(flattened) / self.fs
            stream_chunk, rnnoise_speech_prob = self._prepare_stream_chunk(flattened)
            is_speech, speech_level = self._detect_speech_activity(stream_chunk, noise_floor, rnnoise_speech_prob)
            if not speech_started:
                noise_floor = (noise_floor * 0.92) + (speech_level * 0.08)

            if is_speech:
                speech_started = True
                speech_duration += duration
                silence_duration = 0.0
                accumulated_audio.append(stream_chunk)
            elif speech_started:
                silence_duration += duration
                accumulated_audio.append(stream_chunk)

            if speech_started and time.time() - last_interim_emit >= self.preview_interval_sec:
                preview_audio = self._build_preview_audio(accumulated_audio)
                interim_result = self._transcribe_raw(
                    preview_audio,
                    remove_fillers=False,
                    beam_size=1,
                    preview_mode=True,
                )
                if interim_result and interim_result.get("text"):
                    interim_result["type"] = "interim"
                    self.live_text = interim_result["text"]
                    self._emit(interim_result)
                last_interim_emit = time.time()

            if speech_started and silence_duration >= self.max_silence_sec and speech_duration >= self.min_speech_sec:
                if self.auto_stop_on_silence:
                    self.is_recording = False
                break

        # Final processing
        if accumulated_audio and speech_duration >= self.min_speech_sec:
            final_audio = np.concatenate(accumulated_audio).flatten()
            self._finalize_transcription(final_audio)
        else:
            self.is_processing = False
            self._emit({"type": "final", "text": "", "error": "No speech detected"})

    def _transcribe_raw(
        self,
        audio_data: np.ndarray,
        remove_fillers: bool = True,
        beam_size: int = 2,
        preview_mode: bool = False,
    ) -> Dict[str, Any] | str:
        """Core faster-whisper transcription with Multi-Layered Biasing."""
        if not self.model: return ""
        prepared_audio = self._apply_voice_focus(audio_data)
        
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
        
        # 3. Transcribe. Preview mode stays intentionally cheap so text appears quickly.
        transcribe_kwargs = {
            "beam_size": beam_size,
            "initial_prompt": initial_prompt,
            "language": self.config.get("language"),
        }
        if preview_mode:
            transcribe_kwargs.update(
                {
                    "vad_filter": False,
                    "word_timestamps": False,
                    "condition_on_previous_text": False,
                }
            )
        else:
            transcribe_kwargs.update(
                {
                    "vad_filter": True,
                    "vad_parameters": dict(min_silence_duration_ms=500),
                    "word_timestamps": True,
                }
            )

        segments, info = self.model.transcribe(prepared_audio, **transcribe_kwargs)
        
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
        clean_text = sterilize_transcript(full_text, remove_filler=use_professional and remove_fillers)
        
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
        print(f"{Fore.CYAN}[Engine] Transcribing locally...")
        
        # 1. Core Transcription with Bias
        result = self._transcribe_raw(audio_data)
        text = result["text"]
        if not text:
            self.is_processing = False
            self._emit({"type": "final", "text": "", "error": "No speech detected"})
            return

        print(f"{Fore.WHITE}[Transcript] Raw: {text}")

        result.update({"word_count": len(text.split())})
        style = self.config.get("enhancement_style", "Professional")
        custom_prompt = self.config.get("custom_style_prompt", "")
        should_refine = self._should_run_cloud_refinement(result)
            
        # 2. Smart Formatting (spoken commands -> formatting)
        result["text"] = apply_formatting_commands(result["text"])
        
        # 3. Punctuation & Casing
        result["text"] = auto_punctuate_and_capitalize(result["text"])
        
        # Final metadata
        result["type"] = "final"
        result["mode"] = "local"
        result["pending_refinement"] = should_refine
        
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
        mode = result.get("mode", "local")
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

        if should_refine:
            threading.Thread(
                target=self._run_background_refinement,
                args=(text, style, custom_prompt, txt_path, result.copy()),
                daemon=True,
            ).start()

    def _apply_voice_focus(self, audio_data: np.ndarray) -> np.ndarray:
        audio = np.asarray(audio_data, dtype=np.float32).flatten()
        if audio.size == 0:
            return audio

        audio = audio - np.mean(audio)

        if audio.size > 256 and self.voice_focus_sos is not None:
            try:
                audio = sosfilt(self.voice_focus_sos, audio).astype(np.float32)
            except Exception:
                pass

        abs_audio = np.abs(audio)
        peak = float(np.max(abs_audio)) if abs_audio.size else 0.0
        if peak > 0:
            audio = audio / peak

        abs_audio = np.abs(audio)
        floor = float(np.percentile(abs_audio, 35)) if abs_audio.size else 0.0
        gate = max(floor * 1.3, self.vad_rms_threshold * 0.45)
        audio = np.where(np.abs(audio) < gate, audio * 0.18, audio)
        return audio.astype(np.float32)

    def _measure_speech_level(self, audio_chunk: np.ndarray) -> float:
        focused = self._apply_voice_focus(audio_chunk)
        if focused.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(focused))))

    def _build_preview_audio(self, chunks: list[np.ndarray]) -> np.ndarray:
        if not chunks:
            return np.array([], dtype=np.float32)

        target_window_sec = min(self.preview_window_sec, 1.8)
        target_samples = int(target_window_sec * self.fs)
        selected = []
        collected = 0

        for chunk in reversed(chunks):
            selected.insert(0, chunk)
            collected += len(chunk)
            if collected >= target_samples:
                break

        preview_audio = np.concatenate(selected).flatten()
        if preview_audio.size > target_samples:
            preview_audio = preview_audio[-target_samples:]

        return preview_audio.astype(np.float32)

    def _should_run_cloud_refinement(self, result: Dict[str, Any]) -> bool:
        if not self.config.get("use_ai_refinement", False):
            print(f"{Fore.YELLOW}[AI] Refinement disabled in settings.")
            return False

        privacy_mode = self.config.get("privacy_mode", "standard")
        threshold = self.config.get("cloud_enhancement_threshold", 0.7)
        confidence = float(result.get("confidence", 1.0) or 1.0)

        if privacy_mode == "extreme":
            print(f"{Fore.YELLOW}[Privacy] Extreme mode active. AI refinement skipped.")
            return False

        if self.ai is None:
            print(f"{Fore.YELLOW}[AI] No cloud provider configured. Using local transcript.")
            return False

        if not self.api_status and not self._check_internet():
            print(f"{Fore.YELLOW}[AI] Offline. Using local transcript.")
            return False

        if confidence >= threshold:
            print(f"{Fore.CYAN}[AI] Local confidence {confidence:.2f} is above threshold. Skipping cloud cleanup.")
            return False

        print(f"{Fore.CYAN}[Hybrid] Low confidence ({confidence:.2f}) -> scheduling background cloud cleanup.")
        return True

    def _run_background_refinement(
        self,
        source_text: str,
        style: str,
        custom_prompt: str,
        transcript_path: str,
        base_result: Dict[str, Any],
    ) -> None:
        self._emit({"type": "state", "state": "refining"})
        try:
            refined_data = self.ai.refine_text(source_text, style, custom_prompt) if self.ai else None
            if not refined_data or not refined_data.get("text"):
                return

            refined_result = dict(base_result)
            refined_result.update(refined_data)
            refined_result["text"] = auto_punctuate_and_capitalize(
                apply_formatting_commands(refined_result["text"])
            )
            refined_result["type"] = "refined"
            refined_result["mode"] = "hybrid"
            refined_result["pending_refinement"] = False

            try:
                with open(transcript_path, "w", encoding="utf-8") as handle:
                    handle.write(refined_result["text"])
            except Exception as exc:
                refined_result["warning"] = f"Refined transcript was produced but could not update history: {exc}"

            self.mcp.publish_event("transcription.refined", refined_result)
            self._emit(refined_result)
        finally:
            self._emit({"type": "state", "state": "idle"})

    def _ensure_vad_backend(self) -> None:
        if not self.use_silero_vad or load_silero_vad is None or VADIterator is None or torch is None:
            return

        if self.silero_model is not None and self.silero_iterator is not None:
            return

        try:
            self.silero_model = load_silero_vad()
            self.silero_window_samples = 512 if self.fs == 16000 else 256
            self.silero_iterator = VADIterator(self.silero_model, sampling_rate=self.fs)
            self.silero_last_error = ""
            print(f"{Fore.CYAN}[Engine] Silero VAD ready for streaming endpointing.")
        except Exception as exc:
            self.silero_model = None
            self.silero_iterator = None
            self.silero_last_error = str(exc)
            print(f"{Fore.YELLOW}[Engine] Silero VAD unavailable, falling back to RMS gating: {exc}")

    def _ensure_noise_backend(self) -> None:
        if not self.noise_suppression_enabled or self.noise_suppression_engine != "rnnoise" or RNNoise is None:
            return

        if self.rnnoise_stream is not None:
            return

        try:
            self.rnnoise_stream = RNNoise(sample_rate=self.fs)
            self.rnnoise_last_error = ""
            print(f"{Fore.CYAN}[Engine] RNNoise suppression ready.")
        except Exception as exc:
            self.rnnoise_stream = None
            self.rnnoise_last_error = str(exc)
            print(f"{Fore.YELLOW}[Engine] RNNoise unavailable, continuing without suppression: {exc}")

    def _detect_speech_activity(
        self,
        audio_chunk: np.ndarray,
        noise_floor: float,
        rnnoise_speech_prob: Optional[float] = None,
    ) -> tuple[bool, float]:
        speech_level = self._measure_speech_level(audio_chunk)
        silero_state = self._detect_speech_with_silero(audio_chunk)
        if silero_state is not None:
            return silero_state, speech_level

        speech_threshold = max(self.vad_rms_threshold, noise_floor * self.vad_noise_ratio)
        rnnoise_state = rnnoise_speech_prob is not None and rnnoise_speech_prob >= self.rnnoise_speech_threshold
        return speech_level >= speech_threshold or rnnoise_state, speech_level

    def _detect_speech_with_silero(self, audio_chunk: np.ndarray) -> Optional[bool]:
        if self.silero_iterator is None or torch is None:
            return None

        chunk = audio_chunk
        if chunk.size < self.silero_window_samples:
            chunk = np.pad(chunk, (0, self.silero_window_samples - chunk.size))
        elif chunk.size > self.silero_window_samples:
            chunk = chunk[:self.silero_window_samples]

        try:
            speech_event = self.silero_iterator(torch.from_numpy(chunk), return_seconds=False)
            if speech_event:
                if "start" in speech_event:
                    self.silero_in_speech = True
                if "end" in speech_event:
                    self.silero_in_speech = False
            return self.silero_in_speech
        except Exception as exc:
            self.silero_last_error = str(exc)
            self.silero_iterator = None
            print(f"{Fore.YELLOW}[Engine] Silero VAD stream failed, reverting to RMS gating: {exc}")
            return None

    def _prepare_stream_chunk(self, audio_chunk: np.ndarray) -> tuple[np.ndarray, Optional[float]]:
        processed = np.asarray(audio_chunk, dtype=np.float32).flatten()
        rnnoise_prob: Optional[float] = None

        if self.noise_suppression_enabled and self.rnnoise_stream is not None:
            try:
                frames = list(self.rnnoise_stream.denoise_chunk(processed, partial=False))
                if frames:
                    probs = [float(np.mean(frame_prob)) for frame_prob, _denoised in frames]
                    rnnoise_prob = float(np.mean(probs)) if probs else None
                    denoised_frames = []
                    for _prob, denoised in frames:
                        denoised_np = np.asarray(denoised).astype(np.float32).flatten()
                        if denoised_np.size:
                            denoised_frames.append(denoised_np / 32768.0)
                    if denoised_frames:
                        processed = np.concatenate(denoised_frames).astype(np.float32)
            except Exception as exc:
                self.rnnoise_last_error = str(exc)
                self.rnnoise_stream = None
                print(f"{Fore.YELLOW}[Engine] RNNoise stream failed, reverting to raw audio: {exc}")

        if processed.size == 0:
            processed = np.asarray(audio_chunk, dtype=np.float32).flatten()

        return processed, rnnoise_prob

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
