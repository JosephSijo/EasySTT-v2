import copy
import json
import os
import pathlib
from typing import Any, Dict, List


class EngineCatalogService:
    """Stores engine profiles and tailors recommendations to the current PC."""

    BASE_CATALOG: List[Dict[str, Any]] = [
        {
            "id": "faster-whisper",
            "name": "faster-whisper",
            "description": "High-quality Whisper transcription via CTranslate2 with strong GPU and CPU support.",
            "integration_level": "native",
            "download_size": "Bundled",
            "best_for": "Best overall mix of speed and quality",
        },
        {
            "id": "whisper.cpp",
            "name": "whisper.cpp",
            "description": "Very lightweight native runtime that works well on CPU-only and portable setups.",
            "integration_level": "profile",
            "download_size": "~150 MB runtime + models",
            "best_for": "Best lightweight option for Windows builds",
        },
        {
            "id": "sherpa-onnx",
            "name": "sherpa-onnx",
            "description": "Streaming-first engine with good hotword and low-latency customization potential.",
            "integration_level": "profile",
            "download_size": "~200 MB runtime + models",
            "best_for": "Best for streaming and hotword-focused workflows",
        },
        {
            "id": "vosk",
            "name": "Vosk",
            "description": "Small offline models with simple deployment on older hardware.",
            "integration_level": "profile",
            "download_size": "~50 MB runtime + models",
            "best_for": "Best fallback for older or low-memory systems",
        },
    ]

    def __init__(self, app_name: str = "EasySTT"):
        appdata = os.getenv("APPDATA") or str(pathlib.Path.home() / "AppData" / "Roaming")
        self.root_dir = pathlib.Path(appdata) / app_name / "engines"
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def build_catalog(self, specs: Dict[str, Any], installed: List[Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
        installed_map = {item.get("id"): item for item in (installed or [])}
        catalog = []

        for entry in self.BASE_CATALOG:
            engine = copy.deepcopy(entry)
            engine["installed"] = engine["id"] in installed_map
            engine["recommended"] = False
            engine["recommendation"] = ""

            if engine["id"] == "faster-whisper":
                engine["recommended"] = True
                engine["recommendation"] = "Recommended for this build because it is already integrated."
                if specs.get("has_cuda"):
                    engine["recommendation"] += " CUDA detected, so larger local models are realistic."
            elif engine["id"] == "whisper.cpp" and not specs.get("has_cuda"):
                engine["recommended"] = True
                engine["recommendation"] = "Recommended as a lightweight CPU-first engine for this PC."
            elif engine["id"] == "sherpa-onnx" and specs.get("memory_gb", 0) >= 8:
                engine["recommendation"] = "Good fit if you want future hotword and streaming features."
            elif engine["id"] == "vosk" and specs.get("memory_gb", 0) < 8:
                engine["recommended"] = True
                engine["recommendation"] = "Recommended as a low-memory fallback."

            catalog.append(engine)

        return catalog

    def install_profile(self, engine: Dict[str, Any]) -> pathlib.Path:
        engine_dir = self.root_dir / engine["id"]
        engine_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = engine_dir / "manifest.json"

        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(engine, handle, indent=2)

        return manifest_path
