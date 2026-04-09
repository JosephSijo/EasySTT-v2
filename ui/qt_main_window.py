import sys
import pathlib
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QStackedWidget, QLabel, QFrame, QLineEdit, 
                             QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
                             QComboBox, QCheckBox, QFileDialog, QMessageBox,
                             QApplication, QProgressBar, QTextEdit)
from PySide6.QtCore import Qt, Signal, QSize, QTimer, Slot
from PySide6.QtGui import QIcon, QColor
from PySide6.QtGui import QTextOption

from .qt_styles import EZ_THEME_QSS
from .qt_widgets import (EzSidebar, EzToggle, SelectableCard, StatusBadge, 
                        WaveformVisualizer, HealthCard)
from .diagnostics_view import DiagnosticsView
from .settings_dialogs import CustomApiProfilesDialog, EngineCatalogDialog
from core.ai_handler import AIHandler
from core.transcript_history import TranscriptHistoryService
from core.win32_utils import apply_window_masking, enable_acrylic_effect, set_window_shadow
from core.system_specs import SystemSpecs

class StartupOverlay(QFrame):
    closeRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StartupOverlay")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._init_ui()
        self.update_progress(
            5,
            "Booting interface",
            "Preparing the desktop shell. Controls stay locked until startup completes.",
        )

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(70, 70, 70, 70)
        outer.addStretch()

        card = QFrame()
        card.setObjectName("StartupCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(12)

        eyebrow = QLabel("STARTUP READINESS")
        eyebrow.setObjectName("StartupEyebrow")
        title = QLabel("Preparing EasySTT")
        title.setObjectName("StartupTitle")

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("StartupProgress")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        self.status_label = QLabel()
        self.status_label.setObjectName("StartupStatus")
        self.detail_label = QLabel()
        self.detail_label.setObjectName("StartupDetail")
        self.detail_label.setWordWrap(True)

        self.app_state = QLabel()
        self.app_state.setObjectName("StartupState")
        self.engine_state = QLabel()
        self.engine_state.setObjectName("StartupState")
        self.hotkey_state = QLabel()
        self.hotkey_state.setObjectName("StartupState")

        self.lock_note = QLabel("Controls stay disabled until startup completes.")
        self.lock_note.setObjectName("StartupDetail")
        self.lock_note.setWordWrap(True)

        self.close_btn = QPushButton("Close App")
        self.close_btn.setObjectName("SecondaryButton")
        self.close_btn.clicked.connect(self.closeRequested.emit)
        self.close_btn.hide()

        card_layout.addWidget(eyebrow)
        card_layout.addWidget(title)
        card_layout.addWidget(self.progress_bar)
        card_layout.addWidget(self.status_label)
        card_layout.addWidget(self.detail_label)
        card_layout.addWidget(self.app_state)
        card_layout.addWidget(self.engine_state)
        card_layout.addWidget(self.hotkey_state)
        card_layout.addWidget(self.lock_note)
        card_layout.addWidget(self.close_btn, alignment=Qt.AlignLeft)

        outer.addWidget(card, alignment=Qt.AlignCenter)
        outer.addStretch()

    def update_progress(self, percent, status, detail):
        value = max(0, min(100, int(percent)))
        self.progress_bar.setValue(value)
        self.status_label.setText(status)
        self.detail_label.setText(detail)
        self.app_state.setText("App shell: ready")

        if value < 55:
            self.engine_state.setText("Speech engine: warming up")
        elif value < 95:
            self.engine_state.setText("Speech engine: loading active model")
        else:
            self.engine_state.setText("Speech engine: model ready")

        if value < 95:
            self.hotkey_state.setText("Global hotkey: waiting")
        elif value < 100:
            self.hotkey_state.setText("Global hotkey: binding")
        else:
            self.hotkey_state.setText("Global hotkey: active")

        self.close_btn.hide()

    def mark_ready(self, message):
        self.update_progress(100, "Everything is ready", message)
        self.lock_note.setText("Startup finished. Unlocking the workspace now.")

    def mark_failed(self, message):
        self.progress_bar.setValue(100)
        self.status_label.setText("Startup failed")
        self.detail_label.setText(message)
        self.app_state.setText("App shell: waiting for shutdown")
        self.engine_state.setText("Speech engine: not ready")
        self.hotkey_state.setText("Global hotkey: inactive")
        self.lock_note.setText("The workspace will stay locked because startup did not complete.")
        self.close_btn.show()

class DashboardView(QWidget):
    recordingRequested = Signal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 60, 60, 40)
        layout.setSpacing(0)

        # Top Bar
        top_bar = QHBoxLayout()
        breadcrumbs = QLabel("Workspace  ›  Dictation")
        breadcrumbs.setStyleSheet("color: #444444; font-size: 11px;")
        
        actions = QHBoxLayout()
        session_badge = QLabel("Local dictation ready")
        session_badge.setStyleSheet("color: #7f95a3; font-size: 11px;")
        actions.addWidget(session_badge)
        
        top_bar.addWidget(breadcrumbs)
        top_bar.addStretch()
        top_bar.addLayout(actions)
        layout.addLayout(top_bar)

        # Content with Side Info
        middle_layout = QHBoxLayout()
        
        # Spacer for Left
        middle_layout.addStretch(1)
        
        center_content = QVBoxLayout()
        center_content.setAlignment(Qt.AlignCenter)
        center_content.setSpacing(25)

        title = QLabel("Ready to capture\nyour thoughts?")
        title.setObjectName("DashboardTitle")
        title.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel("Start recording to transcribe your voice in real-time with\nfast local-first transcription.")
        subtitle.setObjectName("DashboardSub")
        subtitle.setAlignment(Qt.AlignCenter)

        self.waveform = WaveformVisualizer()
        
        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setObjectName("MicButton")
        self.mic_btn.setFixedSize(120, 120)
        self.mic_btn.setCursor(Qt.PointingHandCursor)
        self.mic_btn.setAccessibleName("Start recording")
        self.mic_btn.clicked.connect(self.recordingRequested.emit)
        
        hint_layout = QVBoxLayout()
        hint = QLabel("Click to start recording")
        hint.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff;")
        self.kbd_hint = QLabel()
        self.kbd_hint.setStyleSheet("color: #444444; font-size: 10px;")
        self.refresh_shortcut_hint()
        hint_layout.addWidget(hint, alignment=Qt.AlignCenter)
        hint_layout.addWidget(self.kbd_hint, alignment=Qt.AlignCenter)

        center_content.addWidget(title)
        center_content.addWidget(subtitle)
        center_content.addWidget(self.waveform, alignment=Qt.AlignCenter)
        center_content.addWidget(self.mic_btn, alignment=Qt.AlignCenter)
        center_content.addLayout(hint_layout)
        
        middle_layout.addLayout(center_content, 2)
        
        # Right Side Info (Health Card)
        right_panel = QVBoxLayout()
        self.health = HealthCard("Runtime Summary", [
            ("Engine", self.config.get("selected_model_label", "Whisper Turbo"), 100),
            ("Provider", self.config.get("provider", "Gemini"), 100)
        ])
        right_panel.addWidget(self.health)
        right_panel.addStretch()
        middle_layout.addLayout(right_panel, 1)
        
        layout.addLayout(middle_layout)
        layout.addStretch()

        # Bottom Dock 
        dock = QFrame()
        dock.setObjectName("EzCard")
        dock.setFixedHeight(60)
        dock_layout = QHBoxLayout(dock)
        dock_layout.setContentsMargins(30, 0, 30, 0)
        
        self.mic_status = QLabel("Microphone: system default")
        self.mic_status.setStyleSheet("color: #ffffff; font-size: 11px;")
        lang_status = QLabel("Language: English (US)")
        lang_status.setStyleSheet("color: #1392ec; font-size: 11px; font-weight: bold;")
        
        dock_layout.addWidget(self.mic_status)
        dock_layout.addStretch()
        dock_layout.addWidget(lang_status)
        
        layout.addWidget(dock, alignment=Qt.AlignCenter)
        self.refresh_input_device_hint()

    def refresh_shortcut_hint(self, shortcut=None):
        shortcut = (shortcut or self.config.get("shortcut", "ctrl+alt+r")).upper()
        self.kbd_hint.setText(f"{shortcut}  to quick start/stop")

    def refresh_input_device_hint(self):
        device_id = self.config.get("selected_input_device")
        if device_id is None:
            self.mic_status.setText("Microphone: system default")
        else:
            self.mic_status.setText(f"Microphone: input device #{device_id}")

