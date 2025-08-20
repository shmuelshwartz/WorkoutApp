import core
from backend import presets
from backend.workout_session import WorkoutSession
import sqlite3
import pytest


def test_workout_session_flow(sample_db):
    loaded = presets.load_workout_presets(sample_db)
    assert any(p["name"] == "Push Day" for p in loaded)

    session = WorkoutSession("Push Day", db_path=sample_db, rest_duration=1)
    assert session.next_exercise_display() == "Push-up set 1 of 2"
    assert session.upcoming_exercise_display() == "Push-up set 2 of 2"

    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 10})
    session.mark_set_completed()
    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 8})
    session.mark_set_completed()

    assert session.next_exercise_display().startswith("Bench Press")
    before = session.rest_target_time
    session.adjust_rest_timer(5)
    assert session.rest_target_time - before >= 5

    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 5, "Weight": 100, "Machine": "A"})
    session.mark_set_completed()
    finished = session.record_metrics(session.current_exercise, session.current_set, {"Reps": 5, "Weight": 100, "Machine": "A"})
    assert finished

    summary = session.summary()
    assert "Push Day" in summary
    assert "Bench Press" in summary


def test_exercises_preloaded(sample_db):
    session = WorkoutSession("Push Day", db_path=sample_db)
    first = session.exercises
    second = session.exercises
    assert first is second
    assert all(data["exercise_info"] is not None for data in session.session_data)


def test_pre_set_metrics_flow(sample_db):
    session = WorkoutSession("Push Day", db_path=sample_db, rest_duration=1)

    # complete push-up sets to reach Bench Press
    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 10})
    session.mark_set_completed()
    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 8})
    session.mark_set_completed()

    assert session.next_exercise_name() == "Bench Press"
    # Bench Press requires the "Reps" metric pre-set
    assert not session.has_required_pre_set_metrics()
    session.set_pre_set_metrics({"Reps": 5})
    assert session.has_required_pre_set_metrics()
    session.record_metrics(session.current_exercise, session.current_set, {"Weight": 100})
    assert session.exercises[1]["results"][0]["metrics"] == {
        "Reps": 5,
        "Weight": 100,
        "Machine": None,
    }


def test_pre_set_metrics_require_selection(sample_db):
    session = WorkoutSession("Push Day", db_path=sample_db, rest_duration=1)

    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 10})
    session.mark_set_completed()
    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 8})
    session.mark_set_completed()

    assert session.next_exercise_name() == "Bench Press"
    session.set_pre_set_metrics({"Reps": ""})
    assert not session.has_required_pre_set_metrics()
    session.set_pre_set_metrics({"Reps": 5})
    assert session.has_required_pre_set_metrics()


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

    session = WorkoutSession("Push Day", db_path=sample_db)
    assert session.rest_duration == 10

    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 10})
    session.mark_set_completed()
    assert session.rest_duration == 10

    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 8})
    session.mark_set_completed()
    assert session.rest_duration == 30


def test_required_post_set_metrics(sample_db):
    session = WorkoutSession("Push Day", db_path=sample_db, rest_duration=1)
    session.mark_set_completed()
    assert not session.has_required_post_set_metrics()
    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 10})
    assert session.has_required_post_set_metrics()


def test_mark_set_completed_time_adjustment(sample_db, monkeypatch):
    session = WorkoutSession("Push Day", db_path=sample_db, rest_duration=30)
    session.preset_snapshot[0]["rest"] = 30
    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 10})
    monkeypatch.setattr(core.time, "time", lambda: 165.0)
    session.mark_set_completed(adjust_seconds=-5)
    assert session.last_set_time == pytest.approx(160.0)
    assert session.rest_target_time == pytest.approx(190.0)


def test_update_set_duration_updates_rest(sample_db, monkeypatch):
    monkeypatch.setattr(core.time, "time", lambda: 100.0)
    session = WorkoutSession("Push Day", db_path=sample_db, rest_duration=30)
    start = session.current_set_start_time
    session.mark_set_completed()
    session.update_set_duration(session.current_exercise, session.current_set, 42.0)
    assert session.last_set_time == pytest.approx(start + 42.0)
    assert session.rest_target_time == pytest.approx(start + 42.0 + session.rest_duration)


