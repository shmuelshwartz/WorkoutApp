import sqlite3
import pytest
import core


def _complete_session(db_path):
    session = core.WorkoutSession("Push Day", db_path=db_path, rest_duration=1)
    session.record_metrics({"Reps": 10})
    session.mark_set_completed()
    session.record_metrics({"Reps": 8})
    session.mark_set_completed()
    session.record_metrics({"Reps": 5, "Weight": 100, "Machine": "A"})
    session.mark_set_completed()
    session.record_metrics({"Reps": 5, "Weight": 100, "Machine": "A"})
    return session


def test_save_completed_session(sample_db):
    session = _complete_session(sample_db)
    core.save_completed_session(session, db_path=sample_db)
    conn = sqlite3.connect(sample_db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM session_sessions")
    assert cur.fetchone()[0] == 1
    cur.execute("SELECT COUNT(*) FROM session_exercise_sets")
    assert cur.fetchone()[0] == 4
    conn.close()


def test_save_session_validation(sample_db):
    session = core.WorkoutSession("Push Day", db_path=sample_db)
    with pytest.raises(ValueError):
        core.save_completed_session(session, db_path=sample_db)