class RecordingView(QWidget):
    stopRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        header = QHBoxLayout()
        timer_badge = QLabel(" ● LIVE ")
        timer_badge.setStyleSheet("background: #3c1a1a; color: #f44336; border-radius: 10px; font-weight: bold; padding: 5px;")
        session_title = QLabel("Active session: Voice dictation")
        session_title.setStyleSheet("color: #666666; font-size: 11px;")
        header.addWidget(timer_badge)
        header.addWidget(session_title)
        header.addStretch()
        self.status_line = QLabel("Listening for speech...")
        self.status_line.setStyleSheet("color: #7f95a3; font-size: 11px;")
        header.addWidget(self.status_line)
        layout.addLayout(header)

        wave_box = QVBoxLayout()
        self.waveform = WaveformVisualizer()
        self.waveform.setActive(True)
        self.waveform.setFixedWidth(420)
        wave_box.addWidget(self.waveform, alignment=Qt.AlignCenter)
        self.det_label = QLabel("VOICE-FOCUSED CAPTURE")
        self.det_label.setStyleSheet("color: #1392ec; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        wave_box.addWidget(self.det_label, alignment=Qt.AlignCenter)
        layout.addLayout(wave_box)

        self.transcript_area = QFrame()
        self.transcript_area.setObjectName("TranscriptCard")
        self.transcript_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        t_layout = QVBoxLayout(self.transcript_area)
        t_layout.setContentsMargins(28, 28, 28, 24)
        t_layout.setSpacing(12)
        self.main_text = QTextEdit()
        self.main_text.setObjectName("MainTranscript")
        self.main_text.setReadOnly(True)
        self.main_text.setAcceptRichText(False)
        self.main_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.main_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main_text.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.main_text.setPlainText("Press record and start speaking. Live text will stay inside this panel.")
        self.interim_text = QLabel("...")
        self.interim_text.setObjectName("InterimTranscript")
        self.interim_text.setWordWrap(True)
        t_layout.addWidget(self.main_text, 1)
        t_layout.addWidget(self.interim_text)
        layout.addWidget(self.transcript_area)

        ctrl_card = QFrame()
        ctrl_card.setObjectName("EzCard")
        ctrl_card.setFixedWidth(340)
        ctrl_layout = QHBoxLayout(ctrl_card)
        stop_btn = QPushButton("Stop Recording")
        stop_btn.setObjectName("StopButton")
        stop_btn.setAccessibleName("Stop recording")
        stop_btn.clicked.connect(self.stopRequested.emit)
        ctrl_layout.addWidget(stop_btn)
        layout.addWidget(ctrl_card, alignment=Qt.AlignCenter)

class ConfigurationView(QWidget):
    shortcutChanged = Signal(str)
    apiSettingsChanged = Signal()

    def __init__(self, config, engine, hotkey_manager=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.engine = engine
        self.hotkey_manager = hotkey_manager
        self.system_specs = SystemSpecs.detect()
        self.builtin_models = [
            ("Whisper Turbo", "turbo"),
            ("Whisper Tiny", "tiny"),
            ("Whisper Base", "base"),
            ("Whisper Small", "small"),
            ("Whisper Medium", "medium"),
            ("Whisper Large v3", "large-v3"),
        ]
        self._init_ui()
        self._load_from_config()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()
        title_label = QLabel("Engine, Model & API Control")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        status_widget = StatusBadge(label="SYSTEM", status=self.system_specs.get("tier", "ready"))
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(status_widget)
        layout.addLayout(header_layout)

        summary = QLabel(
            f"{self.system_specs.get('os')} {self.system_specs.get('os_version')} • "
            f"{self.system_specs.get('memory_gb')} GB RAM • "
            f"{self.system_specs.get('cpu_count')} logical cores"
        )
        summary.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(summary)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QScrollArea > QWidget > QWidget { background: transparent; }")

        content = QWidget()
        content.setObjectName("SettingsScrollHost")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 18)
        content_layout.setSpacing(20)

        content_layout.addWidget(self._build_engine_section())
        content_layout.addWidget(self._build_model_section())
        content_layout.addWidget(self._build_api_section())
        content_layout.addWidget(self._build_behavior_section())
        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _build_engine_section(self):
        card, card_layout = self._make_section_card("STT Engines", "Popular local engines, tuned to this PC.")
        self.engine_summary_label = QLabel()
        self.engine_summary_label.setWordWrap(True)
        self.engine_summary_label.setStyleSheet("color: #d5dce1;")
        browse_btn = QPushButton("Browse Recommended Engines")
        browse_btn.setObjectName("SecondaryButton")
        browse_btn.clicked.connect(self._open_engine_catalog)
        card_layout.addWidget(self.engine_summary_label)
        card_layout.addWidget(browse_btn, alignment=Qt.AlignLeft)
        return card

    def _build_model_section(self):
        card, card_layout = self._make_section_card(
            "Models",
            "Select bundled Whisper presets or register your own local/Hugging Face model target.",
        )

        model_label = QLabel("ACTIVE MODEL")
        model_label.setStyleSheet("color: #5d7688; font-size: 11px; font-weight: bold;")
        self.model_combo = QComboBox()
        apply_btn = QPushButton("Apply Selected Model")
        apply_btn.setObjectName("SecondaryButton")
        apply_btn.clicked.connect(self._save_selected_model)
        card_layout.addWidget(model_label)
        card_layout.addWidget(self.model_combo)
        card_layout.addWidget(apply_btn, alignment=Qt.AlignLeft)

        self.model_target_label = QLabel()
        self.model_target_label.setWordWrap(True)
        self.model_target_label.setStyleSheet("color: #8aa0af; font-size: 11px;")
        card_layout.addWidget(self.model_target_label)

        self.custom_model_name_edit = QLineEdit()
        self.custom_model_name_edit.setPlaceholderText("Custom model label")
        self.custom_model_target_edit = QLineEdit()
        self.custom_model_target_edit.setPlaceholderText("Local model folder or Hugging Face model ID")
        browse_btn = QPushButton("Browse Folder")
        browse_btn.setObjectName("SecondaryButton")
        browse_btn.clicked.connect(self._browse_model_path)
        save_btn = QPushButton("Save Custom Model")
        save_btn.setObjectName("SecondaryButton")
        save_btn.clicked.connect(self._save_custom_model)

        row = QHBoxLayout()
        row.addWidget(self.custom_model_target_edit)
        row.addWidget(browse_btn)
        card_layout.addWidget(QLabel("ADD CUSTOM MODEL"))
        card_layout.addWidget(self.custom_model_name_edit)
        card_layout.addLayout(row)
        card_layout.addWidget(save_btn, alignment=Qt.AlignLeft)
        return card

    def _build_api_section(self):
        card, card_layout = self._make_section_card(
            "AI APIs",
            "Choose built-in providers or attach custom endpoints with your own default models.",
        )

        self.provider_combo = QComboBox()
        self.provider_combo.currentIndexChanged.connect(self._refresh_provider_inputs)
        self.base_url_edit = QLineEdit()
        self.model_edit = QLineEdit()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)

        card_layout.addWidget(QLabel("PROVIDER"))
        card_layout.addWidget(self.provider_combo)
        card_layout.addWidget(QLabel("BASE URL"))
        card_layout.addWidget(self.base_url_edit)
        card_layout.addWidget(QLabel("DEFAULT MODEL"))
        card_layout.addWidget(self.model_edit)
        card_layout.addWidget(QLabel("API KEY"))
        card_layout.addWidget(self.api_key_edit)

        actions = QHBoxLayout()
        manage_btn = QPushButton("Manage Custom APIs")
        manage_btn.setObjectName("SecondaryButton")
        manage_btn.clicked.connect(self._open_custom_api_dialog)
        test_btn = QPushButton("Test Connection")
        test_btn.setObjectName("SecondaryButton")
        test_btn.clicked.connect(self._test_api_connection)
        save_btn = QPushButton("Save API Settings")
        save_btn.setObjectName("SecondaryButton")
        save_btn.clicked.connect(self._save_api_settings)
        actions.addWidget(manage_btn)
        actions.addWidget(test_btn)
        actions.addWidget(save_btn)
        actions.addStretch()
        card_layout.addLayout(actions)
        return card

    def _build_behavior_section(self):
        card, card_layout = self._make_section_card(
            "Relevant Customizations",
            "Quick settings that affect hotkeys, privacy, and transcript flow.",
        )

        card_layout.addWidget(QLabel("GLOBAL HOTKEY"))
        self.shortcut_edit = QLineEdit()
        card_layout.addWidget(self.shortcut_edit)

        card_layout.addWidget(QLabel("PRIVACY MODE"))
        self.privacy_combo = QComboBox()
        self.privacy_combo.addItem("Standard", "standard")
        self.privacy_combo.addItem("Extreme / Local Only", "extreme")
        self.privacy_combo.addItem("Enterprise", "enterprise")
        card_layout.addWidget(self.privacy_combo)

        self.refinement_check = QCheckBox("Enable background AI cleanup for low-confidence transcripts")
        self.clipboard_check = QCheckBox("Auto-copy transcript to clipboard")
        card_layout.addWidget(self.refinement_check)
        card_layout.addWidget(self.clipboard_check)

        storage_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        browse_btn = QPushButton("Browse")
        browse_btn.setObjectName("SecondaryButton")
        browse_btn.clicked.connect(self._browse_storage_path)
        storage_row.addWidget(self.path_edit)
        storage_row.addWidget(browse_btn)
        card_layout.addWidget(QLabel("STORAGE PATH"))
        card_layout.addLayout(storage_row)

        save_btn = QPushButton("Save Behavior Settings")
        save_btn.setObjectName("SecondaryButton")
        save_btn.clicked.connect(self._save_behavior_settings)
        card_layout.addWidget(save_btn, alignment=Qt.AlignLeft)
        return card

    def _make_section_card(self, title, subtitle):
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

    def _load_from_config(self):
        self._populate_provider_combo()
        self._populate_model_combo()
        self.shortcut_edit.setText(self.config.get("shortcut", "ctrl+alt+r"))
        self.refinement_check.setChecked(bool(self.config.get("use_ai_refinement", True)))
        self.clipboard_check.setChecked(bool(self.config.get("auto_clipboard", True)))
        self.path_edit.setText(self.config.get("storage_path", ""))

        target_mode = self.config.get("privacy_mode", "standard")
        for index in range(self.privacy_combo.count()):
            if self.privacy_combo.itemData(index) == target_mode:
                self.privacy_combo.setCurrentIndex(index)
                break

        self._refresh_engine_summary()

    def _populate_provider_combo(self):
        current_provider = self.config.get("provider", "Gemini")
        self.provider_combo.blockSignals(True)
        self.provider_combo.clear()
        self.provider_combo.addItem("Gemini (Built-in)", {"kind": "builtin", "id": "Gemini"})
        self.provider_combo.addItem("OpenAI (Built-in)", {"kind": "builtin", "id": "OpenAI"})

        for profile in self.config.get_custom_api_profiles():
            self.provider_combo.addItem(
                f"{profile.get('name', 'Custom API')} (Custom)",
                {"kind": "custom", "id": profile.get("id")},
            )

        selected_index = 0
        for index in range(self.provider_combo.count()):
            meta = self.provider_combo.itemData(index)
            if meta and meta.get("id") == current_provider:
                selected_index = index
                break

        self.provider_combo.setCurrentIndex(selected_index)
        self.provider_combo.blockSignals(False)
        self._refresh_provider_inputs()

    def _refresh_provider_inputs(self):
        meta = self.provider_combo.currentData() or {"kind": "builtin", "id": "Gemini"}
        provider_id = meta.get("id")

        if meta.get("kind") == "builtin":
            api_models = self.config.get("api_models", {})
            keys = self.config.get("keys", {})
            self.base_url_edit.setText("Built-in provider")
            self.base_url_edit.setReadOnly(True)
            self.model_edit.setText(api_models.get(provider_id, ""))
            self.api_key_edit.setText(keys.get(provider_id, ""))
        else:
            profile = self._find_custom_profile(provider_id)
            if not profile:
                self.base_url_edit.clear()
                self.model_edit.clear()
                self.api_key_edit.clear()
                return
            self.base_url_edit.setReadOnly(False)
            self.base_url_edit.setText(profile.get("base_url", ""))
            self.model_edit.setText(profile.get("model", ""))
            self.api_key_edit.setText(profile.get("api_key", ""))

    def _populate_model_combo(self):
        current_target = self.config.get("whisper_model", "turbo")
        self.model_combo.clear()

        for label, target in self.builtin_models:
            self.model_combo.addItem(label, target)

        for profile in self.config.get_custom_models():
            target = profile.get("target") or profile.get("path", "")
            self.model_combo.addItem(f"{profile.get('name', 'Custom Model')} (Custom)", target)

        selected_index = 0
        found_target = False
        for index in range(self.model_combo.count()):
            if self.model_combo.itemData(index) == current_target:
                selected_index = index
                found_target = True
                break

        if not found_target and current_target:
            self.model_combo.addItem(self.config.get("selected_model_label", "Current Custom Model"), current_target)
            selected_index = self.model_combo.count() - 1

        self.model_combo.setCurrentIndex(selected_index)
        self.model_target_label.setText(f"Current runtime target: {current_target}")

    def _save_selected_model(self):
        model_target = self.model_combo.currentData()
        model_label = self.model_combo.currentText()
        self.config.set("whisper_model", model_target)
        self.config.set("selected_model_label", model_label)
        self.engine.model = None
        self.engine.loaded_model_target = None
        self.model_target_label.setText(f"Current runtime target: {model_target}")
        self._refresh_engine_summary()
        QMessageBox.information(self, "Model Updated", f"{model_label} will be used on the next recording.")

    def _browse_model_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Model Folder")
        if path:
            self.custom_model_target_edit.setText(path)

    def _save_custom_model(self):
        label = self.custom_model_name_edit.text().strip()
        target = self.custom_model_target_edit.text().strip()

        if not label or not target:
            QMessageBox.warning(self, "Missing Model Data", "Enter both a label and a target path/model ID.")
            return

        profile = {
            "id": f"custom-model-{label.lower().replace(' ', '-')}",
            "name": label,
            "target": target,
        }
        self.config.upsert_custom_model(profile)
        self.custom_model_name_edit.clear()
        self.custom_model_target_edit.clear()
        self._populate_model_combo()
        QMessageBox.information(self, "Custom Model Saved", f"{label} is now available in the model selector.")

    def _open_custom_api_dialog(self):
        dialog = CustomApiProfilesDialog(self.config, self)
        dialog.profilesUpdated.connect(self._populate_provider_combo)
        dialog.exec()
        self._populate_provider_combo()
        self.apiSettingsChanged.emit()

    def _save_api_settings(self):
        meta = self.provider_combo.currentData() or {"kind": "builtin", "id": "Gemini"}
        provider_id = meta.get("id")
        model = self.model_edit.text().strip()
        api_key = self.api_key_edit.text().strip()
        base_url = self.base_url_edit.text().strip()

        if meta.get("kind") == "builtin":
            keys = self.config.get("keys", {})
            keys[provider_id] = api_key
            api_models = self.config.get("api_models", {})
            api_models[provider_id] = model
            self.config.set("keys", keys)
            self.config.set("api_models", api_models)
        else:
            profile = self._find_custom_profile(provider_id)
            if not profile:
                QMessageBox.warning(self, "Missing Profile", "Select a valid custom API profile before saving.")
                return
            profile["model"] = model
            profile["api_key"] = api_key
            profile["base_url"] = base_url
            self.config.upsert_custom_api_profile(profile)

        self.config.set("provider", provider_id)
        self.engine.refresh_ai_handler()
        self.apiSettingsChanged.emit()
        QMessageBox.information(self, "API Settings Saved", "AI provider settings were updated.")

    def _test_api_connection(self):
        meta = self.provider_combo.currentData() or {"kind": "builtin", "id": "Gemini"}
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Missing API Key", "Enter an API key before testing.")
            return

        if meta.get("kind") == "builtin":
            provider_name = meta.get("id", "Gemini")
            api_type = "gemini" if provider_name == "Gemini" else "openai_compatible"
            base_url = None
        else:
            profile = self._find_custom_profile(meta.get("id"))
            if not profile:
                QMessageBox.warning(self, "Missing Profile", "Select a valid custom API profile before testing.")
                return
            provider_name = profile.get("name", "Custom API")
            api_type = profile.get("api_type", "openai_compatible")
            base_url = self.base_url_edit.text().strip() or None

        ok, message = AIHandler.validate_api_key(provider_name, api_key, base_url=base_url, api_type=api_type)
        if ok:
            QMessageBox.information(self, "API Test", "Connection succeeded.")
        else:
            QMessageBox.warning(self, "API Test", message)

    def _browse_storage_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Storage Folder", self.path_edit.text())
        if path:
            self.path_edit.setText(path)

    def _save_behavior_settings(self):
        shortcut = self.shortcut_edit.text().strip() or "ctrl+alt+r"
        self.config.set("shortcut", shortcut)
        self.config.set("privacy_mode", self.privacy_combo.currentData())
        self.config.set("use_ai_refinement", self.refinement_check.isChecked())
        self.config.set("auto_clipboard", self.clipboard_check.isChecked())
        self.config.set("storage_path", self.path_edit.text().strip())

        message = "Behavior settings were updated."
        if self.hotkey_manager is not None:
            success, status_message = self.hotkey_manager.register(shortcut)
            if success:
                message += f"\nHotkey reloaded live as {shortcut.upper()}."
            else:
                message += f"\nSaved, but the hotkey could not be rebound now: {status_message}"
        else:
            message += "\nRestart the app to apply hotkey changes."

        self.shortcutChanged.emit(shortcut)
        QMessageBox.information(self, "Behavior Saved", message)

    def _open_engine_catalog(self):
        dialog = EngineCatalogDialog(self.config, self)
        dialog.selectionChanged.connect(self._refresh_engine_summary)
        dialog.exec()
        self._refresh_engine_summary()

    def _refresh_engine_summary(self):
        preferred_engine = self.config.get("preferred_engine_profile", "faster-whisper")
        selected_model = self.config.get("selected_model_label", self.config.get("whisper_model", "turbo"))
        recommended_model = SystemSpecs.recommended_whisper_model(self.system_specs)
        installed_count = len(self.config.get_installed_engines())
        summary = (
            f"Preferred engine profile: {preferred_engine}\n"
            f"Active runtime target: {selected_model}\n"
            f"Recommended local Whisper model for this PC: {recommended_model}\n"
            f"Installed engine profiles: {installed_count}"
        )
        if preferred_engine != "faster-whisper":
            summary += "\nNote: the live runtime still falls back to faster-whisper today."
        self.engine_summary_label.setText(summary)

    def _find_custom_profile(self, profile_id):
        for profile in self.config.get_custom_api_profiles():
            if profile.get("id") == profile_id:
                return dict(profile)
        return {}

