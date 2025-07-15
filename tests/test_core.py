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


def test_predefined_only_details_and_metrics():
    db_path = Path(__file__).resolve().parents[1] / "data" / "workout.db"

    # Bench Press exists only as a predefined exercise
    details = core.get_exercise_details("Bench Press", db_path)
    assert details and not details["is_user_created"]
    builtin = core.get_exercise_details("Bench Press", db_path, is_user_created=False)
    assert builtin == details
    assert core.get_exercise_details("Bench Press", db_path, is_user_created=True) is None

    metrics_default = core.get_metrics_for_exercise("Bench Press", db_path)
    metrics_builtin = core.get_metrics_for_exercise("Bench Press", db_path, is_user_created=False)
    assert metrics_default == metrics_builtin
    assert core.get_metrics_for_exercise("Bench Press", db_path, is_user_created=True) == []


def test_metric_type_schema():
    db_path = Path(__file__).resolve().parents[1] / "data" / "workout.db"
    schema = core.get_metric_type_schema(db_path)

    names = [f["name"] for f in schema]
    assert "name" in names
    assert "input_type" in names
    assert "source_type" in names
    assert "input_timing" in names
    assert "is_required" in names
    assert "scope" in names
    assert "description" in names
    for field in schema:
        if field["name"] in {"input_type", "source_type", "input_timing", "scope"}:
            assert field.get("options")


def test_workout_session_loads_preset_and_records(monkeypatch):
    db_path = Path(__file__).resolve().parents[1] / "data" / "workout.db"

    session = core.WorkoutSession("Push Day", db_path=db_path)

    assert session.exercises
    assert session.exercises[0]["name"] == "Shoulder Circles"


    total_sets = sum(ex["sets"] for ex in session.exercises)
    finished = False
    for i in range(total_sets):
        session.mark_set_completed()
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


def test_workout_session_summary_contains_details():
    db_path = Path(__file__).resolve().parents[1] / "data" / "workout.db"
    session = core.WorkoutSession("Push Day", db_path=db_path)

    total_sets = sum(ex["sets"] for ex in session.exercises)
    for i in range(total_sets):
        session.mark_set_completed()
        session.record_metrics({"Reps": i + 1})

    summary = session.summary()

    assert "Workout: Push Day" in summary
    for ex in session.exercises:
        assert ex["name"] in summary
    assert "Set 1" in summary
    assert "Reps" in summary
    assert "Duration:" in summary


def test_rest_timer_updates_on_record(monkeypatch):
    db_path = Path(__file__).resolve().parents[1] / "data" / "workout.db"

    fake_time = [1000.0]

    def _time():
        return fake_time[0]

    monkeypatch.setattr(core.time, "time", _time)

    session = core.WorkoutSession("Push Day", db_path=db_path)
    assert session.rest_target_time == fake_time[0] + core.DEFAULT_REST_DURATION

    fake_time[0] += 30
    session.mark_set_completed()
    session.record_metrics({"Reps": 1})
    assert session.last_set_time == 1030.0
    assert session.rest_target_time == 1030.0 + core.DEFAULT_REST_DURATION

    session.adjust_rest_timer(10)
    assert session.rest_target_time == 1040.0 + core.DEFAULT_REST_DURATION


def test_exercise_object_loads_and_edits_without_db_change(tmp_path):
    db_src = Path(__file__).resolve().parents[1] / "data" / "workout.db"
    db_path = tmp_path / "workout.db"
    db_path.write_bytes(db_src.read_bytes())

    ex = core.Exercise("Bench Press", db_path=db_path)

    assert ex.name == "Bench Press"
    assert ex.metrics

    original = core.get_metrics_for_exercise("Bench Press", db_path)

    # manipulate the in-memory object
    ex.update_metric("Reps", input_type="float")
    ex.remove_metric("Weight")
    ex.add_metric({"name": "Tempo", "input_type": "int", "source_type": "manual_text", "values": []})

    # database should remain unchanged until the exercise is saved
    after = core.get_metrics_for_exercise("Bench Press", db_path)
    assert after == original

    assert any(m["name"] == "Tempo" for m in ex.metrics)
    assert not any(m["name"] == "Weight" for m in ex.metrics)
    for m in ex.metrics:
        if m["name"] == "Reps":
            assert m["input_type"] == "float"


def test_exercise_save_persists_changes(tmp_path):
    db_src = Path(__file__).resolve().parents[1] / "data" / "workout.db"
    db_path = tmp_path / "workout.db"
    db_path.write_bytes(db_src.read_bytes())

    ex = core.Exercise("Push-ups", db_path=db_path)
    ex.description = "Modified description"
    assert not ex.is_user_created

    core.save_exercise(ex)

    # default should return the user-created copy
    details = core.get_exercise_details("Push-ups", db_path)
    assert details["is_user_created"]
    assert details["description"] == "Modified description"

    # explicit queries for each variant
    built_in = core.get_exercise_details("Push-ups", db_path, is_user_created=False)
    assert built_in and not built_in["is_user_created"]
    user_copy = core.get_exercise_details("Push-ups", db_path, is_user_created=True)
    assert user_copy["description"] == "Modified description"

    default_metrics = core.get_metrics_for_exercise("Push-ups", db_path)
    user_metrics = core.get_metrics_for_exercise("Push-ups", db_path, is_user_created=True)
    built_in_metrics = core.get_metrics_for_exercise("Push-ups", db_path, is_user_created=False)
    assert default_metrics == user_metrics
    assert built_in_metrics

    reloaded = core.Exercise("Push-ups", db_path=db_path)
    assert reloaded.is_user_created
