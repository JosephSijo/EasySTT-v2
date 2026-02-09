# test_config.py
from core.config_manager import ConfigManager
import os

print("--- DIAGNOSTIC TEST ---")

# 1. Initialize the Manager (This triggers the folder creation)
print("1. Initializing ConfigManager...")
try:
    cfg = ConfigManager()
    print("   ✅ Initialization successful.")
except Exception as e:
    print(f"   ❌ CRITICAL ERROR: {e}")
    # If APPDATA is None (e.g. running in some IDE shells), we need a fallback
    if os.getenv("APPDATA") is None:
        print("   ⚠️ Reason: 'APPDATA' environment variable is missing.")

# 2. Print the exact path
print(f"\n2. Your Config Path is:\n   📂 {cfg.config_dir}")

# 3. Verify File Creation
if cfg.config_file.exists():
    print(f"   ✅ config.json found at: {cfg.config_file}")
else:
    print("   ❌ config.json was NOT created.")

# 4. Test Saving
print("\n3. Testing Write Permission...")
try:
    cfg.set("test_run", "success")
    print("   ✅ Settings saved successfully.")
except Exception as e:
    print(f"   ❌ Write Error: {e}")

input("\nPress Enter to close...")