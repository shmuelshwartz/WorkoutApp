import sqlite3
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core
from backend.exercise import Exercise
from backend.workout_session import WorkoutSession



@pytest.fixture()
def sample_db(tmp_path):
    db_path = tmp_path / "workout.db"
    schema = Path(__file__).resolve().parents[1] / "data" / "workout_schema.sql"
    conn = sqlite3.connect(db_path)
    with open(schema) as f:
        conn.executescript(f.read())
    cur = conn.cursor()
    # metric types
    cur.execute(
        "INSERT INTO library_metric_types (name, type, input_timing, is_required, scope, description, is_user_created) "
        "VALUES ('Reps', 'int', 'post_set', 1, 'set', '', 0)"
    )
    cur.execute(
        "INSERT INTO library_metric_types (name, type, input_timing, is_required, scope, description, is_user_created) "
        "VALUES ('Weight', 'float', 'post_set', 0, 'set', '', 0)"
    )
    # exercises
    cur.execute(
        "INSERT INTO library_exercises (name, description, is_user_created) VALUES ('Push Up', 'Upper body', 0)"
    )
    cur.execute(
        "INSERT INTO library_exercises (name, description, is_user_created) VALUES ('Bench Press', 'Chest', 0)"
    )
    # exercise metrics
    cur.execute(
        "INSERT INTO library_exercise_metrics (exercise_id, metric_type_id, position) VALUES (1, 1, 0)"
    )
    cur.execute(
        "INSERT INTO library_exercise_metrics (exercise_id, metric_type_id, position) VALUES (2, 1, 0)"
    )
    cur.execute(
        "INSERT INTO library_exercise_metrics (exercise_id, metric_type_id, position) VALUES (2, 2, 1)"
    )
    # preset with one section and two exercises
    cur.execute("INSERT INTO preset_presets (name) VALUES ('Push Day')")
    cur.execute(
        "INSERT INTO preset_preset_sections (preset_id, name, position) VALUES (1, 'Main', 0)"
    )
    cur.execute(
        """
        INSERT INTO preset_section_exercises
            (section_id, exercise_name, exercise_description, position, number_of_sets, library_exercise_id)
        VALUES (1, 'Push Up', '', 0, 2, 1)
        """
    )
    cur.execute(
        """
        INSERT INTO preset_section_exercises
            (section_id, exercise_name, exercise_description, position, number_of_sets, library_exercise_id)
        VALUES (1, 'Bench Press', '', 1, 3, 2)
        """
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
                {"name": "Push Up", "sets": 2, "rest": 120},
                {"name": "Bench Press", "sets": 3, "rest": 120},
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
        mtype="int",
        input_timing="post_set",
        scope="set",
        db_path=sample_db,
    )
    assert isinstance(metric_id, int)
    core.add_metric_to_exercise("Push Up", "Tempo", db_path=sample_db)
    metrics = [
        m["name"] for m in core.get_metrics_for_exercise("Push Up", db_path=sample_db)
    ]
    assert "Tempo" in metrics
    core.remove_metric_from_exercise("Push Up", "Tempo", db_path=sample_db)
    metrics = [
        m["name"] for m in core.get_metrics_for_exercise("Push Up", db_path=sample_db)
    ]
    assert "Tempo" not in metrics


def test_workout_session_progress(sample_db, monkeypatch):
    session = WorkoutSession("Push Day", db_path=sample_db, rest_duration=1)
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
        complete = session.record_metrics(session.current_exercise, session.current_set, {"Reps": 10})
        count += 1
    assert count == 5  # two sets push up + three sets bench press
    assert session.end_time is not None


def test_exercise_metric_override_table(sample_db):
    core.set_exercise_metric_override(
        "Bench Press",
        "Weight",
        input_timing="pre_session",
        is_required=True,
        scope="exercise",
        db_path=sample_db,
    )
    metrics = core.get_metrics_for_exercise("Bench Press", db_path=sample_db)
    override = next(m for m in metrics if m["name"] == "Weight")
    assert override["input_timing"] == "pre_session"
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
        input_timing="pre_session",
        db_path=sample_db,
    )
    core.update_metric_type("Weight", input_timing="post_session", db_path=sample_db)
    metrics = core.get_metrics_for_exercise("Bench Press", db_path=sample_db)
    override = next(m for m in metrics if m["name"] == "Weight")
    assert override["input_timing"] == "pre_session"

    core.set_exercise_metric_override("Bench Press", "Weight", db_path=sample_db)
    metrics = core.get_metrics_for_exercise("Bench Press", db_path=sample_db)
    updated = next(m for m in metrics if m["name"] == "Weight")
    assert updated["input_timing"] == "post_session"


