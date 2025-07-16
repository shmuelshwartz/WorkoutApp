import core


def test_exercise_load_modify_save(sample_db):
    ex = core.Exercise("Push-up", db_path=sample_db)
    assert ex.name == "Push-up"
    assert any(m["name"] == "Reps" for m in ex.metrics)
    ex.add_metric({
        "name": "Weight",
        "input_type": "float",
        "source_type": "manual_text",
        "input_timing": "pre_set",
        "is_required": False,
        "scope": "set",
        "description": "",
    })
    core.save_exercise(ex)

    loaded = core.Exercise("Push-up", db_path=sample_db, is_user_created=True)
    names = [m["name"] for m in loaded.metrics]
    assert "Weight" in names
    assert loaded.is_user_created
