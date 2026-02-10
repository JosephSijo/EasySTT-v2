from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QFrame, QScrollArea, QProgressBar, QLineEdit,
                             QSizePolicy, QSpacerItem)
from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QTimer, QRect

class WaveformVisualizer(QWidget):
    """
    Animated spectral waveform for voice detection feedback.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        self.setFixedWidth(200)
        self.bars = 12
        self.bar_heights = [10] * self.bars
        self._current_level = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(100)
        self._active = False

    def setActive(self, active):
        self._active = active
        if not active:
            self._current_level = 0.0

    def set_level(self, level: float):
        """Sets the current audio level (0.0 to 1.0)"""
        self._current_level = level

    def _animate(self):
        import random
        if self._active:
            # Shift heights based on current level + some micro-variation
            base_h = 5 + (self._current_level * 50)
            self.bar_heights = [max(2, int(base_h * random.uniform(0.5, 1.2))) for _ in range(self.bars)]
        else:
            self.bar_heights = [random.randint(2, 6) for _ in range(self.bars)]
        self.update()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor, QPen
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        spacing = 8
        bar_width = 4
        center_y = self.height() // 2
        
        for i, h in enumerate(self.bar_heights):
            x = (i * (bar_width + spacing)) + (self.width() - (self.bars * (bar_width + spacing))) // 2
            color = QColor("#1392ec") if self._active else QColor("#1a2b36")
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x, center_y - h//2, bar_width, h, 2, 2)

class HealthCard(QFrame):
    """
    Workspace health card with progress bars.
    """
    def __init__(self, title, items, parent=None):
        super().__init__(parent)
        self.setObjectName("HealthCard")
        layout = QVBoxLayout(self)
        
        header = QHBoxLayout()
        h_label = QLabel(title.upper())
        h_label.setStyleSheet("font-size: 10px; font-weight: bold; color: #ffffff;")
        header.addWidget(h_label)
        header.addStretch()
        opt_label = QLabel("OPTIMAL")
        opt_label.setStyleSheet("color: #4caf50; font-size: 8px; font-weight: bold;")
        header.addWidget(opt_label)
        layout.addLayout(header)
        
        for label, val, percent in items:
            row = QHBoxLayout()
            l_widget = QLabel(label)
            l_widget.setStyleSheet("color: #ffffff; font-size: 10px;")
            row.addWidget(l_widget)
            row.addStretch()
            v_label = QLabel(val)
            v_label.setStyleSheet("color: #888888; font-size: 10px;")
            row.addWidget(v_label)
            layout.addLayout(row)
            
            bar = QProgressBar()
            bar.setObjectName("HealthBar")
            bar.setValue(percent)
            bar.setTextVisible(False)
            bar.setFixedHeight(4)
            layout.addWidget(bar)

class SidebarProfile(QFrame):
    """
    Profile section at the bottom of the sidebar.
    """
    def __init__(self, name, plan, parent=None):
        super().__init__(parent)
        self.setObjectName("UserProfile")
        self.setFixedHeight(70)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        
        avatar = QLabel("👤")
        avatar.setStyleSheet("font-size: 24px; background: #0d171d; border-radius: 18px; padding: 5px;")
        
        details = QVBoxLayout()
        details.setSpacing(0)
        u_name = QLabel(name)
        u_name.setStyleSheet("font-weight: bold; color: #ffffff; font-size: 12px;")
        u_plan = QLabel(plan)
        u_plan.setStyleSheet("color: #1392ec; font-size: 9px; font-weight: bold;")
        details.addWidget(u_name)
        details.addWidget(u_plan)
        
        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(24, 24)
        settings_btn.setStyleSheet("background: transparent; border: none; font-size: 14px;")
        
        layout.addWidget(avatar)
        layout.addLayout(details)
        layout.addStretch()
        layout.addWidget(settings_btn)

class EzSidebar(QFrame):
    tabChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EzSidebar")
        self.setFixedWidth(260)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(0)

        # 1. Logo
        logo_container = QWidget()
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(25, 0, 0, 20)
        logo_label = QLabel("EzSTT")
        logo_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        logo_layout.addWidget(logo_label)
        layout.addWidget(logo_container)

        # 2. Top Nav
        self.nav_group = QWidget()
        self.nav_layout = QVBoxLayout(self.nav_group)
        self.nav_layout.setContentsMargins(0, 0, 0, 10)
        self.nav_layout.setSpacing(2)
        
        self.nav_btns = {}
        self._add_nav_btn("🏠  HOME", "home", active=True)
        self._add_nav_btn("🧩  ECOSYSTEM", "ecosystem")
        self._add_nav_btn("🛡️  PRIVACY", "privacy")
        self._add_nav_btn("⚙️  SETTINGS", "settings")
        layout.addWidget(self.nav_group)

        # 3. Search
        self.search = QLineEdit()
        self.search.setObjectName("SidebarSearch")
        self.search.setPlaceholderText("Search transcriptions...")
        layout.addWidget(self.search)

        # 4. History
        h1 = QLabel("  RECENT TRANSCRIPTIONS")
        h1.setObjectName("SidebarHeading")
        layout.addWidget(h1)
        
        self.recent_layout = QVBoxLayout()
        self.recent_layout.setContentsMargins(0, 5, 0, 5)
        self._add_history_btn(self.recent_layout, "Product Roadmap Sync", "2 mins ago • 14:32")
        self._add_history_btn(self.recent_layout, "Interview with Sarah J.", "Yesterday • 45:10")
        layout.addLayout(self.recent_layout)

        # 5. Folders
        h2 = QLabel("  FOLDERS")
        h2.setObjectName("SidebarHeading")
        layout.addWidget(h2)
        self.folder_layout = QVBoxLayout()
        self._add_history_btn(self.folder_layout, "📁 Personal Notes")
        self._add_history_btn(self.folder_layout, "📁 Client Meetings")
        layout.addLayout(self.folder_layout)
        
        layout.addStretch()

        # 6. Profile
        self.profile = SidebarProfile("Alex Chen", "PREMIUM PLAN")
        layout.addWidget(self.profile)

        self.workspace_btn = QPushButton("← Back to Workspace")
        self.workspace_btn.setObjectName("NavButton")
        self.workspace_btn.setFixedHeight(40)
        layout.addWidget(self.workspace_btn)

    def _add_nav_btn(self, text, key, active=False):
        btn = QPushButton(text)
        btn.setObjectName("NavButton")
        btn.setProperty("active", active)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self._on_nav_clicked(key))
        self.nav_layout.addWidget(btn)
        self.nav_btns[key] = btn

    def _on_nav_clicked(self, key):
        for k, b in self.nav_btns.items():
            b.setProperty("active", k == key)
            b.style().unpolish(b)
            b.style().polish(b)
        self.tabChanged.emit(key)

    def _add_history_btn(self, target_layout, text, sub=None):
        btn = QPushButton()
        btn.setObjectName("SidebarItem")
        btn.setCursor(Qt.PointingHandCursor)
        l = QVBoxLayout(btn)
        l.setContentsMargins(25, 8, 25, 8)
        l.setSpacing(2)
        t = QLabel(text); t.setStyleSheet("font-weight: 500; font-size: 13px; color: inherit;")
        l.addWidget(t)
        if sub:
            s = QLabel(sub); s.setStyleSheet("font-size: 9px; color: #555555;")
            l.addWidget(s)
        target_layout.addWidget(btn)

class EzToggle(QPushButton):
    toggledSignal = Signal(bool)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(40, 24)
        self.setCursor(Qt.PointingHandCursor)
        self._state = False
        self.clicked.connect(self._handle_click)
    def _handle_click(self):
        self._state = not self._state
        self.toggledSignal.emit(self._state)
        self._update_style()
    def _update_style(self):
        color = "#1392ec" if self._state else "#1a2b36"
        self.setStyleSheet(f"background-color: {color}; border-radius: 12px; border: none;")

class SelectableCard(QFrame):
    clicked = Signal()
    def __init__(self, title, subtitle, icon="✦", parent=None):
        super().__init__(parent)
        self.setObjectName("EzCard")
        self.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        header = QHBoxLayout()
        ic = QLabel(icon); ic.setStyleSheet("font-size: 24px; color: #1392ec;")
        text_layout = QVBoxLayout()
        self.t = QLabel(title); self.t.setObjectName("CardTitle")
        self.s = QLabel(subtitle); self.s.setObjectName("CardSubTitle"); self.s.setWordWrap(True)
        text_layout.addWidget(self.t); text_layout.addWidget(self.s)
        header.addWidget(ic); header.addLayout(text_layout); header.addStretch()
        layout.addLayout(header)
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

class StatusBadge(QWidget):
    def __init__(self, label="SYSTEM", status="READY", parent=None):
        super().__init__(parent)
        l = QHBoxLayout(self); l.setContentsMargins(0, 0, 0, 0)
        self.lab = QLabel(label.upper()); self.lab.setStyleSheet("color: #888888; font-size: 8px; font-weight: bold;")
        self.sta = QLabel(status.upper()); self.sta.setStyleSheet("color: #4caf50; font-size: 8px; font-weight: bold;")
        l.addWidget(self.lab); l.addWidget(self.sta)
