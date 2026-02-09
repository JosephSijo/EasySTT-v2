import hashlib
import json
import os
import pathlib
from typing import Dict, Optional

class LicenseManager:
    """
    Manages plugin licenses and user subscription tiers.
    Supports basic local validation and prepared for remote verification.
    """
    
    def __init__(self):
        app_data = pathlib.Path(os.getenv("APPDATA", ".")) / "EasySTT"
        self.license_file = app_data / "licenses.json"
        self.licenses = self._load_licenses()

    def _load_licenses(self) -> Dict[str, str]:
        if self.license_file.exists():
            try:
                with open(self.license_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_license(self, plugin_id: str, key: str):
        self.licenses[plugin_id] = key
        with open(self.license_file, 'w') as f:
            json.dump(self.licenses, f, indent=4)

    def is_licensed(self, plugin_id: str) -> bool:
        """
        Validates the license for a given plugin.
        For sample purposes, any key containing 'PRO' or being 'FREE' is valid.
        """
        key = self.licenses.get(plugin_id)
        if not key:
            return False
            
        # Mock validation logic
        if "PRO" in key.upper() or key.upper() == "FREE":
            return True
        return False

    def get_subscription_tier(self) -> str:
        """Returns the current user's tier based on the global license key."""
        global_key = self.licenses.get("global", "")
        if "ENT" in global_key.upper():
            return "Enterprise"
        elif "PRO" in global_key.upper():
            return "Professional"
        return "Free"
    def is_pro(self) -> bool:
        """Returns True if the user is in Professional or Enterprise tier."""
        tier = self.get_subscription_tier()
        return tier in ["Professional", "Enterprise"]