def test_undo_last_set_restores_metrics_and_timer(sample_db, monkeypatch):
    session = WorkoutSession("Push Day", db_path=sample_db, rest_duration=1)
    start = session.current_set_start_time

    monkeypatch.setattr(core.time, "time", lambda: start + 5)
    session.mark_set_completed()
    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 10})

    monkeypatch.setattr(core.time, "time", lambda: start + 6)
    assert session.undo_last_set()
    assert session.current_exercise == 0
    assert session.current_set == 0
    assert session.exercises[0]["results"] == []
    assert session.pending_pre_set_metrics == {(0, 0): {"Reps": 10}}
    assert session.current_set_start_time == start
    assert session.resume_from_last_start is True


def test_undo_set_start_returns_to_rest(sample_db, monkeypatch):
    session = WorkoutSession("Push Day", db_path=sample_db, rest_duration=10)
    start = session.current_set_start_time

    # simulate beginning a set 5 seconds later
    monkeypatch.setattr(core.time, "time", lambda: start + 5)
    session.current_set_start_time = start + 5

    session.undo_set_start()

    assert session.current_set_start_time == start
    assert session.resume_from_last_start is False
    assert session.rest_target_time == start + session.rest_duration


def test_edit_set_overwrites_in_place(sample_db):
    session = WorkoutSession("Push Day", db_path=sample_db, rest_duration=1)
    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 10})
    session.mark_set_completed()
    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 8})

    session.edit_set_metrics(0, 0, {"Reps": 12})
    ex = session.exercises[0]
    assert len(ex["results"]) == 2
    assert ex["results"][0]["metrics"]["Reps"] == 12
    assert ex["results"][1]["metrics"]["Reps"] == 8


def test_apply_edited_preset_preserves_metrics(sample_db):
    session = WorkoutSession("Push Day", db_path=sample_db, rest_duration=1)
    # record first set of Push-up
    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 10})
    session.mark_set_completed()

    # build sections from current session and swap first two exercises
    sections = []
    for s_idx, name in enumerate(session.section_names):
        start = session.section_starts[s_idx]
        end = (
            session.section_starts[s_idx + 1]
            if s_idx + 1 < len(session.section_starts)
            else len(session.preset_snapshot)
        )
        ex_list = []
        for ex in session.preset_snapshot[start:end]:
            ex_list.append(
                {
                    "name": ex["name"],
                    "sets": ex["sets"],
                    "rest": ex["rest"],
                    "library_id": ex.get("library_exercise_id"),
                    "id": ex.get("preset_section_exercise_id"),
                }
            )
        sections.append({"name": name, "exercises": ex_list})

    # swap first two exercises
    sections[0]["exercises"][0], sections[0]["exercises"][1] = (
        sections[0]["exercises"][1],
        sections[0]["exercises"][0],
    )
    session.apply_edited_preset(sections)

    # Push-up moved to second position with its recorded metrics intact
    assert session.exercises[1]["name"] == "Push-up"
    assert session.exercises[1]["results"][0]["metrics"]["Reps"] == 10
    # Bench Press remains first with its metric definitions
    assert session.exercises[0]["name"] == "Bench Press"
    metric_names = [m["name"] for m in session.exercises[0]["metric_defs"]]
    assert "Reps" in metric_names


def test_skip_exercise_and_undo(sample_db):
    session = WorkoutSession("Push Day", db_path=sample_db, rest_duration=1)
    original_sets = session.preset_snapshot[0]["sets"]
    session.record_metrics(session.current_exercise, session.current_set, {"Reps": 10})
    session.mark_set_completed()
    assert session.current_exercise == 0 and session.current_set == 1
    assert session.skip_exercise()
    assert session.current_exercise == 1 and session.current_set == 0
    assert session.preset_snapshot[0]["sets"] == 1
    assert session.session_data[0]["skipped_sets"] == original_sets - 1
    assert session.undo_last_set()
    assert session.current_exercise == 0 and session.current_set == 1
    assert session.preset_snapshot[0]["sets"] == original_sets
    assert "skipped_sets" not in session.session_data[0]
    assert session.resume_from_last_start is False


def test_skip_last_exercise_noop(sample_db):
    session = WorkoutSession("Push Day", db_path=sample_db, rest_duration=1)
    assert session.skip_exercise()
    assert not session.skip_exercise()
