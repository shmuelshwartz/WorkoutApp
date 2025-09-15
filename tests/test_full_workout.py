import sqlite3
from pathlib import Path

from backend import exercises, metrics, sessions
from backend.exercise import Exercise
from backend.preset_editor import PresetEditor
from backend.workout_session import WorkoutSession


def _init_db(db_path: Path) -> None:
    """Create an empty workout database at ``db_path`` using the bundled schema."""
    schema = Path(__file__).resolve().parents[1] / "data" / "workout_schema.sql"
    conn = sqlite3.connect(db_path)
    with open(schema, "r", encoding="utf-8") as fh:
        conn.executescript(fh.read())
    conn.commit()
    conn.close()


def test_full_workout_flow(tmp_path):
    """Simulate a complete workout using the real backend helpers."""
    db_path = tmp_path / "workout.db"
    _init_db(db_path)

    # ------------------------------------------------------------------
    # Stub metric types
    # ------------------------------------------------------------------
    metrics.add_metric_type(
        "Reps", "int", "post_set", "set", is_required=True, db_path=db_path
    )
    metrics.add_metric_type(
        "Weight", "float", "pre_set", "set", is_required=False, db_path=db_path
    )
    metrics.add_metric_type(
        "Notes", "str", "post_set", "set", is_required=False, db_path=db_path
    )

    # ------------------------------------------------------------------
    # Stub exercises with attached metrics
    # ------------------------------------------------------------------
    bench = Exercise(db_path=db_path)
    bench.name = "Bench Press"
    bench.description = "Bench Press exercise"
    bench.add_metric(
        {
            "name": "Reps",
            "type": "int",
            "input_timing": "post_set",
            "is_required": True,
            "scope": "set",
            "description": "",
        }
    )
    bench.add_metric(
        {
            "name": "Weight",
            "type": "float",
            "input_timing": "pre_set",
            "is_required": False,
            "scope": "set",
            "description": "",
        }
    )
    exercises.save_exercise(bench)

    pull = Exercise(db_path=db_path)
    pull.name = "Pull-up"
    pull.description = "Pull-up exercise"
    pull.add_metric(
        {
            "name": "Reps",
            "type": "int",
            "input_timing": "post_set",
            "is_required": True,
            "scope": "set",
            "description": "",
        }
    )
    pull.add_metric(
        {
            "name": "Notes",
            "type": "str",
            "input_timing": "post_set",
            "is_required": False,
            "scope": "set",
            "description": "",
        }
    )
    exercises.save_exercise(pull)

    # ------------------------------------------------------------------
    # Preset creation
    # ------------------------------------------------------------------
    editor = PresetEditor(db_path=db_path)
    editor.preset_name = "Flow Test"
    sec = editor.add_section("Main")
    editor.add_exercise(sec, "Bench Press", sets=2)
    editor.add_exercise(sec, "Pull-up", sets=2)
    editor.save()
    editor.close()

    # ------------------------------------------------------------------
    # Session simulation
    # ------------------------------------------------------------------
    session = WorkoutSession("Flow Test", db_path=db_path, rest_duration=1)

    for weight, reps in [(100, 10), (110, 8)]:
        session.set_pre_set_metrics({"Weight": weight})
        finished = session.record_metrics(
            session.current_exercise, session.current_set, {"Reps": reps}
        )
        if not finished:
            session.mark_set_completed()

    for reps, note in [(8, "good"), (6, "tired")]:
        finished = session.record_metrics(
            session.current_exercise,
            session.current_set,
            {"Reps": reps, "Notes": note},
        )
        if not finished:
            session.mark_set_completed()

    sessions.save_completed_session(session, db_path=db_path)

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Exercises
    cur.execute("SELECT name FROM library_exercises WHERE deleted=0 ORDER BY name")
    assert [r[0] for r in cur.fetchall()] == ["Bench Press", "Pull-up"]

    # Metric types and linkage
    cur.execute("SELECT name FROM library_metric_types WHERE deleted=0 ORDER BY name")
    assert [r[0] for r in cur.fetchall()] == ["Notes", "Reps", "Weight"]
    cur.execute(
        """
        SELECT e.name, mt.name
          FROM library_exercise_metrics em
          JOIN library_exercises e ON em.exercise_id = e.id
          JOIN library_metric_types mt ON em.metric_type_id = mt.id
         WHERE em.deleted = 0
         ORDER BY e.name, mt.name
        """
    )
    assert cur.fetchall() == [
        ("Bench Press", "Reps"),
        ("Bench Press", "Weight"),
        ("Pull-up", "Notes"),
        ("Pull-up", "Reps"),
    ]

    # Preset structure
    cur.execute(
        """
        SELECT se.exercise_name, se.number_of_sets
          FROM preset_section_exercises se
          JOIN preset_preset_sections ps ON se.section_id = ps.id
          JOIN preset_presets p ON ps.preset_id = p.id
         WHERE p.name = ? AND se.deleted = 0
         ORDER BY se.position
        """,
        ("Flow Test",),
    )
    assert cur.fetchall() == [("Bench Press", 2), ("Pull-up", 2)]
    cur.execute(
        """
        SELECT se.exercise_name, pem.metric_name
          FROM preset_exercise_metrics pem
          JOIN preset_section_exercises se ON pem.section_exercise_id = se.id
          JOIN preset_preset_sections ps ON se.section_id = ps.id
          JOIN preset_presets p ON ps.preset_id = p.id
         WHERE p.name = ? AND pem.deleted = 0
         ORDER BY se.exercise_name, pem.metric_name
        """,
        ("Flow Test",),
    )
    assert cur.fetchall() == [
        ("Bench Press", "Reps"),
        ("Bench Press", "Weight"),
        ("Pull-up", "Notes"),
        ("Pull-up", "Reps"),
    ]

    conn.close()

    # Session details
    details = sessions.get_session_details(session.start_time, db_path=db_path)
    assert [ex["name"] for ex in details["exercises"]] == ["Bench Press", "Pull-up"]
    bench_sets = details["exercises"][0]["sets"]
    assert bench_sets[0]["metrics"] == [
        {"name": "Reps", "value": "10"},
        {"name": "Weight", "value": "100"},
    ]
    assert bench_sets[1]["metrics"] == [
        {"name": "Reps", "value": "8"},
        {"name": "Weight", "value": "110"},
    ]
    pull_sets = details["exercises"][1]["sets"]
    assert pull_sets[0]["metrics"] == [
        {"name": "Reps", "value": "8"},
        {"name": "Notes", "value": "good"},
    ]
    assert pull_sets[1]["metrics"] == [
        {"name": "Reps", "value": "6"},
        {"name": "Notes", "value": "tired"},
    ]

    print("Workout simulation completed successfully")
