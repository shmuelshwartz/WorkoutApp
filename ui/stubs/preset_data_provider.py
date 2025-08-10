"""Stub data provider for :class:`EditPresetScreen`.

Supplies static data so the screen can run in ``test_mode`` without
backend or database access.
"""
from __future__ import annotations

from pathlib import Path


class StubPresetDataProvider:
    """Minimal stand-in used for previews and tests."""

    DEFAULT_SETS_PER_EXERCISE = 3

    def __init__(self) -> None:
        self.db_path = Path("stub.db")

    def get_metrics_for_exercise(
        self, name: str, db_path: Path | None = None, preset_name: str | None = None
    ) -> list:
        return [{"name": "Reps", "scope": "set"}]

    def get_all_metric_types(self, include_user_created: bool = True) -> list:
        return [
            {"name": "Focus", "scope": "preset", "is_user_created": False},
            {"name": "Duration", "scope": "session", "is_user_created": False},
            {"name": "Reps", "scope": "exercise", "is_user_created": False},
        ]

    def load_workout_presets(self, db_path: Path | None = None) -> None:  # pragma: no cover - stub
        pass

    def get_all_exercises(
        self, db_path: Path | None = None, include_user_created: bool = True
    ) -> list:
        return [
            ("Push Ups", False),
            ("Sit Ups", False),
            ("Custom Move", True),
        ]

    def get_presets(self) -> list:
        return [
            {"name": "Push"},
            {"name": "Pull"},
            {"name": "Legs"},
        ]
