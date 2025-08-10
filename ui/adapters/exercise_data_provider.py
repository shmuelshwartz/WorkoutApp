from __future__ import annotations

"""Adapter-based data provider for ``EditExerciseScreen``.

This module bridges the UI layer with backend logic while keeping the screen
itself free from direct backend or database imports.
"""

import sqlite3
from typing import Any

import core
from backend.exercise import Exercise


class ExerciseDataProvider:
    """Provides exercise data backed by the real database."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or core.DEFAULT_DB_PATH

    def get_exercise(self, name: str, is_user_created: bool | None = None) -> Exercise:
        return Exercise(name, db_path=self.db_path, is_user_created=is_user_created)

    def save_exercise(self, exercise_obj: Any) -> None:
        core.save_exercise(exercise_obj)

    def exercise_name_exists(self, name: str) -> bool:
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM library_exercises WHERE name = ? AND is_user_created = 1",
            (name,),
        )
        exists = cur.fetchone() is not None
        conn.close()
        return exists
