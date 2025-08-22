"""Utility helpers for exporting workout data."""
from __future__ import annotations

from datetime import datetime


def make_export_name() -> str:
    """Return an auto-generated export filename.

    The name follows the format ``workout_YYYY_MM_DD_HH__MM__SS.db`` using
    the current local time.
    """
    return datetime.now().strftime("workout_%Y_%m_%d_%H__%M__%S.db")

