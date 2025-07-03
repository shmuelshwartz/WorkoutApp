from pathlib import Path
import sys

# Ensure the project root is on the import path so `core` can be imported
sys.path.append(str(Path(__file__).resolve().parents[1]))
import core

EXPECTED_PRESETS = [
    {
        "name": "Push Day",
        "exercises": [
            "Shoulder Circles",
            "Push-ups",
            "Bench Press",
            "Overhead Press",
        ],
    },
    {
        "name": "Pull Day",
        "exercises": [
            "Jumping Jacks",
            "Front Lever",
            "Pull-ups",
            "Barbell Rows",
        ],
    },
    {
        "name": "Leg Day",
        "exercises": [
            "Skipping Rope",
            "Squats",
            "Deadlifts",
            "Lunges",
        ],
    },
]

def test_load_workout_presets_updates_global():
    db_path = Path(__file__).resolve().parents[1] / "data" / "workout.db"
    presets = core.load_workout_presets(db_path)
    assert presets == EXPECTED_PRESETS
    assert core.WORKOUT_PRESETS == EXPECTED_PRESETS
