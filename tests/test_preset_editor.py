import shutil
import sqlite3
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import PresetEditor, DEFAULT_SETS_PER_EXERCISE, DEFAULT_REST_DURATION


@pytest.fixture
def db_copy(tmp_path):
    """Return a temporary empty database using the bundled schema."""
    dst = tmp_path / "workout.db"
    schema = Path(__file__).resolve().parents[1] / "data" / "workout.sql"
    conn = sqlite3.connect(dst)
    with open(schema, "r", encoding="utf-8") as fh:
        conn.executescript(fh.read())
    # minimal exercise for tests
    conn.execute(
        "INSERT INTO library_exercises (name, description, is_user_created) VALUES ('Push ups', '', 0)"
    )
    conn.commit()
    conn.close()
    return dst


@pytest.fixture
def db_with_preset(db_copy):
    """Create a preset with one section and one exercise for loading tests."""
    conn = sqlite3.connect(db_copy)
    cur = conn.cursor()
    cur.execute("INSERT INTO preset_presets (name) VALUES (?)", ("Test Preset",))
    preset_id = cur.lastrowid
    cur.execute(
        "INSERT INTO preset_sections (preset_id, name, position) VALUES (?, ?, 0)",
        (preset_id, "Warmup"),
    )
    section_id = cur.lastrowid
    # Use an existing exercise from the sample DB
    cur.execute("SELECT id FROM library_exercises WHERE name = 'Push ups'")
    ex_id = cur.fetchone()[0]
    cur.execute(
        """
        INSERT INTO preset_section_exercises
            (section_id, exercise_name, exercise_description, position, number_of_sets, library_exercise_id)
        VALUES (?, 'Push ups', '', 0, 3, ?)
        """,
        (section_id, ex_id),
    )
    conn.commit()
    conn.close()
    return db_copy


def test_add_and_remove_section(db_copy):
    editor = PresetEditor(db_path=db_copy)
    idx1 = editor.add_section("Warmup")
    idx2 = editor.add_section("Main")
    assert idx1 == 0
    assert idx2 == 1
    assert [s["name"] for s in editor.sections] == ["Warmup", "Main"]
    editor.remove_section(0)
    assert len(editor.sections) == 1
    assert editor.sections[0]["name"] == "Main"
    editor.close()


def test_add_exercise_success(db_copy):
    editor = PresetEditor(db_path=db_copy)
    editor.add_section("Warmup")
    ex = editor.add_exercise(0, "Push ups", sets=4)
    assert ex == {"name": "Push ups", "sets": 4, "rest": DEFAULT_REST_DURATION}
    assert editor.sections[0]["exercises"] == [ex]
    editor.close()


def test_add_exercise_invalid_index(db_copy):
    editor = PresetEditor(db_path=db_copy)
    editor.add_section("Warmup")
    with pytest.raises(IndexError):
        editor.add_exercise(2, "Push ups")
    editor.close()


def test_add_exercise_unknown_exercise(db_copy):
    editor = PresetEditor(db_path=db_copy)
    editor.add_section("Warmup")
    with pytest.raises(ValueError):
        editor.add_exercise(0, "DoesNotExist")
    editor.close()


def test_to_dict_after_modifications(db_copy):
    editor = PresetEditor(db_path=db_copy)
    editor.preset_name = "My Preset"
    editor.add_section("Warmup")
    editor.add_exercise(0, "Push ups")
    expected = {
        "name": "My Preset",
        "sections": [
            {
                "name": "Warmup",
                "exercises": [
                    {
                        "name": "Push ups",
                        "sets": DEFAULT_SETS_PER_EXERCISE,
                        "rest": DEFAULT_REST_DURATION,
                    }
                ],
            }
        ],
    }
    assert editor.to_dict() == expected
    editor.close()


def test_load_existing_preset(db_with_preset):
    editor = PresetEditor("Test Preset", db_path=db_with_preset)
    assert editor.preset_name == "Test Preset"
    assert len(editor.sections) == 1
    sec = editor.sections[0]
    assert sec["name"] == "Warmup"
    assert sec["exercises"] == [{"name": "Push ups", "sets": 3, "rest": 120}]
    editor.close()


def test_close_closes_connection(db_copy):
    editor = PresetEditor(db_path=db_copy)
    editor.close()
    with pytest.raises(sqlite3.ProgrammingError):
        editor.conn.execute("SELECT 1")


