import os
import json
import pathlib
from colorama import Fore
from typing import List, Dict

class PersonalizationManager:
    """
    Manages local vocabulary (names, jargon, phrases) for prompt biasing.
    Enhanced with UI helper methods for vocabulary management.
    """
    
    def __init__(self):
        # Store vocabulary in AppData for persistence across updates
        app_data = pathlib.Path(os.getenv("APPDATA", ".")) / "EasySTT"
        app_data.mkdir(parents=True, exist_ok=True)
        self.file_path = app_data / "vocabulary.json"
        
        # Fallback: Also check local directory for migration
        self.legacy_file = pathlib.Path("vocabulary.json")
        self.data = self._load()

    def _load(self) -> Dict[str, List[str]]:
        """Load vocabulary, migrating from legacy location if needed."""
        default = {"names": [], "jargon": [], "phrases": []}
        
        # Try AppData first
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return default
        
        # Migrate from legacy location
        if self.legacy_file.exists():
            try:
                with open(self.legacy_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._save(data)  # Save to new location
                    print(f"{Fore.GREEN}[Personalization] Migrated vocabulary to AppData.")
                    return data
            except:
                pass
        
        return default

    def _save(self, data: Dict[str, List[str]] = None):
        """Save vocabulary to AppData."""
        data = data or self.data
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"{Fore.RED}[Error] Failed to save vocabulary: {e}")

    def save(self):
        """Public save method."""
        self._save()

    def add_term(self, category: str, term: str) -> bool:
        """Add a term to a category. Returns True if added."""
        if not term or not term.strip():
            return False
        
        term = term.strip()
        if category not in self.data:
            self.data[category] = []
        
        if term not in self.data[category]:
            self.data[category].append(term)
            self._save()
            return True
        return False

    def remove_term(self, category: str, term: str) -> bool:
        """Remove a term from a category. Returns True if removed."""
        if category in self.data and term in self.data[category]:
            self.data[category].remove(term)
            self._save()
            return True
        return False

    def get_all_terms(self) -> Dict[str, List[str]]:
        """Get all vocabulary terms organized by category."""
        return self.data.copy()

    def get_terms(self, category: str) -> List[str]:
        """Get all terms in a specific category."""
        return self.data.get(category, []).copy()

    def clear_category(self, category: str) -> bool:
        """Clear all terms in a category. Returns True if cleared."""
        if category in self.data:
            self.data[category] = []
            self._save()
            return True
        return False

    def has_vocabulary(self) -> bool:
        """Check if any vocabulary has been trained."""
        return any(len(terms) > 0 for terms in self.data.values())

    def get_prompt_bias(self) -> str:
        """Generate prompt bias string for Whisper."""
        all_terms = (
            self.data.get("names", []) + 
            self.data.get("jargon", []) + 
            self.data.get("phrases", [])
        )
        if not all_terms:
            return ""
        # Filter duplicates and empty strings
        unique_terms = sorted(list(set(filter(None, all_terms))))
        return "Vocabulary: " + ", ".join(unique_terms) + ". "
