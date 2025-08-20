from __future__ import annotations

"""Utility functions for loading and saving user settings.

The settings are stored as a list of dictionaries to preserve order.
Each dictionary contains ``key``, ``value`` and ``type`` entries.
"""

from pathlib import Path
import json
from typing import Any, List, Dict

# Path to the JSON file where settings are persisted.
SETTINGS_PATH = Path(__file__).resolve().parents[1] / "data" / "settings.json"

# Default settings to initialize the file on first run.
DEFAULT_SETTINGS: List[Dict[str, Any]] = [
    {"key": "sound_level", "value": 1.0, "type": "slider"},
    {"key": "sound_on", "value": True, "type": "bool"},
]

# Internal cache so settings are only read from disk once.
_settings_cache: List[Dict[str, Any]] | None = None


def load_settings() -> List[Dict[str, Any]]:
    """Load settings from :data:`SETTINGS_PATH` or create defaults."""
    if SETTINGS_PATH.exists():
        try:
            with SETTINGS_PATH.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    save_settings(DEFAULT_SETTINGS)
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: List[Dict[str, Any]]) -> None:
    """Persist ``settings`` to :data:`SETTINGS_PATH`."""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SETTINGS_PATH.open("w", encoding="utf-8") as fh:
        json.dump(settings, fh)


def get_settings() -> List[Dict[str, Any]]:
    """Return the cached settings list, loading from disk if needed."""
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = load_settings()
    return _settings_cache


def get_value(key: str) -> Any:
    """Fetch the value associated with ``key``."""
    for item in get_settings():
        if item.get("key") == key:
            return item.get("value")
    return None


def set_value(key: str, value: Any) -> None:
    """Update ``key`` with ``value`` and persist the change."""
    settings = get_settings()
    for item in settings:
        if item.get("key") == key:
            item["value"] = value
            break
    else:
        settings.append({"key": key, "value": value, "type": type(value).__name__})
    save_settings(settings)