def test_save_new_preset(db_copy):
    editor = PresetEditor(db_path=db_copy)
    editor.preset_name = "My Preset"
    editor.add_section("Warmup")
    editor.add_exercise(0, "Push ups", sets=4)
    editor.save()
    conn = sqlite3.connect(db_copy)
    cur = conn.cursor()
    cur.execute("SELECT name FROM preset_presets")
    assert cur.fetchone()[0] == "My Preset"
    cur.execute("SELECT name FROM preset_sections")
    assert cur.fetchone()[0] == "Warmup"
    cur.execute("SELECT exercise_name, number_of_sets, rest_time FROM preset_section_exercises")
    assert cur.fetchone() == ("Push ups", 4, 120)
    conn.close()
    editor.close()


def test_save_existing_preset(db_with_preset):
    editor = PresetEditor("Test Preset", db_path=db_with_preset)
    editor.sections[0]["exercises"][0]["sets"] = 5
    editor.save()
    conn = sqlite3.connect(db_with_preset)
    cur = conn.cursor()
    cur.execute("SELECT number_of_sets, rest_time FROM preset_section_exercises")
    assert cur.fetchone() == (5, 120)
    conn.close()
    editor.close()


def test_save_duplicate_name(db_with_preset):
    editor = PresetEditor(db_path=db_with_preset)
    editor.preset_name = "Test Preset"
    with pytest.raises(ValueError):
        editor.save()
    editor.close()


def test_save_preserves_metric_overrides(db_copy):
    conn = sqlite3.connect(db_copy)
    cur = conn.cursor()

    # create a metric type and associate with the exercise
    cur.execute(
        """
        INSERT INTO library_metric_types
            (name, input_type, source_type, input_timing, is_required, scope, description, is_user_created)
        VALUES ('Reps', 'int', 'manual_text', 'post_set', 0, 'set', '', 0)
        """
    )
    mt_id = cur.lastrowid
    ex_id = cur.execute(
        "SELECT id FROM library_exercises WHERE name='Push ups'"
    ).fetchone()[0]
    cur.execute(
        "INSERT INTO library_exercise_metrics (exercise_id, metric_type_id, position) VALUES (?, ?, 0)",
        (ex_id, mt_id),
    )
    em_id = cur.lastrowid

    # apply override for this metric
    cur.execute(
        """
        UPDATE library_exercise_metrics
           SET input_type = 'int',
               source_type = 'manual_text',
               input_timing = 'pre_workout',
               is_required = 1,
               scope = 'set'
         WHERE id = ?
        """,
        (em_id,),
    )
    conn.commit()
    conn.close()

    editor = PresetEditor(db_path=db_copy)
    editor.preset_name = "Override Preset"
    editor.add_section("Warmup")
    editor.add_exercise(0, "Push ups")
    editor.save()

    conn = sqlite3.connect(db_copy)
    cur = conn.cursor()
    cur.execute(
        "SELECT metric_name, input_timing, is_required, scope FROM preset_section_exercise_metrics"
    )
    result = cur.fetchone()
    conn.close()
    editor.close()

    assert result == ("Reps", "pre_workout", 1, "set")


def test_save_missing_exercise_fails(db_copy):
    editor = PresetEditor(db_path=db_copy)
    editor.preset_name = "My Preset"
    editor.add_section("Warmup")
    editor.add_exercise(0, "Push ups")
    editor.sections[0]["exercises"][0]["name"] = "DoesNotExist"
    with pytest.raises(ValueError):
        editor.save()
    editor.close()


def test_is_modified_tracking(db_copy):
    editor = PresetEditor(db_path=db_copy)
    # New editor should not be marked as modified
    assert editor.is_modified() is False

    editor.preset_name = "My Preset"
    assert editor.is_modified() is True

    editor.mark_saved()
    assert editor.is_modified() is False

    editor.add_section("Warmup")
    assert editor.is_modified() is True
    editor.close()


def test_remove_exercise_and_save(db_with_preset):
    editor = PresetEditor("Test Preset", db_path=db_with_preset)
    editor.remove_exercise(0, 0)
    assert editor.sections[0]["exercises"] == []
    assert editor.is_modified() is True
    editor.save()
    conn = sqlite3.connect(db_with_preset)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM preset_section_exercises")
    count = cur.fetchone()[0]
    conn.close()
    editor.close()
    assert count == 0



