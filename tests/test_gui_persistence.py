from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QFileDialog

from bilibili_drops_miner.gui_parts.app_style import configure_qt_app
from bilibili_drops_miner.gui_parts.config_io import save_config_data
from bilibili_drops_miner.gui_parts.gui_state import GuiStateStore
from bilibili_drops_miner.gui_parts.main_window import MinerGUI


class GuiPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        configure_qt_app(cls.app)

    @staticmethod
    def _state_for(directory: str) -> GuiStateStore:
        settings = QSettings(
            str(Path(directory) / "gui.ini"),
            QSettings.IniFormat,
        )
        return GuiStateStore(settings)

    @staticmethod
    def _config_payload() -> dict[str, object]:
        return {
            "cookie": "SESSDATA=test; bili_jct=test",
            "room_ids": [123, 456],
            "thread_count": 3,
            "reconnect_delay_seconds": 11,
            "enable_web_heartbeat": True,
            "task_ids": ["task-a", "task-b"],
            "task_query_interval_seconds": 42,
            "notify_urls": ["gotify://example.invalid/token"],
            "notify_on_task_complete": False,
            "verbose": True,
        }

    def test_first_launch_geometry_intersects_primary_screen(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            window = MinerGUI(gui_state=self._state_for(temp_dir))
            try:
                screen = QApplication.primaryScreen()
                self.assertIsNotNone(screen)
                self.assertTrue(
                    window.frameGeometry().intersects(screen.availableGeometry())
                )
            finally:
                window.close()

    def test_window_geometry_is_saved_and_restored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state = self._state_for(temp_dir)
            first = MinerGUI(gui_state=state)
            first.resize(860, 700)
            first.move(20, 30)
            first.show()
            self.app.processEvents()
            expected_size = first.size()
            first.close()

            self.assertFalse(state.window_geometry().isEmpty())

            second = MinerGUI(gui_state=state)
            try:
                self.assertEqual(second.size(), expected_size)
            finally:
                second.close()

    def test_log_toggle_does_not_resize_the_window(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            window = MinerGUI(gui_state=self._state_for(temp_dir))
            try:
                window.show()
                self.app.processEvents()
                original_size = window.size()

                window._log_toggle_btn.click()
                self.app.processEvents()
                self.assertTrue(window.log_text.isVisible())
                self.assertEqual(window.size(), original_size)

                window._log_toggle_btn.click()
                self.app.processEvents()
                self.assertFalse(window.log_text.isVisible())
                self.assertEqual(window.size(), original_size)
            finally:
                window.close()

    def test_window_has_stable_minimum_width_for_action_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            window = MinerGUI(gui_state=self._state_for(temp_dir))
            try:
                self.assertGreaterEqual(window.minimumWidth(), 940)
                self.assertGreaterEqual(window.minimumHeight(), 760)
                window.resize(window.minimumSize())
                window.show()
                window._log_toggle_btn.click()
                self.app.processEvents()
                self.assertLessEqual(
                    window.centralWidget().layout().minimumSize().height(),
                    window.centralWidget().height(),
                )
            finally:
                window.close()

    def test_startup_auto_loads_last_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            save_config_data(config_path, self._config_payload())
            state = self._state_for(temp_dir)
            state.set_saved_cookie("SESSDATA=stale; bili_jct=stale")
            state.set_last_config_path(config_path)
            state.sync()

            window = MinerGUI(gui_state=state)
            try:
                self.assertEqual(
                    window.cookie_edit.text(),
                    "SESSDATA=test; bili_jct=test",
                )
                self.assertEqual(window.rooms_edit.text(), "123,456")
                self.assertEqual(window.threads_edit.text(), "3")
                self.assertEqual(window.reconnect_edit.text(), "11")
                self.assertEqual(window.task_ids_edit.text(), "task-a,task-b")
                self.assertEqual(window.task_interval_edit.text(), "42")
                self.assertEqual(
                    window.notify_urls_edit.text(),
                    "gotify://example.invalid/token",
                )
                self.assertTrue(window.disable_task_notify_check.isChecked())
                self.assertTrue(window.verbose_check.isChecked())
            finally:
                window.close()

    def test_saved_cookie_is_restored_without_a_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state = self._state_for(temp_dir)
            state.set_saved_cookie("SESSDATA=saved; bili_jct=saved")
            state.sync()

            window = MinerGUI(gui_state=state)
            try:
                self.assertEqual(
                    window.cookie_edit.text(),
                    "SESSDATA=saved; bili_jct=saved",
                )
            finally:
                window.close()

    def test_auto_fetched_cookie_is_persisted_immediately(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state = self._state_for(temp_dir)
            window = MinerGUI(gui_state=state)
            try:
                window._apply_auto_cookie("SESSDATA=fetched; bili_jct=fetched")
                self.assertEqual(
                    state.saved_cookie(),
                    "SESSDATA=fetched; bili_jct=fetched",
                )
            finally:
                window.close()

    def test_externally_imported_cookie_refreshes_running_window(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "gui.ini"
            window_state = GuiStateStore(
                QSettings(str(settings_path), QSettings.IniFormat)
            )
            external_state = GuiStateStore(
                QSettings(str(settings_path), QSettings.IniFormat)
            )
            window = MinerGUI(gui_state=window_state)
            try:
                external_state.set_saved_cookie(
                    "SESSDATA=current-profile; DedeUserID=123"
                )
                external_state.mark_cookie_imported("external-revision")
                external_state.sync()

                window._poll_external_cookie_import()

                self.assertEqual(
                    window.cookie_edit.text(),
                    "SESSDATA=current-profile; DedeUserID=123",
                )
            finally:
                window.close()

    def test_task_fetch_uses_single_room_from_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            window = MinerGUI(gui_state=self._state_for(temp_dir))
            try:
                window.rooms_edit.setText("23612045")
                with patch.object(
                    window.browser_actions,
                    "auto_fetch_task_ids",
                ) as auto_fetch:
                    window.auto_fetch_task_ids()

                auto_fetch.assert_called_once_with(23612045)
            finally:
                window.close()

    def test_missing_last_config_path_is_forgotten(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state = self._state_for(temp_dir)
            state.set_last_config_path(Path(temp_dir) / "missing.json")
            state.sync()

            window = MinerGUI(gui_state=state)
            try:
                self.assertIsNone(state.last_config_path())
                self.assertEqual(window.cookie_edit.text(), "")
                self.assertEqual(window.rooms_edit.text(), "23612045")
            finally:
                window.close()

    def test_invalid_last_config_does_not_open_modal_or_forget_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "invalid.json"
            config_path.write_text("not-json", encoding="utf-8")
            state = self._state_for(temp_dir)
            state.set_last_config_path(config_path)
            state.sync()

            window = MinerGUI(gui_state=state)
            try:
                self.assertEqual(state.last_config_path(), config_path.resolve())
                self.assertEqual(window.cookie_edit.text(), "")
            finally:
                window.close()

    def test_manual_load_remembers_config_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "loaded.json"
            save_config_data(config_path, self._config_payload())
            state = self._state_for(temp_dir)
            window = MinerGUI(gui_state=state)
            try:
                with patch.object(
                    QFileDialog,
                    "getOpenFileName",
                    return_value=(str(config_path), "JSON 文件 (*.json)"),
                ):
                    window.load_config()

                self.assertEqual(state.last_config_path(), config_path.resolve())
                self.assertEqual(window.rooms_edit.text(), "123,456")
            finally:
                window.close()

    def test_manual_save_remembers_config_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "saved.json"
            state = self._state_for(temp_dir)
            window = MinerGUI(gui_state=state)
            window.cookie_edit.setText("SESSDATA=test; bili_jct=test")
            try:
                with patch.object(
                    QFileDialog,
                    "getSaveFileName",
                    return_value=(str(config_path), "JSON 文件 (*.json)"),
                ):
                    window.save_config()

                self.assertEqual(state.last_config_path(), config_path.resolve())
                payload = json.loads(config_path.read_text(encoding="utf-8"))
                self.assertEqual(payload["cookie"], "SESSDATA=test; bili_jct=test")
            finally:
                window.close()


if __name__ == "__main__":
    unittest.main()
