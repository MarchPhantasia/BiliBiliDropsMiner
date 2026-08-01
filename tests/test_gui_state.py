from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QByteArray, QSettings

from bilibili_drops_miner.gui_parts.gui_state import (
    COOKIE_IMPORT_REVISION_KEY,
    LAST_CONFIG_PATH_KEY,
    SAVED_COOKIE_KEY,
    WINDOW_GEOMETRY_KEY,
    GuiStateStore,
)


class GuiStateStoreTests(unittest.TestCase):
    def test_geometry_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "gui.ini"
            state = GuiStateStore(QSettings(str(settings_path), QSettings.IniFormat))
            geometry = QByteArray(b"saved-window-geometry")

            state.set_window_geometry(geometry)
            state.sync()

            restored = GuiStateStore(
                QSettings(str(settings_path), QSettings.IniFormat)
            )
            self.assertEqual(restored.window_geometry(), geometry)

    def test_last_config_path_is_absolute_and_can_be_cleared(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = QSettings(
                str(Path(temp_dir) / "gui.ini"),
                QSettings.IniFormat,
            )
            state = GuiStateStore(settings)
            config_path = Path(temp_dir) / "config.json"

            state.set_last_config_path(config_path)
            state.sync()

            self.assertEqual(state.last_config_path(), config_path.resolve())
            self.assertEqual(
                set(settings.allKeys()),
                {LAST_CONFIG_PATH_KEY},
            )

            state.clear_last_config_path()
            state.sync()

            self.assertIsNone(state.last_config_path())
            self.assertNotIn(LAST_CONFIG_PATH_KEY, settings.allKeys())

    def test_saved_cookie_round_trip_and_clear(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = QSettings(
                str(Path(temp_dir) / "gui.ini"),
                QSettings.IniFormat,
            )
            state = GuiStateStore(settings)

            state.set_saved_cookie("  SESSDATA=sess; bili_jct=csrf  ")
            state.sync()

            self.assertEqual(state.saved_cookie(), "SESSDATA=sess; bili_jct=csrf")
            self.assertIn(SAVED_COOKIE_KEY, settings.allKeys())

            state.set_saved_cookie("")
            state.sync()

            self.assertEqual(state.saved_cookie(), "")
            self.assertNotIn(SAVED_COOKIE_KEY, settings.allKeys())

    def test_cookie_import_revision_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = QSettings(
                str(Path(temp_dir) / "gui.ini"),
                QSettings.IniFormat,
            )
            state = GuiStateStore(settings)

            revision = state.mark_cookie_imported("revision-1")
            state.sync()

            self.assertEqual(revision, "revision-1")
            self.assertEqual(state.cookie_import_revision(), "revision-1")
            self.assertIn(COOKIE_IMPORT_REVISION_KEY, settings.allKeys())

    def test_only_expected_gui_state_keys_are_written(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = QSettings(
                str(Path(temp_dir) / "gui.ini"),
                QSettings.IniFormat,
            )
            state = GuiStateStore(settings)

            state.set_window_geometry(QByteArray(b"geometry"))
            state.set_last_config_path(Path(temp_dir) / "config.json")
            state.sync()

            self.assertEqual(
                set(settings.allKeys()),
                {WINDOW_GEOMETRY_KEY, LAST_CONFIG_PATH_KEY},
            )


if __name__ == "__main__":
    unittest.main()
