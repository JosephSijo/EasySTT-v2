from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.ai_handler import AIHandler
from .qt_widgets import WaveformVisualizer


class MicrophoneTester(QObject):
    levelChanged = Signal(float)
    statusChanged = Signal(str)
    calibrationReady = Signal(dict)

    def __init__(self, sample_rate: int = 16000):
        super().__init__()
        self.fs = sample_rate
        self.stream = None
        self.running = False

    def list_input_devices(self) -> list[dict[str, Any]]:
        devices = []
        try:
            for index, device in enumerate(sd.query_devices()):
                if device.get("max_input_channels", 0) > 0:
                    devices.append(
                        {
                            "id": index,
                            "name": device.get("name", f"Input {index}"),
                            "channels": int(device.get("max_input_channels", 0)),
                            "default_samplerate": int(device.get("default_samplerate", 16000)),
                        }
                    )
        except Exception as exc:
            self.statusChanged.emit(f"Failed to list microphones: {exc}")
        return devices

    def start(self, device_id: Optional[int] = None) -> None:
        self.stop()

        try:
            self.stream = sd.InputStream(
                device=device_id,
                samplerate=self.fs,
                channels=1,
                callback=self._callback,
            )
            self.stream.start()
            self.running = True
            self.statusChanged.emit("Microphone test is running. Speak to see the level meter move.")
        except Exception as exc:
            self.stream = None
            self.running = False
            self.statusChanged.emit(f"Microphone test failed: {exc}")

    def stop(self) -> None:
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass

        self.stream = None
        self.running = False
        self.levelChanged.emit(0.0)
        self.statusChanged.emit("Microphone test stopped.")

    def calibrate_noise(self, device_id: Optional[int], duration_sec: float = 2.5) -> None:
        def worker():
            self.statusChanged.emit("Capturing room noise. Stay quiet for a moment...")
            try:
                frames = int(self.fs * duration_sec)
                capture = sd.rec(
                    frames,
                    samplerate=self.fs,
                    channels=1,
                    dtype="float32",
                    device=device_id,
                    blocking=True,
                )
                audio = np.asarray(capture).flatten()
                rms = float(np.sqrt(np.mean(np.square(audio)))) if audio.size else 0.0
                peak = float(np.max(np.abs(audio))) if audio.size else 0.0
                recommended_threshold = max(0.008, min(0.08, rms * 2.4))
                recommended_ratio = max(1.4, min(3.5, 1.7 + (peak * 8.0)))
                noise_profile = {
                    "rms": rms,
                    "peak": peak,
                    "vad_rms_threshold": round(recommended_threshold, 4),
                    "vad_noise_ratio": round(recommended_ratio, 2),
                    "silence_duration_ms": 850 if rms < 0.02 else 1100,
                }
                self.calibrationReady.emit(noise_profile)
                self.statusChanged.emit("Calibration finished. Review the suggested values and save them.")
            except Exception as exc:
                self.statusChanged.emit(f"Calibration failed: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _callback(self, indata, frames, time_info, status) -> None:  # pragma: no cover - hardware driven
        if status:
            self.statusChanged.emit(str(status))
        level = float(np.max(np.abs(indata))) if len(indata) else 0.0
        self.levelChanged.emit(level)


class DiagnosticsView(QWidget):
    hotkeyShortcutChanged = Signal(str)
    hotkeyRebindRequested = Signal(str)
    apiTestRequested = Signal()
    audioSettingsChanged = Signal()

    hotkeyTriggered = Signal(str, int)

    def __init__(self, config, hotkey_manager, engine=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.hotkey_manager = hotkey_manager
        self.engine = engine
        self.hotkey_test_armed = False
        self.microphone_tester = MicrophoneTester()

        self.hotkeyTriggered.connect(self._handle_hotkey_triggered)
        self.microphone_tester.levelChanged.connect(self._handle_mic_level)
        self.microphone_tester.statusChanged.connect(self._handle_mic_status)
        self.microphone_tester.calibrationReady.connect(self._handle_calibration_ready)

        if self.hotkey_manager is not None:
            self.hotkey_manager.add_listener(self._on_hotkey_trigger)

        self._build_ui()
        self.refresh_all()

    def closeEvent(self, event):  # pragma: no cover - UI lifecycle
        if self.hotkey_manager is not None:
            self.hotkey_manager.remove_listener(self._on_hotkey_trigger)
        self.microphone_tester.stop()
        super().closeEvent(event)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(18)

        title = QLabel("Test Lab")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        subtitle = QLabel("Run practical checks for your hotkey, microphone, active AI API, and the speech pipeline.")
        subtitle.setStyleSheet("color: #8aa0af; font-size: 12px;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        layout.addWidget(self._build_hotkey_card())
        layout.addWidget(self._build_microphone_card())
        layout.addWidget(self._build_audio_pipeline_card())
        layout.addWidget(self._build_api_card())
        layout.addStretch()

    def _build_hotkey_card(self):
        card, card_layout = self._make_card("Hotkey Test", "Rebind and verify the configured global shortcut.")

        self.hotkey_summary = QLabel()
        self.hotkey_summary.setWordWrap(True)
        self.hotkey_summary.setStyleSheet("color: #d5dce1;")
        self.hotkey_result = QLabel("No hotkey test has run yet.")
        self.hotkey_result.setStyleSheet("color: #8aa0af;")

        actions = QHBoxLayout()
        self.rebind_hotkey_btn = QPushButton("Rebind Current Shortcut")
        self.rebind_hotkey_btn.setObjectName("SecondaryButton")
        self.rebind_hotkey_btn.clicked.connect(self._rebind_hotkey)
        self.arm_hotkey_btn = QPushButton("Arm Hotkey Test")
        self.arm_hotkey_btn.setObjectName("SecondaryButton")
        self.arm_hotkey_btn.clicked.connect(self._arm_hotkey_test)
        self.simulate_hotkey_btn = QPushButton("Simulate Trigger")
        self.simulate_hotkey_btn.setObjectName("SecondaryButton")
        self.simulate_hotkey_btn.clicked.connect(self._simulate_hotkey_trigger)
        actions.addWidget(self.rebind_hotkey_btn)
        actions.addWidget(self.arm_hotkey_btn)
        actions.addWidget(self.simulate_hotkey_btn)
        actions.addStretch()

        card_layout.addWidget(self.hotkey_summary)
        card_layout.addLayout(actions)
        card_layout.addWidget(self.hotkey_result)
        return card

    def _build_microphone_card(self):
        card, card_layout = self._make_card("Microphone Test", "Preview live mic levels, choose the input device, and save it for dictation.")

        self.microphone_combo = QComboBox()
        self.microphone_status = QLabel()
        self.microphone_status.setWordWrap(True)
        self.microphone_status.setStyleSheet("color: #8aa0af;")
        self.microphone_waveform = WaveformVisualizer()
        self.microphone_waveform.setActive(False)

        actions = QHBoxLayout()
        refresh_btn = QPushButton("Refresh Devices")
        refresh_btn.setObjectName("SecondaryButton")
        refresh_btn.clicked.connect(self.refresh_microphones)
        start_btn = QPushButton("Start Mic Test")
        start_btn.setObjectName("SecondaryButton")
        start_btn.clicked.connect(self._start_microphone_test)
        stop_btn = QPushButton("Stop Mic Test")
        stop_btn.setObjectName("SecondaryButton")
        stop_btn.clicked.connect(self.microphone_tester.stop)
        save_btn = QPushButton("Use Selected Device")
        save_btn.setObjectName("SecondaryButton")
        save_btn.clicked.connect(self._save_selected_device)
        actions.addWidget(refresh_btn)
        actions.addWidget(start_btn)
        actions.addWidget(stop_btn)
        actions.addWidget(save_btn)
        actions.addStretch()

        card_layout.addWidget(self.microphone_combo)
        card_layout.addWidget(self.microphone_waveform, alignment=Qt.AlignLeft)
        card_layout.addLayout(actions)
        card_layout.addWidget(self.microphone_status)
        return card

    def _build_audio_pipeline_card(self):
        card, card_layout = self._make_card(
            "Calibration & Audio Pipeline",
            "Tune silence detection and noise suppression for this microphone and room.",
        )

        self.pipeline_summary = QLabel()
        self.pipeline_summary.setWordWrap(True)
        self.pipeline_summary.setStyleSheet("color: #d5dce1;")

        self.auto_stop_check = QCheckBox("Auto-stop when trailing silence is detected")
        self.silero_check = QCheckBox("Use Silero VAD for speech endpointing")
        self.noise_suppression_check = QCheckBox("Enable RNNoise suppression before transcription")

        self.silence_spin = QSpinBox()
        self.silence_spin.setRange(300, 2500)
        self.silence_spin.setSuffix(" ms")

        self.rms_spin = QDoubleSpinBox()
        self.rms_spin.setRange(0.001, 0.100)
        self.rms_spin.setDecimals(4)
        self.rms_spin.setSingleStep(0.001)

        self.noise_ratio_spin = QDoubleSpinBox()
        self.noise_ratio_spin.setRange(1.0, 4.0)
        self.noise_ratio_spin.setDecimals(2)
        self.noise_ratio_spin.setSingleStep(0.05)

        self.pipeline_status = QLabel("No calibration has run yet.")
        self.pipeline_status.setWordWrap(True)
        self.pipeline_status.setStyleSheet("color: #8aa0af;")

        card_layout.addWidget(self.pipeline_summary)
        card_layout.addWidget(QLabel("SILENCE WINDOW"))
        card_layout.addWidget(self.silence_spin)
        card_layout.addWidget(QLabel("RMS SPEECH THRESHOLD"))
        card_layout.addWidget(self.rms_spin)
        card_layout.addWidget(QLabel("NOISE RATIO"))
        card_layout.addWidget(self.noise_ratio_spin)
        card_layout.addWidget(self.auto_stop_check)
        card_layout.addWidget(self.silero_check)
        card_layout.addWidget(self.noise_suppression_check)

        actions = QHBoxLayout()
        calibrate_btn = QPushButton("Capture Ambient Noise")
        calibrate_btn.setObjectName("SecondaryButton")
        calibrate_btn.clicked.connect(self._calibrate_microphone)
        save_btn = QPushButton("Save Audio Profile")
        save_btn.setObjectName("SecondaryButton")
        save_btn.clicked.connect(self._save_audio_profile)
        actions.addWidget(calibrate_btn)
        actions.addWidget(save_btn)
        actions.addStretch()

        card_layout.addLayout(actions)
        card_layout.addWidget(self.pipeline_status)
        return card

    def _build_api_card(self):
        card, card_layout = self._make_card("API Test", "Validate the provider currently selected in settings using the saved credentials.")

        self.api_summary = QLabel()
        self.api_summary.setWordWrap(True)
        self.api_summary.setStyleSheet("color: #d5dce1;")
        self.api_result = QLabel("No API probe has run yet.")
        self.api_result.setStyleSheet("color: #8aa0af;")

        action_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh Summary")
        refresh_btn.setObjectName("SecondaryButton")
        refresh_btn.clicked.connect(self.refresh_api_summary)
        test_btn = QPushButton("Test Active Provider")
        test_btn.setObjectName("SecondaryButton")
        test_btn.clicked.connect(self._test_api)
        action_row.addWidget(refresh_btn)
        action_row.addWidget(test_btn)
        action_row.addStretch()

        card_layout.addWidget(self.api_summary)
        card_layout.addLayout(action_row)
        card_layout.addWidget(self.api_result)
        return card

    def _make_card(self, title: str, subtitle: str):
        card = QFrame()
        card.setObjectName("EzCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #ffffff;")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setWordWrap(True)
        subtitle_label.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        return card, layout

    def refresh_all(self):
        self.refresh_hotkey_summary()
        self.refresh_microphones()
        self.refresh_audio_settings()
        self.refresh_api_summary()

    def refresh_hotkey_summary(self):
        shortcut = self.config.get("shortcut", "ctrl+alt+r").upper()
        snapshot = self.hotkey_manager.status_snapshot() if self.hotkey_manager else {}
        registered = bool(snapshot.get("is_registered"))
        trigger_count = int(snapshot.get("trigger_count", 0) or 0)
        last_error = snapshot.get("last_error") or "None"

        self.hotkey_summary.setText(
            f"Configured shortcut: {shortcut}\n"
            f"Registered now: {'Yes' if registered else 'No'}\n"
            f"Trigger count this session: {trigger_count}\n"
            f"Last error: {last_error}"
        )

    def refresh_microphones(self):
        self.microphone_combo.clear()
        devices = self.microphone_tester.list_input_devices()
        selected_device = self.config.get("selected_input_device")

        if not devices:
            self.microphone_combo.addItem("No input devices found", None)
            self.microphone_status.setText("No microphone devices were detected.")
            return

        chosen_index = 0
        for index, device in enumerate(devices):
            label = f"{device['name']} ({device['channels']} ch)"
            self.microphone_combo.addItem(label, device["id"])
            if selected_device == device["id"]:
                chosen_index = index

        self.microphone_combo.setCurrentIndex(chosen_index)
        self.microphone_status.setText(f"Found {len(devices)} input device(s). Select one and start the mic test.")

    def refresh_audio_settings(self):
        self.silence_spin.setValue(int(self.config.get("silence_duration_ms", 850)))
        self.rms_spin.setValue(float(self.config.get("vad_rms_threshold", 0.012)))
        self.noise_ratio_spin.setValue(float(self.config.get("vad_noise_ratio", 2.0)))
        self.auto_stop_check.setChecked(bool(self.config.get("auto_stop_on_silence", True)))
        self.silero_check.setChecked(bool(self.config.get("use_silero_vad", True)))
        self.noise_suppression_check.setChecked(bool(self.config.get("noise_suppression_enabled", True)))
        self._update_audio_summary()

    def _update_audio_summary(self):
        selected_device = self.config.get("selected_input_device")
        suppression = "RNNoise on" if self.noise_suppression_check.isChecked() else "suppression off"
        self.pipeline_summary.setText(
            f"Active input device: {selected_device if selected_device is not None else 'system default'}\n"
            f"Endpointing: {self.silence_spin.value()} ms silence • RMS {self.rms_spin.value():.4f} • ratio {self.noise_ratio_spin.value():.2f}\n"
            f"Speech detection: {'Silero VAD' if self.silero_check.isChecked() else 'RMS fallback'} • {suppression}"
        )

    def refresh_api_summary(self):
        provider = self.config.get("provider", "Gemini")
        key_present = False
        model_name = ""
        details = ""

        profile = None
        for item in self.config.get_custom_api_profiles():
            if item.get("id") == provider:
                profile = item
                break

        if profile:
            key_present = bool(profile.get("api_key"))
            model_name = profile.get("model", "")
            details = profile.get("base_url", "")
        else:
            keys = self.config.get("keys", {})
            key_present = bool(keys.get(provider))
            model_name = self.config.get("api_models", {}).get(provider, "")
            details = "Built-in provider"

        self.api_summary.setText(
            f"Active provider: {provider}\n"
            f"Configured model: {model_name or 'Not set'}\n"
            f"Endpoint: {details}\n"
            f"API key present: {'Yes' if key_present else 'No'}"
        )

    def _rebind_hotkey(self):
        if self.hotkey_manager is None:
            self.hotkey_result.setText("Hotkey manager is unavailable.")
            return

        shortcut = self.config.get("shortcut", "ctrl+alt+r")
        success, message = self.hotkey_manager.register(shortcut)
        self.refresh_hotkey_summary()
        self.hotkey_result.setText(message if success else f"Failed: {message}")

    def _arm_hotkey_test(self):
        self.hotkey_test_armed = True
        shortcut = self.config.get("shortcut", "ctrl+alt+r").upper()
        self.hotkey_result.setText(f"Waiting for {shortcut}. Press the real hotkey now.")

    def _simulate_hotkey_trigger(self):
        if self.hotkey_manager is None:
            self.hotkey_result.setText("Hotkey manager is unavailable.")
            return
        self.hotkey_manager.simulate_trigger()

    def _on_hotkey_trigger(self, shortcut: str, trigger_count: int):
        self.hotkeyTriggered.emit(shortcut, trigger_count)

    def _handle_hotkey_triggered(self, shortcut: str, trigger_count: int):
        self.refresh_hotkey_summary()
        label = shortcut.upper() if shortcut else self.config.get("shortcut", "ctrl+alt+r").upper()
        if self.hotkey_test_armed:
            self.hotkey_result.setText(f"Success: detected {label}. Trigger count is now {trigger_count}.")
            self.hotkey_test_armed = False
        else:
            self.hotkey_result.setText(f"Hotkey fired: {label} (count {trigger_count}).")

    def _start_microphone_test(self):
        device_id = self.microphone_combo.currentData()
        self.microphone_waveform.setActive(True)
        self.microphone_tester.start(device_id=device_id)

    def _save_selected_device(self):
        self.config.set("selected_input_device", self.microphone_combo.currentData())
        self.audioSettingsChanged.emit()
        self.refresh_audio_settings()
        self.microphone_status.setText("Selected microphone saved for future recordings.")

    def _calibrate_microphone(self):
        self.pipeline_status.setText("Listening to room tone for calibration...")
        self.microphone_tester.calibrate_noise(self.microphone_combo.currentData())

    def _handle_calibration_ready(self, payload: Dict[str, Any]):
        self.rms_spin.setValue(float(payload.get("vad_rms_threshold", 0.012)))
        self.noise_ratio_spin.setValue(float(payload.get("vad_noise_ratio", 2.0)))
        self.silence_spin.setValue(int(payload.get("silence_duration_ms", 850)))
        self.pipeline_status.setText(
            f"Ambient RMS {payload.get('rms', 0.0):.4f}, peak {payload.get('peak', 0.0):.4f}. "
            "Suggested settings loaded into the controls."
        )
        self._update_audio_summary()

    def _save_audio_profile(self):
        self.config.set("selected_input_device", self.microphone_combo.currentData())
        self.config.set("silence_duration_ms", int(self.silence_spin.value()))
        self.config.set("vad_rms_threshold", float(self.rms_spin.value()))
        self.config.set("vad_noise_ratio", float(self.noise_ratio_spin.value()))
        self.config.set("auto_stop_on_silence", self.auto_stop_check.isChecked())
        self.config.set("use_silero_vad", self.silero_check.isChecked())
        self.config.set("noise_suppression_enabled", self.noise_suppression_check.isChecked())

        if self.engine is not None:
            self.engine.auto_stop_on_silence = self.auto_stop_check.isChecked()
            self.engine.use_silero_vad = self.silero_check.isChecked()
            self.engine.vad_rms_threshold = float(self.rms_spin.value())
            self.engine.vad_noise_ratio = float(self.noise_ratio_spin.value())
            self.engine.max_silence_sec = max(0.4, self.silence_spin.value() / 1000)
            self.engine.noise_suppression_enabled = self.noise_suppression_check.isChecked()
            if hasattr(self.engine, "_ensure_vad_backend"):
                self.engine._ensure_vad_backend()
            if hasattr(self.engine, "_ensure_noise_backend"):
                self.engine._ensure_noise_backend()

        self.audioSettingsChanged.emit()
        self.refresh_audio_settings()
        self.pipeline_status.setText("Audio pipeline settings saved. The next recording will use them.")

    def _handle_mic_level(self, level: float):
        self.microphone_waveform.set_level(level)

    def _handle_mic_status(self, status: str):
        if "stopped" in status.lower():
            self.microphone_waveform.setActive(False)
        self.microphone_status.setText(status)

    def _test_api(self):
        provider = self.config.get("provider", "Gemini")
        api_type = "gemini" if provider == "Gemini" else "openai_compatible"
        base_url: Optional[str] = None
        api_key = ""

        for profile in self.config.get_custom_api_profiles():
            if profile.get("id") == provider:
                api_type = profile.get("api_type", "openai_compatible")
                base_url = profile.get("base_url") or None
                api_key = profile.get("api_key", "")
                break

        if not api_key:
            keys = self.config.get("keys", {})
            api_key = keys.get(provider, "")

        if not api_key:
            self.api_result.setText("No API key is configured for the active provider.")
            return

        ok, message = AIHandler.validate_api_key(provider, api_key, base_url=base_url, api_type=api_type)
        timestamp = time.strftime("%H:%M:%S")
        if ok:
            self.api_result.setText(f"[{timestamp}] API probe succeeded.")
        else:
            self.api_result.setText(f"[{timestamp}] API probe failed: {message}")
            QMessageBox.warning(self, "API Test Failed", message)
