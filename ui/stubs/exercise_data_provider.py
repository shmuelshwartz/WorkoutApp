from __future__ import annotations

"""Stub data provider for EditExerciseScreen.

Provides a minimal Exercise-like object for test mode without any backend
or database dependencies.
"""

from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class _ExerciseStub:
    """Simple stand-in for the backend ``Exercise`` class."""

    name: str = "Sample Exercise"
    description: str = "Example description"
    metrics: List[Dict] = field(default_factory=lambda: [{"name": "Reps", "input_timing": "set", "is_required": True}])
    is_user_created: bool = True

    def __post_init__(self):
        self._original = {
            "name": self.name,
            "description": self.description,
            "metrics": [m.copy() for m in self.metrics],
        }

    # ------------------------------------------------------------------
    # Methods mimicking the real ``Exercise`` interface
    # ------------------------------------------------------------------
    def remove_metric(self, metric_name: str) -> None:
        self.metrics = [m for m in self.metrics if m.get("name") != metric_name]

    def is_modified(self) -> bool:
        return (
            self.name != self._original["name"]
            or self.description != self._original["description"]
            or self.metrics != self._original["metrics"]
        )


class StubExerciseDataProvider:
    """Data provider used when ``test_mode=True``."""

    def get_exercise(self, name: str, is_user_created: bool | None = None) -> _ExerciseStub:
        return _ExerciseStub(name=name)

    # The real provider persists data. The stub simply prints to console.
    def save_exercise(self, exercise_obj: _ExerciseStub) -> None:
        print(f"Stub save for exercise: {exercise_obj.name}")