class QtMainWindow(QMainWindow):
    def __init__(self, config, engine, hotkey_manager=None):
        super().__init__()
        self.config = config
        self.engine = engine
        self.hotkey_manager = hotkey_manager
        self.history_service = TranscriptHistoryService(self.config)
        self.app_ready = False
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1100, 800)
        self.setStyleSheet(EZ_THEME_QSS)
        self._init_ui()
        self.show()
        self._apply_native_effects()

    def _init_ui(self):
        self.central_widget = QWidget()
        self.central_widget.setObjectName("MainContent")
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.sidebar = EzSidebar(self)
        self.sidebar.tabChanged.connect(self._handle_nav)
        self.sidebar.transcriptSelected.connect(self.open_transcript_file)
        self.main_layout.addWidget(self.sidebar)

        self.content_stack = QStackedWidget()
        self.main_layout.addWidget(self.content_stack)

        self.dashboard = DashboardView(self.config)
        self.recording = RecordingView()
        self.settings = ConfigurationView(self.config, self.engine, self.hotkey_manager)
        self.diagnostics = DiagnosticsView(self.config, self.hotkey_manager, self.engine)

        self.settings.shortcutChanged.connect(self.dashboard.refresh_shortcut_hint)
        self.settings.shortcutChanged.connect(lambda _shortcut: self.diagnostics.refresh_hotkey_summary())
        self.settings.apiSettingsChanged.connect(self.diagnostics.refresh_api_summary)
        self.diagnostics.audioSettingsChanged.connect(self.dashboard.refresh_input_device_hint)

        self.content_stack.addWidget(self.dashboard)
        self.content_stack.addWidget(self.recording)
        self.content_stack.addWidget(self.settings)
        self.content_stack.addWidget(self.diagnostics)

        self.startup_overlay = StartupOverlay(self.central_widget)
        self.startup_overlay.closeRequested.connect(QApplication.instance().quit)

        self._set_app_locked(True)
        self._handle_nav("home")

    def _apply_native_effects(self):
        hwnd = self.winId()
        apply_window_masking(int(hwnd), radius=30)
        enable_acrylic_effect(int(hwnd), theme="dark")
        set_window_shadow(int(hwnd), enabled=True)

    def _set_app_locked(self, locked):
        self.app_ready = not locked
        for widget in (self.sidebar, self.dashboard, self.recording, self.settings, self.diagnostics):
            widget.setEnabled(not locked)

        if locked:
            self.content_stack.setCurrentWidget(self.dashboard)
            self.startup_overlay.show()
            self.startup_overlay.raise_()

    @Slot(int, str, str)
    def update_startup_progress(self, percent, title, detail):
        self.startup_overlay.update_progress(percent, title, detail)
        self.startup_overlay.raise_()

    @Slot(str)
    def finish_startup(self, message):
        self.startup_overlay.mark_ready(message)
        self._set_app_locked(False)
        self.startup_overlay.hide()
        self.dashboard.refresh_input_device_hint()
        self.refresh_transcript_history()

    @Slot(str)
    def fail_startup(self, message):
        self._set_app_locked(True)
        self.startup_overlay.mark_failed(message)
        self.startup_overlay.raise_()

    def _handle_nav(self, key):
        if not self.app_ready:
            self.content_stack.setCurrentWidget(self.dashboard)
            return

        target = self.dashboard
        if key == "settings":
            target = self.settings
        elif key == "diagnostics":
            self.diagnostics.refresh_all()
            target = self.diagnostics
        self.content_stack.setCurrentWidget(target)

    def refresh_transcript_history(self):
        self.sidebar.refresh_history(self.history_service.list_entries())

    def open_transcript_file(self, path: str):
        transcript_path = pathlib.Path(path)
        try:
            text = transcript_path.read_text(encoding="utf-8")
        except Exception as exc:
            QMessageBox.warning(self, "Transcript Unavailable", f"Could not open transcript:\n{exc}")
            return

        self.recording.waveform.setActive(False)
        self.recording.det_label.setText("SAVED TRANSCRIPT")
        self.recording.status_line.setText(f"Viewing saved transcript from {transcript_path.name}")
        self.recording.main_text.setPlainText(text.strip() or "This transcript file is empty.")
        self.recording.interim_text.setText("")
        self.content_stack.setCurrentWidget(self.recording)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "startup_overlay"):
            self.startup_overlay.setGeometry(self.central_widget.rect())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()
