"""Stub data provider for ExerciseLibraryScreen."""

from __future__ import annotations

from typing import List, Tuple, Dict


class StubExerciseLibraryProvider:
    """Provides stub exercises and metric types for testing."""

    def __init__(self) -> None:
        self.exercises: List[Tuple[str, bool]] = [
            ("Push Ups", False),
            ("Custom Move", True),
        ]
        self.metrics: List[Dict[str, object]] = [
            {"name": "Reps", "is_user_created": False},
            {"name": "Weight", "is_user_created": False},
            {"name": "Custom Metric", "is_user_created": True},
        ]

    # Exercise methods
    def get_all_exercises(self, include_user_created: bool = True) -> List[Tuple[str, bool]]:
        data = self.exercises
        if include_user_created:
            return list(data)
        return [ex for ex in data if not ex[1]]

    def delete_exercise(self, name: str) -> None:
        self.exercises = [ex for ex in self.exercises if ex[0] != name]

    # Metric methods
    def get_all_metric_types(self, include_user_created: bool = True) -> List[Dict[str, object]]:
        data = self.metrics
        if include_user_created:
            return list(data)
        return [m for m in data if not m["is_user_created"]]

    def delete_metric_type(self, name: str) -> None:
        self.metrics = [m for m in self.metrics if m["name"] != name]
