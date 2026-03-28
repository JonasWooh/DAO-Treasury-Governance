from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_repo_secrets.py"
SPEC = importlib.util.spec_from_file_location("check_repo_secrets", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RepoSecretScanTests(unittest.TestCase):
    def test_placeholder_detection_ignores_examples(self) -> None:
        self.assertTrue(MODULE.looks_like_placeholder("https://your-sepolia-rpc-url"))
        self.assertTrue(MODULE.looks_like_placeholder("<replace-me>"))
        self.assertFalse(MODULE.looks_like_placeholder("https://rpc.sepolia.org"))

    def test_secret_value_detection_requires_real_private_key_shape(self) -> None:
        self.assertTrue(MODULE.looks_like_secret_value("SEPOLIA_PRIVATE_KEY", "0x" + ("ab" * 32)))
        self.assertFalse(MODULE.looks_like_secret_value("SEPOLIA_PRIVATE_KEY", "os.environ.get('SEPOLIA_PRIVATE_KEY')"))
        self.assertFalse(MODULE.looks_like_secret_value("SEPOLIA_PRIVATE_KEY", "your-private-key"))
        self.assertFalse(MODULE.looks_like_secret_value("CampusInnovationFundToken", "0x" + ("ab" * 32)))

    def test_sensitive_path_detection_skips_examples(self) -> None:
        self.assertTrue(MODULE.is_sensitive_path(MODULE.ROOT / "config" / "mainnet.env"))
        self.assertTrue(MODULE.is_sensitive_path(MODULE.ROOT / "wallets" / "demo.json"))
        self.assertTrue(MODULE.is_sensitive_path(MODULE.ROOT / "keys" / "demo.pem"))
        self.assertFalse(MODULE.is_sensitive_path(MODULE.ROOT / "config" / "sepolia.env.example"))
        self.assertFalse(MODULE.is_sensitive_path(MODULE.ROOT / "README.md"))


if __name__ == "__main__":
    unittest.main()
