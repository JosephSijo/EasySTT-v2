import re
import time
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.ai_handler import AIHandler
from core.engine_catalog import EngineCatalogService
from core.system_specs import SystemSpecs


def _slugify(value: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return clean or f"profile-{int(time.time())}"


class CustomApiProfilesDialog(QDialog):
    profilesUpdated = Signal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.current_profile_id: Optional[str] = None
        self.setWindowTitle("Custom AI APIs")
        self.resize(860, 420)
        self._build_ui()
        self._load_profiles()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(16)

        self.profile_list = QListWidget()
        self.profile_list.currentRowChanged.connect(self._load_selected_profile)
        root.addWidget(self.profile_list, 1)

        editor = QFrame()
        editor_layout = QVBoxLayout(editor)
        editor_layout.setSpacing(10)

        title = QLabel("Custom API Profile")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #ffffff;")
        subtitle = QLabel("Add Gemini or OpenAI-compatible endpoints and reusable model defaults.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #8aa0af;")
        editor_layout.addWidget(title)
        editor_layout.addWidget(subtitle)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Profile name")
        editor_layout.addWidget(self._labeled_field("Name", self.name_edit))

        self.type_combo = QComboBox()
        self.type_combo.addItem("OpenAI Compatible", "openai_compatible")
        self.type_combo.addItem("Gemini", "gemini")
        editor_layout.addWidget(self._labeled_field("API Type", self.type_combo))

        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText("https://api.example.com/v1")
        editor_layout.addWidget(self._labeled_field("Base URL", self.base_url_edit))

        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("Model name, for example gpt-4o-mini or gemini-2.0-flash")
        editor_layout.addWidget(self._labeled_field("Default Model", self.model_edit))

        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("API key")
        editor_layout.addWidget(self._labeled_field("API Key", self.key_edit))

        buttons = QHBoxLayout()
        self.new_btn = QPushButton("New")
        self.new_btn.clicked.connect(self._reset_form)
        self.test_btn = QPushButton("Test")
        self.test_btn.clicked.connect(self._test_profile)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_profile)
        self.save_btn = QPushButton("Save Profile")
        self.save_btn.clicked.connect(self._save_profile)
        buttons.addWidget(self.new_btn)
        buttons.addWidget(self.test_btn)
        buttons.addStretch()
        buttons.addWidget(self.delete_btn)
        buttons.addWidget(self.save_btn)
        editor_layout.addLayout(buttons)
        editor_layout.addStretch()

        root.addWidget(editor, 2)

    def _labeled_field(self, label: str, widget: QWidget) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label_widget = QLabel(label.upper())
        label_widget.setStyleSheet("font-size: 11px; font-weight: 700; color: #5d7688;")
        layout.addWidget(label_widget)
        layout.addWidget(widget)
        return wrapper

    def _load_profiles(self):
        self.profile_list.clear()
        profiles = self.config.get_custom_api_profiles()

        for profile in profiles:
            self.profile_list.addItem(profile.get("name", profile.get("id", "Custom API")))

        if profiles:
            self.profile_list.setCurrentRow(0)
        else:
            self._reset_form()

    def _load_selected_profile(self, index: int):
        profiles = self.config.get_custom_api_profiles()
        if index < 0 or index >= len(profiles):
            return

        profile = profiles[index]
        self.current_profile_id = profile.get("id")
        self.name_edit.setText(profile.get("name", ""))
        self.type_combo.setCurrentIndex(0 if profile.get("api_type", "openai_compatible") == "openai_compatible" else 1)
        self.base_url_edit.setText(profile.get("base_url", ""))
        self.model_edit.setText(profile.get("model", ""))
        self.key_edit.setText(profile.get("api_key", ""))

    def _reset_form(self):
        self.current_profile_id = None
        self.profile_list.clearSelection()
        self.name_edit.clear()
        self.type_combo.setCurrentIndex(0)
        self.base_url_edit.clear()
        self.model_edit.clear()
        self.key_edit.clear()

    def _save_profile(self):
        name = self.name_edit.text().strip()
        model = self.model_edit.text().strip()
        api_type = self.type_combo.currentData()
        base_url = self.base_url_edit.text().strip()

        if not name:
            QMessageBox.warning(self, "Missing Name", "Enter a profile name before saving.")
            return

        if not model:
            QMessageBox.warning(self, "Missing Model", "Enter a default model name for this API.")
            return

        if api_type == "openai_compatible" and not base_url:
            QMessageBox.warning(self, "Missing Base URL", "OpenAI-compatible profiles need a base URL.")
            return

        profile_id = self.current_profile_id or f"custom-{_slugify(name)}"
        profile = {
            "id": profile_id,
            "name": name,
            "api_type": api_type,
            "base_url": base_url,
            "model": model,
            "api_key": self.key_edit.text().strip(),
        }

        self.config.upsert_custom_api_profile(profile)
        self.profilesUpdated.emit()
        self._load_profiles()
        self._select_profile(profile_id)

    def _select_profile(self, profile_id: str):
        profiles = self.config.get_custom_api_profiles()
        for index, profile in enumerate(profiles):
            if profile.get("id") == profile_id:
                self.profile_list.setCurrentRow(index)
                return

    def _delete_profile(self):
        if not self.current_profile_id:
            return

        self.config.remove_custom_api_profile(self.current_profile_id)
        self.current_profile_id = None
        self.profilesUpdated.emit()
        self._load_profiles()

    def _test_profile(self):
        api_type = self.type_combo.currentData()
        key = self.key_edit.text().strip()
        if not key:
            QMessageBox.warning(self, "Missing API Key", "Enter an API key before testing.")
            return

        ok, message = AIHandler.validate_api_key(
            self.name_edit.text().strip() or "Custom API",
            key,
            base_url=self.base_url_edit.text().strip() or None,
            api_type=api_type,
        )
        if ok:
            QMessageBox.information(self, "API Test", "Connection succeeded.")
        else:
            QMessageBox.warning(self, "API Test", message)


