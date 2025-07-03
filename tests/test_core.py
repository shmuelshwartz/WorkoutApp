from pathlib import Path
import sys

# Ensure the project root is on the import path so `core` can be imported
sys.path.append(str(Path(__file__).resolve().parents[1]))
import core

EXPECTED_PRESETS = [
    {
        "name": "Push Day",
        "exercises": [
            {"name": "Shoulder Circles", "sets": 3},
            {"name": "Push-ups", "sets": 3},
            {"name": "Bench Press", "sets": 3},
            {"name": "Overhead Press", "sets": 3},
        ],
    },
    {
        "name": "Pull Day",
        "exercises": [
            {"name": "Jumping Jacks", "sets": 3},
            {"name": "Front Lever", "sets": 3},
            {"name": "Pull-ups", "sets": 3},
            {"name": "Barbell Rows", "sets": 3},
        ],
    },
    {
        "name": "Leg Day",
        "exercises": [
            {"name": "Skipping Rope", "sets": 3},
            {"name": "Squats", "sets": 3},
            {"name": "Deadlifts", "sets": 3},
            {"name": "Lunges", "sets": 3},
        ],
    },
]

def test_load_workout_presets_updates_global():
    db_path = Path(__file__).resolve().parents[1] / "data" / "workout.db"
    presets = core.load_workout_presets(db_path)
    assert presets == EXPECTED_PRESETS
    assert core.WORKOUT_PRESETS == EXPECTED_PRESETS


def test_exercise_set_counts():
    db_path = Path(__file__).resolve().parents[1] / "data" / "workout.db"
    presets = core.load_workout_presets(db_path)
    for preset in presets:
        for exercise in preset["exercises"]:
            assert exercise["sets"] == 3
