import sqlite3
import pytest
from backend import sessions
from backend.workout_session import WorkoutSession


def _complete_session(db_path):
    conn = sqlite3.connect(db_path)
    preset_id = conn.execute(
        "SELECT id FROM preset_presets WHERE name='Push Day'"
    ).fetchone()[0]
    metric_type_id = conn.execute(
        "SELECT id FROM library_metric_types WHERE name='Reps'"
    ).fetchone()[0]
    conn.execute(
        """
        INSERT INTO preset_preset_metrics
            (preset_id, library_metric_type_id, metric_name, metric_description,
             type, input_timing, scope, is_required, position)
        VALUES (?, ?, 'Session Reps', 'Total session reps', 'int', 'pre_workout', 'session', 1, 0)
        """,
        (preset_id, metric_type_id),
    )
    conn.commit()
    conn.close()

    session = WorkoutSession("Push Day", db_path=db_path, rest_duration=1)
    session.set_session_metrics({"Session Reps": 28})
    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 10})
    session.mark_set_completed()
    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 8})
    session.mark_set_completed()
    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 5, "Weight": 100, "Machine": "A"})
    session.mark_set_completed()
    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 5, "Weight": 100, "Machine": "A"})
    return session


def test_save_completed_session(sample_db):
    session = _complete_session(sample_db)
    sessions.save_completed_session(session, db_path=sample_db)
    conn = sqlite3.connect(sample_db)
    cur = conn.cursor()
    cur.execute("SELECT preset_id FROM session_sessions")
    assert cur.fetchone()[0] is not None
    cur.execute(
        "SELECT library_metric_type_id, preset_preset_metric_id, metric_description FROM session_session_metrics"
    )
    assert all(all(val is not None for val in row) for row in cur.fetchall())
    cur.execute(
        "SELECT library_exercise_id, preset_section_exercise_id, exercise_description FROM session_section_exercises"
    )
    assert all(row[0] is not None and row[1] is not None for row in cur.fetchall())
    cur.execute(
        "SELECT library_metric_type_id, preset_exercise_metric_id, metric_description FROM session_exercise_metrics"
    )
    assert all(row[0] is not None and row[1] is not None for row in cur.fetchall())
    cur.execute("SELECT started_at, ended_at, notes FROM session_exercise_sets")
    assert all(row[0] is not None and row[1] is not None and row[2] == '' for row in cur.fetchall())
    conn.close()


def test_save_session_validation(sample_db):
    session = WorkoutSession("Push Day", db_path=sample_db)
    with pytest.raises(ValueError):
        sessions.save_completed_session(session, db_path=sample_db)
