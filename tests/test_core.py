from pathlib import Path
import sys

# Ensure the project root is on the import path so `core` can be imported
sys.path.append(str(Path(__file__).resolve().parents[1]))
import core


def test_load_workout_presets_updates_global():
    db_path = Path(__file__).resolve().parents[1] / "data" / "workout.db"
    presets = core.load_workout_presets(db_path)

    assert presets == core.WORKOUT_PRESETS
    assert isinstance(presets, list)

    for preset in presets:
        assert isinstance(preset, dict)
        assert "name" in preset
        assert "exercises" in preset
        assert isinstance(preset["exercises"], list)
        for exercise in preset["exercises"]:
            assert isinstance(exercise, dict)
            assert "name" in exercise
            assert "sets" in exercise


def test_exercise_sets_are_positive_ints():
    db_path = Path(__file__).resolve().parents[1] / "data" / "workout.db"
    presets = core.load_workout_presets(db_path)

    for preset in presets:
        for exercise in preset["exercises"]:
            assert isinstance(exercise["sets"], int)
            assert exercise["sets"] > 0


def test_get_metrics_for_exercise():
    db_path = Path(__file__).resolve().parents[1] / "data" / "workout.db"
    metrics = core.get_metrics_for_exercise("Bench Press", db_path)

    assert isinstance(metrics, list)
    assert metrics
    for metric in metrics:
        assert "name" in metric
        assert "input_type" in metric
        assert "source_type" in metric
        assert "values" in metric
        if metric["source_type"] == "manual_enum":
            assert isinstance(metric["values"], list)
            assert metric["values"]


def test_get_all_exercises():
    db_path = Path(__file__).resolve().parents[1] / "data" / "workout.db"
    exercises = core.get_all_exercises(db_path)

    assert isinstance(exercises, list)
    assert exercises
    for name in exercises:
        assert isinstance(name, str)
