import sqlite3
import os
import pathlib
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

class PrivacyManager:
    """
    Enforces privacy policies and maintains a secure audit trail.
    Supports Local-Only, Hybrid, and Enterprise modes.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            app_data = pathlib.Path(os.getenv("APPDATA", ".")) / "EasySTT"
            db_path = str(app_data / "privacy.db")
            
        self.db_path = db_path
        self._init_db()
        self.logger = logging.getLogger("PrivacyManager")

    def _init_db(self):
        """Initializes the SQLite database for privacy auditing."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    mode TEXT NOT NULL, -- 'local', 'hybrid', 'cloud'
                    duration_seconds REAL,
                    confidence REAL,
                    privacy_level TEXT, -- 'standard', 'extreme', 'enterprise'
                    agents_contacted TEXT -- JSON list of MCP agent IDs
                )
            ''')
            conn.commit()

    def log_transcription(self, mode: str, confidence: float, duration: float, agents: List[str] = []):
        """Records a transcription event in the audit log."""
        import json
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO audit_log (mode, confidence, duration_seconds, agents_contacted)
                VALUES (?, ?, ?, ?)
            ''', (mode, confidence, duration, json.dumps(agents)))
            conn.commit()

    def get_audit_summary(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent audit log entries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?', (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def is_feature_allowed(self, feature: str, current_mode: str) -> bool:
        """Checks if a feature (e.g., 'cloud_enhance') is allowed in the current privacy mode."""
        if current_mode == "local" and feature == "cloud_enhance":
            return False
        return True

    def purge_old_data(self, storage_path: str, max_days: int):
        """Purges audit logs and files older than max_days."""
        if max_days <= 0:
            return

        cutoff_date = datetime.now() - timedelta(days=max_days)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')

        # 1. Purge Audit Log
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM audit_log WHERE timestamp < ?', (cutoff_str,))
            conn.commit()

        # 2. Purge Files (Recordings and Transcripts)
        if os.path.exists(storage_path):
            now = time.time()
            max_seconds = max_days * 86400
            for filename in os.listdir(storage_path):
                file_path = os.path.join(storage_path, filename)
                if os.path.isfile(file_path):
                    if os.stat(file_path).st_mtime < now - max_seconds:
                        try:
                            os.remove(file_path)
                            self.logger.info(f"Purged old file: {filename}")
                        except Exception as e:
                            self.logger.error(f"Failed to purge {filename}: {e}")
