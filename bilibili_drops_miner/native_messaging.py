from __future__ import annotations

import json
import struct
import sys
from collections.abc import Sequence
from typing import Any, BinaryIO

from bilibili_drops_miner.gui_parts.chrome_companion import (
    CHROME_EXTENSION_ORIGIN,
)
from bilibili_drops_miner.gui_parts.gui_state import GuiStateStore
from bilibili_drops_miner.utils import join_cookie


MAX_NATIVE_MESSAGE_BYTES = 1024 * 1024
COOKIE_NAMES = {
    "SESSDATA",
    "bili_jct",
    "DedeUserID",
    "DedeUserID__ckMd5",
    "buvid3",
    "b_nut",
    "sid",
}


def is_native_messaging_invocation(argv: Sequence[str]) -> bool:
    return any(
        argument == "--native-messaging-host"
        or argument == CHROME_EXTENSION_ORIGIN
        for argument in argv[1:]
    )


def read_native_message(stream: BinaryIO) -> dict[str, Any]:
    header = stream.read(4)
    if len(header) != 4:
        raise ValueError("native message header missing")
    (message_size,) = struct.unpack("=I", header)
    if message_size <= 0 or message_size > MAX_NATIVE_MESSAGE_BYTES:
        raise ValueError("native message size invalid")
    payload = stream.read(message_size)
    if len(payload) != message_size:
        raise ValueError("native message payload incomplete")
    message = json.loads(payload.decode("utf-8"))
    if not isinstance(message, dict):
        raise ValueError("native message must be an object")
    return message


def write_native_message(stream: BinaryIO, message: dict[str, Any]) -> None:
    payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
    if len(payload) > MAX_NATIVE_MESSAGE_BYTES:
        raise ValueError("native response is too large")
    stream.write(struct.pack("=I", len(payload)))
    stream.write(payload)
    stream.flush()


def cookie_string_from_message(message: dict[str, Any]) -> tuple[str, list[str]]:
    if message.get("type") != "save_bilibili_cookies":
        raise ValueError("unsupported native message")
    raw_cookies = message.get("cookies")
    if not isinstance(raw_cookies, list):
        raise ValueError("cookies must be a list")

    cookie_map: dict[str, str] = {}
    for raw_cookie in raw_cookies:
        if not isinstance(raw_cookie, dict):
            continue
        name = str(raw_cookie.get("name") or "").strip()
        value = str(raw_cookie.get("value") or "")
        if name in COOKIE_NAMES and value:
            cookie_map[name] = value

    if not cookie_map.get("SESSDATA") or not cookie_map.get("DedeUserID"):
        raise ValueError("Bilibili login cookies are incomplete")
    ordered_names = [name for name in COOKIE_NAMES if name in cookie_map]
    ordered_names.sort(key=lambda name: (name != "SESSDATA", name))
    ordered_map = {name: cookie_map[name] for name in ordered_names}
    return join_cookie(ordered_map), ordered_names


def handle_native_message(
    message: dict[str, Any],
    *,
    state: GuiStateStore | None = None,
) -> dict[str, Any]:
    cookie, cookie_names = cookie_string_from_message(message)
    store = state if state is not None else GuiStateStore()
    store.set_saved_cookie(cookie)
    revision = store.mark_cookie_imported()
    store.sync()
    return {
        "ok": True,
        "saved_count": len(cookie_names),
        "cookie_names": cookie_names,
        "revision": revision,
    }


def run_native_messaging_host(
    *,
    input_stream: BinaryIO | None = None,
    output_stream: BinaryIO | None = None,
    state: GuiStateStore | None = None,
) -> int:
    source = input_stream or sys.stdin.buffer
    destination = output_stream or sys.stdout.buffer
    try:
        message = read_native_message(source)
        response = handle_native_message(message, state=state)
    except Exception as exc:
        response = {"ok": False, "error": str(exc)}
    write_native_message(destination, response)
    return 0 if response.get("ok") else 1
