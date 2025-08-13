"""Shared constants and globals for backend modules."""

from __future__ import annotations

from pathlib import Path

# Default values used throughout the application
DEFAULT_SETS_PER_EXERCISE = 3
DEFAULT_REST_DURATION = 120

# Path to the bundled SQLite database shipped with the application
DEFAULT_DB_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "workout.db"
)

# In-memory cache of loaded workout presets
WORKOUT_PRESETS: list = []

__all__ = [
    "DEFAULT_SETS_PER_EXERCISE",
    "DEFAULT_REST_DURATION",
    "DEFAULT_DB_PATH",
    "WORKOUT_PRESETS",
]