class EngineCatalogDialog(QDialog):
    selectionChanged = Signal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.system_specs = SystemSpecs.detect()
        self.catalog_service = EngineCatalogService()
        self.setWindowTitle("Engine Catalog")
        self.resize(900, 620)
        self._build_ui()
        self._refresh_catalog()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Recommended STT Engines")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #ffffff;")
        summary = QLabel(self._build_summary_text())
        summary.setWordWrap(True)
        summary.setStyleSheet("color: #8aa0af;")
        layout.addWidget(title)
        layout.addWidget(summary)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_host = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_host)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(12)
        self.scroll.setWidget(self.scroll_host)
        layout.addWidget(self.scroll)

    def _build_summary_text(self) -> str:
        gpu = self.system_specs.get("gpu_name") or "CPU only"
        return (
            f"{self.system_specs.get('os')} {self.system_specs.get('os_version')} • "
            f"{self.system_specs.get('memory_gb')} GB RAM • "
            f"{self.system_specs.get('cpu_count')} logical cores • {gpu}"
        )

    def _refresh_catalog(self):
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        catalog = self.catalog_service.build_catalog(
            self.system_specs,
            self.config.get_installed_engines(),
        )

        for engine in catalog:
            self.scroll_layout.addWidget(self._build_engine_card(engine))

        self.scroll_layout.addStretch()

    def _build_engine_card(self, engine: Dict[str, Any]) -> QWidget:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background: #0a141a; border: 1px solid #1a2b36; border-radius: 14px; }"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)

        title_row = QHBoxLayout()
        title = QLabel(engine["name"])
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #ffffff;")
        title_row.addWidget(title)
        title_row.addStretch()

        status_parts = []
        if engine.get("integration_level") == "native":
            status_parts.append("Integrated")
        else:
            status_parts.append("Profile Ready")
        if engine.get("recommended"):
            status_parts.append("Recommended")
        if engine.get("installed"):
            status_parts.append("Installed")

        badge = QLabel(" • ".join(status_parts))
        badge.setStyleSheet("color: #1392ec; font-size: 11px; font-weight: 700;")
        title_row.addWidget(badge)
        layout.addLayout(title_row)

        description = QLabel(engine["description"])
        description.setWordWrap(True)
        description.setStyleSheet("color: #d5dce1;")
        layout.addWidget(description)

        fit = QLabel(f"Best for: {engine['best_for']} | Package: {engine['download_size']}")
        fit.setStyleSheet("color: #8aa0af; font-size: 11px;")
        layout.addWidget(fit)

        recommendation = engine.get("recommendation")
        if recommendation:
            note = QLabel(recommendation)
            note.setWordWrap(True)
            note.setStyleSheet("color: #4caf50; font-size: 11px;")
            layout.addWidget(note)

        actions = QHBoxLayout()
        install_btn = QPushButton("Reinstall Profile" if engine.get("installed") else "Install Profile")
        install_btn.clicked.connect(lambda _checked=False, data=engine: self._install_profile(data))
        preferred_btn = QPushButton("Set Preferred")
        preferred_btn.clicked.connect(lambda _checked=False, data=engine: self._set_preferred(data))
        actions.addWidget(install_btn)
        actions.addWidget(preferred_btn)
        actions.addStretch()
        layout.addLayout(actions)

        return card

    def _install_profile(self, engine: Dict[str, Any]):
        manifest_path = self.catalog_service.install_profile(engine)
        self.config.upsert_installed_engine(engine)
        self._refresh_catalog()
        self.selectionChanged.emit()
        QMessageBox.information(
            self,
            "Engine Profile Installed",
            f"{engine['name']} profile saved to:\n{manifest_path}",
        )

    def _set_preferred(self, engine: Dict[str, Any]):
        self.config.set("preferred_engine_profile", engine["id"])
        self.selectionChanged.emit()

        message = f"{engine['name']} is now your preferred engine profile."
        if engine.get("integration_level") != "native":
            message += "\n\nThe current transcription runtime still uses faster-whisper until that backend is wired in."

        QMessageBox.information(self, "Preferred Engine", message)
