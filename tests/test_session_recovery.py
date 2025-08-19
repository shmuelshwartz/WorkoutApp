import json
from pathlib import Path

from backend.workout_session import WorkoutSession
from backend.sessions import save_completed_session


def test_session_state_roundtrip(tmp_path, sample_db):
    base = tmp_path / "session_recovery"
    session = WorkoutSession(
        "Push Day", db_path=sample_db, rest_duration=1, recovery_base=base
    )
    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 10})
    session.mark_set_completed()
    state = session.export_state()
    recovered = WorkoutSession.from_state(state)
    assert state == recovered.export_state()


def test_recovery_files_and_clear(tmp_path, sample_db):
    base = tmp_path / "session_recovery"
    session = WorkoutSession(
        "Push Day", db_path=sample_db, rest_duration=1, recovery_base=base
    )
    session.set_session_metrics({"Mood": "Good"})
    f1 = base.with_name(base.name + "_1.json")
    f2 = base.with_name(base.name + "_2.json")
    assert f1.exists() and f2.exists()
    with f1.open() as fh:
        data1 = json.load(fh)
    with f2.open() as fh:
        data2 = json.load(fh)
    assert data1 == data2 == session.export_state()

    # simulate loss of primary file and ensure backup loads
    f1.unlink()
    loaded = WorkoutSession.load_recovery_state(base)
    assert loaded == data2

    # saving the session clears any recovery files
    session.session_metrics = {}
    session.end_time = session.start_time + 1
    save_completed_session(session, db_path=sample_db)
    assert not f1.exists() and not f2.exists()
