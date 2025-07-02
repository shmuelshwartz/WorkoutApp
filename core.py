"""Core data structures for workout presets."""

from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class Exercise:
    """Represents a single exercise in a workout preset."""

    name: str
    sets: int
    reps: int


@dataclass
class WorkoutPreset:
    """A workout preset consisting of multiple exercises."""

    name: str
    exercises: List[Exercise] = field(default_factory=list)


WORKOUT_PRESETS: Dict[str, WorkoutPreset] = {
    "Day 1": WorkoutPreset(
        name="Day 1 - Push",
        exercises=[
            Exercise("Bench Press", 3, 10),
            Exercise("Overhead Press", 3, 10),
            Exercise("Tricep Dip", 3, 12),
        ],
    ),
    "Day 2": WorkoutPreset(
        name="Day 2 - Pull",
        exercises=[
            Exercise("Pull Up", 3, 8),
            Exercise("Barbell Row", 3, 10),
            Exercise("Bicep Curl", 3, 12),
        ],
    ),
    "Day 3": WorkoutPreset(
        name="Day 3 - Legs",
        exercises=[
            Exercise("Squat", 3, 10),
            Exercise("Lunge", 3, 12),
            Exercise("Calf Raise", 3, 15),
        ],
    ),
}

