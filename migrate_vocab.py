import json
import os
import sqlite3
import pathlib
from core.vocabulary_engine import VocabularyEngine

def migrate_vocabulary():
    """Migrates from vocabulary.json to vocabulary.db"""
    # 1. Locate Legacy Data
    app_data = pathlib.Path(os.getenv("APPDATA", ".")) / "EasySTT"
    json_path = app_data / "vocabulary.json"
    legacy_local = pathlib.Path("vocabulary.json")
    
    target_json = None
    if json_path.exists():
        target_json = json_path
    elif legacy_local.exists():
        target_json = legacy_local
        
    if not target_json:
        print("[Migration] No legacy vocabulary found to migrate.")
        return

    # 2. Load Legacy Data
    try:
        with open(target_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[Migration] Error reading legacy JSON: {e}")
        return

    # 3. Initialize New Engine
    engine = VocabularyEngine()
    
    # 4. Migrate Terms
    count = 0
    # Current categories in personalization.py: ["names", "jargon", "phrases"]
    for category in ["names", "jargon", "phrases"]:
        for term in data.get(category, []):
            engine.add_word(term, category="manual", boost=1.2 if category == "names" else 1.0)
            count += 1
            
    print(f"[Migration] Successfully migrated {count} terms to SQLite database.")
    
    # 5. Backup legacy file
    backup_path = target_json.with_suffix(".json.bak")
    try:
        os.rename(target_json, backup_path)
        print(f"[Migration] Legacy file backed up to {backup_path.name}")
    except Exception as e:
        print(f"[Migration] Warning: Could not backup legacy file: {e}")

if __name__ == "__main__":
    migrate_vocabulary()
