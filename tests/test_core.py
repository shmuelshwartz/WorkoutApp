import sqlite3
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core


@pytest.fixture()
def sample_db(tmp_path):
    db_path = tmp_path / "workout.db"
    schema = Path(__file__).resolve().parents[1] / "data" / "workout.sql"
    conn = sqlite3.connect(db_path)
    with open(schema) as f:
        conn.executescript(f.read())
    cur = conn.cursor()
    # metric types
    cur.execute(
        "INSERT INTO library_metric_types (name, input_type, source_type, input_timing, is_required, scope, description, is_user_created) "
        "VALUES ('Reps', 'int', 'manual_text', 'post_set', 1, 'set', '', 0)"
    )
    cur.execute(
        "INSERT INTO library_metric_types (name, input_type, source_type, input_timing, is_required, scope, description, is_user_created) "
        "VALUES ('Weight', 'float', 'manual_text', 'post_set', 0, 'set', '', 0)"
    )
    # exercises
    cur.execute("INSERT INTO library_exercises (name, description, is_user_created) VALUES ('Push Up', 'Upper body', 0)")
    cur.execute("INSERT INTO library_exercises (name, description, is_user_created) VALUES ('Bench Press', 'Chest', 0)")
    # exercise metrics
    cur.execute("INSERT INTO library_exercise_metrics (exercise_id, metric_type_id, position) VALUES (1, 1, 0)")
    cur.execute("INSERT INTO library_exercise_metrics (exercise_id, metric_type_id, position) VALUES (2, 1, 0)")
    cur.execute("INSERT INTO library_exercise_metrics (exercise_id, metric_type_id, position) VALUES (2, 2, 1)")
    # preset with one section and two exercises
    cur.execute("INSERT INTO preset_presets (name) VALUES ('Push Day')")
    cur.execute("INSERT INTO preset_sections (preset_id, name, position) VALUES (1, 'Main', 0)")
    cur.execute(
        "INSERT INTO preset_section_exercises (section_id, exercise_id, position, number_of_sets) VALUES (1, 1, 0, 2)"
    )
    cur.execute(
        "INSERT INTO preset_section_exercises (section_id, exercise_id, position, number_of_sets) VALUES (1, 2, 1, 3)"
    )
    conn.commit()
    conn.close()
    return db_path


def test_load_workout_presets(sample_db):
    presets = core.load_workout_presets(sample_db)
    assert core.WORKOUT_PRESETS == presets
    assert presets == [
        {
            "name": "Push Day",
            "exercises": [
                {"name": "Push Up", "sets": 2},
                {"name": "Bench Press", "sets": 3},
            ],
        }
    ]


def test_get_all_exercises(sample_db):
    names = core.get_all_exercises(sample_db)
    assert names == ["Bench Press", "Push Up"]
    names_flags = core.get_all_exercises(sample_db, include_user_created=True)
    assert names_flags == [("Bench Press", False), ("Push Up", False)]


def test_get_metrics_with_override(sample_db):
    # apply override before fetching
    core.set_section_exercise_metric_override(
        "Push Day",
        0,
        "Bench Press",
        "Weight",
        input_timing="pre_set",
        is_required=True,
        scope="set",
        db_path=sample_db,
    )
    metrics = core.get_metrics_for_exercise(
        "Bench Press", db_path=sample_db, preset_name="Push Day"
    )
    override = next(m for m in metrics if m["name"] == "Weight")
    assert override["input_timing"] == "pre_set"
    assert override["is_required"] is True


def test_add_and_remove_metric(sample_db):
    metric_id = core.add_metric_type(
        name="Tempo",
        input_type="int",
        source_type="manual_text",
        input_timing="post_set",
        scope="set",
        db_path=sample_db,
    )
    assert isinstance(metric_id, int)
    core.add_metric_to_exercise("Push Up", "Tempo", db_path=sample_db)
    metrics = [m["name"] for m in core.get_metrics_for_exercise("Push Up", db_path=sample_db)]
    assert "Tempo" in metrics
    core.remove_metric_from_exercise("Push Up", "Tempo", db_path=sample_db)
    metrics = [m["name"] for m in core.get_metrics_for_exercise("Push Up", db_path=sample_db)]
    assert "Tempo" not in metrics


def test_workout_session_progress(sample_db, monkeypatch):
    session = core.WorkoutSession("Push Day", db_path=sample_db, rest_duration=1)
    assert session.next_exercise_name() == "Push Up"
    assert session.next_exercise_display() == "Push Up set 1 of 2"
    # speed up time by patching time.time
    t = [session.start_time]

    def fake_time():
        t[0] += 1
        return t[0]

    monkeypatch.setattr(core.time, "time", fake_time)
    complete = False
    count = 0
    while not complete:
        complete = session.record_metrics({"Reps": 10})
        count += 1
    assert count == 5  # two sets push up + three sets bench press
    assert session.end_time is not None


def test_exercise_metric_override_table(sample_db):
    core.set_exercise_metric_override(
        "Bench Press",
        "Weight",
        input_timing="pre_workout",
        is_required=True,
        scope="exercise",
        db_path=sample_db,
    )
    metrics = core.get_metrics_for_exercise("Bench Press", db_path=sample_db)
    override = next(m for m in metrics if m["name"] == "Weight")
    assert override["input_timing"] == "pre_workout"
    assert override["is_required"] is True

    core.set_exercise_metric_override("Bench Press", "Weight", db_path=sample_db)
    metrics = core.get_metrics_for_exercise("Bench Press", db_path=sample_db)
    default = next(m for m in metrics if m["name"] == "Weight")
    assert default["input_timing"] == "post_set"
    assert default["is_required"] is False


def test_global_update_removes_override(sample_db):
    core.set_exercise_metric_override(
        "Bench Press",
        "Weight",
        input_timing="pre_workout",
        db_path=sample_db,
    )
    core.update_metric_type("Weight", input_timing="post_workout", db_path=sample_db)
    metrics = core.get_metrics_for_exercise("Bench Press", db_path=sample_db)
    override = next(m for m in metrics if m["name"] == "Weight")
    assert override["input_timing"] == "pre_workout"

    core.set_exercise_metric_override("Bench Press", "Weight", db_path=sample_db)
    metrics = core.get_metrics_for_exercise("Bench Press", db_path=sample_db)
    updated = next(m for m in metrics if m["name"] == "Weight")
    assert updated["input_timing"] == "post_workout"
