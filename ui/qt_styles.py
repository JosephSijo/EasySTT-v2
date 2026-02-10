# EzSTT PySide6 Theme Engine
# Aesthetic: Deep Space / Obsidian

EZ_THEME_QSS = """
/* Global Styles */
QMainWindow, QWidget#MainContent {
    background-color: #081015;
    color: #ffffff;
    font-family: 'Segoe UI Variable Display', 'Inter', sans-serif;
}

/* Sidebar */
QFrame#EzSidebar {
    background-color: #050b0f;
    border-right: 1px solid #1a2b36;
}

QLineEdit#SidebarSearch {
    background-color: #0a141a;
    border: none;
    border-radius: 6px;
    padding: 10px 15px;
    color: #888888;
    font-size: 11px;
    margin: 10px 15px;
}

QLabel#SidebarHeading {
    color: #444444;
    font-size: 9px;
    font-weight: bold;
    margin-left: 20px;
    margin-top: 20px;
    margin-bottom: 5px;
}

QPushButton#SidebarItem {
    background-color: transparent;
    color: #555555;
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

QLabel#DashboardSub {
    font-size: 14px;
    color: #666666;
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

QLabel#MainTranscript {
    font-size: 28px;
    font-weight: 500;
    line-height: 1.4;
    color: #ffffff;
}

QLabel#InterimTranscript {
    font-size: 28px;
    color: #555555;
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

/* User Profile (Sidebar Bottom) */
QFrame#UserProfile {
    background-color: #0a141a;
    border-radius: 10px;
    margin: 10px;
}

/* Common Components (from Phase 17) */
QPushButton#NavButton {
    background-color: transparent;
    color: #888888;
    border: none;
    text-align: left;
    padding: 12px 25px;
    font-size: 13px;
    font-weight: 500;
}
"""
