import time
from typing import Callable, Dict, List, Optional

try:
    import keyboard
except ImportError:  # pragma: no cover - handled at runtime
    keyboard = None


class HotkeyManager:
    """Owns the app-wide hotkey binding and lightweight diagnostics state."""

    def __init__(self):
        self.shortcut: Optional[str] = None
        self.primary_handler: Optional[Callable[[], None]] = None
        self.hotkey_id = None
        self.is_registered = False
        self.last_error = ""
        self.trigger_count = 0
        self.last_trigger_time: Optional[float] = None
        self._listeners: List[Callable[[str, int], None]] = []

    def set_primary_handler(self, handler: Callable[[], None]) -> None:
        self.primary_handler = handler

    def register(self, shortcut: str, handler: Optional[Callable[[], None]] = None) -> tuple[bool, str]:
        if handler is not None:
            self.primary_handler = handler

        self.unregister()
        self.shortcut = shortcut

        if keyboard is None:
            self.is_registered = False
            self.last_error = "keyboard library is not installed."
            return False, self.last_error

        try:
            self.hotkey_id = keyboard.add_hotkey(shortcut, self._fire)
            self.is_registered = True
            self.last_error = ""
            return True, f"Registered {shortcut.upper()}"
        except Exception as exc:  # pragma: no cover - depends on host permissions
            self.hotkey_id = None
            self.is_registered = False
            self.last_error = str(exc)
            return False, self.last_error

    def unregister(self) -> None:
        if keyboard is not None and self.hotkey_id is not None:
            try:
                keyboard.remove_hotkey(self.hotkey_id)
            except Exception:
                pass

        self.hotkey_id = None
        self.is_registered = False

    def add_listener(self, listener: Callable[[str, int], None]) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[str, int], None]) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def simulate_trigger(self) -> None:
        self._fire()

    def status_snapshot(self) -> Dict[str, Optional[str] | bool | int | float]:
        return {
            "shortcut": self.shortcut,
            "is_registered": self.is_registered,
            "last_error": self.last_error,
            "trigger_count": self.trigger_count,
            "last_trigger_time": self.last_trigger_time,
        }

    def shutdown(self) -> None:
        self.unregister()

    def _fire(self) -> None:
        self.trigger_count += 1
        self.last_trigger_time = time.time()

        if self.primary_handler is not None:
            try:
                self.primary_handler()
            except Exception as exc:
                self.last_error = str(exc)

        shortcut = self.shortcut or ""
        for listener in list(self._listeners):
            try:
                listener(shortcut, self.trigger_count)
            except Exception:
                pass
