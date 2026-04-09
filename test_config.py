import unittest

from core.config_manager import ConfigManager


class ConfigManagerTests(unittest.TestCase):
    def test_config_manager_creates_and_writes_config(self):
        cfg = ConfigManager("EasySTTConfigTest")

        self.assertTrue(cfg.config_dir.exists(), "Config directory was not created.")
        self.assertTrue(cfg.config_file.exists(), "Config file was not created.")

        cfg.set("test_run", "success")
        self.assertEqual(cfg.get("test_run"), "success")


if __name__ == "__main__":
    unittest.main()
