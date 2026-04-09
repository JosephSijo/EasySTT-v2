import os
import json
import pathlib
from typing import Any, Dict, List, Optional

class ConfigManager:
    """
    Handles loading and saving application settings.
    Stores data in the user's AppData folder to survive application updates.
    """
    
    def __init__(self, app_name: str = "EasySTT"):
        self.app_name = app_name
        appdata = os.getenv("APPDATA") or str(pathlib.Path.home() / "AppData" / "Roaming")
        self.config_dir = pathlib.Path(appdata) / self.app_name
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
            "api_models": {
                "Gemini": "gemini-2.0-flash",
                "OpenAI": "gpt-4o"
            },
            "custom_api_profiles": [],
            "storage_path": str(pathlib.Path.home() / "Documents" / "EasySTT"),
            "auto_clear_days": 30,
            "a2a_enabled": False,
            "auto_clipboard": True,
            "shortcut": "ctrl+alt+r",
            "selected_input_device": None,
            "total_tokens_used": 0,
            "language": "en",
            "auto_submit": True,
            "use_ai_refinement": False,
            "enhancement_style": "Professional",
            "custom_style_prompt": "",
            "whisper_model": "turbo",
            "selected_model_label": "Whisper Turbo",
            "custom_models": [],
            "show_confidence": False,
            "privacy_mode": "standard", # 'standard' (hybrid), 'extreme' (local), 'enterprise'
            "cloud_enhancement_threshold": 0.7,
            "installed_engines": [],
            "preferred_engine_profile": "faster-whisper",
            "preview_interval_ms": 300,
            "preview_window_ms": 3500,
            "silence_duration_ms": 850,
            "min_speech_ms": 250,
            "vad_rms_threshold": 0.012,
            "vad_noise_ratio": 2.0,
            "auto_stop_on_silence": True,
            "use_silero_vad": True,
            "noise_suppression_enabled": True,
            "noise_suppression_engine": "rnnoise",
            "rnnoise_speech_threshold": 0.35,
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
                        data[k] = v.copy() if isinstance(v, dict) else list(v) if isinstance(v, list) else v
                    elif k == "keys" and isinstance(data[k], dict):
                        # Ensure all providers exist in the nested keys dict
                        for pk, pv in self.defaults[k].items():
                            if pk not in data[k]:
                                data[k][pk] = pv
                    elif k == "api_models" and isinstance(data[k], dict):
                        for mk, mv in self.defaults[k].items():
                            if mk not in data[k]:
                                data[k][mk] = mv
                                
                return data
        except Exception:
            return self.defaults.copy()

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self.save_config(self.config)

    def save_config(self, data: Dict[str, Any]) -> None:
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def get_custom_api_profiles(self) -> List[Dict[str, Any]]:
        return list(self.config.get("custom_api_profiles", []))

    def upsert_custom_api_profile(self, profile: Dict[str, Any]) -> None:
        profiles = self.get_custom_api_profiles()
        updated = False

        for index, item in enumerate(profiles):
            if item.get("id") == profile.get("id"):
                profiles[index] = profile
                updated = True
                break

        if not updated:
            profiles.append(profile)

        self.set("custom_api_profiles", profiles)

    def remove_custom_api_profile(self, profile_id: str) -> None:
        profiles = [item for item in self.get_custom_api_profiles() if item.get("id") != profile_id]
        self.set("custom_api_profiles", profiles)

    def get_custom_models(self) -> List[Dict[str, str]]:
        return list(self.config.get("custom_models", []))

    def upsert_custom_model(self, model: Dict[str, str]) -> None:
        models = self.get_custom_models()
        updated = False

        for index, item in enumerate(models):
            if item.get("id") == model.get("id"):
                models[index] = model
                updated = True
                break

        if not updated:
            models.append(model)

        self.set("custom_models", models)

    def remove_custom_model(self, model_id: str) -> None:
        models = [item for item in self.get_custom_models() if item.get("id") != model_id]
        self.set("custom_models", models)

    def get_installed_engines(self) -> List[Dict[str, Any]]:
        return list(self.config.get("installed_engines", []))

    def upsert_installed_engine(self, engine: Dict[str, Any]) -> None:
        engines = self.get_installed_engines()
        updated = False

        for index, item in enumerate(engines):
            if item.get("id") == engine.get("id"):
                engines[index] = engine
                updated = True
                break

        if not updated:
            engines.append(engine)

        self.set("installed_engines", engines)
