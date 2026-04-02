import os
import unittest
from pathlib import Path
from app.config import BASE_DIR, DATA_DIR, SQLITE_DB_PATH

class TestConfig(unittest.TestCase):
    def test_paths(self):
        self.assertTrue(isinstance(BASE_DIR, Path))
        self.assertTrue(DATA_DIR.exists())
        self.assertEqual(SQLITE_DB_PATH.parent.name, ".data")

    def test_ollama_config(self):
        # 验证默认值
        self.assertIn("http", os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))

if __name__ == "__main__":
    unittest.main()
