import json
import os
import pathlib
import threading
from typing import List, Dict, Any, Optional
from colorama import Fore

class MarketplaceService:
    """
    Handles discovery and metadata retrieval for remote STT plugins.
    Uses a mock remote registry for MVP.
    """
    
    # Mock remote registry URL (in a real app, this would be an API endpoint)
    MOCK_REGISTRY_URL = "https://api.easystt.com/v1/plugins"
    
    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir is None:
            app_data = pathlib.Path(os.getenv("APPDATA", ".")) / "EasySTT" / "cache"
            app_data.mkdir(parents=True, exist_ok=True)
            cache_dir = str(app_data)
        
        self.cache_dir = cache_dir
        self.manifest_cache_path = os.path.join(self.cache_dir, "marketplace_cache.json")
        self.registry_data: List[Dict[str, Any]] = []
        
        # Load cache if exists
        self._load_cache()

    def _load_cache(self):
        """Loads the registry from local cache."""
        if os.path.exists(self.manifest_cache_path):
            try:
                with open(self.manifest_cache_path, 'r') as f:
                    self.registry_data = json.load(f)
            except Exception as e:
                print(f"{Fore.YELLOW}[Marketplace] Failed to load cache: {e}")

    def fetch_registry(self, force: bool = False) -> List[Dict[str, Any]]:
        """
        Fetches the plugin registry. 
        Mock implementation: returns a hardcoded list after a small delay.
        """
        if self.registry_data and not force:
            return self.registry_data
        
        print(f"{Fore.CYAN}[Marketplace] Fetching remote plugin registry...")
        
        # Simulated Network Delay
        # In real implementation: requests.get(self.MOCK_REGISTRY_URL)
        
        # Mock Data
        self.registry_data = [
            {
                "id": "medical-pro-2024",
                "name": "Medical Terminology PRO",
                "author": "BioDictate Inc.",
                "description": "Comprehensive medical vocabulary with 50,000+ terms including pharmacology and anatomy.",
                "version": "1.2.0",
                "tier": "PRO",
                "price": "$12.99",
                "category": "Medical",
                "rating": 4.8,
                "installs": 1200,
                "download_url": "https://cdn.easystt.com/plugins/medical-pro.zip",
                "size": "45MB"
            },
            {
                "id": "legal-uk-addon",
                "name": "UK Legal & Parliamentary",
                "author": "LexisFlow",
                "description": "Specialized for UK law courts, parliamentary proceedings, and case law terminology.",
                "version": "0.9.5",
                "tier": "FREE",
                "price": "Free",
                "category": "Legal",
                "rating": 4.5,
                "installs": 850,
                "download_url": "https://cdn.easystt.com/plugins/uk-legal.zip",
                "size": "12MB"
            },
            {
                "id": "dev-python-expert",
                "name": "Python & Data Science",
                "author": "EasySTT Community",
                "description": "Optimized for dictating Python code, library names (Pandas, TensorFlow), and data science jargon.",
                "version": "2.0.1",
                "tier": "FREE",
                "price": "Free",
                "category": "Technology",
                "rating": 4.9,
                "installs": 3500,
                "download_url": "https://cdn.easystt.com/plugins/python-dev.zip",
                "size": "8MB"
            }
        ]
        
        # Save to cache
        try:
            with open(self.manifest_cache_path, 'w') as f:
                json.dump(self.registry_data, f, indent=4)
        except Exception as e:
            print(f"{Fore.RED}[Marketplace] Failed to cache registry: {e}")
            
        return self.registry_data

    def get_plugin_details(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Returns metadata for a specific plugin."""
        for p in self.registry_data:
            if p["id"] == plugin_id:
                return p
        return None
