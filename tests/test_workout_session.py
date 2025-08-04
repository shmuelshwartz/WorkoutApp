import core
import sqlite3


def test_workout_session_flow(sample_db):
    presets = core.load_workout_presets(sample_db)
    assert any(p["name"] == "Push Day" for p in presets)

    session = core.WorkoutSession("Push Day", db_path=sample_db, rest_duration=1)
    assert session.next_exercise_display() == "Push-up set 1 of 2"
    assert session.upcoming_exercise_display() == "Push-up set 2 of 2"

    session.record_metrics({"Reps": 10})
    session.mark_set_completed()
    session.record_metrics({"Reps": 8})
    session.mark_set_completed()

    assert session.next_exercise_display().startswith("Bench Press")
    before = session.rest_target_time
    session.adjust_rest_timer(5)
    assert session.rest_target_time - before >= 5

    session.record_metrics({"Reps": 5, "Weight": 100, "Machine": "A"})
    session.mark_set_completed()
    finished = session.record_metrics({"Reps": 5, "Weight": 100, "Machine": "A"})
    assert finished

    summary = session.summary()
    assert "Push Day" in summary
    assert "Bench Press" in summary


def test_pre_set_metrics_flow(sample_db):
    session = core.WorkoutSession("Push Day", db_path=sample_db, rest_duration=1)

    # complete push-up sets to reach Bench Press
    session.record_metrics({"Reps": 10})
    session.mark_set_completed()
    session.record_metrics({"Reps": 8})
    session.mark_set_completed()

    assert session.next_exercise_name() == "Bench Press"
    # Bench Press requires the "Reps" metric pre-set
    assert not session.has_required_pre_set_metrics()
    session.set_pre_set_metrics({"Reps": 5})
    assert session.has_required_pre_set_metrics()
    session.record_metrics({"Weight": 100})
    assert session.exercises[1]["results"][0]["metrics"] == {"Reps": 5, "Weight": 100}


def test_rest_time_uses_next_exercise(sample_db):
    conn = sqlite3.connect(sample_db)
    conn.execute(
        "UPDATE preset_section_exercises SET rest_time=10 WHERE exercise_name='Push-up'"
    )
    conn.execute(
        "UPDATE preset_section_exercises SET rest_time=30 WHERE exercise_name='Bench Press'"
    )
    conn.commit()
    conn.close()

    session = core.WorkoutSession("Push Day", db_path=sample_db)
    assert session.rest_duration == 10

    session.record_metrics({"Reps": 10})
    session.mark_set_completed()
    assert session.rest_duration == 10

    session.record_metrics({"Reps": 8})
    session.mark_set_completed()
    assert session.rest_duration == 30


def test_required_post_set_metrics(sample_db):
    session = core.WorkoutSession("Push Day", db_path=sample_db, rest_duration=1)
    session.mark_set_completed()
    assert not session.has_required_post_set_metrics()
    session.record_metrics({"Reps": 10})
    assert session.has_required_post_set_metrics()
