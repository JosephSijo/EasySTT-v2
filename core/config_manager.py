import os
import json
import pathlib
from typing import Any, Dict

class ConfigManager:
    """
    Handles loading and saving application settings.
    Stores data in the user's AppData folder to survive application updates.
    """
    
    def __init__(self, app_name: str = "EasySTT"):
        self.app_name = app_name
        self.config_dir = pathlib.Path(os.getenv("APPDATA")) / self.app_name
        self.config_file = self.config_dir / "config.json"
        self.defaults = {
            "provider": "Gemini",
            "keys": {
                "Gemini": "", 
                "OpenAI": "", 
                "Anthropic": "", 
                "DeepSeek": "", 
                "Mistral": "", 
                "Groq": ""
            },
            "storage_path": str(pathlib.Path.home() / "Documents" / "EasySTT"),
            "auto_clear_days": 30,
            "auto_clipboard": True,
            "shortcut": "ctrl+alt+r",
            "total_tokens_used": 0,
            "language": "en",
            "auto_submit": True,
            "use_ai_refinement": True,
            "enhancement_style": "Professional",
            "custom_style_prompt": "",
            "whisper_model": "turbo",
            "show_confidence": False,
            "privacy_mode": "standard", # 'standard' (hybrid), 'extreme' (local), 'enterprise'
            "cloud_enhancement_threshold": 0.7
        }
        self.config = self._load_initial_config()

    def _load_initial_config(self) -> Dict[str, Any]:
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
        if not self.config_file.exists():
            self.save_config(self.defaults)
            return self.defaults.copy()
            
        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
                
                # --- MIGRATION LOGIC ---
                # 1. Migrate single api_key to keys dictionary
                if "api_key" in data:
                    provider = data.get("provider", "Gemini")
                    if "keys" not in data:
                        data["keys"] = self.defaults["keys"].copy()
                    data["keys"][provider] = data["api_key"]
                    del data["api_key"]
                
                # 2. Ensure all default keys exist
                for k, v in self.defaults.items():
                    if k not in data:
                        data[k] = v
                    elif k == "keys" and isinstance(data[k], dict):
                        # Ensure all providers exist in the nested keys dict
                        for pk, pv in self.defaults[k].items():
                            if pk not in data[k]:
                                data[k][pk] = pv
                                
                return data
        except Exception:
            return self.defaults.copy()

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self.save_config(self.config)

    def save_config(self, data: Dict[str, Any]) -> None:
        with open(self.config_file, "w") as f:
            json.dump(data, f, indent=4)
