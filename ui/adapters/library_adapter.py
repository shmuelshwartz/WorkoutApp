"""Backend adapter for ``ExerciseLibraryScreen``."""

from __future__ import annotations

import core
from core import DEFAULT_DB_PATH


class LibraryAdapter:
    """Adapter that proxies calls to :mod:`core` functions."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path

    def get_all_exercises(self, include_user_created: bool = True):
        return core.get_all_exercises(
            self.db_path, include_user_created=include_user_created
        )

    def get_all_metric_types(self, include_user_created: bool = True):
        return core.get_all_metric_types(
            self.db_path, include_user_created=include_user_created
        )

    def delete_exercise(self, name: str):
        core.delete_exercise(name, db_path=self.db_path, is_user_created=True)

    def delete_metric_type(self, name: str):
        core.delete_metric_type(name, db_path=self.db_path, is_user_created=True)