def test_override_with_user_flag(sample_db):
    conn = sqlite3.connect(sample_db)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO library_exercises (name, description, is_user_created) VALUES ('Bench Press', 'Alt', 1)"
    )
    user_ex_id = cur.lastrowid
    cur.execute(
        "SELECT metric_type_id, position FROM library_exercise_metrics WHERE exercise_id = 2"
    )
    for metric_type_id, pos in cur.fetchall():
        cur.execute(
            "INSERT INTO library_exercise_metrics (exercise_id, metric_type_id, position) VALUES (?, ?, ?)",
            (user_ex_id, metric_type_id, pos),
        )
    conn.commit()
    conn.close()

    core.set_exercise_metric_override(
        "Bench Press",
        "Weight",
        input_timing="pre_session",
        is_user_created=True,
        db_path=sample_db,
    )

    metrics_user = core.get_metrics_for_exercise(
        "Bench Press", db_path=sample_db, is_user_created=True
    )
    user_override = next(m for m in metrics_user if m["name"] == "Weight")
    assert user_override["input_timing"] == "pre_session"

    metrics_default = core.get_metrics_for_exercise(
        "Bench Press", db_path=sample_db, is_user_created=False
    )
    default_metric = next(m for m in metrics_default if m["name"] == "Weight")
    assert default_metric["input_timing"] == "post_set"


def test_delete_metric_type(sample_db):
    metric_id = core.add_metric_type(
        name="Tempo",
        mtype="int",
        input_timing="post_set",
        scope="set",
        db_path=sample_db,
    )
    assert isinstance(metric_id, int)
    assert core.delete_metric_type("Tempo", db_path=sample_db, is_user_created=True)
    metrics = core.get_all_metric_types(sample_db, include_user_created=True)
    assert all(m["name"] != "Tempo" for m in metrics)
    assert (
        core.delete_metric_type("Tempo", db_path=sample_db, is_user_created=True)
        is False
    )


def test_delete_metric_type_in_use_by_preset_exercise(sample_db):
    mt_id = core.add_metric_type(
        name="Velocity",
        mtype="float",
        input_timing="post_set",
        scope="set",
        db_path=sample_db,
    )

    conn = sqlite3.connect(sample_db)
    cur = conn.cursor()
    bench_se_id = cur.execute(
        "SELECT id FROM preset_section_exercises WHERE exercise_name = 'Bench Press'"
    ).fetchone()[0]
    cur.execute(
        """
        INSERT INTO preset_exercise_metrics
            (section_exercise_id, metric_name, type, input_timing, is_required, scope, library_metric_type_id)
        VALUES (?, 'Velocity', 'float', 'post_set', 0, 'set', ?)
        """,
        (bench_se_id, mt_id),
    )
    conn.commit()
    conn.close()

    with pytest.raises(ValueError):
        core.delete_metric_type("Velocity", db_path=sample_db, is_user_created=True)


def test_find_presets_and_apply_changes(sample_db):
    names = core.find_presets_using_exercise("Push Up", db_path=sample_db)
    assert names == ["Push Day"]

    ex = Exercise("Push Up", db_path=sample_db, is_user_created=False)
    ex.add_metric(
        {
            "name": "Weight",
            "type": "float",
            "input_timing": "post_set",
            "is_required": False,
            "scope": "set",
        }
    )
    core.add_metric_to_exercise("Push Up", "Weight", db_path=sample_db)

    conn = sqlite3.connect(sample_db)
    before = {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in [
            "session_sessions",
            "session_session_sections",
            "session_section_exercises",
            "session_exercise_sets",
            "session_exercise_metrics",
        ]
    }
    conn.close()

    core.apply_exercise_changes_to_presets(ex, ["Push Day"], db_path=sample_db)

    conn = sqlite3.connect(sample_db)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT pem.metric_name FROM preset_exercise_metrics pem
        JOIN preset_section_exercises se ON pem.section_exercise_id = se.id
        JOIN preset_preset_sections s ON se.section_id = s.id
        JOIN preset_presets p ON s.preset_id = p.id
        WHERE p.name = 'Push Day' AND se.library_exercise_id = 1 AND pem.deleted = 0
        ORDER BY pem.position
        """
    )
    names = [r[0] for r in cur.fetchall()]
    after = {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in [
            "session_sessions",
            "session_session_sections",
            "session_section_exercises",
            "session_exercise_sets",
            "session_exercise_metrics",
        ]
    }
    conn.close()

    assert "Weight" in names
    assert before == after
