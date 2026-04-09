import pathlib
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtWidgets import QApplication

from core.config_manager import ConfigManager
from core.engine import STTEngine
from core.hotkey_manager import HotkeyManager
from ui.qt_main_window import QtMainWindow


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    smoke_output_dir = REPO_ROOT / "verification" / ".smoke-output"
    smoke_output_dir.mkdir(parents=True, exist_ok=True)

    config = ConfigManager("EasySTTSmokeTest")
    config.set("a2a_enabled", False)
    config.set("storage_path", str(smoke_output_dir))
    config.set("shortcut", "ctrl+alt+t")

    config.upsert_custom_api_profile(
        {
            "id": "custom-smoke",
            "name": "Smoke API",
            "api_type": "openai_compatible",
            "base_url": "https://example.invalid/v1",
            "model": "gpt-4o-mini",
            "api_key": "",
        }
    )
    config.set("provider", "custom-smoke")

    config.upsert_custom_model(
        {
            "id": "smoke-model",
            "name": "Smoke Custom Model",
            "target": "hf.co/example/smoke-model",
        }
    )
    config.set("whisper_model", "turbo")
    config.set("selected_model_label", "Whisper Turbo")
    (smoke_output_dir / "stt_123456.txt").write_text(
        "This is a smoke transcript history entry for the sidebar.",
        encoding="utf-8",
    )

    app = QApplication.instance() or QApplication([])
    engine = STTEngine(config)
    hotkey_manager = HotkeyManager()
    hotkey_manager.set_primary_handler(lambda: None)

    window = None
    try:
        window = QtMainWindow(config, engine, hotkey_manager)
        app.processEvents()

        _assert(not window.dashboard.isEnabled(), "Window should start locked before readiness completes.")
        window.update_startup_progress(80, "Smoke startup", "Simulating model preload for the readiness gate.")
        window.finish_startup("Smoke startup complete.")
        app.processEvents()
        _assert(window.dashboard.isEnabled(), "Window did not unlock after readiness finished.")

        _assert(window.content_stack.count() == 4, "Expected dashboard, recording, settings, and diagnostics pages.")
        _assert(window.settings.provider_combo.count() >= 3, "Expected built-in and custom API providers.")
        _assert(window.settings.model_combo.count() >= 7, "Expected built-in and custom models in the selector.")

        provider_ids = []
        for index in range(window.settings.provider_combo.count()):
            meta = window.settings.provider_combo.itemData(index) or {}
            provider_ids.append(meta.get("id"))
        _assert("custom-smoke" in provider_ids, "Custom API profile did not appear in settings.")

        model_targets = [window.settings.model_combo.itemData(index) for index in range(window.settings.model_combo.count())]
        _assert("hf.co/example/smoke-model" in model_targets, "Custom model did not appear in settings.")

        _assert("Preferred engine profile" in window.settings.engine_summary_label.text(), "Engine summary did not render.")
        _assert(window.sidebar.history_entries, "Transcript history did not load into the sidebar.")

        window._handle_nav("diagnostics")
        app.processEvents()
        window.diagnostics.refresh_all()

        before = hotkey_manager.status_snapshot().get("trigger_count", 0)
        hotkey_manager.simulate_trigger()
        after = hotkey_manager.status_snapshot().get("trigger_count", 0)
        _assert(after == before + 1, "Hotkey diagnostics did not record the simulated trigger.")
        _assert("Active provider: custom-smoke" in window.diagnostics.api_summary.text(), "Diagnostics API summary is stale.")

        print("SMOKE_OK")
    finally:
        hotkey_manager.shutdown()
        if window is not None:
            window.close()
            app.processEvents()
        app.quit()


if __name__ == "__main__":
    main()
