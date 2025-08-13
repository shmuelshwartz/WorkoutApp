import core
from backend import exercises
from backend.exercise import Exercise


def test_get_all_exercises(sample_db):
    names = exercises.get_all_exercises(sample_db)
    assert names == ["Bench Press", "Push-up"]

    ex = Exercise(db_path=sample_db)
    ex.name = "Custom"
    ex.add_metric({
        "name": "Reps",
        "type": "int",
        "input_timing": "post_set",
        "is_required": True,
        "scope": "set",
        "description": "",
    })
    exercises.save_exercise(ex)

    all_with_flags = exercises.get_all_exercises(sample_db, include_user_created=True)
    assert ("Custom", True) in all_with_flags


def test_get_metrics_for_exercise(sample_db):
    default = core.get_metrics_for_exercise("Bench Press", db_path=sample_db)
    override = core.get_metrics_for_exercise("Bench Press", preset_name="Push Day", db_path=sample_db)

    def get_timing(metrics, name):
        return next(m for m in metrics if m["name"] == name)["input_timing"]

    assert get_timing(default, "Reps") == "post_set"
    assert get_timing(override, "Reps") == "pre_set"
    assert core.get_metrics_for_exercise("Unknown", db_path=sample_db) == []


def test_load_workout_presets(sample_db):
    presets = core.load_workout_presets(sample_db)
    assert presets == [
        {
            "name": "Push Day",
            "exercises": [
                {"name": "Push-up", "sets": 2, "rest": 120},
                {"name": "Bench Press", "sets": 2, "rest": 120},
            ],
        }
    ]
