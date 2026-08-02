from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


CHROME_EXTENSION_ID = "illpcmbmojgliojnfhleklbdonlhmhfc"
CHROME_EXTENSION_ORIGIN = f"chrome-extension://{CHROME_EXTENSION_ID}/"
CHROME_COOKIE_SYNC_URL = f"{CHROME_EXTENSION_ORIGIN}sync.html"
NATIVE_HOST_NAME = "com.mi0e.bilibili_drops_miner"
NATIVE_HOST_FILENAME = f"{NATIVE_HOST_NAME}.json"


def chrome_extension_directory() -> Path:
    if getattr(sys, "frozen", False):
        bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return bundle_root / "chrome_extension"
    return Path(__file__).resolve().parents[2] / "chrome_extension"


def chrome_native_host_manifest_path(home: Path | None = None) -> Path:
    user_home = home if home is not None else Path.home()
    return (
        user_home
        / "Library"
        / "Application Support"
        / "Google"
        / "Chrome"
        / "NativeMessagingHosts"
        / NATIVE_HOST_FILENAME
    )


def build_native_host_manifest(executable_path: str | Path) -> dict[str, Any]:
    return {
        "name": NATIVE_HOST_NAME,
        "description": "Bilibili Drops Miner cookie bridge",
        "path": str(Path(executable_path).resolve(strict=False)),
        "type": "stdio",
        "allowed_origins": [CHROME_EXTENSION_ORIGIN],
    }


def register_native_messaging_host(
    *,
    executable_path: str | Path | None = None,
    manifest_path: str | Path | None = None,
) -> Path:
    executable = Path(executable_path or sys.executable).resolve(strict=False)
    destination = (
        Path(manifest_path)
        if manifest_path is not None
        else chrome_native_host_manifest_path()
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        build_native_host_manifest(executable),
        ensure_ascii=True,
        indent=2,
    )
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(payload + "\n", encoding="utf-8")
    os.replace(temporary, destination)
    return destination


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


def _current_chrome_profile_directory(profile_root: Path) -> Path | None:
    local_state = _read_json_object(profile_root / "Local State") or {}
    profile_state = local_state.get("profile")
    last_used = (
        str(profile_state.get("last_used") or "").strip()
        if isinstance(profile_state, dict)
        else ""
    )
    if last_used and Path(last_used).name == last_used:
        profile_dir = profile_root / last_used
        if profile_dir.is_dir():
            return profile_dir

    default_profile = profile_root / "Default"
    if default_profile.is_dir():
        return default_profile
    return None


def _chrome_profile_preferences(profile_dir: Path) -> Path | None:
    # Chrome's extension registry lives in Secure Preferences. Preferences is
    # only a compatibility fallback when the secure file does not exist.
    for filename in ("Secure Preferences", "Preferences"):
        path = profile_dir / filename
        if path.is_file():
            return path
    return None


def chrome_extension_is_installed(profile_root: Path | None = None) -> bool:
    root = profile_root or (
        Path.home()
        / "Library"
        / "Application Support"
        / "Google"
        / "Chrome"
    )
    profile_dir = _current_chrome_profile_directory(root)
    if profile_dir is None:
        return False
    preferences_path = _chrome_profile_preferences(profile_dir)
    if preferences_path is None:
        return False

    preferences = _read_json_object(preferences_path) or {}
    extensions = preferences.get("extensions")
    settings = extensions.get("settings") if isinstance(extensions, dict) else None
    extension = (
        settings.get(CHROME_EXTENSION_ID) if isinstance(settings, dict) else None
    )
    return isinstance(extension, dict) and extension.get("state") == 1


def _open_chrome_url(url: str) -> None:
    subprocess.Popen(
        ["open", "-a", "Google Chrome", url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def open_cookie_sync_page() -> None:
    _open_chrome_url(CHROME_COOKIE_SYNC_URL)


def open_extension_setup() -> Path:
    extension_dir = chrome_extension_directory()
    _open_chrome_url("chrome://extensions/")
    subprocess.Popen(
        ["open", "-R", str(extension_dir / "manifest.json")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return extension_dir


def chrome_companion_is_available() -> bool:
    return (
        sys.platform == "darwin"
        and bool(getattr(sys, "frozen", False))
        and chrome_extension_directory().joinpath("manifest.json").is_file()
        and Path("/Applications/Google Chrome.app").is_dir()
    )
