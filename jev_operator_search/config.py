"""Persist the TypeSafe API key outside of Blender's preferences file.

Add-on preferences only reach disk when Blender saves `userpref.blend` — which
does not happen if *Auto-Save Preferences* is off, so a key pasted into the
add-on preferences can be gone again at the next launch. The key is therefore
mirrored into a small JSON file in the extension's user directory, written the
moment it is entered and read back when the add-on registers.
"""

import json
import os

import bpy

_FILENAME = "config.json"


def _config_dir():
    # Extensions (4.2+) get their own user-writable directory; fall back to a
    # named folder under the user config path for a plain add-on install.
    extension_path_user = getattr(bpy.utils, "extension_path_user", None)
    if extension_path_user is not None:
        try:
            return extension_path_user(__package__, create=True)
        except Exception:
            pass
    return bpy.utils.user_resource("CONFIG", path=__package__.rpartition(".")[2], create=True)


def _config_path():
    directory = _config_dir()
    return os.path.join(directory, _FILENAME) if directory else ""


def load_api_key():
    """Return the stored key, or "" if there is none (or it can't be read)."""
    path = _config_path()
    if not path or not os.path.exists(path):
        return ""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("api_key", "") or ""
    except (OSError, ValueError):
        return ""


def save_api_key(api_key):
    """Write the key to disk, readable only by the current user.

    An empty key removes the stored file, so clearing the field in the add-on
    preferences also forgets the key.
    """
    path = _config_path()
    if not path:
        return
    if not api_key:
        try:
            os.remove(path)
        except OSError:
            pass
        return
    try:
        # Create with 0600 so the key isn't world-readable on shared machines.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"api_key": api_key}, fh)
    except OSError:
        pass
