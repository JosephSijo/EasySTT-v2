import os
import json
import logging
import pathlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class PluginManifest:
    id: str
    name: str
    version: str
    author: str
    permissions: List[str]
    vocabulary_path: Optional[str] = None
    priority: int = 10

class PluginManager:
    """
    Handles MCP plugin discovery, validation, and lifecycle.
    Allows for dynamic vocabulary injection and processing hooks.
    """
    
    def __init__(self, plugins_dir: Optional[str] = None):
        if plugins_dir is None:
            app_data = pathlib.Path(os.getenv("APPDATA", ".")) / "EasySTT"
            plugins_dir = str(app_data / "plugins")
            
        self.plugins_dir = plugins_dir
        os.makedirs(self.plugins_dir, exist_ok=True)
        self.plugins: Dict[str, PluginManifest] = {}
        self.logger = logging.getLogger("PluginManager")

    def discover_plugins(self) -> List[PluginManifest]:
        """Scans the plugins directory for valid MCP plugin manifests."""
        self.plugins = {}
        for item in os.listdir(self.plugins_dir):
            item_path = os.path.join(self.plugins_dir, item)
            if os.path.isdir(item_path):
                manifest_path = os.path.join(item_path, "manifest.json")
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, 'r') as f:
                            data = json.load(f)
                            manifest = PluginManifest(**data)
                            self.plugins[manifest.id] = manifest
                    except Exception as e:
                        self.logger.error(f"Failed to load plugin manifest at {manifest_path}: {e}")
        
        return list(self.plugins.values())

    def get_active_vocabulary_paths(self) -> List[str]:
        """Returns paths to vocabulary files for all discovered plugins."""
        paths = []
        for p_id, manifest in self.plugins.items():
            if manifest.vocabulary_path:
                full_path = os.path.join(self.plugins_dir, p_id, manifest.vocabulary_path)
                if os.path.exists(full_path):
                    paths.append(full_path)
        return paths

    def get_plugin_info(self, plugin_id: str) -> Optional[PluginManifest]:
        return self.plugins.get(plugin_id)

    def is_installed(self, plugin_id: str) -> bool:
        """Checks if a specific plugin ID is present in the local directory."""
        # Ensure latest state
        self.discover_plugins()
        return plugin_id in self.plugins

    def install_remote(self, plugin_data: Dict[str, Any]) -> bool:
        """
        Simulates remote plugin installation.
        In production, this would download a ZIP and extract it.
        """
        plugin_id = plugin_data["id"]
        plugin_path = os.path.join(self.plugins_dir, plugin_id)
        os.makedirs(plugin_path, exist_ok=True)
        
        # Create a mock manifest and empty vocabulary for the installed plugin
        manifest = {
            "id": plugin_id,
            "name": plugin_data["name"],
            "version": plugin_data["version"],
            "author": plugin_data["author"],
            "permissions": ["vocabulary"],
            "vocabulary_path": "vocabulary.json",
            "priority": 10
        }
        
        vocab = {
            "metadata": {"name": plugin_data["name"]},
            "terms": [
                {"word": f"Sample-{plugin_id}-Term", "phonetic": "", "boost": 1.2}
            ]
        }
        
        try:
            with open(os.path.join(plugin_path, "manifest.json"), 'w') as f:
                json.dump(manifest, f, indent=4)
            with open(os.path.join(plugin_path, "vocabulary.json"), 'w') as f:
                json.dump(vocab, f, indent=4)
            
            # Refresh local discovery
            self.discover_plugins()
            return True
        except Exception as e:
            self.logger.error(f"Failed to install plugin {plugin_id}: {e}")
            return False
