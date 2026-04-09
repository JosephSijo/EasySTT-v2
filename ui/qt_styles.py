# EzSTT PySide6 Theme Engine
# Aesthetic: Deep Space / Obsidian

EZ_THEME_QSS = """
/* Global Styles */
QMainWindow, QWidget#MainContent {
    background-color: #081015;
    color: #ffffff;
    font-family: 'Segoe UI Variable Display', 'Inter', sans-serif;
}

QFrame#StartupOverlay {
    background-color: rgba(4, 10, 14, 235);
}

QFrame#StartupCard {
    background-color: #0a141a;
    border: 1px solid #1a2b36;
    border-radius: 18px;
}

QLabel#StartupEyebrow {
    color: #1392ec;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}

QLabel#StartupTitle {
    color: #ffffff;
    font-size: 28px;
    font-weight: bold;
}

QLabel#StartupStatus {
    color: #ffffff;
    font-size: 16px;
    font-weight: 600;
}

QLabel#StartupDetail, QLabel#StartupState {
    color: #8aa0af;
    font-size: 12px;
}

QProgressBar#StartupProgress {
    border: 1px solid #1a2b36;
    border-radius: 10px;
    background-color: #050b0f;
    color: #d5dce1;
    text-align: center;
    min-height: 24px;
}

QProgressBar#StartupProgress::chunk {
    background-color: #1392ec;
    border-radius: 8px;
}

/* Sidebar */
QFrame#EzSidebar {
    background-color: #050b0f;
    border-right: 1px solid #1a2b36;
}

QLineEdit#SidebarSearch {
    background-color: #0a141a;
    border: 1px solid #13202a;
    border-radius: 6px;
    padding: 10px 15px;
    color: #6d8595;
    font-size: 11px;
    margin: 10px 15px;
}

QLabel#SidebarHeading {
    color: #7f95a3;
    font-size: 10px;
    font-weight: bold;
    margin-left: 20px;
    margin-top: 20px;
    margin-bottom: 5px;
}

QPushButton#SidebarItem {
    background-color: transparent;
    color: #9db1c0;
    text-align: left;
    padding: 8px 25px;
    font-size: 12px;
    border: none;
}

QPushButton#SidebarItem:hover {
    color: #ffffff;
}

QPushButton#SidebarItem[active="true"] {
    background-color: #0d171d;
    color: #1392ec;
    border-radius: 8px;
    margin: 0px 10px;
}

/* Dashboard & Recording View */
QLabel#DashboardTitle {
    font-size: 42px;
    font-weight: bold;
    color: #ffffff;
}

QFrame#EzCard {
    background-color: #0a141a;
    border: 1px solid #1a2b36;
    border-radius: 14px;
}

QLabel#DashboardSub {
    font-size: 14px;
    color: #90a3af;
    line-height: 20px;
}

/* Mic Button */
QPushButton#MicButton {
    background-color: #1392ec;
    border-radius: 60px;
}

QPushButton#MicButton:hover {
    background-color: #1a9df2;
}

/* Health Cards (Workspace) */
QFrame#HealthCard {
    background-color: #0a141a;
    border-radius: 12px;
    padding: 15px;
}

QProgressBar#HealthBar {
    border: none;
    background-color: #050b0f;
    height: 4px;
    border-radius: 2px;
}

QProgressBar#HealthBar::chunk {
    background-color: #1392ec;
    border-radius: 2px;
}

/* Transcript Area */
QFrame#TranscriptCard {
    background-color: #050b0f;
    border: 1px solid #1a2b36;
    border-radius: 15px;
}

QTextEdit#MainTranscript {
    background-color: transparent;
    border: none;
    color: #f2f7fb;
    font-size: 23px;
    font-weight: 500;
    line-height: 1.4;
    selection-background-color: #17415f;
}

QLabel#InterimTranscript {
    font-size: 17px;
    color: #7f95a3;
    font-style: italic;
}

/* Session Controls */
QPushButton#PauseButton {
    background-color: #1a2b36;
    color: #ffffff;
    border-radius: 10px;
    padding: 10px 25px;
    font-weight: 600;
}

QPushButton#StopButton {
    background-color: #f44336;
    color: #ffffff;
    border-radius: 10px;
    padding: 10px 25px;
    font-weight: 600;
}

QPushButton#SecondaryButton {
    background-color: #0d171d;
    color: #d5dce1;
    border: 1px solid #1a2b36;
    border-radius: 10px;
    padding: 10px 14px;
    min-height: 20px;
}

QPushButton#SecondaryButton:hover {
    border-color: #1392ec;
    color: #ffffff;
}

QLineEdit, QComboBox, QTextEdit {
    background-color: #081015;
    border: 1px solid #1a2b36;
    border-radius: 8px;
    padding: 10px 12px;
    color: #ffffff;
}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border: 1px solid #1392ec;
}

QCheckBox {
    color: #d5dce1;
    spacing: 8px;
}

QScrollArea, QWidget#SettingsScrollHost {
    background: transparent;
}

/* User Profile (Sidebar Bottom) */
QFrame#UserProfile {
    background-color: #0a141a;
    border-radius: 10px;
    margin: 10px;
}

/* Common Components (from Phase 17) */
QPushButton#NavButton {
    background-color: transparent;
    color: #9db1c0;
    border: none;
    text-align: left;
    padding: 12px 25px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton#NavButton:hover {
    color: #ffffff;
    background-color: #091219;
}

QPushButton#NavButton[active="true"] {
    background-color: #0d171d;
    color: #ffffff;
    border-left: 3px solid #1392ec;
}
"""
