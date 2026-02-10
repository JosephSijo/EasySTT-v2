import sys
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QStackedWidget, QLabel, QFrame, QLineEdit, 
                             QPushButton, QScrollArea, QSizePolicy, QSpacerItem)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QIcon, QColor

from .qt_styles import EZ_THEME_QSS
from .qt_widgets import (EzSidebar, EzToggle, SelectableCard, StatusBadge, 
                        WaveformVisualizer, HealthCard)
from core.win32_utils import apply_window_masking, enable_acrylic_effect, set_window_shadow

class DashboardView(QWidget):
    recordingRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 60, 60, 40)
        layout.setSpacing(0)

        # Top Bar
        top_bar = QHBoxLayout()
        breadcrumbs = QLabel("Workspaces  ›  Main Dashboard")
        breadcrumbs.setStyleSheet("color: #444444; font-size: 11px;")
        
        actions = QHBoxLayout()
        import_btn = QPushButton("☁️ Import Audio")
        import_btn.setObjectName("SecondaryButton")
        actions.addWidget(import_btn)
        actions.addWidget(QLabel("🔔"))
        actions.addWidget(QLabel("❓"))
        
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
        
        subtitle = QLabel("Start recording to transcribe your voice in real-time with\nenterprise-grade accuracy.")
        subtitle.setObjectName("DashboardSub")
        subtitle.setAlignment(Qt.AlignCenter)

        self.waveform = WaveformVisualizer()
        
        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setObjectName("MicButton")
        self.mic_btn.setFixedSize(120, 120)
        self.mic_btn.setCursor(Qt.PointingHandCursor)
        self.mic_btn.clicked.connect(self.recordingRequested.emit)
        
        hint_layout = QVBoxLayout()
        hint = QLabel("Click to start recording")
        hint.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff;")
        kbd_hint = QLabel("SPACEBAR  to quick start/stop")
        kbd_hint.setStyleSheet("color: #444444; font-size: 10px;")
        hint_layout.addWidget(hint, alignment=Qt.AlignCenter)
        hint_layout.addWidget(kbd_hint, alignment=Qt.AlignCenter)

        center_content.addWidget(title)
        center_content.addWidget(subtitle)
        center_content.addWidget(self.waveform, alignment=Qt.AlignCenter)
        center_content.addWidget(self.mic_btn, alignment=Qt.AlignCenter)
        center_content.addLayout(hint_layout)
        
        middle_layout.addLayout(center_content, 2)
        
        # Right Side Info (Health Card)
        right_panel = QVBoxLayout()
        self.health = HealthCard("Workspace Health", [
            ("Storage (2.4 GB)", "48%", 48),
            ("Credits (140 mins left)", "70%", 70)
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
        
        mic_status = QLabel("🟢 Microphone: MacBook Pro (Default)")
        mic_status.setStyleSheet("color: #ffffff; font-size: 11px;")
        lang_status = QLabel("Language: English (US)")
        lang_status.setStyleSheet("color: #1392ec; font-size: 11px; font-weight: bold;")
        
        dock_layout.addWidget(mic_status)
        dock_layout.addStretch()
        dock_layout.addWidget(lang_status)
        
        layout.addWidget(dock, alignment=Qt.AlignCenter)

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
        timer_badge = QLabel(" ● 03:45 REC ")
        timer_badge.setStyleSheet("background: #3c1a1a; color: #f44336; border-radius: 10px; font-weight: bold; padding: 5px;")
        session_title = QLabel("Active Session: Marketing Q3 Strategy")
        session_title.setStyleSheet("color: #666666; font-size: 11px;")
        header.addWidget(timer_badge)
        header.addWidget(session_title)
        header.addStretch()
        share_btn = QPushButton("🔗 Share")
        share_btn.setObjectName("SecondaryButton")
        header.addWidget(share_btn)
        header.addWidget(QLabel("⋮"))
        layout.addLayout(header)

        layout.addStretch()
        wave_box = QVBoxLayout()
        self.waveform = WaveformVisualizer()
        self.waveform.setActive(True)
        self.waveform.setFixedWidth(400)
        wave_box.addWidget(self.waveform, alignment=Qt.AlignCenter)
        det_label = QLabel("VOICE DETECTED")
        det_label.setStyleSheet("color: #1392ec; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        wave_box.addWidget(det_label, alignment=Qt.AlignCenter)
        layout.addLayout(wave_box)

        self.transcript_area = QFrame()
        self.transcript_area.setObjectName("TranscriptCard")
        t_layout = QVBoxLayout(self.transcript_area)
        t_layout.setContentsMargins(40, 60, 40, 60)
        self.main_text = QLabel("The quick brown fox jumps over the lazy dog and proceeds to explain the new architectural vision for the project.")
        self.main_text.setObjectName("MainTranscript")
        self.main_text.setWordWrap(True)
        self.main_text.setAlignment(Qt.AlignCenter)
        self.interim_text = QLabel("...")
        self.interim_text.setObjectName("InterimTranscript")
        self.interim_text.setAlignment(Qt.AlignCenter)
        t_layout.addWidget(self.main_text)
        t_layout.addWidget(self.interim_text)
        layout.addWidget(self.transcript_area)

        layout.addStretch()
        ctrl_card = QFrame()
        ctrl_card.setObjectName("EzCard")
        ctrl_card.setFixedWidth(400)
        ctrl_layout = QHBoxLayout(ctrl_card)
        pause_btn = QPushButton("⏸ PAUSE")
        pause_btn.setObjectName("PauseButton")
        stop_btn = QPushButton("⏹ STOP RECORDING")
        stop_btn.setObjectName("StopButton")
        stop_btn.clicked.connect(self.stopRequested.emit)
        ctrl_layout.addWidget(pause_btn)
        ctrl_layout.addWidget(stop_btn)
        layout.addWidget(ctrl_card, alignment=Qt.AlignCenter)

class ConfigurationView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        header_layout = QHBoxLayout()
        title_label = QLabel("AI Intelligence")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        status_widget = StatusBadge(label="SYSTEM STATUS", status="READY")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(status_widget)
        layout.addLayout(header_layout)

        description = QLabel("Configure your preferred language models and API integrations.")
        description.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(description)

        self._add_provider_card(layout, "Gemini Pro", "GOOGLE CLOUD API", "✦")
        self._add_provider_card(layout, "GPT-4o", "OPENAI API", "⌘")
        self._add_provider_card(layout, "Claude 3.5 Sonnet", "ANTHROPIC API", "▲")

        storage_header = QLabel("Storage")
        storage_header.setStyleSheet("font-size: 18px; font-weight: 600; margin-top: 20px;")
        layout.addWidget(storage_header)

        storage_card = QFrame()
        storage_card.setObjectName("EzCard")
        storage_layout = QVBoxLayout(storage_card)
        storage_layout.setContentsMargins(20, 20, 20, 20)
        path_label = QLabel("Save Directory")
        path_label.setStyleSheet("color: #888888; font-size: 11px; margin-bottom: 5px;")
        storage_layout.addWidget(path_label)
        path_input_layout = QHBoxLayout()
        self.path_edit = QLineEdit("/Users/ezstt/Documents/EzSTT/Recordings")
        self.path_edit.setReadOnly(True)
        browse_btn = QPushButton("Browse")
        browse_btn.setObjectName("SecondaryButton")
        path_input_layout.addWidget(self.path_edit)
        path_input_layout.addWidget(browse_btn)
        storage_layout.addLayout(path_input_layout)
        layout.addWidget(storage_card)
        layout.addStretch()

    def _add_provider_card(self, parent_layout, name, subtext, icon_char):
        card = QFrame()
        card.setObjectName("EzCard")
        card.setFixedHeight(120)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 15, 20, 15)
        top_row = QHBoxLayout()
        text_layout = QVBoxLayout()
        name_label = QLabel(name)
        name_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        sub_label = QLabel(subtext)
        sub_label.setStyleSheet("font-size: 9px; color: #888888;")
        text_layout.addWidget(name_label)
        text_layout.addWidget(sub_label)
        toggle = EzToggle()
        top_row.addLayout(text_layout)
        top_row.addStretch()
        top_row.addWidget(toggle)
        card_layout.addLayout(top_row)
        key_layout = QHBoxLayout()
        key_input = QLineEdit()
        key_input.setPlaceholderText("Enter API Key")
        key_input.setEchoMode(QLineEdit.Password)
        test_btn = QPushButton("TEST")
        test_btn.setObjectName("SecondaryButton")
        test_btn.setFixedWidth(60)
        key_layout.addWidget(key_input)
        key_layout.addWidget(test_btn)
        card_layout.addLayout(key_layout)
        parent_layout.addWidget(card)

class QtMainWindow(QMainWindow):
    def __init__(self, config, engine):
        super().__init__()
        self.config = config
        self.engine = engine
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
        self.main_layout.addWidget(self.sidebar)

        self.content_stack = QStackedWidget()
        self.main_layout.addWidget(self.content_stack)

        self.dashboard = DashboardView()
        self.recording = RecordingView()
        self.settings = ConfigurationView()

        self.content_stack.addWidget(self.dashboard)
        self.content_stack.addWidget(self.recording)
        self.content_stack.addWidget(self.settings)

    def _apply_native_effects(self):
        hwnd = self.winId()
        apply_window_masking(int(hwnd), radius=30)
        enable_acrylic_effect(int(hwnd), theme="dark")
        set_window_shadow(int(hwnd), enabled=True)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()
