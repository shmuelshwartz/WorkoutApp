from backend import exercises
from backend.exercise import Exercise
import pytest


def test_exercise_load_modify_save(sample_db):
    ex = Exercise("Push-up", db_path=sample_db)
    assert ex.name == "Push-up"
    assert any(m["name"] == "Reps" for m in ex.metrics)
    ex.add_metric({
        "name": "Weight",
        "type": "float",
        "input_timing": "pre_set",
        "is_required": False,
        "scope": "set",
        "description": "",
    })
    exercises.save_exercise(ex)

    loaded = Exercise("Push-up", db_path=sample_db, is_user_created=True)
    names = [m["name"] for m in loaded.metrics]
    assert "Weight" in names
    assert loaded.is_user_created


def test_had_metric(sample_db):
    ex = Exercise("Push-up", db_path=sample_db)
    assert ex.had_metric("Reps")
    ex.add_metric({"name": "Weight"})
    assert not ex.had_metric("Weight")
    exercises.save_exercise(ex)
    loaded = Exercise("Push-up", db_path=sample_db, is_user_created=True)
    assert loaded.had_metric("Weight")


def test_add_metric_prevents_duplicates():
    ex = Exercise()
    assert ex.add_metric({"name": "Reps"})
    assert not ex.add_metric({"name": "Reps"})
    assert len(ex.metrics) == 1


def test_save_exercise_duplicate_metric(sample_db):
    ex = Exercise("Push-up", db_path=sample_db)
    # Force duplicate metrics directly to simulate a bad state.
    ex.metrics.append({"name": "Reps"})
    ex.metrics.append({"name": "Reps"})
    with pytest.raises(ValueError):
        exercises.save_exercise(ex)
