from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QByteArray, QSettings


SETTINGS_ORGANIZATION = "BiliBiliDropsMiner"
SETTINGS_APPLICATION = "BilibiliDropsMiner"

WINDOW_GEOMETRY_KEY = "main_window/geometry"
LAST_CONFIG_PATH_KEY = "config/last_path"
SAVED_COOKIE_KEY = "credentials/cookie"
COOKIE_IMPORT_REVISION_KEY = "credentials/cookie_import_revision"


class GuiStateStore:
    """Persist local GUI state and the last explicitly entered session cookie."""

    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = (
            settings
            if settings is not None
            else QSettings(SETTINGS_ORGANIZATION, SETTINGS_APPLICATION)
        )

    def window_geometry(self) -> QByteArray:
        value = self._settings.value(WINDOW_GEOMETRY_KEY, QByteArray())
        if isinstance(value, QByteArray):
            return QByteArray(value)
        if isinstance(value, (bytes, bytearray)):
            return QByteArray(value)
        return QByteArray()

    def set_window_geometry(self, geometry: QByteArray) -> None:
        self._settings.setValue(WINDOW_GEOMETRY_KEY, geometry)

    def last_config_path(self) -> Path | None:
        value = self._settings.value(LAST_CONFIG_PATH_KEY, "")
        path_text = str(value or "").strip()
        if not path_text:
            return None
        return Path(path_text)

    def set_last_config_path(self, path: str | Path) -> None:
        normalized = Path(path).expanduser().resolve(strict=False)
        self._settings.setValue(LAST_CONFIG_PATH_KEY, str(normalized))

    def clear_last_config_path(self) -> None:
        self._settings.remove(LAST_CONFIG_PATH_KEY)

    def saved_cookie(self) -> str:
        return str(self._settings.value(SAVED_COOKIE_KEY, "") or "").strip()

    def set_saved_cookie(self, cookie: str) -> None:
        normalized = cookie.strip()
        if normalized:
            self._settings.setValue(SAVED_COOKIE_KEY, normalized)
        else:
            self.clear_saved_cookie()

    def clear_saved_cookie(self) -> None:
        self._settings.remove(SAVED_COOKIE_KEY)

    def cookie_import_revision(self) -> str:
        return str(self._settings.value(COOKIE_IMPORT_REVISION_KEY, "") or "")

    def mark_cookie_imported(self, revision: str | None = None) -> str:
        value = str(revision or time.time_ns())
        self._settings.setValue(COOKIE_IMPORT_REVISION_KEY, value)
        return value

    def sync(self) -> None:
        self._settings.sync()
