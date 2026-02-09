import sqlite3
import os
import pathlib
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from colorama import Fore

class VocabularyEngine:
    """
    Advanced Vocabulary Engine using SQLite.
    Supports multi-layered vocabulary, frequency boosting, and correction learning.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            app_data = pathlib.Path(os.getenv("APPDATA", ".")) / "EasySTT"
            app_data.mkdir(parents=True, exist_ok=True)
            db_path = str(app_data / "vocabulary.db")
        
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite database with the required schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Personal Vocabulary Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS personal_vocabulary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT UNIQUE NOT NULL,
                    phonetic_representation TEXT,
                    boost_score REAL DEFAULT 1.0,
                    learned_from TEXT, -- 'correction', 'manual', 'context'
                    last_used TIMESTAMP,
                    use_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Domain Plugins Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS domain_plugins (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    active BOOLEAN DEFAULT 0,
                    vocabulary_path TEXT,
                    plugin_path TEXT,
                    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Correction History (for phonetic learning)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS correction_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incorrect_text TEXT NOT NULL,
                    corrected_text TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()

    def add_word(self, word: str, category: str = "manual", boost: float = 1.0):
        """Adds or updates a word in the personal vocabulary."""
        word = word.strip()
        if not word: return
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            self._add_word_internal(cursor, word, category, boost)
            conn.commit()

    def _add_word_internal(self, cursor: sqlite3.Cursor, word: str, category: str, boost: float):
        """Internal version of add_word that accepts a cursor."""
        cursor.execute('''
            INSERT INTO personal_vocabulary (word, learned_from, boost_score, last_used, use_count)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(word) DO UPDATE SET
                boost_score = MAX(boost_score, excluded.boost_score),
                last_used = excluded.last_used,
                use_count = use_count + 1
        ''', (word, category, boost, datetime.now().isoformat()))

    def learn_correction(self, incorrect: str, correct: str):
        """Learns from a user correction."""
        if not incorrect or not correct: return
        
        # Log the correction for future analytics/phonetic mapping
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO correction_history (incorrect_text, corrected_text)
                VALUES (?, ?)
            ''', (incorrect, correct))
            
            # Extract new words from the correction
            orig_words = set(incorrect.lower().split())
            corr_words = correct.split()
            
            for word in corr_words:
                clean_word = "".join(c for c in word if c.isalnum())
                if clean_word and clean_word.lower() not in orig_words:
                    # Boost this word using the internal method to avoid nested connections
                    self._add_word_internal(cursor, clean_word, category="correction", boost=1.5)
            
            conn.commit()

    def get_prompt_bias(self, limit: int = 100) -> str:
        """Returns a formatted prompt string for Whisper biasing, including domain terms."""
        words = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 1. Fetch from Personal Vocabulary
            cursor.execute('''
                SELECT word FROM personal_vocabulary
                ORDER BY boost_score DESC, last_used DESC
                LIMIT ?
            ''', (limit,))
            words.extend([row[0] for row in cursor.fetchall()])
            
            # 2. Fetch from Active Domain Plugins
            cursor.execute('SELECT vocabulary_path FROM domain_plugins WHERE active = 1')
            for (vocab_path,) in cursor.fetchall():
                if os.path.exists(vocab_path):
                    try:
                        with open(vocab_path, 'r') as f:
                            data = json.load(f)
                            # Add top terms from the plugin
                            plugin_words = [item['word'] for item in data.get('terms', [])[:limit]]
                            words.extend(plugin_words)
                    except Exception as e:
                        print(f"Error loading domain vocab {vocab_path}: {e}")
            
            if not words:
                return ""
            
            # Final unique list
            unique_words = sorted(list(set(words)))[:limit]
            return "Vocabulary: " + ", ".join(unique_words) + ". "

    def register_plugin(self, manifest_id: str, name: str, vocab_path: str):
        """Registers a plugin's vocabulary in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO domain_plugins (id, name, vocabulary_path, active)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(id) DO UPDATE SET
                    vocabulary_path = excluded.vocabulary_path,
                    active = 1
            ''', (manifest_id, name, vocab_path))
            conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        """Returns engine statistics for the UI."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM personal_vocabulary")
            total_words = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM correction_history")
            total_corrections = cursor.fetchone()[0]
            
            return {
                "total_words": total_words,
                "total_corrections": total_corrections,
                "db_path": self.db_path
            }
