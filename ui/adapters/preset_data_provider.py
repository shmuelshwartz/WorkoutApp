"""Data providers for :class:`EditPresetScreen`.

Defines an adapter that proxies calls to the ``core`` module so that
UI screens avoid importing backend modules directly.
"""
from __future__ import annotations

from pathlib import Path

import core


class CorePresetDataProvider:
    """Adapter bridging ``EditPresetScreen`` with backend core functions."""

    DEFAULT_SETS_PER_EXERCISE = core.DEFAULT_SETS_PER_EXERCISE

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or core.DEFAULT_DB_PATH

    def get_metrics_for_exercise(
        self, name: str, db_path: Path | None = None, preset_name: str | None = None
    ) -> list:
        return core.get_metrics_for_exercise(
            name, db_path=db_path or self.db_path, preset_name=preset_name
        )

    def get_all_metric_types(self, include_user_created: bool = True) -> list:
        return core.get_all_metric_types(
            self.db_path, include_user_created=include_user_created
        )

    def load_workout_presets(self, db_path: Path | None = None) -> None:
        core.load_workout_presets(db_path or self.db_path)

    def get_all_exercises(
        self, db_path: Path | None = None, include_user_created: bool = True
    ) -> list:
        return core.get_all_exercises(
            db_path or self.db_path, include_user_created=include_user_created
        )
