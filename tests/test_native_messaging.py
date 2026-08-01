from __future__ import annotations

import io
import json
import struct
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QSettings

from bilibili_drops_miner.gui_parts.chrome_companion import (
    CHROME_EXTENSION_ORIGIN,
)
from bilibili_drops_miner.gui_parts.gui_state import GuiStateStore
from bilibili_drops_miner.native_messaging import (
    cookie_string_from_message,
    is_native_messaging_invocation,
    read_native_message,
    run_native_messaging_host,
    write_native_message,
)


def _cookie_message() -> dict:
    return {
        "type": "save_bilibili_cookies",
        "cookies": [
            {"name": "SESSDATA", "value": "session-secret"},
            {"name": "DedeUserID", "value": "123"},
            {"name": "bili_jct", "value": "csrf-secret"},
            {"name": "unrelated", "value": "ignored"},
        ],
    }


class NativeMessagingTests(unittest.TestCase):
    def test_native_message_round_trip(self) -> None:
        stream = io.BytesIO()
        write_native_message(stream, _cookie_message())
        stream.seek(0)
        self.assertEqual(read_native_message(stream), _cookie_message())

    def test_cookie_message_filters_to_login_cookie_names(self) -> None:
        cookie, names = cookie_string_from_message(_cookie_message())
        self.assertIn("SESSDATA=session-secret", cookie)
        self.assertIn("DedeUserID=123", cookie)
        self.assertNotIn("unrelated", cookie)
        self.assertEqual(set(names), {"SESSDATA", "DedeUserID", "bili_jct"})

    def test_native_host_persists_cookie_and_returns_no_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = QSettings(
                str(Path(temp_dir) / "gui.ini"),
                QSettings.IniFormat,
            )
            state = GuiStateStore(settings)
            source = io.BytesIO()
            write_native_message(source, _cookie_message())
            source.seek(0)
            destination = io.BytesIO()

            self.assertEqual(
                run_native_messaging_host(
                    input_stream=source,
                    output_stream=destination,
                    state=state,
                ),
                0,
            )
            destination.seek(0)
            response = read_native_message(destination)

            self.assertTrue(response["ok"])
            self.assertEqual(response["saved_count"], 3)
            self.assertNotIn("session-secret", json.dumps(response))
            self.assertIn("SESSDATA=session-secret", state.saved_cookie())
            self.assertTrue(state.cookie_import_revision())

    def test_invalid_message_returns_framed_error(self) -> None:
        payload = json.dumps({"type": "wrong"}).encode()
        source = io.BytesIO(struct.pack("=I", len(payload)) + payload)
        destination = io.BytesIO()

        self.assertEqual(
            run_native_messaging_host(
                input_stream=source,
                output_stream=destination,
            ),
            1,
        )
        destination.seek(0)
        self.assertFalse(read_native_message(destination)["ok"])

    def test_native_invocation_accepts_only_flag_or_extension_origin(self) -> None:
        self.assertTrue(
            is_native_messaging_invocation(["app", CHROME_EXTENSION_ORIGIN])
        )
        self.assertTrue(
            is_native_messaging_invocation(["app", "--native-messaging-host"])
        )
        self.assertFalse(is_native_messaging_invocation(["app"]))


if __name__ == "__main__":
    unittest.main()
