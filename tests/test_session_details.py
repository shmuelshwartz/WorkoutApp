import sqlite3

from backend.sessions import save_completed_session, get_session_details
from backend.workout_session import WorkoutSession


def _prepare_session(db_path: str) -> WorkoutSession:
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
    session.record_metrics(
        session.current_exercise,
        session.current_set,
        {"Reps": 5, "Weight": 100, "Machine": "A"},
    )
    session.mark_set_completed()
    session.record_metrics(
        session.current_exercise,
        session.current_set,
        {"Reps": 5, "Weight": 100, "Machine": "A"},
    )
    return session


def test_get_session_details(sample_db):
    session = _prepare_session(sample_db)
    save_completed_session(session, db_path=sample_db)
    details = get_session_details(session.start_time, db_path=sample_db)
    assert details["preset_name"] == "Push Day"
    assert any(m["name"] == "Session Reps" for m in details["metrics"])
    assert details["exercises"]
    first_ex = details["exercises"][0]
    assert first_ex["sets"]
    first_set = first_ex["sets"][0]
    assert any(m["name"] == "Reps" for m in first_set["metrics"])
