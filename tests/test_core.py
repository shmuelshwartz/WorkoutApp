from pathlib import Path
import sys
import sqlite3

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


def test_workout_session_loads_preset_and_records(monkeypatch):
    db_path = Path(__file__).resolve().parents[1] / "data" / "workout.db"

    session = core.WorkoutSession("Push Day", db_path=db_path)

    assert session.exercises
    assert session.exercises[0]["name"] == "Shoulder Circles"

    def fail_connect(*args, **kwargs):
        raise AssertionError("database accessed during workout")

    monkeypatch.setattr(sqlite3, "connect", fail_connect)

    total_sets = sum(ex["sets"] for ex in session.exercises)
    finished = False
    for i in range(total_sets):
        finished = session.record_metrics({"Reps": i})
    assert finished


def test_metric_type_crud(tmp_path):
    db_src = Path(__file__).resolve().parents[1] / "data" / "workout.db"
    db_path = tmp_path / "workout.db"
    db_path.write_bytes(db_src.read_bytes())

    name = "TestMetric"
    core.add_metric_type(
        name,
        "int",
        "manual_text",
        "post_set",
        "set",
        db_path=db_path,
    )
    types = core.get_all_metric_types(db_path)
    assert any(mt["name"] == name for mt in types)

    core.add_metric_to_exercise("Push-ups", name, db_path)
    metrics = core.get_metrics_for_exercise("Push-ups", db_path)
    assert any(m["name"] == name for m in metrics)

    core.remove_metric_from_exercise("Push-ups", name, db_path)
    metrics = core.get_metrics_for_exercise("Push-ups", db_path)
    assert not any(m["name"] == name for m in metrics)
