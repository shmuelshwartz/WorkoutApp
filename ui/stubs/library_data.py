"""Stub data provider for ``ExerciseLibraryScreen``."""

from __future__ import annotations


class LibraryStubDataProvider:
    """Provides in-memory data for visual testing."""

    def __init__(self):
        self.exercises = [
            ("Push Ups", False),
            ("Custom Move", True),
        ]
        self.metrics = [
            {"name": "Reps", "is_user_created": False},
            {"name": "Time", "is_user_created": False},
            {"name": "Custom Metric", "is_user_created": True},
        ]

    def get_all_exercises(self, include_user_created: bool = True):
        return list(self.exercises)

    def get_all_metric_types(self, include_user_created: bool = True):
        return list(self.metrics)

    def delete_exercise(self, name: str):
        self.exercises = [e for e in self.exercises if e[0] != name]

    def delete_metric_type(self, name: str):
        self.metrics = [m for m in self.metrics if m["name"] != name]
