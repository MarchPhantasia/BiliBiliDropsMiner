from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bilibili_drops_miner.gui_parts.chrome_companion import (
    CHROME_EXTENSION_ID,
    CHROME_EXTENSION_ORIGIN,
    NATIVE_HOST_NAME,
    build_native_host_manifest,
    chrome_extension_directory,
    chrome_extension_is_installed,
    register_native_messaging_host,
)


class ChromeCompanionTests(unittest.TestCase):
    def test_source_extension_has_expected_fixed_id_assets(self) -> None:
        extension_dir = chrome_extension_directory()
        manifest = json.loads(
            extension_dir.joinpath("manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertIn("cookies", manifest["permissions"])
        self.assertIn("nativeMessaging", manifest["permissions"])
        self.assertTrue(extension_dir.joinpath("background.js").is_file())
        self.assertTrue(extension_dir.joinpath("sync.html").is_file())
        self.assertEqual(len(CHROME_EXTENSION_ID), 32)

    def test_native_host_manifest_allows_only_companion_extension(self) -> None:
        manifest = build_native_host_manifest("/Applications/Test.app/host")
        self.assertEqual(manifest["name"], NATIVE_HOST_NAME)
        self.assertEqual(manifest["type"], "stdio")
        self.assertEqual(manifest["allowed_origins"], [CHROME_EXTENSION_ORIGIN])

    def test_register_native_host_writes_valid_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "native-host.json"
            register_native_messaging_host(
                executable_path="/Applications/Test.app/host",
                manifest_path=manifest_path,
            )
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["allowed_origins"], [CHROME_EXTENSION_ORIGIN])
            self.assertEqual(payload["path"], "/Applications/Test.app/host")

    def test_extension_detection_reads_chrome_profile_preferences(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_root = Path(temp_dir)
            profile = profile_root / "Default"
            profile.mkdir()
            preferences = {
                "extensions": {
                    "settings": {CHROME_EXTENSION_ID: {"state": 1}}
                }
            }
            profile.joinpath("Secure Preferences").write_text(
                json.dumps(preferences),
                encoding="utf-8",
            )

            self.assertTrue(chrome_extension_is_installed(profile_root))

    def test_extension_detection_uses_last_used_profile_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_root = Path(temp_dir)
            default_profile = profile_root / "Default"
            active_profile = profile_root / "Profile 1"
            default_profile.mkdir()
            active_profile.mkdir()
            profile_root.joinpath("Local State").write_text(
                json.dumps({"profile": {"last_used": "Profile 1"}}),
                encoding="utf-8",
            )
            default_profile.joinpath("Secure Preferences").write_text(
                json.dumps(
                    {
                        "extensions": {
                            "settings": {CHROME_EXTENSION_ID: {"state": 1}}
                        }
                    }
                ),
                encoding="utf-8",
            )
            active_profile.joinpath("Secure Preferences").write_text(
                json.dumps({"extensions": {"settings": {}}}),
                encoding="utf-8",
            )

            self.assertFalse(chrome_extension_is_installed(profile_root))

    def test_extension_detection_ignores_stale_preferences_after_uninstall(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_root = Path(temp_dir)
            profile = profile_root / "Default"
            profile.mkdir()
            profile.joinpath("Secure Preferences").write_text(
                json.dumps({"extensions": {"settings": {}}}),
                encoding="utf-8",
            )
            profile.joinpath("Preferences").write_text(
                json.dumps(
                    {
                        "extensions": {
                            "settings": {CHROME_EXTENSION_ID: {"state": 1}}
                        }
                    }
                ),
                encoding="utf-8",
            )

            self.assertFalse(chrome_extension_is_installed(profile_root))

    def test_extension_detection_requires_enabled_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_root = Path(temp_dir)
            profile = profile_root / "Default"
            profile.mkdir()
            profile.joinpath("Secure Preferences").write_text(
                json.dumps(
                    {
                        "extensions": {
                            "settings": {CHROME_EXTENSION_ID: {"state": 0}}
                        }
                    }
                ),
                encoding="utf-8",
            )

            self.assertFalse(chrome_extension_is_installed(profile_root))


if __name__ == "__main__":
    unittest.main()
