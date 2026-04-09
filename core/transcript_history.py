import pathlib
from datetime import datetime
from typing import Any, Dict, List


class TranscriptHistoryService:
    """Loads saved transcript files from the configured storage directory."""

    def __init__(self, config):
        self.config = config

    def list_entries(self, limit: int = 12) -> List[Dict[str, Any]]:
        storage_path = pathlib.Path(self.config.get("storage_path", "recordings"))
        if not storage_path.exists():
            return []

        files = sorted(storage_path.glob("*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)
        entries: List[Dict[str, Any]] = []

        for path in files[:limit]:
            try:
                text = path.read_text(encoding="utf-8").strip()
            except Exception:
                continue

            title = self._build_title(text, path.stem)
            modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%b %d • %H:%M")
            word_count = len(text.split()) if text else 0
            entries.append(
                {
                    "path": str(path),
                    "title": title,
                    "subtitle": f"{modified} • {word_count} words",
                    "preview": text[:180],
                }
            )

        return entries

    def _build_title(self, text: str, fallback: str) -> str:
        if not text:
            return fallback

        words = text.replace("\n", " ").split()
        if not words:
            return fallback

        title = " ".join(words[:6]).strip()
        return f"{title}..." if len(words) > 6 else title
